// <copyright file="SharesController.cs" company="slskd Team">
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

// <copyright file="SharesController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Shares.API
{
    using System.Collections.Generic;
    using System.Linq;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.Extensions.Logging;
    using Microsoft.AspNetCore.Mvc;
    using Soulseek;
    using slskd.Core.Security;

    /// <summary>
    ///     Shares.
    /// </summary>
    [ApiController]
    [ApiVersion("0")]
    [Produces("application/json")]
    [Consumes("application/json")]
    [Route("api/v{version:apiVersion}/[controller]")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class SharesController : ControllerBase
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="SharesController"/> class.
        /// </summary>
        /// <param name="shareService"></param>
        /// <param name="logger"></param>
        public SharesController(
            IShareService shareService,
            ILogger<SharesController> logger)
        {
            Shares = shareService;
            Logger = logger;
        }

        private IShareService Shares { get; }
        private ILogger<SharesController> Logger { get; }

        /// <summary>
        ///     Gets the current list of shares.
        /// </summary>
        /// <response code="200">The request completed successfully.</response>
        /// <returns></returns>
        [HttpGet("")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Dictionary<string, IEnumerable<Share>>), 200)]
        public IActionResult List()
        {
            var response = Shares.Hosts.ToDictionary(
                keySelector: host => host.Name,
                elementSelector: host => host.Shares);

            return Ok(response);
        }

        /// <summary>
        ///     Gets the share associated with the specified <see paramref="id"/>.
        /// </summary>
        /// <param name="id">The id of the share.</param>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">The requested share could not be found.</response>
        /// <returns></returns>
        [HttpGet("{id}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Share), 200)]
        [ProducesResponseType(404)]
        public IActionResult Get(string id)
        {
            id = id?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(id))
            {
                return BadRequest("id is required");
            }

            var share = Shares.Hosts.SelectMany(host => host.Shares).FirstOrDefault(share => share.Id == id);

            if (share == default)
            {
                return NotFound();
            }

            return Ok(share);
        }

        /// <summary>
        ///     Returns a list of all shared directories and files.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("contents")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(IEnumerable<Directory>), 200)]
        public async Task<IActionResult> BrowseAll()
        {
            return Ok(await Shares.BrowseAsync());
        }

        /// <summary>
        ///     Gets the contents of the share associated with the specified <see paramref="id"/>.
        /// </summary>
        /// <param name="id">The id of the share.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">The requested share could not be found.</response>
        [HttpGet("{id}/contents")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(IEnumerable<Directory>), 200)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> BrowseShare(string id)
        {
            id = id?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(id))
            {
                return BadRequest("id is required");
            }

            var share = Shares.Hosts.SelectMany(host => host.Shares).FirstOrDefault(share => share.Id == id);

            if (share == default)
            {
                return NotFound();
            }

            var contents = await Shares.BrowseAsync(share);

            return Ok(contents);
        }

        /// <summary>
        ///     Initiates a scan of the configured shares.
        /// </summary>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="409">A share scan is already in progress.</response>
        [HttpPut] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Route("")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        [ProducesResponseType(409)]
        public IActionResult RescanSharesAsync()
        {
            try
            {
                _ = ObserveShareScanAsync(Shares.ScanAsync());
            }
            catch (ShareScanInProgressException)
            {
                return Conflict("A share scan is already in progress.");
            }

            return Ok();
        }

        private async Task ObserveShareScanAsync(Task scanTask)
        {
            try
            {
                await scanTask.ConfigureAwait(false);
            }
            catch (ShareScanInProgressException)
            {
                // The request path reports this synchronously when the scan is already in progress.
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Share rescan failed after it was accepted");
            }
        }

        /// <summary>
        ///     Cancels a share scan, if one is running.
        /// </summary>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="409">A share scan was not in progress.</response>
        [HttpDelete] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
        [Route("")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public IActionResult CancelShareScan()
        {
            if (Shares.TryCancelScan())
            {
                return StatusCode(204);
            }

            return NotFound();
        }
    }
}
