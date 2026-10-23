// <copyright file="SpotifyConnectionController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.SourceFeeds.API;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using slskd.Core.Security;

[ApiController]
[Route("api/integrations/spotify")]
[Route("api/v{version:apiVersion}/integrations/spotify")]
[ApiVersion("0")]
[Produces("application/json")]
[ValidateCsrfForCookiesOnly]
public sealed class SpotifyConnectionController : ControllerBase
{
    public SpotifyConnectionController(
        ISpotifyConnectionService spotifyConnectionService,
        IOptionsMonitor<global::slskd.Options> optionsMonitor)
    {
        SpotifyConnectionService = spotifyConnectionService;
        OptionsMonitor = optionsMonitor;
    }

    private ISpotifyConnectionService SpotifyConnectionService { get; }

    private IOptionsMonitor<global::slskd.Options> OptionsMonitor { get; }

    [HttpGet("status")]
    [Authorize(Policy = AuthPolicy.Any)]
    [ProducesResponseType(typeof(SpotifyConnectionStatus), 200)]
    public IActionResult GetStatus()
    {
        return Ok(SpotifyConnectionService.GetStatus());
    }

    [HttpPost("authorize")]
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
    [ProducesResponseType(typeof(SpotifyAuthorizationStart), 200)]
    [ProducesResponseType(400)]
    public IActionResult Authorize()
    {
        try
        {
            var redirectUri = BuildRedirectUri();
            return Ok(SpotifyConnectionService.BeginAuthorization(redirectUri));
        }
        catch (InvalidOperationException)
        {
            return BadRequest("Spotify authorization is not configured.");
        }
    }

    [HttpGet("callback")]
    [AllowAnonymous]
    [Produces("text/html")]
    public async Task<IActionResult> Callback(
        [FromQuery] string state,
        [FromQuery] string code,
        [FromQuery] string error,
        CancellationToken cancellationToken = default)
    {
        if (!string.IsNullOrWhiteSpace(error))
        {
            return Content(BuildCallbackHtml("Spotify authorization failed."), "text/html");
        }

        if (string.IsNullOrWhiteSpace(state) || string.IsNullOrWhiteSpace(code))
        {
            return BadRequest("Missing Spotify authorization code or state.");
        }

        try
        {
            await SpotifyConnectionService
                .CompleteAuthorizationAsync(state, code, BuildRedirectUri(), cancellationToken)
                .ConfigureAwait(false);
            return Content(BuildCallbackHtml("Spotify account connected. You can close this window."), "text/html");
        }
        catch (InvalidOperationException)
        {
            return BadRequest("Spotify authorization could not be completed.");
        }
    }

    [HttpDelete] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
    public IActionResult Disconnect()
    {
        SpotifyConnectionService.Disconnect();
        return NoContent();
    }

    private string BuildRedirectUri()
    {
        var configured = OptionsMonitor.CurrentValue.Integration.Spotify.RedirectUri;
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return configured;
        }

        return $"{Request.Scheme}://{Request.Host}{Request.PathBase}/api/v0/integrations/spotify/callback";
    }

    private static string BuildCallbackHtml(string message)
        => $$"""
            <!doctype html>
            <html>
              <head><title>Spotify Connection</title></head>
              <body>
                <p>{{System.Net.WebUtility.HtmlEncode(message)}}</p>
                <script>
                  if (window.opener) {
                    window.opener.postMessage({ type: 'slskdn:spotify-connected' }, window.location.origin);
                  }
                </script>
              </body>
            </html>
            """;
}
