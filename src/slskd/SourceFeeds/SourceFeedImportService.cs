// <copyright file="SourceFeedImportService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.SourceFeeds;

using System.Globalization;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using slskd.Common.IO;
using slskd.Common.Security;

public sealed class SourceFeedImportService : ISourceFeedImportService
{
    private const int MaxHistoryEntries = 100;
    private const int MaxHistorySuggestions = 25;
    private const int MaxHistorySkippedRows = 25;
    private const int MaxSourcePreviewLength = 160;
    private const int MaxProviderResponseBytes = 512 * 1024;

    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private static readonly Regex SpotifyUrlRegex = new(
        @"open\.spotify\.com/(?<type>playlist|album|track|artist|user|collection)/(?<id>[A-Za-z0-9._-]+)?",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    private static readonly Regex SpotifyUriRegex = new(
        @"spotify:(?<type>playlist|album|track|artist|user|liked|saved-tracks|saved-albums|followed-artists|playlists):?(?<id>[A-Za-z0-9._-]+)?",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    private static readonly Regex ListenBrainzUserRegex = new(
        @"listenbrainz\.org/user/(?<user>[^/?#]+)",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    private static readonly Regex LastFmUserRegex = new(
        @"last\.fm/user/(?<user>[^/?#]+)(?<path>/[^?#]*)?",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    private readonly object _storageSync = new();
    private readonly string _storagePath;
    private readonly List<SourceFeedImportHistoryEntry> _history = [];
    private readonly Func<Uri, CancellationToken, Task<(bool Safe, string Reason)>> _checkOutboundUri;

    public SourceFeedImportService(
        IHttpClientFactory httpClientFactory,
        IOptionsMonitor<global::slskd.Options> optionsMonitor,
        ISpotifyConnectionService spotifyConnectionService,
        ILogger<SourceFeedImportService> logger)
        : this(
            httpClientFactory,
            optionsMonitor,
            spotifyConnectionService,
            logger,
            Path.Combine(
                string.IsNullOrWhiteSpace(global::slskd.Program.AppDirectory)
                    ? global::slskd.Program.DefaultAppDirectory
                    : global::slskd.Program.AppDirectory,
                "source-feed-import-history.json"),
            OutboundUriGuard.CheckAsync)
    {
    }

    public SourceFeedImportService(
        IHttpClientFactory httpClientFactory,
        IOptionsMonitor<global::slskd.Options> optionsMonitor,
        ISpotifyConnectionService spotifyConnectionService,
        ILogger<SourceFeedImportService> logger,
        string storagePath)
        : this(httpClientFactory, optionsMonitor, spotifyConnectionService, logger, storagePath, OutboundUriGuard.CheckAsync)
    {
    }

    internal SourceFeedImportService(
        IHttpClientFactory httpClientFactory,
        IOptionsMonitor<global::slskd.Options> optionsMonitor,
        ISpotifyConnectionService spotifyConnectionService,
        ILogger<SourceFeedImportService> logger,
        string storagePath,
        Func<Uri, CancellationToken, Task<(bool Safe, string Reason)>> checkOutboundUri)
    {
        HttpClientFactory = httpClientFactory;
        OptionsMonitor = optionsMonitor;
        SpotifyConnectionService = spotifyConnectionService;
        Logger = logger;
        _storagePath = storagePath;
        _checkOutboundUri = checkOutboundUri ?? throw new ArgumentNullException(nameof(checkOutboundUri));
        LoadHistory();
    }

    private IHttpClientFactory HttpClientFactory { get; }

    private IOptionsMonitor<global::slskd.Options> OptionsMonitor { get; }

    private ISpotifyConnectionService SpotifyConnectionService { get; }

    private ILogger<SourceFeedImportService> Logger { get; }

    public async Task<SourceFeedImportResult> PreviewAsync(
        SourceFeedImportRequest request,
        CancellationToken cancellationToken = default)
    {
        var sourceText = request.SourceText.Trim();
        if (string.IsNullOrWhiteSpace(sourceText))
        {
            var emptyResult = new SourceFeedImportResult();
            RecordHistory(request, emptyResult);
            return emptyResult;
        }

        var safeLimit = Math.Clamp(request.Limit, 1, OptionsMonitor.CurrentValue.Integration.Spotify.MaxItemsPerImport);
        var sourceKind = request.SourceKind.Trim().ToLowerInvariant();
        SourceFeedImportResult result;

        if (request.FetchProviderUrls && LooksLikeSpotify(sourceText, sourceKind))
        {
            result = await PreviewSpotifyAsync(request, safeLimit, cancellationToken).ConfigureAwait(false);
            RecordHistory(request, result);
            return result;
        }

        if (request.FetchProviderUrls && LooksLikeProviderUrl(sourceText, sourceKind))
        {
            result = await PreviewProviderUrlAsync(sourceText, sourceKind, safeLimit, cancellationToken).ConfigureAwait(false);
            RecordHistory(request, result);
            return result;
        }

        result = PreviewLocalText(sourceText, sourceKind, request.IncludeAlbum, safeLimit);
        RecordHistory(request, result);
        return result;
    }

    public Task<IReadOnlyList<SourceFeedImportHistoryEntry>> GetHistoryAsync(
        int limit = 50,
        CancellationToken cancellationToken = default)
    {
        var safeLimit = Math.Clamp(limit, 1, MaxHistoryEntries);
        lock (_storageSync)
        {
            return Task.FromResult<IReadOnlyList<SourceFeedImportHistoryEntry>>(_history
                .OrderByDescending(entry => entry.ImportedAt)
                .Take(safeLimit)
                .ToList());
        }
    }

    public Task<SourceFeedImportHistoryEntry?> GetHistoryEntryAsync(
        string importId,
        CancellationToken cancellationToken = default)
    {
        var normalizedImportId = importId.Trim();
        lock (_storageSync)
        {
            return Task.FromResult(_history.FirstOrDefault(entry =>
                string.Equals(entry.ImportId, normalizedImportId, StringComparison.OrdinalIgnoreCase)));
        }
    }

    private static bool LooksLikeSpotify(string sourceText, string sourceKind)
    {
        return sourceKind == "spotify" ||
            sourceText.StartsWith("spotify:", StringComparison.OrdinalIgnoreCase) ||
            sourceText.Contains("open.spotify.com", StringComparison.OrdinalIgnoreCase);
    }

    private static bool LooksLikeProviderUrl(string sourceText, string sourceKind)
    {
        if (!Uri.TryCreate(sourceText, UriKind.Absolute, out var uri))
        {
            return false;
        }

        if (sourceKind is not "auto")
        {
            return HostMatchesProvider(uri.Host, sourceKind);
        }

        return HostMatchesProvider(uri.Host, "apple") ||
            HostMatchesProvider(uri.Host, "youtube") ||
            HostMatchesProvider(uri.Host, "bandcamp") ||
            HostMatchesProvider(uri.Host, "listenbrainz") ||
            HostMatchesProvider(uri.Host, "lastfm");
    }

    private SourceFeedImportResult PreviewLocalText(string sourceText, string sourceKind, bool includeAlbum, int limit)
    {
        IReadOnlyList<SourceFeedRow> rows;
        var kind = sourceKind == "auto" ? DetectLocalKind(sourceText) : sourceKind;

        rows = kind switch
        {
            "csv" => ParseCsvRows(sourceText, includeAlbum),
            "m3u" or "pls" => ParsePlaylistRows(sourceText),
            "rss" or "opml" => ParseXmlRows(sourceText),
            _ => ParsePlainTextRows(sourceText),
        };

        return BuildResult("local", kind, string.Empty, rows.Take(limit));
    }

    private async Task<SourceFeedImportResult> PreviewProviderUrlAsync(
        string sourceText,
        string sourceKind,
        int limit,
        CancellationToken cancellationToken)
    {
        var provider = DetectProvider(sourceText, sourceKind);
        var rows = new List<SourceFeedRow>();
        var requests = provider switch
        {
            "apple" => await FetchAppleMusicRowsAsync(sourceText, rows, limit, cancellationToken).ConfigureAwait(false),
            "youtube" => await FetchYouTubeRowsAsync(sourceText, rows, limit, cancellationToken).ConfigureAwait(false),
            "listenbrainz" => await FetchListenBrainzRowsAsync(sourceText, rows, limit, cancellationToken).ConfigureAwait(false),
            "lastfm" => await FetchLastFmRowsAsync(sourceText, rows, limit, cancellationToken).ConfigureAwait(false),
            _ => 0,
        };

        if (rows.Count == 0)
        {
            requests += await FetchProviderMetadataPageAsync(provider, sourceText, rows, cancellationToken).ConfigureAwait(false);
        }

        var result = BuildResult(provider, "url", sourceText, rows.Take(limit));
        result.NetworkRequestCount = requests;
        return result;
    }

    private static string DetectProvider(string sourceText, string sourceKind)
    {
        if (sourceKind is not "auto")
        {
            return sourceKind == "itunes" ? "apple" : sourceKind.Replace(".", string.Empty, StringComparison.OrdinalIgnoreCase);
        }

        if (!Uri.TryCreate(sourceText, UriKind.Absolute, out var uri))
        {
            return "url";
        }

        var host = uri.Host;
        if (HostMatchesProvider(host, "apple"))
        {
            return "apple";
        }

        if (HostMatchesProvider(host, "youtube"))
        {
            return "youtube";
        }

        if (HostMatchesProvider(host, "bandcamp"))
        {
            return "bandcamp";
        }

        if (HostMatchesProvider(host, "listenbrainz"))
        {
            return "listenbrainz";
        }

        return HostMatchesProvider(host, "lastfm") ? "lastfm" : "url";
    }

    private static bool HostMatchesProvider(string host, string sourceKind)
    {
        var provider = sourceKind.Replace(".", string.Empty, StringComparison.OrdinalIgnoreCase);
        return provider switch
        {
            "apple" or "itunes" => IsHostOrSubdomain(host, "music.apple.com") || IsHostOrSubdomain(host, "itunes.apple.com"),
            "youtube" => IsHostOrSubdomain(host, "youtube.com") || IsHostOrSubdomain(host, "youtu.be"),
            "bandcamp" => IsHostOrSubdomain(host, "bandcamp.com"),
            "listenbrainz" => IsHostOrSubdomain(host, "listenbrainz.org"),
            "lastfm" => IsHostOrSubdomain(host, "last.fm"),
            _ => false,
        };
    }

    private static bool IsHostOrSubdomain(string host, string domain)
    {
        return host.Equals(domain, StringComparison.OrdinalIgnoreCase) ||
            host.EndsWith("." + domain, StringComparison.OrdinalIgnoreCase);
    }

    private async Task<int> FetchAppleMusicRowsAsync(string sourceText, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var ids = ExtractAppleNumericIds(sourceText).Distinct().Take(2).ToArray();
        if (ids.Length == 0)
        {
            return 0;
        }

        var requests = 0;
        foreach (var id in ids)
        {
            var lookup = await GetJsonAsync<AppleLookupResponse>(
                $"https://itunes.apple.com/lookup?id={Uri.EscapeDataString(id)}&entity=song&limit={Math.Min(limit, 200).ToString(CultureInfo.InvariantCulture)}",
                cancellationToken).ConfigureAwait(false);
            requests++;
            rows.AddRange((lookup?.Results ?? [])
                .Where(item => !string.IsNullOrWhiteSpace(item.TrackName))
                .Select(item => new SourceFeedRow(
                    Title: item.TrackName,
                    Artist: item.ArtistName,
                    Album: item.CollectionName,
                    Source: "apple",
                    SourceId: item.TrackId.ToString(CultureInfo.InvariantCulture),
                    ProviderUrl: string.IsNullOrWhiteSpace(item.TrackViewUrl) ? sourceText : item.TrackViewUrl,
                    RawText: item.TrackName)));

            if (rows.Count >= limit)
            {
                break;
            }
        }

        return requests;
    }

    private async Task<int> FetchYouTubeRowsAsync(string sourceText, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var options = OptionsMonitor.CurrentValue.Integration.YouTube;
        var apiKey = options.ApiKey;
        var playlistId = ExtractYouTubePlaylistId(sourceText);
        if (!options.Enabled || string.IsNullOrWhiteSpace(apiKey) || string.IsNullOrWhiteSpace(playlistId))
        {
            return 0;
        }

        var requests = 0;
        string? pageToken = null;
        while (rows.Count < limit)
        {
            var pageLimit = Math.Min(50, limit - rows.Count);
            var uri = $"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults={pageLimit.ToString(CultureInfo.InvariantCulture)}&playlistId={Uri.EscapeDataString(playlistId)}&key={Uri.EscapeDataString(apiKey)}" +
                (string.IsNullOrWhiteSpace(pageToken) ? string.Empty : $"&pageToken={Uri.EscapeDataString(pageToken)}");
            var page = await GetJsonAsync<YouTubePlaylistItemsResponse>(uri, cancellationToken).ConfigureAwait(false);
            requests++;

            var items = page?.Items ?? [];
            if (items.Count == 0)
            {
                break;
            }

            var startingRow = rows.Count;
            rows.AddRange(items.Select((item, index) =>
            {
                var title = item.Snippet?.Title ?? string.Empty;
                var videoId = item.Snippet?.ResourceId?.VideoId ?? string.Empty;
                var row = ParseLooseLine(title, "youtube:playlist", startingRow + index + 1);
                return row with
                {
                    SourceId = string.IsNullOrWhiteSpace(videoId) ? row.SourceId : videoId,
                    ProviderUrl = string.IsNullOrWhiteSpace(videoId) ? sourceText : $"https://www.youtube.com/watch?v={Uri.EscapeDataString(videoId)}",
                };
            }));

            pageToken = page?.NextPageToken;
            if (string.IsNullOrWhiteSpace(pageToken))
            {
                break;
            }
        }

        return requests;
    }

    private async Task<int> FetchListenBrainzRowsAsync(string sourceText, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var match = ListenBrainzUserRegex.Match(sourceText);
        if (!match.Success)
        {
            return 0;
        }

        var user = Uri.UnescapeDataString(match.Groups["user"].Value);
        var pageLimit = Math.Min(limit, 100);
        var listens = await GetJsonAsync<ListenBrainzListensResponse>(
            $"https://api.listenbrainz.org/1/user/{Uri.EscapeDataString(user)}/listens?count={pageLimit.ToString(CultureInfo.InvariantCulture)}",
            cancellationToken).ConfigureAwait(false);

        rows.AddRange((listens?.Payload?.Listens ?? []).Select((listen, index) =>
        {
            var metadata = listen.TrackMetadata ?? new ListenBrainzTrackMetadata();
            return new SourceFeedRow(
                Title: metadata.TrackName,
                Artist: metadata.ArtistName,
                Album: metadata.ReleaseName,
                Source: "listenbrainz:listens",
                SourceId: metadata.AdditionalInfo?.RecordingMsid ?? (index + 1).ToString(CultureInfo.InvariantCulture),
                ProviderUrl: sourceText,
                RawText: metadata.TrackName);
        }));
        return 1;
    }

    private async Task<int> FetchLastFmRowsAsync(string sourceText, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var options = OptionsMonitor.CurrentValue.Integration.LastFm;
        var apiKey = options.ApiKey;
        var target = ParseLastFmTarget(sourceText);
        if (!options.Enabled || string.IsNullOrWhiteSpace(apiKey) || string.IsNullOrWhiteSpace(target.User))
        {
            return 0;
        }

        var pageLimit = Math.Min(200, limit);
        var uri = $"https://ws.audioscrobbler.com/2.0/?method={target.Method}&user={Uri.EscapeDataString(target.User)}&api_key={Uri.EscapeDataString(apiKey)}&format=json&limit={pageLimit.ToString(CultureInfo.InvariantCulture)}";
        var page = await GetJsonAsync<LastFmTracksResponse>(uri, cancellationToken).ConfigureAwait(false);
        var tracks = page?.RecentTracks?.Track ?? page?.LovedTracks?.Track ?? page?.TopTracks?.Track ?? [];
        rows.AddRange(tracks.Take(limit).Select((track, index) => new SourceFeedRow(
            Title: track.Name,
            Artist: track.Artist?.Name ?? track.Artist?.Text ?? string.Empty,
            Album: track.Album?.Text ?? string.Empty,
            Source: target.Source,
            SourceId: FirstNonEmpty(track.Mbid, (index + 1).ToString(CultureInfo.InvariantCulture)),
            ProviderUrl: track.Url,
            RawText: track.Name)));
        return 1;
    }

    private async Task<int> FetchProviderMetadataPageAsync(
        string provider,
        string sourceText,
        List<SourceFeedRow> rows,
        CancellationToken cancellationToken)
    {
        if (!Uri.TryCreate(sourceText, UriKind.Absolute, out _))
        {
            return 0;
        }

        var html = await GetStringAsync(sourceText, cancellationToken).ConfigureAwait(false);
        var title = FirstNonEmpty(
            ExtractMeta(html, "music:song"),
            ExtractMeta(html, "og:title"),
            ExtractMeta(html, "twitter:title"),
            ExtractTitle(html));
        title = CleanProviderTitle(title, provider);
        if (string.IsNullOrWhiteSpace(title))
        {
            return 1;
        }

        var artist = FirstNonEmpty(
            ExtractMeta(html, "music:musician:description"),
            ExtractMeta(html, "byl"),
            ExtractMeta(html, "article:author"));
        var row = ParseLooseLine(title, provider, 1) with
        {
            Artist = string.IsNullOrWhiteSpace(artist) ? ParseLooseLine(title, provider, 1).Artist : artist,
            ProviderUrl = sourceText,
        };
        rows.Add(row);
        return 1;
    }

    private async Task<SourceFeedImportResult> PreviewSpotifyAsync(
        SourceFeedImportRequest request,
        int limit,
        CancellationToken cancellationToken)
    {
        var target = ParseSpotifyTarget(request.SourceText.Trim());
        var token = await GetSpotifyAccessTokenAsync(
            target.RequiresUserToken,
            request.ProviderAccessToken,
            cancellationToken).ConfigureAwait(false);

        if (target.RequiresUserToken && string.IsNullOrWhiteSpace(token))
        {
            return new SourceFeedImportResult
            {
                Provider = "spotify",
                SourceKind = target.Type,
                SourceId = target.Id,
                RequiresAccessToken = true,
                RequiredScopeHint = target.ScopeHint,
            };
        }

        if (string.IsNullOrWhiteSpace(token))
        {
            return new SourceFeedImportResult
            {
                Provider = "spotify",
                SourceKind = target.Type,
                SourceId = target.Id,
                RequiresAccessToken = true,
                RequiredScopeHint = "Configure integrations.spotify.client_id/client_secret, connect a Spotify account, or provide a Spotify bearer token.",
            };
        }

        var rows = new List<SourceFeedRow>();
        var requests = 0;

        switch (target.Type)
        {
            case "playlist":
                requests += await FetchSpotifyPlaylistItemsAsync(token, target.Id, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "album":
                requests += await FetchSpotifyAlbumTracksAsync(token, target.Id, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "track":
                requests += await FetchSpotifyTrackAsync(token, target.Id, rows, cancellationToken).ConfigureAwait(false);
                break;
            case "artist":
                requests += await FetchSpotifyArtistTopTracksAsync(token, target.Id, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "user":
                requests += await FetchSpotifyUserPlaylistsAsync(token, target.Id, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "liked":
            case "saved-tracks":
                requests += await FetchSpotifySavedTracksAsync(token, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "saved-albums":
                requests += await FetchSpotifySavedAlbumsAsync(token, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "followed-artists":
                requests += await FetchSpotifyFollowedArtistsAsync(token, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
            case "playlists":
                requests += await FetchSpotifyCurrentUserPlaylistsAsync(token, rows, limit, cancellationToken).ConfigureAwait(false);
                break;
        }

        var result = BuildResult("spotify", target.Type, target.Id, rows);
        result.NetworkRequestCount = requests;
        return result;
    }

    private async Task<string> GetSpotifyAccessTokenAsync(
        bool requiresUserToken,
        string providerAccessToken,
        CancellationToken cancellationToken)
    {
        if (!string.IsNullOrWhiteSpace(providerAccessToken))
        {
            return providerAccessToken.Trim();
        }

        if (requiresUserToken)
        {
            return await SpotifyConnectionService.GetAccessTokenAsync(cancellationToken).ConfigureAwait(false);
        }

        var appToken = await GetSpotifyAppTokenAsync(cancellationToken).ConfigureAwait(false);
        return string.IsNullOrWhiteSpace(appToken)
            ? await SpotifyConnectionService.GetAccessTokenAsync(cancellationToken).ConfigureAwait(false)
            : appToken;
    }

    private async Task<string> GetSpotifyAppTokenAsync(CancellationToken cancellationToken)
    {
        var options = OptionsMonitor.CurrentValue.Integration.Spotify;
        if (!options.Enabled || string.IsNullOrWhiteSpace(options.ClientId) || string.IsNullOrWhiteSpace(options.ClientSecret))
        {
            return string.Empty;
        }

        using var request = new HttpRequestMessage(HttpMethod.Post, "https://accounts.spotify.com/api/token");
        var credentials = Convert.ToBase64String(Encoding.UTF8.GetBytes($"{options.ClientId}:{options.ClientSecret}"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Basic", credentials);
        request.Content = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["grant_type"] = "client_credentials",
        });

        using var response = await SendSpotifyAsync(request, cancellationToken).ConfigureAwait(false);
        var token = await response.Content.ReadFromJsonAsync<SpotifyTokenResponse>(JsonOptions, cancellationToken).ConfigureAwait(false);
        return token?.AccessToken ?? string.Empty;
    }

    private async Task<int> FetchSpotifyPlaylistItemsAsync(string token, string playlistId, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var requests = 0;
        var offset = 0;

        while (rows.Count < limit)
        {
            var pageLimit = Math.Min(50, limit - rows.Count);
            var relative = $"https://api.spotify.com/v1/playlists/{Uri.EscapeDataString(playlistId)}/items?limit={pageLimit}&offset={offset}&additional_types=track";
            var page = await GetSpotifyAsync<SpotifyPaging<SpotifyPlaylistItem>>(token, relative, cancellationToken).ConfigureAwait(false);
            requests++;
            if (page?.Items == null || page.Items.Count == 0)
            {
                break;
            }

            rows.AddRange(page.Items.Select(item => ToRow(item.Track, "spotify:playlist", playlistId)).Where(row => row != null)!);

            if (page.Next == null || rows.Count >= page.Total)
            {
                break;
            }

            offset += page.Items.Count;
        }

        return requests;
    }

    private async Task<int> FetchSpotifyAlbumTracksAsync(string token, string albumId, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var album = await GetSpotifyAsync<SpotifyAlbum>($"Bearer {token}", $"https://api.spotify.com/v1/albums/{Uri.EscapeDataString(albumId)}", cancellationToken).ConfigureAwait(false);
        rows.AddRange((album?.Tracks?.Items ?? [])
            .Select(track => ToRow(track with { Album = new SpotifyAlbumSummary { Name = album?.Name ?? string.Empty } }, "spotify:album", albumId))
            .Where(row => row != null)!);
        return 1;
    }

    private async Task<int> FetchSpotifyTrackAsync(string token, string trackId, List<SourceFeedRow> rows, CancellationToken cancellationToken)
    {
        var track = await GetSpotifyAsync<SpotifyTrack>(token, $"https://api.spotify.com/v1/tracks/{Uri.EscapeDataString(trackId)}", cancellationToken).ConfigureAwait(false);
        var row = ToRow(track, "spotify:track", trackId);
        if (row != null)
        {
            rows.Add(row);
        }

        return 1;
    }

    private async Task<int> FetchSpotifyArtistTopTracksAsync(string token, string artistId, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var market = OptionsMonitor.CurrentValue.Integration.Spotify.Market;
        var top = await GetSpotifyAsync<SpotifyTopTracks>(token, $"https://api.spotify.com/v1/artists/{Uri.EscapeDataString(artistId)}/top-tracks?market={Uri.EscapeDataString(market)}", cancellationToken).ConfigureAwait(false);
        rows.AddRange((top?.Tracks ?? []).Take(limit).Select(track => ToRow(track, "spotify:artist-top-tracks", artistId)).Where(row => row != null)!);
        return 1;
    }

    private async Task<int> FetchSpotifySavedTracksAsync(string token, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
        => await FetchSpotifyTrackPagesAsync(token, "https://api.spotify.com/v1/me/tracks", rows, limit, "spotify:liked", cancellationToken).ConfigureAwait(false);

    private async Task<int> FetchSpotifySavedAlbumsAsync(string token, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var requests = 0;
        var offset = 0;

        while (rows.Count < limit)
        {
            var pageLimit = Math.Min(20, limit - rows.Count);
            var page = await GetSpotifyAsync<SpotifyPaging<SpotifySavedAlbum>>(
                token,
                $"https://api.spotify.com/v1/me/albums?limit={pageLimit}&offset={offset}",
                cancellationToken).ConfigureAwait(false);
            requests++;
            if (page?.Items == null || page.Items.Count == 0)
            {
                break;
            }

            foreach (var album in page.Items.Select(item => item.Album).Where(album => album != null))
            {
                rows.Add(new SourceFeedRow(
                    Title: album!.Name,
                    Artist: string.Join(" ", album.Artists.Select(artist => artist.Name).Where(value => !string.IsNullOrWhiteSpace(value))),
                    Album: album.Name,
                    Source: "spotify:saved-albums",
                    SourceId: album.Id,
                    ProviderUrl: album.ExternalUrls?.Spotify ?? string.Empty,
                    RawText: album.Name));
            }

            if (page.Next == null || rows.Count >= page.Total)
            {
                break;
            }

            offset += page.Items.Count;
        }

        return requests;
    }

    private async Task<int> FetchSpotifyFollowedArtistsAsync(string token, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var requests = 0;
        string? after = null;

        while (rows.Count < limit)
        {
            var pageLimit = Math.Min(50, limit - rows.Count);
            var uri = $"https://api.spotify.com/v1/me/following?type=artist&limit={pageLimit}" +
                (string.IsNullOrWhiteSpace(after) ? string.Empty : $"&after={Uri.EscapeDataString(after)}");
            var page = await GetSpotifyAsync<SpotifyFollowedArtists>(token, uri, cancellationToken).ConfigureAwait(false);
            requests++;
            var artists = page?.Artists?.Items ?? [];
            if (artists.Count == 0)
            {
                break;
            }

            rows.AddRange(artists.Select(artist => new SourceFeedRow(
                Title: artist.Name,
                Artist: artist.Name,
                Album: string.Empty,
                Source: "spotify:followed-artists",
                SourceId: artist.Id,
                ProviderUrl: artist.ExternalUrls?.Spotify ?? string.Empty,
                RawText: artist.Name)));

            after = page?.Artists?.Cursors?.After;
            if (string.IsNullOrWhiteSpace(after))
            {
                break;
            }
        }

        return requests;
    }

    private async Task<int> FetchSpotifyCurrentUserPlaylistsAsync(string token, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
        => await FetchSpotifyPlaylistCollectionAsync(token, "https://api.spotify.com/v1/me/playlists", rows, limit, cancellationToken).ConfigureAwait(false);

    private async Task<int> FetchSpotifyUserPlaylistsAsync(string token, string userId, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
        => await FetchSpotifyPlaylistCollectionAsync(token, $"https://api.spotify.com/v1/users/{Uri.EscapeDataString(userId)}/playlists", rows, limit, cancellationToken).ConfigureAwait(false);

    private async Task<int> FetchSpotifyPlaylistCollectionAsync(string token, string uri, List<SourceFeedRow> rows, int limit, CancellationToken cancellationToken)
    {
        var requests = 0;
        var offset = 0;

        while (rows.Count < limit)
        {
            var page = await GetSpotifyAsync<SpotifyPaging<SpotifyPlaylistSummary>>(token, $"{uri}?limit=20&offset={offset}", cancellationToken).ConfigureAwait(false);
            requests++;
            if (page?.Items == null || page.Items.Count == 0)
            {
                break;
            }

            foreach (var playlist in page.Items)
            {
                requests += await FetchSpotifyPlaylistItemsAsync(token, playlist.Id, rows, limit, cancellationToken).ConfigureAwait(false);
                if (rows.Count >= limit)
                {
                    break;
                }
            }

            if (page.Next == null || rows.Count >= page.Total)
            {
                break;
            }

            offset += page.Items.Count;
        }

        return requests;
    }

    private async Task<int> FetchSpotifyTrackPagesAsync(string token, string uri, List<SourceFeedRow> rows, int limit, string source, CancellationToken cancellationToken)
    {
        var requests = 0;
        var offset = 0;

        while (rows.Count < limit)
        {
            var pageLimit = Math.Min(50, limit - rows.Count);
            var page = await GetSpotifyAsync<SpotifyPaging<SpotifySavedTrack>>(
                token,
                $"{uri}?limit={pageLimit}&offset={offset}",
                cancellationToken).ConfigureAwait(false);
            requests++;
            if (page?.Items == null || page.Items.Count == 0)
            {
                break;
            }

            rows.AddRange(page.Items.Select(item => ToRow(item.Track, source, item.Track?.Id ?? string.Empty)).Where(row => row != null)!);

            if (page.Next == null || rows.Count >= page.Total)
            {
                break;
            }

            offset += page.Items.Count;
        }

        return requests;
    }

    private async Task<T?> GetSpotifyAsync<T>(string token, string uri, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, uri);
        request.Headers.Authorization = token.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase)
            ? AuthenticationHeaderValue.Parse(token)
            : new AuthenticationHeaderValue("Bearer", token);
        using var response = await SendSpotifyAsync(request, cancellationToken).ConfigureAwait(false);
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        return await JsonSerializer.DeserializeAsync<T>(stream, JsonOptions, cancellationToken).ConfigureAwait(false);
    }

    private async Task<HttpResponseMessage> SendSpotifyAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var options = OptionsMonitor.CurrentValue.Integration.Spotify;
        var client = HttpClientFactory.CreateClient(OutboundUriGuard.NoRedirectHttpClientName);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(options.TimeoutSeconds));
        var response = await client.SendAsync(request, timeout.Token).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
        return response;
    }

    private async Task<T?> GetJsonAsync<T>(string uri, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, uri);
        using var response = await SendProviderAsync(request, cancellationToken).ConfigureAwait(false);
        await using var stream = await ReadProviderResponseAsync(response, cancellationToken).ConfigureAwait(false);
        return await JsonSerializer.DeserializeAsync<T>(stream, JsonOptions, cancellationToken).ConfigureAwait(false);
    }

    private async Task<string> GetStringAsync(string uri, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, uri);
        using var response = await SendProviderAsync(request, cancellationToken).ConfigureAwait(false);
        await using var stream = await ReadProviderResponseAsync(response, cancellationToken).ConfigureAwait(false);
        using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true, leaveOpen: false);
        return await reader.ReadToEndAsync(cancellationToken).ConfigureAwait(false);
    }

    private async Task<HttpResponseMessage> SendProviderAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        if (request.RequestUri == null || !request.RequestUri.IsAbsoluteUri)
        {
            throw new InvalidOperationException("Provider URL must be absolute.");
        }

        var (safe, reason) = await _checkOutboundUri(request.RequestUri, cancellationToken).ConfigureAwait(false);
        if (!safe)
        {
            throw new InvalidOperationException($"Provider URL blocked by outbound guard: {reason}");
        }

        var options = OptionsMonitor.CurrentValue.Integration.Spotify;
        var client = HttpClientFactory.CreateClient(OutboundUriGuard.NoRedirectHttpClientName);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(options.TimeoutSeconds));
        request.Headers.UserAgent.ParseAdd("slskdN-source-feed-import/1.0");
        var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
        if (response.Content.Headers.ContentLength is long contentLength && contentLength > MaxProviderResponseBytes)
        {
            response.Dispose();
            throw new InvalidOperationException("Provider response was too large.");
        }

        return response;
    }

    private static async Task<Stream> ReadProviderResponseAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        var buffer = new byte[8192];
        var memory = new MemoryStream();
        var total = 0;
        int read;
        while ((read = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken).ConfigureAwait(false)) > 0)
        {
            total += read;
            if (total > MaxProviderResponseBytes)
            {
                memory.Dispose();
                throw new InvalidOperationException("Provider response was too large.");
            }

            await memory.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
        }

        memory.Position = 0;
        return memory;
    }

    private static SpotifyTarget ParseSpotifyTarget(string sourceText)
    {
        var uriMatch = SpotifyUriRegex.Match(sourceText);
        if (uriMatch.Success)
        {
            return NormalizeSpotifyTarget(uriMatch.Groups["type"].Value, uriMatch.Groups["id"].Value);
        }

        var urlMatch = SpotifyUrlRegex.Match(sourceText);
        if (urlMatch.Success)
        {
            var type = urlMatch.Groups["type"].Value.ToLowerInvariant();
            if (type == "collection")
            {
                var path = sourceText.ToLowerInvariant();
                if (path.Contains("albums", StringComparison.OrdinalIgnoreCase))
                {
                    return NormalizeSpotifyTarget("saved-albums", string.Empty);
                }

                if (path.Contains("following", StringComparison.OrdinalIgnoreCase) || path.Contains("artists", StringComparison.OrdinalIgnoreCase))
                {
                    return NormalizeSpotifyTarget("followed-artists", string.Empty);
                }

                return NormalizeSpotifyTarget("liked", string.Empty);
            }

            return NormalizeSpotifyTarget(type, urlMatch.Groups["id"].Value);
        }

        return NormalizeSpotifyTarget(sourceText.Trim().ToLowerInvariant(), string.Empty);
    }

    private static SpotifyTarget NormalizeSpotifyTarget(string type, string id)
    {
        var normalized = type.Trim().ToLowerInvariant() switch
        {
            "collection" or "liked" or "saved-tracks" => "saved-tracks",
            "saved-albums" => "saved-albums",
            "followed-artists" => "followed-artists",
            "playlists" => "playlists",
            var value => value,
        };

        return normalized switch
        {
            "saved-tracks" => new SpotifyTarget("saved-tracks", id, true, "user-library-read"),
            "saved-albums" => new SpotifyTarget("saved-albums", id, true, "user-library-read"),
            "followed-artists" => new SpotifyTarget("followed-artists", id, true, "user-follow-read"),
            "playlists" => new SpotifyTarget("playlists", id, true, "playlist-read-private playlist-read-collaborative"),
            "user" => new SpotifyTarget("user", id, false, string.Empty),
            var value => new SpotifyTarget(value, id, false, string.Empty),
        };
    }

    private static SourceFeedRow? ToRow(SpotifyTrack? track, string source, string sourceId)
    {
        if (track == null)
        {
            return null;
        }

        return new SourceFeedRow(
            Title: track.Name,
            Artist: string.Join(" ", track.Artists.Select(artist => artist.Name).Where(value => !string.IsNullOrWhiteSpace(value))),
            Album: track.Album?.Name ?? string.Empty,
            Source: source,
            SourceId: sourceId,
            ProviderUrl: track.ExternalUrls?.Spotify ?? string.Empty,
            RawText: track.Name);
    }

    private static SourceFeedImportResult BuildResult(string provider, string sourceKind, string sourceId, IEnumerable<SourceFeedRow> rows)
    {
        var result = new SourceFeedImportResult
        {
            Provider = provider,
            SourceKind = sourceKind,
            SourceId = sourceId,
        };
        var keys = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var row in rows)
        {
            result.TotalRows++;
            var searchText = BuildSearchText(row.Title, row.Artist, row.Album);
            if (string.IsNullOrWhiteSpace(searchText))
            {
                result.SkippedCount++;
                result.SkippedRows.Add(new SourceFeedSkippedRow
                {
                    RowNumber = result.TotalRows,
                    Reason = "Missing artist/title metadata",
                    RawText = row.RawText,
                });
                continue;
            }

            var key = $"{provider}:{row.Source}:{NormalizeKey(searchText)}";
            if (!keys.Add(key))
            {
                result.DuplicateCount++;
                continue;
            }

            result.Suggestions.Add(new SourceFeedSuggestion
            {
                Title = string.IsNullOrWhiteSpace(row.Title) ? searchText : row.Title,
                Artist = row.Artist,
                Album = row.Album,
                SearchText = searchText,
                Source = row.Source,
                SourceId = row.SourceId,
                SourceItemId = row.SourceId,
                ProviderUrl = row.ProviderUrl,
                EvidenceKey = key,
                Reason = $"Imported from {provider} {sourceKind}.",
            });
        }

        result.SuggestionCount = result.Suggestions.Count;
        return result;
    }

    private void RecordHistory(SourceFeedImportRequest request, SourceFeedImportResult result)
    {
        var entry = new SourceFeedImportHistoryEntry
        {
            ImportId = BuildImportId(request, result),
            ImportedAt = DateTimeOffset.UtcNow,
            Provider = result.Provider,
            SourceKind = result.SourceKind,
            SourceId = result.SourceId,
            SourceFingerprint = BuildSourceFingerprint(request.SourceText),
            SourcePreview = BuildSourcePreview(request.SourceText),
            Limit = request.Limit,
            IncludeAlbum = request.IncludeAlbum,
            FetchProviderUrls = request.FetchProviderUrls,
            TotalRows = result.TotalRows,
            SuggestionCount = result.SuggestionCount,
            DuplicateCount = result.DuplicateCount,
            SkippedCount = result.SkippedCount,
            NetworkRequestCount = result.NetworkRequestCount,
            RequiresAccessToken = result.RequiresAccessToken,
            RequiredScopeHint = result.RequiredScopeHint,
            Suggestions = result.Suggestions.Take(MaxHistorySuggestions).ToList(),
            SkippedRows = result.SkippedRows.Take(MaxHistorySkippedRows).ToList(),
        };

        lock (_storageSync)
        {
            _history.RemoveAll(existing => string.Equals(existing.ImportId, entry.ImportId, StringComparison.OrdinalIgnoreCase));
            _history.Insert(0, entry);
            if (_history.Count > MaxHistoryEntries)
            {
                _history.RemoveRange(MaxHistoryEntries, _history.Count - MaxHistoryEntries);
            }

            PersistHistory();
        }
    }

    private void LoadHistory()
    {
        lock (_storageSync)
        {
            if (!File.Exists(_storagePath))
            {
                return;
            }

            try
            {
                var json = File.ReadAllText(_storagePath);
                var state = JsonSerializer.Deserialize<SourceFeedImportHistoryState>(json, JsonOptions);
                if (state == null)
                {
                    return;
                }

                _history.Clear();
                _history.AddRange(state.History
                    .OrderByDescending(entry => entry.ImportedAt)
                    .Take(MaxHistoryEntries));
            }
            catch (IOException)
            {
                Logger.LogWarning("[SourceFeedImport] Failed to load import history from {Path}", _storagePath);
            }
            catch (JsonException)
            {
                Logger.LogWarning("[SourceFeedImport] Failed to parse import history from {Path}", _storagePath);
            }
        }
    }

    private void PersistHistory()
    {
        var state = new SourceFeedImportHistoryState
        {
            History = _history
                .OrderByDescending(entry => entry.ImportedAt)
                .Take(MaxHistoryEntries)
                .ToList(),
        };
        AtomicFileWriter.WriteAllText(_storagePath, JsonSerializer.Serialize(state, JsonOptions));
    }

    private static string BuildImportId(SourceFeedImportRequest request, SourceFeedImportResult result)
    {
        var input = $"{Guid.NewGuid():N}|{result.Provider}|{result.SourceKind}|{result.SourceId}|{BuildSourceFingerprint(request.SourceText)}";
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16].ToLowerInvariant();
    }

    private static string BuildSourceFingerprint(string sourceText)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(sourceText.Trim()));
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static string BuildSourcePreview(string sourceText)
    {
        var preview = Regex.Replace(sourceText.Trim(), @"\s+", " ");
        return preview.Length <= MaxSourcePreviewLength ? preview : preview[..MaxSourcePreviewLength];
    }

