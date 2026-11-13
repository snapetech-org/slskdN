// <copyright file="SourceFeedImportServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Tests.Unit.SourceFeeds;

using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using slskd.SourceFeeds;
using Xunit;

public class SourceFeedImportServiceTests
{
    [Fact]
    public async Task PreviewAsync_CsvRows_ReturnsSuggestionsWithoutNetwork()
    {
        var handler = new QueueHttpHandler();
        var service = CreateService(handler);

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "Track name,Artist name,Album name\nSong,Artist,Album",
            SourceKind = "csv",
            IncludeAlbum = true,
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song Album", suggestion.SearchText);
        Assert.Equal("csv", result.SourceKind);
        Assert.Equal(0, handler.Requests.Count);
    }

    [Fact]
    public async Task PreviewAsync_SpotifyLikedWithoutToken_ReturnsScopeHint()
    {
        var service = CreateService(new QueueHttpHandler());

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "spotify:liked",
            SourceKind = "spotify",
        });

        Assert.True(result.RequiresAccessToken);
        Assert.Equal("user-library-read", result.RequiredScopeHint);
        Assert.Empty(result.Suggestions);
    }

    [Fact]
    public async Task PreviewAsync_DeduplicatesRepeatedLocalRows()
    {
        var handler = new QueueHttpHandler();
        var service = CreateService(handler);

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "Artist - Song\nartist - song",
            SourceKind = "text",
        });

        Assert.Single(result.Suggestions);
        Assert.Equal(1, result.DuplicateCount);
        Assert.Equal(0, handler.Requests.Count);
    }

    [Fact]
    public async Task PreviewAsync_SpotifyPlaylist_FetchesPlaylistItems()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson("""{"access_token":"app-token"}""");
        handler.EnqueueJson(
            """
            {
              "total": 1,
              "items": [
                {
                  "track": {
                    "id": "track-1",
                    "name": "Song",
                    "album": { "name": "Album" },
                    "artists": [{ "id": "artist-1", "name": "Artist" }],
                    "external_urls": { "spotify": "https://open.spotify.com/track/track-1" }
                  }
                }
              ]
            }
            """);
        var service = CreateService(handler, spotifyEnabled: true);

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "https://open.spotify.com/playlist/playlist-1",
            SourceKind = "spotify",
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song Album", suggestion.SearchText);
        Assert.Equal("spotify:playlist", suggestion.Source);
        Assert.Equal(2, handler.Requests.Count);
        Assert.Contains("/v1/playlists/playlist-1/items", handler.Requests[1].RequestUri!.ToString());
    }

    [Fact]
    public async Task PreviewAsync_SpotifyLikedWithConnectedAccount_UsesStoredToken()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson(
            """
            {
              "total": 1,
              "items": [
                {
                  "track": {
                    "id": "track-1",
                    "name": "Song",
                    "album": { "name": "Album" },
                    "artists": [{ "id": "artist-1", "name": "Artist" }],
                    "external_urls": { "spotify": "https://open.spotify.com/track/track-1" }
                  }
                }
              ]
            }
            """);
        var service = CreateService(handler, connectedSpotifyToken: "connected-token");

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "spotify:liked",
            SourceKind = "spotify",
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song Album", suggestion.SearchText);
        Assert.False(result.RequiresAccessToken);
        Assert.Equal("Bearer", handler.Requests[0].Headers.Authorization?.Scheme);
        Assert.Equal("connected-token", handler.Requests[0].Headers.Authorization?.Parameter);
    }

    [Fact]
    public async Task PreviewAsync_AppleMusicUrl_FetchesItunesLookupRows()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson(
            """
            {
              "resultCount": 1,
              "results": [
                {
                  "trackId": 123,
                  "trackName": "Song",
                  "artistName": "Artist",
                  "collectionName": "Album",
                  "trackViewUrl": "https://music.apple.com/us/album/song/456?i=123"
                }
              ]
            }
            """);
        var service = CreateService(handler);

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "https://music.apple.com/us/album/album/456?i=123",
            SourceKind = "auto",
            FetchProviderUrls = true,
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song Album", suggestion.SearchText);
        Assert.Equal("apple", suggestion.Source);
        Assert.Equal(1, result.NetworkRequestCount);
        Assert.Contains("itunes.apple.com/lookup?id=123", handler.Requests[0].RequestUri!.ToString());
    }

    [Fact]
    public async Task PreviewAsync_ListenBrainzUserUrl_FetchesPublicListens()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson(
            """
            {
              "payload": {
                "listens": [
                  {
                    "track_metadata": {
                      "artist_name": "Artist",
                      "track_name": "Song",
                      "release_name": "Album",
                      "additional_info": { "recording_msid": "msid-1" }
                    }
                  }
                ]
              }
            }
            """);
        var service = CreateService(handler);

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "https://listenbrainz.org/user/demo/listens/",
            SourceKind = "auto",
            FetchProviderUrls = true,
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song Album", suggestion.SearchText);
        Assert.Equal("listenbrainz:listens", suggestion.Source);
        Assert.Equal("msid-1", suggestion.SourceId);
        Assert.Contains("/1/user/demo/listens", handler.Requests[0].RequestUri!.ToString());
    }

    [Fact]
    public async Task PreviewAsync_ProviderMetadataPage_FallsBackToOgTitle()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueHtml(
            """
            <html>
              <head>
                <meta property="og:title" content="Artist - Song | Bandcamp">
              </head>
            </html>
            """);
        var service = CreateService(handler);

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "https://artist.bandcamp.com/track/song",
            SourceKind = "auto",
            FetchProviderUrls = true,
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song", suggestion.SearchText);
        Assert.Equal("bandcamp", suggestion.Source);
        Assert.Equal("https://artist.bandcamp.com/track/song", suggestion.ProviderUrl);
    }

    [Fact]
    public async Task PreviewAsync_YouTubePlaylistWithApiKey_FetchesPlaylistItems()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson(
            """
            {
              "items": [
                {
                  "snippet": {
                    "title": "Artist - Song",
                    "resourceId": { "videoId": "video-1" }
                  }
                }
              ]
            }
            """);
        var service = CreateService(handler, youtubeApiKey: "youtube-key");

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "https://www.youtube.com/playlist?list=playlist-1",
            SourceKind = "auto",
            FetchProviderUrls = true,
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song", suggestion.SearchText);
        Assert.Equal("youtube:playlist", suggestion.Source);
        Assert.Equal("video-1", suggestion.SourceId);
        Assert.Contains("playlistItems", handler.Requests[0].RequestUri!.ToString());
        Assert.Contains("playlistId=playlist-1", handler.Requests[0].RequestUri!.ToString());
    }

    [Fact]
    public async Task PreviewAsync_LastFmLovedWithApiKey_FetchesLovedTracks()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson(
            """
            {
              "lovedtracks": {
                "track": [
                  {
                    "name": "Song",
                    "mbid": "recording-1",
                    "url": "https://www.last.fm/music/Artist/_/Song",
                    "artist": { "name": "Artist" }
                  }
                ]
              }
            }
            """);
        var service = CreateService(handler, lastFmApiKey: "lastfm-key");

        var result = await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "https://www.last.fm/user/demo/loved",
            SourceKind = "auto",
            FetchProviderUrls = true,
        });

        var suggestion = Assert.Single(result.Suggestions);
        Assert.Equal("Artist Song", suggestion.SearchText);
        Assert.Equal("lastfm:loved", suggestion.Source);
        Assert.Equal("recording-1", suggestion.SourceId);
        Assert.Contains("method=user.getlovedtracks", handler.Requests[0].RequestUri!.ToString());
    }

    [Fact]
    public async Task PreviewAsync_RecordsRestartSafeHistory()
    {
        var storagePath = CreateStoragePath();
        var service = CreateService(new QueueHttpHandler(), storagePath: storagePath);

        await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "Track name,Artist name,Album name\nSong,Artist,Album",
            SourceKind = "csv",
            IncludeAlbum = true,
            Limit = 20,
        });

        var reloaded = CreateService(new QueueHttpHandler(), storagePath: storagePath);
        var history = await reloaded.GetHistoryAsync();

        var entry = Assert.Single(history);
        Assert.Equal("local", entry.Provider);
        Assert.Equal("csv", entry.SourceKind);
        Assert.Equal(1, entry.SuggestionCount);
        Assert.Equal(0, entry.NetworkRequestCount);
        Assert.Equal(20, entry.Limit);
        Assert.True(entry.IncludeAlbum);
        Assert.NotEmpty(entry.SourceFingerprint);
        Assert.Contains("Track name", entry.SourcePreview);
        Assert.Single(entry.Suggestions);
        Assert.Empty(entry.SkippedRows);
    }

    [Fact]
    public async Task PreviewAsync_HistoryStoresSamplesWithoutProviderToken()
    {
        var handler = new QueueHttpHandler();
        handler.EnqueueJson(
            """
            {
              "total": 1,
              "items": [
                {
                  "track": {
                    "id": "track-1",
                    "name": "Song",
                    "album": { "name": "Album" },
                    "artists": [{ "id": "artist-1", "name": "Artist" }],
                    "external_urls": { "spotify": "https://open.spotify.com/track/track-1" }
                  }
                }
              ]
            }
            """);
        var service = CreateService(handler);

        await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "spotify:liked",
            SourceKind = "spotify",
            ProviderAccessToken = "sensitive-provider-token",
        });
        var history = await service.GetHistoryAsync();

        var entry = Assert.Single(history);
        Assert.Equal("spotify", entry.Provider);
        Assert.Equal("saved-tracks", entry.SourceKind);
        Assert.Equal(1, entry.NetworkRequestCount);
        var suggestion = Assert.Single(entry.Suggestions);
        Assert.Equal("Artist Song Album", suggestion.SearchText);
        Assert.DoesNotContain("sensitive-provider-token", JsonSerializer.Serialize(entry));
    }

    [Fact]
    public async Task GetHistoryEntryAsync_ReturnsMatchingImportRun()
    {
        var service = CreateService(new QueueHttpHandler());
        await service.PreviewAsync(new SourceFeedImportRequest
        {
            SourceText = "Artist - Song",
            SourceKind = "text",
        });
        var history = await service.GetHistoryAsync();

        var entry = await service.GetHistoryEntryAsync(history[0].ImportId);
        var missing = await service.GetHistoryEntryAsync("missing");

        Assert.NotNull(entry);
        Assert.Equal(history[0].ImportId, entry.ImportId);
        Assert.Null(missing);
    }

    private static SourceFeedImportService CreateService(
        QueueHttpHandler handler,
        bool spotifyEnabled = false,
        string connectedSpotifyToken = "",
        string youtubeApiKey = "",
        string lastFmApiKey = "",
        string? storagePath = null)
    {
        var httpClient = new HttpClient(handler);
        var factory = new Mock<IHttpClientFactory>();
        factory.Setup(x => x.CreateClient(It.IsAny<string>())).Returns(httpClient);
        var options = new Mock<IOptionsMonitor<global::slskd.Options>>();
        options.SetupGet(x => x.CurrentValue).Returns(new global::slskd.Options
        {
            Integration = new global::slskd.Options.IntegrationOptions
            {
                Spotify = new global::slskd.Options.IntegrationOptions.SpotifyOptions
                {
                    Enabled = spotifyEnabled,
                    ClientId = spotifyEnabled ? "client" : string.Empty,
                    ClientSecret = spotifyEnabled ? "secret" : string.Empty,
                },
                YouTube = new global::slskd.Options.IntegrationOptions.YouTubeOptions
                {
                    Enabled = !string.IsNullOrWhiteSpace(youtubeApiKey),
                    ApiKey = youtubeApiKey,
                },
                LastFm = new global::slskd.Options.IntegrationOptions.LastFmOptions
                {
                    Enabled = !string.IsNullOrWhiteSpace(lastFmApiKey),
                    ApiKey = lastFmApiKey,
                },
            },
        });

        var spotifyConnection = new Mock<ISpotifyConnectionService>();
        spotifyConnection
            .Setup(x => x.GetAccessTokenAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(connectedSpotifyToken);

        return new SourceFeedImportService(
            factory.Object,
            options.Object,
            spotifyConnection.Object,
            NullLogger<SourceFeedImportService>.Instance,
            storagePath ?? CreateStoragePath(),
            static (_, _) => Task.FromResult<(bool Safe, string Reason)>((true, string.Empty)));
    }

    private static string CreateStoragePath()
    {
        return Path.Combine(Path.GetTempPath(), "slskdn-source-feed-tests", $"{Guid.NewGuid():N}.json");
    }

    private sealed class QueueHttpHandler : HttpMessageHandler
    {
        private readonly Queue<HttpResponseMessage> responses = new();

        public List<HttpRequestMessage> Requests { get; } = [];

        public void EnqueueJson(string json)
        {
            responses.Enqueue(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(json, Encoding.UTF8, "application/json"),
            });
        }

        public void EnqueueHtml(string html)
        {
            responses.Enqueue(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(html, Encoding.UTF8, "text/html"),
            });
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Requests.Add(request);
            return Task.FromResult(responses.Dequeue());
        }
    }
}
