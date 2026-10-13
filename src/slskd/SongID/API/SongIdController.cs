// <copyright file="SongIdController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.SongID.API;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.ComponentModel.DataAnnotations;
using slskd.Authentication;
using slskd.Core.Features;
using slskd.Core.Security;

[ApiController]
[Route("api/v{version:apiVersion}/songid")]
[ApiVersion("0")]
[Produces("application/json")]
[Consumes("application/json")]
[Authorize(Policy = AuthPolicy.Any)]
[ValidateCsrfForCookiesOnly]
[FeatureGate(FeatureId.SongId)]
public sealed class SongIdController : ControllerBase
{
    private readonly ISongIdService _songIdService;
    private readonly ISongIdCapabilityReporter _capabilityReporter;

    public SongIdController(ISongIdService songIdService, ISongIdCapabilityReporter capabilityReporter)
    {
        _songIdService = songIdService;
        _capabilityReporter = capabilityReporter;
    }

    private BadRequestObjectResult BadRequestWithCode(string code, string message)
    {
        Response.Headers["X-Slskd-Error-Code"] = code;
        return BadRequest(message);
    }

    [HttpGet("capabilities")]
    [ProducesResponseType(typeof(IReadOnlyList<SongIdCapability>), 200)]
    public async Task<IActionResult> GetCapabilities(CancellationToken cancellationToken)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        var capabilities = await _capabilityReporter.GetCapabilitiesAsync(cancellationToken).ConfigureAwait(false);
        return Ok(capabilities);
    }

    [HttpPost("runs")]
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
    public async Task<IActionResult> CreateRun([FromBody, Required] SongIdRunRequest request, CancellationToken cancellationToken)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        if (request == null)
        {
            return BadRequestWithCode("songid.source-required", "SongID source is required.");
        }

        request.Source = request.Source?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(request.Source))
        {
            return BadRequestWithCode("songid.source-required", "SongID source is required.");
        }

        try
        {
            var run = await _songIdService.QueueAnalyzeAsync(request.Source, cancellationToken).ConfigureAwait(false);
            return Accepted(run);
        }
        catch (ArgumentException)
        {
            return BadRequestWithCode("songid.request-invalid", "SongID request is invalid.");
        }
        catch (InvalidOperationException)
        {
            return BadRequestWithCode("songid.analysis-queue-failed", "SongID analysis could not be queued.");
        }
    }

    [HttpGet("runs")]
    public IActionResult ListRuns([FromQuery] int limit = 10)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        limit = limit <= 0 ? 10 : limit;
        return Ok(_songIdService.List(limit));
    }

    [HttpGet("runs/queue")]
    [ProducesResponseType(typeof(SongIdQueueSummary), 200)]
    public IActionResult GetQueueSummary([FromQuery] int activeLimit = 25)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        activeLimit = activeLimit <= 0 ? 25 : activeLimit;
        return Ok(_songIdService.GetQueueSummary(activeLimit));
    }

    [HttpGet("runs/{id:guid}")]
    public IActionResult GetRun(Guid id)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        var run = _songIdService.Get(id);
        return run == null ? NotFound() : Ok(run);
    }

    [HttpGet("runs/{id:guid}/evidence-package")]
    [ProducesResponseType(typeof(SongIdRunEvidencePackage), 200)]
    [ProducesResponseType(404)]
    public IActionResult GetEvidencePackage(Guid id)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        var package = _songIdService.GetEvidencePackage(id);
        return package == null ? NotFound() : Ok(package);
    }

    [HttpGet("runs/{id:guid}/forensic-matrix")]
    public IActionResult GetForensicMatrix(Guid id)
    {
        if (Program.IsRelayAgent)
        {
            return Forbid();
        }

        var run = _songIdService.Get(id);
        if (run == null || run.ForensicMatrix == null)
        {
            return NotFound();
        }

        return Ok(run.ForensicMatrix);
    }
}

public sealed class SongIdRunRequest
{
    public string Source { get; set; } = string.Empty;
}