    private sealed class SourceFeedImportHistoryState
    {
        public List<SourceFeedImportHistoryEntry> History { get; init; } = [];
    }

    private static string DetectLocalKind(string sourceText)
    {
        var trimmed = sourceText.TrimStart();
        if (trimmed.StartsWith("#EXTM3U", StringComparison.OrdinalIgnoreCase) || trimmed.Contains("#EXTINF", StringComparison.OrdinalIgnoreCase))
        {
            return "m3u";
        }

        if (trimmed.StartsWith("<rss", StringComparison.OrdinalIgnoreCase) ||
            trimmed.StartsWith("<feed", StringComparison.OrdinalIgnoreCase) ||
            trimmed.StartsWith("<opml", StringComparison.OrdinalIgnoreCase))
        {
            return "rss";
        }

        return LooksLikeCsv(sourceText) ? "csv" : "text";
    }

    private static bool LooksLikeCsv(string sourceText)
    {
        var firstLine = sourceText.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? string.Empty;
        return firstLine.Contains(',', StringComparison.Ordinal) &&
            firstLine.Contains("track", StringComparison.OrdinalIgnoreCase);
    }

    private static IReadOnlyList<SourceFeedRow> ParseCsvRows(string csvText, bool includeAlbum)
    {
        var rows = ParseDelimitedRows(csvText);
        if (rows.Count == 0)
        {
            return [];
        }

        var hasHeader = LooksLikeHeader(rows[0]);
        var header = hasHeader ? rows[0] : [];
        var titleIndex = hasHeader ? FindColumn(header, "trackname", "track", "title", "songname", "song", "name") : 0;
        var artistIndex = hasHeader ? FindColumn(header, "artistname", "artistnames", "artists", "artist") : 1;
        var albumIndex = hasHeader ? FindColumn(header, "albumname", "album", "release") : 2;
        var urlIndex = hasHeader ? FindColumn(header, "url", "spotifyurl", "trackurl", "link") : -1;
        var startIndex = hasHeader ? 1 : 0;
        var result = new List<SourceFeedRow>();

        for (var index = startIndex; index < rows.Count; index++)
        {
            var row = rows[index];
            result.Add(new SourceFeedRow(
                Title: GetCell(row, titleIndex),
                Artist: GetCell(row, artistIndex),
                Album: includeAlbum ? GetCell(row, albumIndex) : string.Empty,
                Source: "csv",
                SourceId: (index + 1).ToString(CultureInfo.InvariantCulture),
                ProviderUrl: GetCell(row, urlIndex),
                RawText: string.Join(",", row)));
        }

        return result;
    }

