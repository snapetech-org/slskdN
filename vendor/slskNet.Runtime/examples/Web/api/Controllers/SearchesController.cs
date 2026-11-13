namespace WebAPI.Controllers
{
    using Asp.Versioning;
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Linq;
    using System.Threading.Tasks;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Soulseek;
    using WebAPI.DTO;
    using WebAPI.Trackers;

    /// <summary>
    ///     Search
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("1")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    public class SearchesController : ControllerBase
    {
        private ISoulseekClient Client { get; }
        private ISearchTracker Tracker { get; }

        /// <summary>
        ///     Initializes a new instance of the <see cref="SearchesController"/> class.
        /// </summary>
        /// <param name="client"></param>
        /// <param name="tracker"></param>
        public SearchesController(ISoulseekClient client, ISearchTracker tracker)
        {
            Client = client;
            Tracker = tracker;
        }

        /// <summary>
        ///     Performs a search for the specified <paramref name="request"/>.
        /// </summary>
        /// <param name="request">The search request.</param>
        /// <returns></returns>
        /// <response code="200">The search completed successfully.</response>
        /// <response code="400">The specified <paramref name="request"/> was malformed.</response>
        /// <response code="500">The search terminated abnormally.</response>
        [HttpPost("")]
        [Authorize]
        [ProducesResponseType(typeof(IEnumerable<SearchResponse>), 200)]
        [ProducesResponseType(400)]
        [ProducesResponseType(typeof(string), 500)]
        public async Task<IActionResult> Post([FromBody] SearchRequest request)
        {
            if (!TryNormalizeSearchRequest(request, out var searchText, out var badRequest))
            {
                return badRequest;
            }

            var id = request.Id ?? Guid.NewGuid();

            var options = request.ToSearchOptions(
                responseReceived: (e) => Tracker.AddOrUpdate(id, e.Search),
                stateChanged: (e) => Tracker.AddOrUpdate(id, e.Search));

            var results = new ConcurrentBag<SearchResponse>();

            try
            {
                await Client.SearchAsync(SearchQuery.FromText(searchText), (r) => results.Add(r), SearchScope.Network, request.Token, options);
                return Ok(results);
            }
            catch (Exception ex)
            {
                return StatusCode(500, $"Search terminated abnormally: {ex.Message}");
            }
            finally
            {
                results = null;
                Tracker.TryRemove(id);
            }
        }

        /// <summary>
        ///     Performs a search for the specified <paramref name="request"/> from the specified <paramref name="username"/>.
        /// </summary>
        /// <param name="request">The search request.</param>
        /// <param name="username">The username to search.</param>
        /// <returns></returns>
        /// <response code="200">The search completed successfully.</response>
        /// <response code="400">The specified <paramref name="request"/> was malformed.</response>
        /// <response code="500">The search terminated abnormally.</response>
        [HttpPost("users/{username}")]
        [Authorize]
        [ProducesResponseType(typeof(IEnumerable<SearchResponse>), 200)]
        [ProducesResponseType(400)]
        [ProducesResponseType(typeof(string), 500)]
        public async Task<IActionResult> PostUsers([FromBody] SearchRequest request, [FromRoute] string username)
        {
            if (string.IsNullOrWhiteSpace(username))
            {
                return BadRequest("Username is required");
            }

            if (!TryNormalizeSearchRequest(request, out var searchText, out var badRequest))
            {
                return badRequest;
            }

            var id = request.Id ?? Guid.NewGuid();

            var options = request.ToSearchOptions(
                responseReceived: (e) => Tracker.AddOrUpdate(id, e.Search),
                stateChanged: (e) => Tracker.AddOrUpdate(id, e.Search));

            var results = new ConcurrentBag<SearchResponse>();

            try
            {
                await Client.SearchAsync(SearchQuery.FromText(searchText), (r) => results.Add(r), SearchScope.User(username), request.Token, options);
                return Ok(results);
            }
            catch (Exception ex)
            {
                return StatusCode(500, $"Search terminated abnormally: {ex.Message}");
            }
            finally
            {
                results = null;
                Tracker.TryRemove(id);
            }
        }

        /// <summary>
        ///     Gets the state of the search corresponding to the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique id of the search.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">A matching search was not found.</response>
        [HttpGet("{id}")]
        [Authorize]
        [ProducesResponseType(typeof(Search), 200)]
        [ProducesResponseType(404)]
        public IActionResult GetById([FromRoute] Guid id)
        {
            Tracker.Searches.TryGetValue(id, out var search);

            if (search == default)
            {
                return NotFound();
            }

            return Ok(search);
        }

        private bool TryNormalizeSearchRequest(SearchRequest request, out string searchText, out IActionResult badRequest)
        {
            searchText = null;
            badRequest = null;

            if (request == null)
            {
                badRequest = BadRequest("Request body is required");
                return false;
            }

            if (string.IsNullOrWhiteSpace(request.SearchText))
            {
                badRequest = BadRequest("Search text is required");
                return false;
            }

            searchText = string.Join(' ', request.SearchText.Split(' ').Where(term => term.Length > 1));

            if (string.IsNullOrWhiteSpace(searchText))
            {
                badRequest = BadRequest("Search text must contain at least one term longer than one character");
                return false;
            }

            if (request.SearchTimeout.HasValue && request.SearchTimeout.Value < 1)
            {
                badRequest = BadRequest("Search timeout must be greater than or equal to one");
                return false;
            }

            if (request.ResponseLimit.HasValue && request.ResponseLimit.Value < 1)
            {
                badRequest = BadRequest("Response limit must be greater than or equal to one");
                return false;
            }

            if (request.FileLimit.HasValue && request.FileLimit.Value < 1)
            {
                badRequest = BadRequest("File limit must be greater than or equal to one");
                return false;
            }

            if (request.MinimumResponseFileCount.HasValue && request.MinimumResponseFileCount.Value < 0)
            {
                badRequest = BadRequest("Minimum response file count must be greater than or equal to zero");
                return false;
            }

            if (request.MaximumPeerQueueLength.HasValue && request.MaximumPeerQueueLength.Value < 0)
            {
                badRequest = BadRequest("Maximum peer queue length must be greater than or equal to zero");
                return false;
            }

            if (request.MinimumPeerUploadSpeed.HasValue && request.MinimumPeerUploadSpeed.Value < 0)
            {
                badRequest = BadRequest("Minimum peer upload speed must be greater than or equal to zero");
                return false;
            }

            return true;
        }
    }
}
