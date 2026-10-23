// <copyright file="OptionsController.cs" company="slskd Team">
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

// <copyright file="OptionsController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Core.API
{
    using System;
    using System.IO;
    using System.Linq;
    using System.Reflection;
    using System.Text.RegularExpressions;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.Extensions.Configuration;
    using Serilog;
    using slskd.Core.Security;
    using slskd.Validation;
    using YamlDotNet.RepresentationModel;
    using IOFile = System.IO.File;

    /// <summary>
    ///     Options.
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class OptionsController : ControllerBase
    {
        private const int MaxYamlValidationBytes = 1024 * 1024;

        public OptionsController(
            OptionsAtStartup optionsAtStartup,
            IOptionsSnapshot<Options> optionsSnapshot,
            IStateMutator<State> stateMutator)
        {
            OptionsAtStartup = optionsAtStartup;
            OptionsSnapshot = optionsSnapshot;
            StateMutator = stateMutator;
        }

        private IOptionsSnapshot<Options> OptionsSnapshot { get; }
        private OptionsAtStartup OptionsAtStartup { get; }
        private IStateMutator<State> StateMutator { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<OptionsController>();

        /// <summary>
        ///     Gets the current application options.
        /// </summary>
        /// <returns></returns>
        [HttpGet]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Options), 200)]
        public IActionResult Current()
        {
            return Ok(OptionsSnapshot.Value.Redact());
        }

        /// <summary>
        ///     Gets the application options provided at startup.
        /// </summary>
        /// <returns></returns>
        /// <summary>
        ///     Overlay the application options with new values.
        /// </summary>
        /// <param name="overlay">The overlay to apply.</param>
        /// <returns></returns>
        [HttpPatch] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        [ProducesResponseType(typeof(OptionsOverlay), 200)]
        public IActionResult ApplyOverlay([FromBody] OptionsOverlay overlay)
        {
            if (!OptionsSnapshot.Value.RemoteConfiguration)
            {
                Log.Warning("Blocked options overlay application; remote configuration is disabled");
                return Forbid();
            }

            if (overlay is null)
            {
                return BadRequest("Options overlay is required");
            }

            if (!overlay.TryValidate(out var result))
            {
                Log.Warning("Options patch validation failed: {Message}", result.GetResultString());
                return BadRequest("Invalid options overlay");
            }

            try
            {
                Program.ApplyConfigurationOverlay(overlay);
                return Ok(Program.ConfigurationOverlay?.Redact());
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to apply options patch");
                return StatusCode(500, "Failed to apply options patch");
            }
        }

        [HttpGet]
        [Route("startup")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Options), 200)]
        public IActionResult Startup()
        {
            return Ok(OptionsAtStartup.Redact());
        }

        /// <summary>
        ///     Gets the debug view of the current application options.
        /// </summary>
        /// <returns></returns>
        [HttpGet]
        [Route("debug")]
        [Authorize(Policy = AuthPolicy.JwtOnly, Roles = AuthRole.AdministratorOnly)]
        [ProducesResponseType(typeof(string), 200)]
        public IActionResult Debug()
        {
            if (!OptionsAtStartup.Debug || !OptionsSnapshot.Value.RemoteConfiguration)
            {
                return Forbid();
            }

            // retrieve the IConfigurationRoot instance with reflection to avoid
            // exposing it as a public member of Program.
            var property = typeof(Program).GetProperty("Configuration", BindingFlags.NonPublic | BindingFlags.Static);
            var configurationRoot = property?.GetValue(null, null) as IConfigurationRoot;
            if (configurationRoot is null)
            {
                return StatusCode(500, "Configuration root is unavailable");
            }

            return Ok(RedactConfigurationDebugView(configurationRoot.GetDebugView()));
        }

        [HttpGet]
        [Authorize(Policy = AuthPolicy.JwtOnly, Roles = AuthRole.AdministratorOnly)]
        [Route("yaml/location")]
        public IActionResult GetYamlFileLocation()
        {
            if (!OptionsSnapshot.Value.RemoteConfiguration)
            {
                return Forbid();
            }

            return Ok(Program.ConfigurationFile);
        }

        [HttpGet]
        [Authorize(Policy = AuthPolicy.JwtOnly, Roles = AuthRole.AdministratorOnly)]
        [Route("yaml")]
        public IActionResult GetYamlFile()
        {
            if (!OptionsSnapshot.Value.RemoteConfiguration)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(Program.ConfigurationFile) || !IOFile.Exists(Program.ConfigurationFile))
            {
                return NotFound();
            }

            var yaml = IOFile.ReadAllText(Program.ConfigurationFile);
            return Ok(yaml);
        }

        [HttpPut] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Authorize(Policy = AuthPolicy.JwtOnly, Roles = AuthRole.AdministratorOnly)]
        [Route("yaml")]
        public IActionResult UpdateYamlFile([FromBody] string yaml)
        {
            if (!OptionsSnapshot.Value.RemoteConfiguration)
            {
                return Forbid();
            }

            if (yaml is null)
            {
                return BadRequest("YAML is required");
            }

            if (System.Text.Encoding.UTF8.GetByteCount(yaml) > MaxYamlValidationBytes)
            {
                return StatusCode(413, "YAML is too large");
            }

            if (!TryValidateYaml(yaml, out var error, out var detail))
            {
                Log.Error("Failed to validate YAML configuration: {Error}", error);
                return BadRequest(string.IsNullOrWhiteSpace(detail) ? error : $"{error}: {detail}");
            }

            try
            {
                IOFile.Copy(Program.ConfigurationFile, $"{Program.ConfigurationFile}.bak", overwrite: true);

                var tempFile = $"{Program.ConfigurationFile}.{Guid.NewGuid():N}.tmp";
                IOFile.WriteAllText(tempFile, yaml);
                IOFile.Move(tempFile, Program.ConfigurationFile, overwrite: true);

                if (OptionsSnapshot.Value.Flags.NoConfigWatch)
                {
                    Log.Information("Configuration watch is disabled; restart required for changes to take effect");
                    StateMutator.SetValue(state => state with { PendingRestart = true });
                }

                return Ok();
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to update configuration file");
                return StatusCode(500, "Failed to update configuration file");
            }
        }

        [HttpPost] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [Route("yaml/validate")]
        public IActionResult ValidateYamlFile([FromBody] string yaml)
        {
            if (!OptionsSnapshot.Value.RemoteConfiguration)
            {
                return Forbid();
            }

            if (yaml is null)
            {
                return BadRequest("YAML is required");
            }

            if (System.Text.Encoding.UTF8.GetByteCount(yaml) > MaxYamlValidationBytes)
            {
                return StatusCode(413, "YAML is too large");
            }

            if (!TryValidateYaml(yaml, out var error))
            {
                return Ok(error);
            }

            return Ok();
        }

        private bool TryValidateYaml(string yaml, out string error) => TryValidateYaml(yaml, out error, out _);

        /// <summary>
        ///     Validates the supplied YAML, producing both a generic, safe-to-expose-to-any-caller
        ///     <paramref name="error"/> and a <paramref name="detail"/> message with the specific
        ///     reason validation failed. <paramref name="detail"/> is only surfaced to callers that
        ///     require Administrator privileges (i.e. <see cref="UpdateYamlFile"/>), since it can
        ///     reveal details about the server's configuration/filesystem; lower-privileged callers
        ///     (e.g. <see cref="ValidateYamlFile"/>) must continue to use <paramref name="error"/> only.
        /// </summary>
        private bool TryValidateYaml(string yaml, out string error, out string detail)
        {
            error = string.Empty;
            detail = string.Empty;

            try
            {
                var options = NormalizeCompatibilityYaml(yaml).FromYaml<Options>();

                if (options is null)
                {
                    return true;
                }

                if (!options.TryValidate(out var result))
                {
                    detail = result.GetResultString();
                    Log.Warning("Configuration validation failed: {Message}", detail);
                    error = "Invalid YAML configuration";
                    return false;
                }
            }
            catch (Exception ex)
            {
                Log.Warning(ex, "Configuration validation failed");
                error = "Invalid YAML configuration";
                detail = ex.Message;

                return false;
            }

            return true;
        }

        private static string NormalizeCompatibilityYaml(string yaml)
        {
            var stream = new YamlStream();

            using (var reader = new StringReader(yaml))
            {
                stream.Load(reader);
            }

            if (stream.Documents.Count == 0 || stream.Documents[0].RootNode is not YamlMappingNode root)
            {
                return yaml;
            }

            var changed = false;
            changed |= NormalizeTopLevelAlias(root, "global", "transfers");
            changed |= NormalizeTopLevelAlias(root, "integration", "integrations");
            changed |= NormalizeLegacyShares(root);
            changed |= NormalizeNestedGlobalLimits(root);
            changed |= NormalizeTransfersGroups(root);

            if (!changed)
            {
                return yaml;
            }

            using var writer = new StringWriter();
            stream.Save(writer, assignAnchors: false);
            return writer.ToString();
        }

        private static bool NormalizeTopLevelAlias(YamlMappingNode root, string legacyName, string canonicalName)
        {
            if (!TryGetMappingChild(root, legacyName, out var legacyKey, out var legacyValue))
            {
                return false;
            }

            if (TryGetMappingChild(root, canonicalName, out _, out var canonicalValue))
            {
                if (canonicalValue is YamlMappingNode canonicalMap && legacyValue is YamlMappingNode legacyMap)
                {
                    MergeMissingYamlChildren(canonicalMap, legacyMap);
                }

                root.Children.Remove(legacyKey);
                return true;
            }

            root.Children.Remove(legacyKey);
            root.Children.Add(new YamlScalarNode(canonicalName), legacyValue);
            return true;
        }

        private static bool NormalizeLegacyShares(YamlMappingNode root)
        {
            if (!TryGetMappingChild(root, "shares", out var sharesKey, out var sharesValue) ||
                sharesValue is not YamlSequenceNode)
            {
                return false;
            }

            var shares = new YamlMappingNode();
            shares.Children.Add(new YamlScalarNode("directories"), sharesValue);
            root.Children.Remove(sharesKey);
            root.Children.Add(sharesKey, shares);
            return true;
        }

        private static bool NormalizeNestedGlobalLimits(YamlMappingNode root)
        {
            if (!TryGetMappingChild(root, "transfers", out _, out var transfersNode) ||
                transfersNode is not YamlMappingNode transfers ||
                !TryGetMappingChild(transfers, "upload", out _, out var uploadNode) ||
                uploadNode is not YamlMappingNode upload ||
                !TryGetMappingChild(upload, "limits", out var uploadLimitsKey, out var uploadLimitsNode))
            {
                return false;
            }

            if (TryGetMappingChild(transfers, "limits", out _, out var limitsNode) &&
                limitsNode is YamlMappingNode limits &&
                uploadLimitsNode is YamlMappingNode uploadLimits)
            {
                MergeMissingYamlChildren(limits, uploadLimits);
            }
            else if (!TryGetMappingChild(transfers, "limits", out _, out _))
            {
                transfers.Children.Add(new YamlScalarNode("limits"), uploadLimitsNode);
            }

            upload.Children.Remove(uploadLimitsKey);
            return true;
        }

        private static bool NormalizeTransfersGroups(YamlMappingNode root)
        {
            if (!TryGetMappingChild(root, "transfers", out _, out var transfersNode) ||
                transfersNode is not YamlMappingNode transfers ||
                !TryGetMappingChild(transfers, "groups", out var transfersGroupsKey, out var transfersGroupsNode))
            {
                return false;
            }

            transfers.Children.Remove(transfersGroupsKey);

            if (TryGetMappingChild(root, "groups", out _, out var rootGroupsNode))
            {
                if (rootGroupsNode is YamlMappingNode rootGroups && transfersGroupsNode is YamlMappingNode transfersGroups)
                {
                    MergeMissingYamlChildren(rootGroups, transfersGroups);
                }
            }
            else
            {
                root.Children.Add(new YamlScalarNode("groups"), transfersGroupsNode);
            }

            return true;
        }

        private static void MergeMissingYamlChildren(YamlMappingNode target, YamlMappingNode source)
        {
            foreach (var child in source.Children.ToArray())
            {
                var name = (child.Key as YamlScalarNode)?.Value;
                if (name is not null && TryGetMappingChild(target, name, out _, out var existing))
                {
                    if (existing is YamlMappingNode existingMap && child.Value is YamlMappingNode childMap)
                    {
                        MergeMissingYamlChildren(existingMap, childMap);
                    }

                    continue;
                }

                target.Children.Add(child.Key, child.Value);
            }
        }

        private static bool TryGetMappingChild(
            YamlMappingNode mapping,
            string name,
            out YamlNode key,
            out YamlNode value)
        {
            var normalizedName = NormalizeYamlKey(name);

            foreach (var child in mapping.Children)
            {
                if (child.Key is YamlScalarNode scalar && NormalizeYamlKey(scalar.Value) == normalizedName)
                {
                    key = child.Key;
                    value = child.Value;
                    return true;
                }
            }

            key = null!;
            value = null!;
            return false;
        }

        private static string NormalizeYamlKey(string? value)
            => (value ?? string.Empty).Replace("_", string.Empty).Replace("-", string.Empty).ToLowerInvariant();

        private static string RedactConfigurationDebugView(string debugView)
        {
            return Regex.Replace(
                debugView ?? string.Empty,
                @"(?im)^(\s*[^=\r\n]*(?:password|passwd|pwd|secret|token|apikey|api_key|key)\s*=\s*).*$",
                "$1*****");
        }
    }
}