    private static IReadOnlyList<SourceFeedRow> ParsePlainTextRows(string sourceText)
    {
        return sourceText
            .Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries)
            .Select((line, index) => ParseLooseLine(line, "text", index + 1))
            .ToList();
    }

    private static IReadOnlyList<SourceFeedRow> ParsePlaylistRows(string sourceText)
    {
        var rows = new List<SourceFeedRow>();
        var lines = sourceText.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries);
        for (var index = 0; index < lines.Length; index++)
        {
            var line = lines[index].Trim();
            if (!line.StartsWith("#EXTINF:", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var comma = line.LastIndexOf(',');
            if (comma >= 0 && comma + 1 < line.Length)
            {
                rows.Add(ParseLooseLine(line[(comma + 1)..], "m3u", index + 1));
            }
        }

        return rows;
    }

    private static IReadOnlyList<SourceFeedRow> ParseXmlRows(string sourceText)
    {
        var rows = new List<SourceFeedRow>();
        var document = XDocument.Parse(sourceText);
        rows.AddRange(document.Descendants()
            .Where(element => element.Name.LocalName is "item" or "entry")
            .Select((element, index) =>
            {
                var title = element.Elements().FirstOrDefault(child => child.Name.LocalName == "title")?.Value ?? string.Empty;
                return ParseLooseLine(title, "rss", index + 1);
            }));
        rows.AddRange(document.Descendants()
            .Where(element => element.Name.LocalName == "outline")
            .Select((element, index) => ParseLooseLine(
                element.Attribute("text")?.Value ?? element.Attribute("title")?.Value ?? string.Empty,
                "opml",
                index + 1)));
        return rows;
    }

    private static SourceFeedRow ParseLooseLine(string line, string source, int rowNumber)
    {
        var text = line.Trim();
        var parts = text.Split(" - ", 2, StringSplitOptions.TrimEntries);
        var artist = parts.Length == 2 ? parts[0] : string.Empty;
        var title = parts.Length == 2 ? parts[1] : text;
        return new SourceFeedRow(title, artist, string.Empty, source, rowNumber.ToString(CultureInfo.InvariantCulture), string.Empty, text);
    }

    private static IReadOnlyList<string> ExtractAppleNumericIds(string sourceText)
    {
        if (!Uri.TryCreate(sourceText, UriKind.Absolute, out var uri))
        {
            return [];
        }

        var ids = new List<string>();
        var query = System.Web.HttpUtility.ParseQueryString(uri.Query);
        var trackId = query["i"];
        if (!string.IsNullOrWhiteSpace(trackId))
        {
            return [trackId];
        }

        var pathId = uri.AbsolutePath
            .Split('/', StringSplitOptions.RemoveEmptyEntries)
            .LastOrDefault(segment => segment.All(char.IsDigit));
        if (!string.IsNullOrWhiteSpace(pathId))
        {
            ids.Add(pathId);
        }

        return ids;
    }

    private static string ExtractYouTubePlaylistId(string sourceText)
    {
        if (!Uri.TryCreate(sourceText, UriKind.Absolute, out var uri))
        {
            return string.Empty;
        }

        var query = System.Web.HttpUtility.ParseQueryString(uri.Query);
        return query["list"] ?? string.Empty;
    }

    private static LastFmTarget ParseLastFmTarget(string sourceText)
    {
        var match = LastFmUserRegex.Match(sourceText);
        if (!match.Success)
        {
            return new LastFmTarget(string.Empty, string.Empty, string.Empty);
        }

        var user = Uri.UnescapeDataString(match.Groups["user"].Value);
        var path = match.Groups["path"].Value.ToLowerInvariant();
        if (path.Contains("loved", StringComparison.OrdinalIgnoreCase))
        {
            return new LastFmTarget(user, "user.getlovedtracks", "lastfm:loved");
        }

        if (path.Contains("toptracks", StringComparison.OrdinalIgnoreCase))
        {
            return new LastFmTarget(user, "user.gettoptracks", "lastfm:top-tracks");
        }

        return new LastFmTarget(user, "user.getrecenttracks", "lastfm:recent-tracks");
    }

    private static string ExtractMeta(string html, string property)
    {
        var escaped = Regex.Escape(property);
        var match = Regex.Match(
            html,
            $"""<meta[^>]+(?:property|name)=["']{escaped}["'][^>]+content=["'](?<value>[^"']+)["'][^>]*>""",
            RegexOptions.IgnoreCase);
        if (!match.Success)
        {
            match = Regex.Match(
                html,
                $"""<meta[^>]+content=["'](?<value>[^"']+)["'][^>]+(?:property|name)=["']{escaped}["'][^>]*>""",
                RegexOptions.IgnoreCase);
        }

        return DecodeHtml(match.Success ? match.Groups["value"].Value : string.Empty);
    }

    private static string ExtractTitle(string html)
    {
        var match = Regex.Match(html, @"<title[^>]*>(?<value>.*?)</title>", RegexOptions.IgnoreCase | RegexOptions.Singleline);
        return DecodeHtml(match.Success ? Regex.Replace(match.Groups["value"].Value, @"\s+", " ") : string.Empty);
    }

    private static string CleanProviderTitle(string title, string provider)
    {
        var cleaned = title.Trim();
        var suffixes = provider switch
        {
            "youtube" => new[] { " - YouTube" },
            "bandcamp" => new[] { " | Bandcamp" },
            "lastfm" => new[] { " | Last.fm", " — Last.fm" },
            "apple" => new[] { " by Apple Music", " on Apple Music" },
            _ => [],
        };

        foreach (var suffix in suffixes)
        {
            if (cleaned.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
            {
                cleaned = cleaned[..^suffix.Length].Trim();
            }
        }

        return cleaned.Trim('"');
    }

    private static string FirstNonEmpty(params string[] values)
        => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? string.Empty;

    private static string DecodeHtml(string value)
        => System.Net.WebUtility.HtmlDecode(value).Trim();

    private static string BuildSearchText(string title, string artist, string album)
    {
        var parts = new[] { artist, title, album }
            .Select(part => part.Trim())
            .Where(part => !string.IsNullOrWhiteSpace(part))
            .ToArray();

        return parts.Length >= 2 || string.IsNullOrWhiteSpace(artist)
            ? string.Join(" ", parts)
            : string.Empty;
    }

    private static string NormalizeKey(string value)
        => Regex.Replace(value.Trim().ToLowerInvariant(), @"\s+", " ");

    private static int FindColumn(IReadOnlyList<string> header, params string[] names)
    {
        for (var index = 0; index < header.Count; index++)
        {
            if (names.Contains(NormalizeHeader(header[index]), StringComparer.OrdinalIgnoreCase))
            {
                return index;
            }
        }

        return -1;
    }

    private static string GetCell(IReadOnlyList<string> row, int index)
        => index >= 0 && index < row.Count ? row[index].Trim() : string.Empty;

    private static bool LooksLikeHeader(IReadOnlyList<string> row)
    {
        return row
            .Select(NormalizeHeader)
            .Any(value => value is "trackname" or "track" or "title" or "songname" or "song" or "artistname" or "artist" or "artists" or "albumname" or "album");
    }

    private static string NormalizeHeader(string value)
    {
        var builder = new StringBuilder();
        foreach (var ch in value)
        {
            if (char.IsLetterOrDigit(ch))
            {
                builder.Append(char.ToLowerInvariant(ch));
            }
        }

        return builder.ToString();
    }

    private static List<List<string>> ParseDelimitedRows(string csvText)
    {
        var rows = new List<List<string>>();
        var row = new List<string>();
        var field = new StringBuilder();
        var inQuotes = false;

        for (var index = 0; index < csvText.Length; index++)
        {
            var ch = csvText[index];
            if (ch == '"')
            {
                if (inQuotes && index + 1 < csvText.Length && csvText[index + 1] == '"')
                {
                    field.Append('"');
                    index++;
                }
                else
                {
                    inQuotes = !inQuotes;
                }
            }
            else if (ch == ',' && !inQuotes)
            {
                row.Add(field.ToString());
                field.Clear();
            }
            else if ((ch == '\n' || ch == '\r') && !inQuotes)
            {
                if (ch == '\r' && index + 1 < csvText.Length && csvText[index + 1] == '\n')
                {
                    index++;
                }

                row.Add(field.ToString());
                field.Clear();
                AddDelimitedRow(rows, row);
                row = [];
            }
            else
            {
                field.Append(ch);
            }
        }

        row.Add(field.ToString());
        AddDelimitedRow(rows, row);
        return rows;
    }

    private static void AddDelimitedRow(List<List<string>> rows, List<string> row)
    {
        if (row.Any(value => !string.IsNullOrWhiteSpace(value)))
        {
            rows.Add(row);
        }
    }

    private sealed record SourceFeedRow(
        string Title,
        string Artist,
        string Album,
        string Source,
        string SourceId,
        string ProviderUrl,
        string RawText);

    private sealed record SpotifyTarget(string Type, string Id, bool RequiresUserToken, string ScopeHint);

    private sealed record SpotifyTokenResponse([property: JsonPropertyName("access_token")] string AccessToken);

    private sealed record SpotifyPaging<T>
    {
        public int Total { get; init; }

        public string? Next { get; init; }

        public List<T> Items { get; init; } = [];
    }

    private sealed record SpotifyPlaylistItem(SpotifyTrack? Track);

    private sealed record SpotifySavedTrack(SpotifyTrack? Track);

    private sealed record SpotifySavedAlbum(SpotifyAlbum? Album);

    private sealed record SpotifyTopTracks(List<SpotifyTrack> Tracks);

    private sealed record SpotifyFollowedArtists(SpotifyArtistPaging Artists);

    private sealed record SpotifyArtistPaging
    {
        public List<SpotifyArtist> Items { get; init; } = [];

        public SpotifyCursor? Cursors { get; init; }
    }

    private sealed record SpotifyCursor(string? After);

    private sealed record SpotifyPlaylistSummary(string Id);

    private sealed record SpotifyTrack
    {
        public string Id { get; init; } = string.Empty;

        public string Name { get; init; } = string.Empty;

        public SpotifyAlbumSummary? Album { get; init; }

        public List<SpotifyArtist> Artists { get; init; } = [];

        [JsonPropertyName("external_urls")]
        public SpotifyExternalUrls? ExternalUrls { get; init; }
    }

    private sealed record SpotifyAlbum
    {
        public string Id { get; init; } = string.Empty;

        public string Name { get; init; } = string.Empty;

        public List<SpotifyArtist> Artists { get; init; } = [];

        public SpotifyPaging<SpotifyTrack>? Tracks { get; init; }

        [JsonPropertyName("external_urls")]
        public SpotifyExternalUrls? ExternalUrls { get; init; }
    }

    private sealed record SpotifyAlbumSummary
    {
        public string Name { get; init; } = string.Empty;
    }

    private sealed record SpotifyArtist
    {
        public string Id { get; init; } = string.Empty;

        public string Name { get; init; } = string.Empty;

        [JsonPropertyName("external_urls")]
        public SpotifyExternalUrls? ExternalUrls { get; init; }
    }

    private sealed record SpotifyExternalUrls
    {
        public string Spotify { get; init; } = string.Empty;
    }

    private sealed record AppleLookupResponse
    {
        public List<AppleLookupItem> Results { get; init; } = [];
    }

    private sealed record AppleLookupItem
    {
        public long TrackId { get; init; }

        public string TrackName { get; init; } = string.Empty;

        public string ArtistName { get; init; } = string.Empty;

        public string CollectionName { get; init; } = string.Empty;

        public string TrackViewUrl { get; init; } = string.Empty;
    }

    private sealed record ListenBrainzListensResponse
    {
        public ListenBrainzPayload? Payload { get; init; }
    }

    private sealed record ListenBrainzPayload
    {
        public List<ListenBrainzListen> Listens { get; init; } = [];
    }

    private sealed record ListenBrainzListen
    {
        [JsonPropertyName("track_metadata")]
        public ListenBrainzTrackMetadata? TrackMetadata { get; init; }
    }

    private sealed record ListenBrainzTrackMetadata
    {
        [JsonPropertyName("artist_name")]
        public string ArtistName { get; init; } = string.Empty;

        [JsonPropertyName("track_name")]
        public string TrackName { get; init; } = string.Empty;

        [JsonPropertyName("release_name")]
        public string ReleaseName { get; init; } = string.Empty;

        [JsonPropertyName("additional_info")]
        public ListenBrainzAdditionalInfo? AdditionalInfo { get; init; }
    }

    private sealed record ListenBrainzAdditionalInfo
    {
        [JsonPropertyName("recording_msid")]
        public string RecordingMsid { get; init; } = string.Empty;
    }

    private sealed record YouTubePlaylistItemsResponse
    {
        public string NextPageToken { get; init; } = string.Empty;

        public List<YouTubePlaylistItem> Items { get; init; } = [];
    }

    private sealed record YouTubePlaylistItem
    {
        public YouTubeSnippet? Snippet { get; init; }
    }

    private sealed record YouTubeSnippet
    {
        public string Title { get; init; } = string.Empty;

        public YouTubeResourceId? ResourceId { get; init; }
    }

    private sealed record YouTubeResourceId
    {
        public string VideoId { get; init; } = string.Empty;
    }

    private sealed record LastFmTarget(string User, string Method, string Source);

    private sealed record LastFmTracksResponse
    {
        [JsonPropertyName("recenttracks")]
        public LastFmTrackContainer? RecentTracks { get; init; }

        [JsonPropertyName("lovedtracks")]
        public LastFmTrackContainer? LovedTracks { get; init; }

        [JsonPropertyName("toptracks")]
        public LastFmTrackContainer? TopTracks { get; init; }
    }

    private sealed record LastFmTrackContainer
    {
        public List<LastFmTrack> Track { get; init; } = [];
    }

    private sealed record LastFmTrack
    {
        public string Name { get; init; } = string.Empty;

        public string Mbid { get; init; } = string.Empty;

        public string Url { get; init; } = string.Empty;

        public LastFmNamedValue? Artist { get; init; }

        public LastFmTextValue? Album { get; init; }
    }

    private sealed record LastFmNamedValue
    {
        public string Name { get; init; } = string.Empty;

        [JsonPropertyName("#text")]
        public string Text { get; init; } = string.Empty;
    }

    private sealed record LastFmTextValue
    {
        [JsonPropertyName("#text")]
        public string Text { get; init; } = string.Empty;
    }
}
