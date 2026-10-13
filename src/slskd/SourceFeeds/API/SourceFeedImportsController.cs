// <copyright file="SourceFeedImportsController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.SourceFeeds.API;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using slskd.Core.Security;

[ApiController]
[Route("api/source-feed-imports")]
[Route("api/v{version:apiVersion}/source-feed-imports")]
[ApiVersion("0")]
[Produces("application/json")]
[ValidateCsrfForCookiesOnly]
public sealed class SourceFeedImportsController : ControllerBase
{
    public SourceFeedImportsController(ISourceFeedImportService sourceFeedImportService)
    {
        SourceFeedImportService = sourceFeedImportService;
    }

    private ISourceFeedImportService SourceFeedImportService { get; }

    private BadRequestObjectResult BadRequestWithCode(string code, string message)
    {
        Response.Headers["X-Slskd-Error-Code"] = code;
        return BadRequest(message);
    }

    [HttpPost("preview")]
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
    [ProducesResponseType(typeof(SourceFeedImportResult), 200)]
    [ProducesResponseType(400)]
    public async Task<IActionResult> Preview(
        [FromBody] SourceFeedImportRequest request,
        CancellationToken cancellationToken = default)
    {
        if (request == null || string.IsNullOrWhiteSpace(request.SourceText))
        {
            return BadRequestWithCode("source-feed-import.source-text-required", "SourceText is required");
        }

        if (request.Limit <= 0)
        {
            return BadRequestWithCode("source-feed-import.limit-must-be-positive", "Limit must be greater than 0");
        }

        var result = await SourceFeedImportService.PreviewAsync(request, cancellationToken).ConfigureAwait(false);
        return Ok(result);
    }

    [HttpGet("history")]
    [Authorize(Policy = AuthPolicy.Any)]
    [ProducesResponseType(typeof(IReadOnlyList<SourceFeedImportHistoryEntry>), 200)]
    public async Task<IActionResult> GetHistory(
        [FromQuery] int limit = 50,
        CancellationToken cancellationToken = default)
    {
        var history = await SourceFeedImportService.GetHistoryAsync(limit, cancellationToken).ConfigureAwait(false);
        return Ok(history);
    }

    [HttpGet("history/{importId}")]
    [Authorize(Policy = AuthPolicy.Any)]
    [ProducesResponseType(typeof(SourceFeedImportHistoryEntry), 200)]
    [ProducesResponseType(404)]
    public async Task<IActionResult> GetHistoryEntry(
        [FromRoute] string importId,
        CancellationToken cancellationToken = default)
    {
        var entry = await SourceFeedImportService.GetHistoryEntryAsync(importId, cancellationToken).ConfigureAwait(false);
        return entry == null ? NotFound() : Ok(entry);
    }
}
