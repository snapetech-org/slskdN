// <copyright file="ApplicationController.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="ApplicationController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Core.API
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.Linq;
    using System.Net;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.Extensions.Hosting;
    using Serilog;
    using slskd.Core.Security;

    /// <summary>
    ///     Application.
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class ApplicationController : ControllerBase
    {
        public ApplicationController(
            IHostApplicationLifetime lifetime,
            IApplication application,
            IOptionsMonitor<Options> optionsMonitor,
            IStateMonitor<State> applicationStateMonitor)
        {
            Lifetime = lifetime;
            Application = application;
            OptionsMonitor = optionsMonitor;
            ApplicationStateMonitor = applicationStateMonitor;
        }

        private IApplication Application { get; }
        private IStateMonitor<State> ApplicationStateMonitor { get; }
        private IOptionsMonitor<Options> OptionsMonitor { get; }
        private IHostApplicationLifetime Lifetime { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<ApplicationController>();

        /// <summary>
        ///     Gets the current state of the application.
        /// </summary>
        /// <returns></returns>
        [HttpGet]
        [Authorize(Policy = AuthPolicy.Any)]
        public IActionResult State()
        {
            return Ok(ApplicationStateMonitor.CurrentValue);
        }

        /// <summary>
        ///     Stops the application.
        /// </summary>
        /// <returns></returns>
        [HttpDelete] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Authorize(Policy = AuthPolicy.JwtOnly, Roles = AuthRole.AdministratorOnly)]
        public IActionResult Shutdown()
        {
            Program.MasterCancellationTokenSource.Cancel();
            Lifetime.StopApplication();

            _ = TaskObservation.Observe(
                Task.Run(async () =>
                {
                    await Task.Delay(500);
                    Environment.Exit(0);
                }),
                ex => Log.Warning(ex, "[ApplicationController] Failed to observe shutdown task"));

            return NoContent();
        }

        /// <summary>
        ///     Restarts the application.
        /// </summary>
        /// <returns></returns>
        [HttpPut] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Authorize(Policy = AuthPolicy.JwtOnly, Roles = AuthRole.AdministratorOnly)]
        public IActionResult Restart()
        {
            Program.MasterCancellationTokenSource.Cancel();
            var currentExecutable = Process.GetCurrentProcess().MainModule?.FileName;
            if (!string.IsNullOrEmpty(currentExecutable))
            {
                Process.Start(currentExecutable, GetRestartArguments(Environment.GetCommandLineArgs()));
            }

            Lifetime.StopApplication();

            return NoContent();
        }

        internal static IEnumerable<string> GetRestartArguments(IEnumerable<string> commandLineArgs)
        {
            return commandLineArgs.Skip(1);
        }

        /// <summary>
        ///     Gets the current application version.
        /// </summary>
        /// <returns></returns>
        [HttpGet("version")]
        [Authorize(Policy = AuthPolicy.Any)]
        public IActionResult GetVersion()
        {
            return Ok(Program.SemanticVersion);
        }

        /// <summary>
        ///     Gets public build and update-check metadata for footer display.
        /// </summary>
        /// <returns></returns>
        [HttpGet("build")]
        [AllowAnonymous]
        public IActionResult GetBuild([FromQuery] bool checkForUpdates = false)
        {
            _ = checkForUpdates;
            return Ok(ApplicationStateMonitor.CurrentValue.Version);
        }

        /// <summary>
        ///     Checks for updates.
        /// </summary>
        /// <returns></returns>
        [HttpGet("version/latest")]
        [Authorize(Policy = AuthPolicy.Any)]
        public async Task<IActionResult> CheckVersion([FromQuery] bool forceCheck = false)
        {
            if (forceCheck)
            {
                await Application.CheckVersionAsync();
            }

            return Ok(ApplicationStateMonitor.CurrentValue.Version);
        }

        /// <summary>
        ///     Forces garbage collection.
        /// </summary>
        /// <returns></returns>
        [HttpPost("gc")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        public IActionResult CollectGarbage()
        {
            Application.CollectGarbage();

            return Ok();
        }

        /// <summary>
        ///     Creates a full memory dump. PR-06: requires Diagnostics.AllowMemoryDump; admin-only; loopback-only unless AllowRemoteDump.
        /// </summary>
        [HttpPost("dump")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        public async Task<IActionResult> DumpMemory()
        {
            var opts = OptionsMonitor.CurrentValue.Diagnostics;
            if (opts?.AllowMemoryDump != true)
            {
                return NotFound();
            }

            if (opts.AllowRemoteDump != true)
            {
                var ip = HttpContext.Connection.RemoteIpAddress;
                if (ip == null || !IPAddress.IsLoopback(ip))
                {
                    return Forbid();
                }
            }

            var dumper = new Dumper();
            var (ok, error, path) = await dumper.TryCreateDumpAsync(HttpContext.RequestAborted).ConfigureAwait(false);

            if (!ok)
            {
                if (error != null && error.Contains("Insufficient", StringComparison.OrdinalIgnoreCase))
                {
                    Log.Warning("Dump failed due to insufficient space or resources: {Error}", error);
                    return StatusCode(507, "Insufficient space to create memory dump.");
                }

                Log.Warning("Dump failed: {Error}", error);

                // PR-06: when DiagnosticsClient/WriteDump unavailable (e.g. older runtime), return 501 with instructions
                var e = error ?? string.Empty;
                var isUnsupported = e.Contains("not supported", StringComparison.OrdinalIgnoreCase) ||
                    e.Contains("platform", StringComparison.OrdinalIgnoreCase) ||
                    e.Contains("Unable to load", StringComparison.OrdinalIgnoreCase) ||
                    e.Contains("DiagnosticsClient", StringComparison.OrdinalIgnoreCase) ||
                    e.Contains("does not support", StringComparison.OrdinalIgnoreCase);
                if (isUnsupported)
                {
                    return StatusCode(501, "Memory dump creation is not supported on this runtime. Use a supported .NET runtime or install dotnet-dump and capture manually (see https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-dump).");
                }

                // PR-06: any other dump creation failure → 501
                return StatusCode(501, "Memory dump creation failed.");
            }

            Response.OnCompleted(() =>
            {
                try
                {
                    System.IO.File.Delete(path!);
                }
                catch (Exception ex)
                {
                    Log.Warning(ex, "Failed to delete temporary memory dump {Path}", path);
                }

                return Task.CompletedTask;
            });

            return PhysicalFile(path!, "application/octet-stream", "slskd.dmp");
        }

        [HttpPost("loopback")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        public IActionResult Loopback([FromBody] object body)
        {
            if (body == null)
            {
                return BadRequest("Body is required");
            }

            Log.Information("Loopback POST: {Body}", body);
            return Ok();
        }
    }
}
