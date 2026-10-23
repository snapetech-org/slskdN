// <copyright file="NowPlayingController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.NowPlaying.API;

using System.Collections.Generic;
using System.Text.Json;
using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using slskd.Authentication;
using slskd.Core.Security;

/// <summary>
///     Now Playing / Scrobble integration (#39).
///     Accepts webhook payloads from Plex, Jellyfin, Tautulli, and a generic JSON format.
/// </summary>
[Route("api/v{version:apiVersion}/[controller]")]
[ApiVersion("0")]
[ApiController]
[Produces("application/json")]
[ValidateCsrfForCookiesOnly]
public class NowPlayingController : ControllerBase
{
    public NowPlayingController(NowPlayingService nowPlaying)
    {
        NowPlaying = nowPlaying;
    }

    private NowPlayingService NowPlaying { get; }

    /// <summary>
    ///     Gets the currently playing track.
    /// </summary>
    [HttpGet]
    [Authorize(Policy = AuthPolicy.Any)]
    public IActionResult Get()
    {
        return Ok(NowPlaying.CurrentTrack);
    }

    /// <summary>
    ///     Sets the currently playing track (generic JSON).
    ///     Body: { "artist": "...", "title": "...", "album": "..." }
    /// </summary>
    [HttpPut] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
    public IActionResult Put([FromBody] NowPlayingRequest request)
    {
        if (request == null)
        {
            return BadRequest("Track data is required");
        }

        var artist = request.Artist?.Trim() ?? string.Empty;
        var title = request.Title?.Trim() ?? string.Empty;
        var album = string.IsNullOrWhiteSpace(request.Album) ? null : request.Album.Trim();

        if (string.IsNullOrWhiteSpace(artist) || string.IsNullOrWhiteSpace(title))
        {
            return BadRequest("Artist and title are required");
        }

        NowPlaying.SetTrack(artist, title, album);
        return NoContent();
    }

    /// <summary>
    ///     Clears the currently playing track.
    /// </summary>
    [HttpDelete] // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- the controller-level ValidateCsrfForCookiesOnly filter validates unsafe cookie-authenticated requests.
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
    public IActionResult Delete()
    {
        NowPlaying.Clear();
        return NoContent();
    }

    /// <summary>
    ///     Webhook receiver for Plex Media Server, Jellyfin, and Tautulli.
    ///     Plex sends multipart/form-data with a "payload" JSON field.
    ///     Jellyfin/Emby send application/json directly.
    ///     Tautulli can be configured to POST generic JSON.
    /// </summary>
    /// <remarks>
    ///     HARDENING-2026-04-20 H13: this endpoint additionally requires the <c>nowplaying</c>
    ///     scope, so operators can issue a dedicated scope-restricted API key for their media
    ///     server instead of handing over a full-access key. A legacy key with <c>scopes="*"</c>
    ///     (the default) still works unchanged.
    /// </remarks>
    [HttpPost("webhook")]
    [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
    [RequireScope("nowplaying")]
    [Consumes("application/json", "multipart/form-data", "application/x-www-form-urlencoded")]
    public async Task<IActionResult> Webhook()
    {
        string json = string.Empty;

        // Plex sends multipart/form-data with a "payload" field
        if (Request.HasFormContentType)
        {
            json = Request.Form["payload"].ToString();
        }
        else
        {
            using var reader = new System.IO.StreamReader(Request.Body);
            json = await reader.ReadToEndAsync(HttpContext.RequestAborted);
        }

        if (string.IsNullOrWhiteSpace(json))
            return BadRequest("Empty payload");

        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            // Detect Plex: has "event" and "Metadata" fields
            if (root.TryGetProperty("event", out var plexEvent) &&
                root.TryGetProperty("Metadata", out var meta))
            {
                var ev = plexEvent.GetString()?.Trim();

                // Only handle play/resume events; clear on stop/pause
                if (ev is "media.play" or "media.resume" or "media.scrobble")
                {
                    var title = meta.TryGetProperty("title", out var t) ? t.GetString()?.Trim() : null;
                    var artist = meta.TryGetProperty("grandparentTitle", out var gp) ? gp.GetString()?.Trim()
                               : meta.TryGetProperty("originalTitle", out var ot) ? ot.GetString()?.Trim()
                               : null;
                    var album = meta.TryGetProperty("parentTitle", out var pt) ? pt.GetString()?.Trim() : null;

                    if (!string.IsNullOrEmpty(artist) && !string.IsNullOrEmpty(title))
                        NowPlaying.SetTrack(artist, title, album);
                }
                else if (ev is "media.pause" or "media.stop")
                {
                    NowPlaying.Clear();
                }

                return Ok();
            }

            // Detect Jellyfin/Emby: has "NotificationType" or "ItemType"
            if (root.TryGetProperty("NotificationType", out var jellyType))
            {
                var type = jellyType.GetString()?.Trim();
                if (type is "PlaybackStart" or "PlaybackProgress")
                {
                    var title = root.TryGetProperty("Name", out var n) ? n.GetString()?.Trim() : null;
                    var artist = root.TryGetProperty("Artist", out var a) ? a.GetString()?.Trim() : null;
                    var album = root.TryGetProperty("Album", out var alb) ? alb.GetString()?.Trim() : null;

                    if (!string.IsNullOrEmpty(artist) && !string.IsNullOrEmpty(title))
                        NowPlaying.SetTrack(artist, title, album);
                }
                else if (type is "PlaybackStop")
                {
                    NowPlaying.Clear();
                }

                return Ok();
            }

            // Generic fallback: { "artist": "...", "title": "...", "album": "...", "event": "play|stop" }
            {
                var evt = root.TryGetProperty("event", out var e) ? e.GetString()?.Trim() : "play";
                var title = root.TryGetProperty("title", out var t) ? t.GetString()?.Trim() : null;
                var artist = root.TryGetProperty("artist", out var a) ? a.GetString()?.Trim() : null;
                var album = root.TryGetProperty("album", out var alb) ? alb.GetString()?.Trim() : null;

                if (evt is "stop" or "pause")
                {
                    NowPlaying.Clear();
                }
                else if (!string.IsNullOrEmpty(artist) && !string.IsNullOrEmpty(title))
                {
                    NowPlaying.SetTrack(artist, title, album);
                }
            }

            return Ok();
        }
        catch (JsonException)
        {
            return BadRequest("Invalid JSON payload");
        }
    }
}

public record NowPlayingRequest
{
    public string Artist { get; init; } = string.Empty;
    public string Title { get; init; } = string.Empty;
    public string Album { get; init; } = string.Empty;
}
