// <copyright file="SearchesController.cs" company="slskd Team">
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

// <copyright file="SearchesController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Search.API
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel.DataAnnotations;
    using System.Threading;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Serilog;
    using slskd.Core.Security;
    using SearchQuery = Soulseek.SearchQuery;
    using SearchScope = Soulseek.SearchScope;

    /// <summary>
    ///     Search.
    /// </summary>
    [ApiController]
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class SearchesController : ControllerBase
    {
        internal const int DefaultListLimit = 500;

        /// <summary>
        ///     Initializes a new instance of the <see cref="SearchesController"/> class.
        /// </summary>
        /// <param name="searchService"></param>
        /// <param name="optionsSnapshot"></param>
        public SearchesController(ISearchService searchService, IOptionsSnapshot<Options> optionsSnapshot)
        {
            Searches = searchService;
            OptionsSnapshot = optionsSnapshot;
        }

        private static SemaphoreSlim SearchRequestLimiter { get; } = new SemaphoreSlim(1, 1);
        private ISearchService Searches { get; }
        private IOptionsSnapshot<Options> OptionsSnapshot { get; }
        private ILogger Log { get; set; } = Serilog.Log.ForContext<SearchesController>();

        /// <summary>
        ///     Performs a search for the specified <paramref name="request"/>.
        /// </summary>
        /// <param name="request">The search request.</param>
        /// <returns></returns>
        /// <response code="200">The search completed successfully.</response>
        /// <response code="400">The specified <paramref name="request"/> was malformed.</response>
        /// <response code="500">The search terminated abnormally.</response>
        [HttpPost("")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        public async Task<IActionResult> Post([FromBody] SearchRequest request)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (request == null)
            {
                return BadRequest("Request is required");
            }

            request.SearchText = request.SearchText?.Trim() ?? string.Empty;
            request.AcquisitionProfile = string.IsNullOrWhiteSpace(request.AcquisitionProfile)
                ? null
                : request.AcquisitionProfile.Trim();
            request.Providers = request.Providers?
                .Select(provider => provider?.Trim() ?? string.Empty)
                .Where(provider => !string.IsNullOrWhiteSpace(provider))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();

            foreach (var validationResult in request.Validate(new ValidationContext(request)))
            {
                foreach (var memberName in validationResult.MemberNames)
                {
                    if (!ModelState.TryGetValue(memberName, out var entry) || entry.Errors.Count == 0)
                    {
                        ModelState.AddModelError(memberName, validationResult.ErrorMessage ?? "Invalid value");
                    }
                }
            }

            if (!ModelState.IsValid)
            {
                return BadRequest(ModelState.GetReadableString());
            }

            if (!SearchRequestLimiter.Wait(0))
            {
                return StatusCode(429, "Only one concurrent operation is permitted. Wait until the previous request completes");
            }

            try
            {
                var id = request.Id ?? Guid.NewGuid();

                Search search;

                try
                {
                    search = await Searches.StartAsync(
                        id,
                        SearchQuery.FromText(request.SearchText),
                        SearchScope.Network,
                        request.ToSearchOptions(),
                        request.Providers);
                    return Ok(search);
                }
                catch (ArgumentException ex)
                {
                    Log.Error(ex, "Failed to execute search {Search}", request);
                    return BadRequest("Invalid search request");
                }
                catch (Soulseek.DuplicateTokenException ex)
                {
                    Log.Error(ex, "Failed to execute search {Search}", request);
                    return Conflict("A search with this ID is already in progress");
                }
                catch (InvalidOperationException ex)
                {
                    Log.Error(ex, "Failed to execute search {Search}", request);
                    return Conflict("Search could not be started");
                }
                catch (Exception ex)
                {
                    Log.Error(ex, "Failed to execute search {Search}", request);
                    return StatusCode(500, "Failed to execute search");
                }
            }
            finally
            {
                SearchRequestLimiter.Release();
            }
        }

        /// <summary>
        ///     Gets the state of the search corresponding to the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique id of the search.</param>
        /// <param name="includeResponses">A value indicating whether to include search responses in the response.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">A matching search was not found.</response>
        [HttpGet("{id}")]
        [Authorize(Policy = AuthPolicy.Any)]
        public async Task<IActionResult> GetById([FromRoute] Guid id, [FromQuery] bool includeResponses = false)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var search = await Searches.FindAsync(search => search.Id == id, includeResponses);

            if (search == default)
            {
                return NotFound();
            }

            return Ok(search);
        }

        /// <summary>
        ///     Gets the state of the search corresponding to the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique id of the search.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">A matching search was not found.</response>
        [HttpGet("{id}/responses")]
        [Authorize(Policy = AuthPolicy.Any)]
        public async Task<IActionResult> GetResponsesById([FromRoute] Guid id)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var search = await Searches.FindAsync(search => search.Id == id, includeResponses: true);

            if (search == default)
            {
                return NotFound();
            }

            return Ok(search.Responses);
        }

        /// <summary>
        ///     Gets the list of active and completed searches.
        /// </summary>
        /// <param name="limit">Maximum number of searches to return (0 uses the default list cap).</param>
        /// <param name="offset">Number of searches to skip (for pagination).</param>
        /// <param name="source">Optional source filter (e.g. "manual", "wishlist", "auto-replace").</param>
        /// <param name="afterStartedAt">Optional start time for a stable descending continuation.</param>
        /// <param name="afterId">ID tie-breaker returned with the previous page's last row.</param>
        /// <returns>The list of searches.</returns>
        [HttpGet("")]
        [Authorize(Policy = AuthPolicy.Any)]
        public async Task<IActionResult> GetAll(
            [FromQuery] int limit = 0,
            [FromQuery] int offset = 0,
            [FromQuery] string? source = null,
            [FromQuery] DateTimeOffset? afterStartedAt = null,
            [FromQuery] Guid? afterId = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (limit < 0 || offset < 0 || afterStartedAt.HasValue != afterId.HasValue ||
                ((afterStartedAt.HasValue || afterId.HasValue) && offset != 0))
            {
                return BadRequest();
            }

            var effectiveLimit = limit == 0 ? DefaultListLimit : limit;
            var searches = await Searches.ListAsync(
                limit: effectiveLimit,
                offset: offset,
                source: source,
                afterStartedAt: afterStartedAt?.UtcDateTime,
                afterId: afterId);
            return Ok(searches);
        }

        /// <summary>
        ///     Stops the search corresponding to the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique id of the search.</param>
        /// <response code="200">The search was stopped.</response>
        /// <response code="304">The search was not in progress.</response>
        /// <returns></returns>
        [HttpPut("{id}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(200)]
        [ProducesResponseType(304)]
        public async Task<IActionResult> Cancel([FromRoute] Guid id)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var search = await Searches.FindAsync(search => search.Id == id);

            if (search == default)
            {
                return NotFound();
            }

            Searches.TryCancel(id);
            return Ok();
        }

        /// <summary>
        ///     Deletes the search corresponding to the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique id of the search.</param>
        /// <response code="204">The search was deleted.</response>
        /// <response code="404">A search with the specified id could not be found.</response>
        /// <returns></returns>
        [HttpDelete("{id}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> Delete([FromRoute] Guid id)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var search = await Searches.FindAsync(search => search.Id == id, includeResponses: false);

            if (search == default)
            {
                return NotFound();
            }

            await Searches.DeleteAsync(search);
            return NoContent();
        }

        /// <summary>
        ///     Deletes all completed searches.
        /// </summary>
        /// <returns>The number of deleted searches.</returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpDelete]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(int), 200)]
        public async Task<IActionResult> DeleteAll()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var count = await Searches.DeleteAllAsync();
            return Ok(new { deleted = count });
        }

        /// <summary>
        ///     Deletes searches based on retention policies.
        ///     When no parameters are provided, uses the configured retention settings.
        /// </summary>
        /// <param name="maxAgeDays">Override: delete searches older than this many days (0 = no age limit).</param>
        /// <param name="maxCount">Override: keep at most this many searches (0 = no count limit).</param>
        /// <returns>The number of deleted searches.</returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpPost("cleanup")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(object), 200)]
        public async Task<IActionResult> Cleanup([FromQuery] int? maxAgeDays = null, [FromQuery] int? maxCount = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var config = OptionsSnapshot.Value.Filters.SearchRetention;
            var effectiveMaxAge = maxAgeDays ?? config.MaxAgeDays;
            var effectiveMaxCount = maxCount ?? config.MaxCount;

            var count = await Searches.CleanupAsync(effectiveMaxAge, effectiveMaxCount);
            return Ok(new
            {
                deleted = count,
                appliedMaxAgeDays = effectiveMaxAge,
                appliedMaxCount = effectiveMaxCount,
            });
        }
    }
}
