// <copyright file="HashDbServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.HashDb;

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using slskd.Events;
using slskd.Audio;
using slskd.HashDb;
using slskd.HashDb.Models;
using slskd.Integrations.MusicBrainz.Models;
using slskd.Jobs;
using slskd.LibraryHealth;
using slskd.Transfers.MultiSource.Metrics;
using Xunit;

[Collection(AllocationTestCollection.Name)]
public class HashDbServiceTests : IDisposable
{
    private readonly string testDir;
    private readonly HashDbService service;

    public HashDbServiceTests()
    {
        testDir = Path.Combine(Path.GetTempPath(), $"hashdb-test-{Guid.NewGuid()}");
        Directory.CreateDirectory(testDir);
        service = new HashDbService(testDir);
    }

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        if (Directory.Exists(testDir))
        {
            Directory.Delete(testDir, recursive: true);
        }
    }

    [Fact]
    public void Constructor_InitializesDatabase()
    {
        var dbPath = Path.Combine(testDir, "hashdb.db");
        Assert.True(File.Exists(dbPath));
    }

    [Fact]
    public void Constructor_InitializesSeqIdToZero()
    {
        Assert.Equal(0, service.CurrentSeqId);
    }

    [Fact]
    public async Task Constructor_IndexesNormalizedRecordingIdPages()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT DISTINCT TRIM(musicbrainz_id) COLLATE NOCASE AS recording_id
            FROM HashDb
            WHERE musicbrainz_id IS NOT NULL AND TRIM(musicbrainz_id) <> ''
              AND TRIM(musicbrainz_id) COLLATE NOCASE > 'm-recording'
            ORDER BY recording_id COLLATE NOCASE
            LIMIT 100
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH HashDb USING INDEX idx_hashdb_recording_normalized", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesBatchedRecordingPresenceQueryWithoutTemporarySort()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT TRIM(musicbrainz_id)
            FROM HashDb
            WHERE musicbrainz_id IS NOT NULL
              AND TRIM(musicbrainz_id) <> ''
              AND TRIM(musicbrainz_id) COLLATE NOCASE IN ('recording-a', 'recording-b')
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH HashDb USING INDEX idx_hashdb_recording_normalized", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesBatchedAlbumTrackQueryWithoutTemporarySort()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT release_id, track_position, recording_id, title, artist, duration_ms, isrc
            FROM AlbumTargetTracks
            WHERE release_id IN ('release-1', 'release-2')
            ORDER BY release_id ASC, track_position ASC
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH AlbumTargetTracks USING INDEX", StringComparison.Ordinal) &&
            detail.Contains("release_id=?", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesCaseInsensitiveRecordingTrackLookup()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT track.release_id, track.track_position, track.recording_id, track.title, track.artist, track.duration_ms, track.isrc
            FROM AlbumTargetTracks AS track
            INNER JOIN AlbumTargets AS album ON album.release_id = track.release_id
            WHERE track.recording_id IS NOT NULL
              AND track.recording_id <> ''
              AND track.recording_id = 'RECORDING-1' COLLATE NOCASE
            ORDER BY album.created_at DESC, track.track_position ASC
            LIMIT 1
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH track USING INDEX idx_album_tracks_recording_nocase", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("SCAN track", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesBoundedRecentAlbumTrackQuery()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT track.release_id, track.track_position, track.recording_id, track.title, track.artist, track.duration_ms, track.isrc
            FROM AlbumTargets AS album INDEXED BY idx_album_targets_created
            INNER JOIN AlbumTargetTracks AS track ON track.release_id = album.release_id
            ORDER BY album.created_at DESC, track.track_position ASC
            LIMIT 50
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SCAN album USING INDEX idx_album_targets_created", StringComparison.Ordinal));
        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH track USING INDEX", StringComparison.Ordinal) &&
            detail.Contains("release_id=?", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("SCAN track", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesBatchedHashEvidenceQueryWithoutTemporarySort()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM HashDb
            WHERE musicbrainz_id IN ('recording-1', 'recording-2')
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH HashDb USING INDEX idx_hashdb_musicbrainz_id", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesCanonicalStatsRecordingLookup()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            "EXPLAIN QUERY PLAN SELECT * FROM CanonicalStats WHERE musicbrainz_recording_id = 'recording-1'";

        await using var reader = await cmd.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        var plan = reader.GetString(3);

        Assert.Contains("SEARCH CanonicalStats USING INDEX idx_canonical_recording", plan, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Constructor_IndexesPeerCapabilityStatsQuery()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM Peers WHERE caps > 0";

        await using var reader = await cmd.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        var plan = reader.GetString(3);

        Assert.Contains("idx_peers_caps", plan, StringComparison.Ordinal);
    }

    [Fact]
    public void GetStats_ReturnsZeroCountsForEmptyDb()
    {
        // Act
        var stats = service.GetStats();

        // Assert
        Assert.Equal(0, stats.TotalPeers);
        Assert.Equal(0, stats.SlskdnPeers);
        Assert.Equal(0, stats.TotalFlacEntries);
        Assert.Equal(0, stats.HashedFlacEntries);
        Assert.Equal(0, stats.TotalHashEntries);
        Assert.True(stats.DatabaseSizeBytes > 0); // SQLite creates some base tables
    }

    [Fact]
    public async Task GetStats_AggregatesPopulatedTablesInOneSnapshot()
    {
        await service.UpdatePeerCapabilitiesAsync(
            "capable-peer",
            slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync);
        await service.TouchPeerAsync("plain-peer");
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "capable-peer",
            Path = "/music/known.flac",
            Size = 50_000_000,
            HashStatusStr = "known",
        });
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "plain-peer",
            Path = "/music/pending.flac",
            Size = 50_000_001,
            HashStatusStr = "none",
        });
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "hash-key",
            ByteHash = "byte-hash",
            Size = 50_000_000,
        });

        var stats = service.GetStats();

        Assert.Equal(2, stats.TotalPeers);
        Assert.Equal(1, stats.SlskdnPeers);
        Assert.Equal(2, stats.TotalFlacEntries);
        Assert.Equal(1, stats.HashedFlacEntries);
        Assert.Equal(1, stats.TotalHashEntries);
        Assert.Equal(1, stats.CurrentSeqId);
    }

    // ========== Peer Management Tests ==========

    [Fact]
    public async Task GetOrCreatePeerAsync_CreatesNewPeer()
    {
        // Act
        var peer = await service.GetOrCreatePeerAsync("testuser");

        // Assert
        Assert.NotNull(peer);
        Assert.Equal("testuser", peer.PeerId);
        Assert.True(peer.LastSeen > 0);
    }

    [Fact]
    public async Task GetOrCreatePeerAsync_ReturnsExistingPeer()
    {
        // Arrange
        await service.GetOrCreatePeerAsync("testuser");

        // Act
        var peer = await service.GetOrCreatePeerAsync("testuser");

        // Assert
        Assert.NotNull(peer);
        Assert.Equal("testuser", peer.PeerId);
    }

    [Fact]
    public async Task GetOrCreatePeerAsync_WithConcurrentSamePeer_ReturnsSinglePeer()
    {
        const string username = "testuser";
        using var start = new ManualResetEventSlim();

        var tasks = Enumerable.Range(0, 32)
            .Select(_ => Task.Run(async () =>
            {
                start.Wait();
                return await service.GetOrCreatePeerAsync(username);
            }))
            .ToArray();

        start.Set();
        var peers = await Task.WhenAll(tasks);

        Assert.All(peers, peer => Assert.Equal(username, peer.PeerId));

        var stats = service.GetStats();
        Assert.Equal(1, stats.TotalPeers);
    }

    [Fact]
    public async Task TouchPeerAsync_NormalizesCreatesAndPreservesCapabilities()
    {
        await service.UpdatePeerCapabilitiesAsync(
            "testuser",
            slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync,
            "slskdn/1.0");
        await using (var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await conn.OpenAsync();
            await using var cmd = conn.CreateCommand();
            cmd.CommandText = "UPDATE Peers SET last_seen = 1, backfills_today = 3, backfill_reset_date = 2 WHERE peer_id = 'testuser'";
            await cmd.ExecuteNonQueryAsync();
        }

        await service.TouchPeerAsync(" testuser ");
        await service.TouchPeerAsync(" new-peer ");

        var peer = Assert.Single(await service.GetSlskdnPeersAsync());
        Assert.Equal("testuser", peer.PeerId);
        Assert.Equal((int)slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync, peer.Caps);
        Assert.Equal("slskdn/1.0", peer.ClientVersion);
        Assert.True(peer.LastSeen > 1);
        Assert.Equal(3, peer.BackfillsToday);
        Assert.Equal(2, peer.BackfillResetDate);
        Assert.Equal("new-peer", (await service.GetOrCreatePeerAsync("new-peer")).PeerId);
    }

    [Fact]
    public async Task UpdatePeerCapabilitiesAsync_CreatesAndPreservesVersionWhenOmitted()
    {
        await service.UpdatePeerCapabilitiesAsync(" testuser ", slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync, " slskdn/1.0 ");
        await service.UpdatePeerCapabilitiesAsync("testuser", slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync);

        var peers = await service.GetSlskdnPeersAsync();
        var peer = Assert.Single(peers);
        Assert.Equal("testuser", peer.PeerId);
        Assert.Equal((int)slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync, peer.Caps);
        Assert.Equal("slskdn/1.0", peer.ClientVersion);
        Assert.NotNull(peer.LastCapCheck);
    }

    // ========== FLAC Inventory Tests ==========

    [Fact]
    public async Task UpsertFlacEntryAsync_InsertsNewEntry()
    {
        var entry = new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
            HashStatusStr = "none",
        };

        await service.UpsertFlacEntryAsync(entry);
        var stats = service.GetStats();
        Assert.Equal(1, stats.TotalFlacEntries);
    }

    [Fact]
    public async Task UpsertFlacEntryAsync_GeneratesFileId()
    {
        // Arrange
        var entry = new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
        };

        // Act
        await service.UpsertFlacEntryAsync(entry);

        // Assert
        Assert.NotNull(entry.FileId);
        Assert.NotEmpty(entry.FileId);
    }

    [Fact]
    public async Task UpsertFlacEntryAsync_UpdatesExistingEntry()
    {
        // Arrange
        var entry = new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
            HashStatusStr = "none",
        };
        await service.UpsertFlacEntryAsync(entry);

        // Act - Update with hash
        entry.HashStatusStr = "known";
        entry.HashValue = "abc123";
        await service.UpsertFlacEntryAsync(entry);

        // Assert
        var retrieved = await service.GetFlacEntryAsync(entry.FileId);
        Assert.NotNull(retrieved);
        Assert.Equal("known", retrieved.HashStatusStr);
    }

    [Fact]
    public async Task PassiveFlacBatchHelpers_BoundInventoryAndPeerCommands()
    {
        var entries = Enumerable.Range(1, 201)
            .Select(index => new FlacInventoryEntry
            {
                PeerId = $"peer-{index}",
                Path = $"/music/track-{index}.flac",
                Size = 50_000_000 + index,
                HashStatusStr = "none",
            })
            .ToList();
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        using var transaction = conn.BeginTransaction();

        var ingestion = await HashDbService.UpsertFlacEntriesInBatchesAsync(
            conn,
            transaction,
            entries,
            CancellationToken.None);
        var peerCommands = await HashDbService.UpsertPeersInBatchesAsync(
            conn,
            transaction,
            entries.Select(entry => entry.PeerId),
            CancellationToken.None);
        transaction.Commit();

        Assert.Equal(201, ingestion.AffectedRows);
        Assert.Equal(3, ingestion.CommandCount);
        Assert.Equal(1, peerCommands);
        Assert.Equal(201, service.GetStats().TotalFlacEntries);
        await using var peerCountCommand = conn.CreateCommand();
        peerCountCommand.CommandText = "SELECT COUNT(*) FROM Peers";
        Assert.Equal(201L, (long)(await peerCountCommand.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task BackfillFromSearchResponsesAsync_PersistsBoundedFilesAndPeers()
    {
        var responses = Enumerable.Range(1, 100)
            .Select(index => new slskd.Search.Response
            {
                Username = $"peer-{index}",
                Files = new[]
                {
                    new slskd.Search.File
                    {
                        Filename = $"/music/track-{index}.flac",
                        Size = 50_000_000 + index,
                    },
                    new slskd.Search.File
                    {
                        Filename = $"/music/cover-{index}.jpg",
                        Size = 100_000,
                    },
                },
            })
            .ToList();

        var count = await service.BackfillFromSearchResponsesAsync(responses);

        Assert.Equal(100, count);
        Assert.Equal(100, service.GetStats().TotalFlacEntries);
        await service.UpdatePeerCapabilitiesAsync(
            "peer-100",
            slskd.Capabilities.PeerCapabilityFlags.SupportsMeshSync);
        Assert.Contains(await service.GetSlskdnPeersAsync(), peer => peer.PeerId == "peer-100");
    }

    [Fact]
    public async Task GetAlbumTargetsAsync_ReturnsStoredTarget()
    {
        var target = new AlbumTarget
        {
            MusicBrainzReleaseId = "mb:abc",
            Title = "Test Album",
            Artist = "Test Artist",
            Metadata = new ReleaseMetadata { ReleaseDate = DateOnly.FromDateTime(DateTime.UtcNow) },
            Tracks = new[]
            {
                new TrackTarget
                {
                    MusicBrainzRecordingId = "rec:1",
                    Position = 1,
                    Title = "Track One",
                    Artist = "Test Artist",
                    Duration = TimeSpan.FromSeconds(180),
                }
            }
        };

        await service.UpsertAlbumTargetAsync(target);
        var stored = (await service.GetAlbumTargetsAsync()).Single();

        Assert.Equal("Test Album", stored.Title);
        Assert.Equal("Test Artist", stored.Artist);
        Assert.Equal(target.Metadata.ReleaseDate?.ToString("yyyy-MM-dd"), stored.ReleaseDate);
    }

    [Fact]
    public async Task GetAlbumTargetsAsync_WithReleaseBatch_ReturnsRequestedTargets()
    {
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-1",
            Title = "Album One",
            Artist = "Artist",
        });
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-2",
            Title = "Album Two",
            Artist = "Artist",
        });

        var targets = (await service.GetAlbumTargetsAsync(new[]
        {
            " release-2 ",
            "release-1",
            "release-2",
            "missing",
        })).ToList();

        Assert.Equal(2, targets.Count);
        Assert.Equal(
            new[] { "release-1", "release-2" },
            targets.Select(target => target.ReleaseId).OrderBy(releaseId => releaseId));
    }

    [Fact]
    public async Task UpsertAlbumTargetAsync_TrimsStoredAlbumAndTrackFields()
    {
        var target = new AlbumTarget
        {
            MusicBrainzReleaseId = " mb:release-1 ",
            DiscogsReleaseId = " discogs-1 ",
            Title = " Test Album ",
            Artist = " Test Artist ",
            Metadata = new ReleaseMetadata
            {
                Country = " US ",
                Label = " Test Label ",
                Status = " Official ",
            },
            Tracks = new[]
            {
                new TrackTarget
                {
                    MusicBrainzRecordingId = " rec:1 ",
                    Position = 1,
                    Title = " Track One ",
                    Artist = " Test Artist ",
                    Isrc = " US-AAA-01 ",
                }
            }
        };

        await service.UpsertAlbumTargetAsync(target);

        var album = await service.GetAlbumTargetAsync("mb:release-1");
        var track = (await service.GetAlbumTracksAsync("mb:release-1")).Single();

        Assert.NotNull(album);
        Assert.Equal("mb:release-1", album!.ReleaseId);
        Assert.Equal("discogs-1", album.DiscogsReleaseId);
        Assert.Equal("Test Album", album.Title);
        Assert.Equal("Test Artist", album.Artist);
        Assert.Equal("US", album.Country);
        Assert.Equal("Test Label", album.Label);
        Assert.Equal("Official", album.Status);
        Assert.Equal("mb:release-1", track.ReleaseId);
        Assert.Equal("rec:1", track.RecordingId);
        Assert.Equal("Track One", track.Title);
        Assert.Equal("Test Artist", track.Artist);
        Assert.Equal("US-AAA-01", track.Isrc);
    }

    [Fact]
    public async Task UpsertAlbumTargetAsync_BatchesLargeTrackReplacementAndPreservesPositionSemantics()
    {
        var tracks = Enumerable.Range(1, 201)
            .Select(index => new TrackTarget
            {
                Position = 0,
                MusicBrainzRecordingId = $" recording-{index} ",
                Title = $" Track {index} ",
                Artist = " Artist ",
            })
            .Append(new TrackTarget
            {
                Position = 1,
                MusicBrainzRecordingId = "recording-replacement",
                Title = "Replacement",
                Artist = "Artist",
            })
            .ToArray();
        var target = new AlbumTarget
        {
            MusicBrainzReleaseId = "large-release",
            Title = "Large Album",
            Artist = "Artist",
            Tracks = tracks,
        };

        await service.UpsertAlbumTargetAsync(target);

        var stored = (await service.GetAlbumTracksAsync("large-release")).ToList();
        Assert.Equal(201, stored.Count);
        Assert.Equal(Enumerable.Range(1, 201), stored.Select(track => track.Position));
        Assert.Equal("recording-replacement", stored[0].RecordingId);
        Assert.Equal("Replacement", stored[0].Title);
        Assert.Equal("recording-201", stored[^1].RecordingId);

        await service.UpsertAlbumTargetAsync(target with
        {
            Tracks = new[]
            {
                new TrackTarget { Position = 0, MusicBrainzRecordingId = "new-1", Title = "New One" },
                new TrackTarget { Position = 0, MusicBrainzRecordingId = "new-2", Title = "New Two" },
            },
        });

        var replaced = (await service.GetAlbumTracksAsync("large-release")).ToList();
        Assert.Equal(2, replaced.Count);
        Assert.Equal(new[] { "new-1", "new-2" }, replaced.Select(track => track.RecordingId));
    }

    [Fact]
    public async Task GetAlbumTracksAsync_WithReleaseBatch_ReturnsRequestedTracks()
    {
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-1",
            Title = "Album One",
            Artist = "Artist",
            Tracks = new[]
            {
                new TrackTarget { Position = 1, MusicBrainzRecordingId = "recording-1", Title = "One" },
            },
        });
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-2",
            Title = "Album Two",
            Artist = "Artist",
            Tracks = new[]
            {
                new TrackTarget { Position = 1, MusicBrainzRecordingId = "recording-2", Title = "Two" },
            },
        });

        var tracks = (await service.GetAlbumTracksAsync(new[]
        {
            " release-1 ",
            "release-1",
            "release-2",
            "missing",
        })).ToList();

        Assert.Equal(2, tracks.Count);
        Assert.Equal(new[] { "release-1", "release-2" }, tracks.Select(track => track.ReleaseId));
        Assert.Equal(new[] { "recording-1", "recording-2" }, tracks.Select(track => track.RecordingId));
    }

    [Fact]
    public async Task GetAlbumTrackByRecordingIdAsync_ReturnsNewestCaseInsensitiveMatch()
    {
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-old",
            Title = "Old Album",
            Artist = "Artist",
            Tracks = new[]
            {
                new TrackTarget { Position = 1, MusicBrainzRecordingId = "recording-1", Title = "Old Track" },
            },
        });
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-new",
            Title = "New Album",
            Artist = "Artist",
            Tracks = new[]
            {
                new TrackTarget { Position = 1, MusicBrainzRecordingId = "recording-1", Title = "New Track" },
            },
        });
        await using (var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await conn.OpenAsync();
            await using var cmd = conn.CreateCommand();
            cmd.CommandText =
                """
                UPDATE AlbumTargets
                SET created_at = CASE release_id WHEN 'release-old' THEN 1 ELSE 2 END
                """;
            await cmd.ExecuteNonQueryAsync();
        }

        var track = await service.GetAlbumTrackByRecordingIdAsync(" RECORDING-1 ");

        Assert.NotNull(track);
        Assert.Equal("release-new", track!.ReleaseId);
        Assert.Equal("New Track", track.Title);
    }

    [Fact]
    public async Task GetRecentAlbumTracksAsync_AppliesGlobalLimitInAlbumOrder()
    {
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-old",
            Title = "Old Album",
            Artist = "Artist",
            Tracks = new[]
            {
                new TrackTarget { Position = 1, MusicBrainzRecordingId = "old-1", Title = "Old One" },
            },
        });
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-new",
            Title = "New Album",
            Artist = "Artist",
            Tracks = new[]
            {
                new TrackTarget { Position = 1, MusicBrainzRecordingId = "new-1", Title = "New One" },
                new TrackTarget { Position = 2, MusicBrainzRecordingId = "new-2", Title = "New Two" },
            },
        });
        await using (var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await conn.OpenAsync();
            await using var cmd = conn.CreateCommand();
            cmd.CommandText =
                """
                UPDATE AlbumTargets
                SET created_at = CASE release_id WHEN 'release-old' THEN 1 ELSE 2 END
                """;
            await cmd.ExecuteNonQueryAsync();
        }

        var tracks = (await service.GetRecentAlbumTracksAsync(2)).ToList();

        Assert.Equal(2, tracks.Count);
        Assert.All(tracks, track => Assert.Equal("release-new", track.ReleaseId));
        Assert.Equal(new[] { 1, 2 }, tracks.Select(track => track.Position));
    }

    [Fact]
    public async Task UpsertCanonicalStatsAsync_TrimsKeysBeforePersisting()
    {
        var stats = new CanonicalStats
        {
            Id = " stats-1 ",
            MusicBrainzRecordingId = " rec-1 ",
            CodecProfileKey = " FLAC_44100_16_2 ",
            BestVariantId = " variant-1 ",
            VariantCount = 2,
            TotalSeenCount = 3,
            AvgQualityScore = 0.8,
            MaxQualityScore = 0.9,
            PercentTranscodeSuspect = 0.1,
            CodecDistribution = new Dictionary<string, int> { ["FLAC"] = 2 },
            BitrateDistribution = new Dictionary<int, int> { [1000] = 2 },
            SampleRateDistribution = new Dictionary<int, int> { [44100] = 2 },
            CanonicalityScore = 0.85,
            LastUpdated = DateTimeOffset.UtcNow,
        };

        await service.UpsertCanonicalStatsAsync(stats);

        var stored = await service.GetCanonicalStatsAsync("rec-1", "FLAC_44100_16_2");

        Assert.NotNull(stored);
        Assert.Equal("stats-1", stored!.Id);
        Assert.Equal("rec-1", stored.MusicBrainzRecordingId);
        Assert.Equal("FLAC_44100_16_2", stored.CodecProfileKey);
        Assert.Equal("variant-1", stored.BestVariantId);
    }

    [Fact]
    public async Task UpsertCanonicalStatsAsync_WithLargeBatch_PersistsAllAndReturnsRecordingStats()
    {
        var stats = Enumerable.Range(1, 201)
            .Select(index => new CanonicalStats
            {
                Id = $" stats-{index} ",
                MusicBrainzRecordingId = " recording-1 ",
                CodecProfileKey = $" profile-{index} ",
                BestVariantId = $" variant-{index} ",
                VariantCount = index,
                TotalSeenCount = index,
                LastUpdated = DateTimeOffset.UtcNow,
            })
            .Append(new CanonicalStats
            {
                Id = "stats-1",
                MusicBrainzRecordingId = "recording-1",
                CodecProfileKey = "profile-1",
                BestVariantId = "replacement",
                VariantCount = 999,
                TotalSeenCount = 999,
                LastUpdated = DateTimeOffset.UtcNow,
            })
            .ToList();

        await service.UpsertCanonicalStatsAsync(stats);
        await service.UpsertCanonicalStatsAsync(new CanonicalStats
        {
            Id = "other-stats",
            MusicBrainzRecordingId = "recording-2",
            CodecProfileKey = "profile-1",
            LastUpdated = DateTimeOffset.UtcNow,
        });

        var stored = await service.GetCanonicalStatsForRecordingAsync(" recording-1 ");

        Assert.Equal(201, stored.Count);
        Assert.All(stored, item => Assert.Equal("recording-1", item.MusicBrainzRecordingId));
        var replacement = Assert.Single(stored, item => item.Id == "stats-1");
        Assert.Equal(999, replacement.VariantCount);
        Assert.Equal("replacement", replacement.BestVariantId);
    }

    [Fact]
    public async Task LookupHashesByRecordingIdAsync_ReturnsMatches()
    {
        var entry = new HashDbEntry
        {
            FlacKey = HashDbEntry.GenerateFlacKey("test.flac", 123456),
            ByteHash = "abcdef",
            Size = 123456,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        };

        await service.StoreHashAsync(entry);
        await service.UpdateHashRecordingIdAsync(entry.FlacKey, "mb:rec1");

        var matches = await service.LookupHashesByRecordingIdAsync("mb:rec1");
        var match = Assert.Single(matches);
        Assert.Equal(entry.FlacKey, match.FlacKey);
    }

    [Fact]
    public async Task LookupHashesByRecordingIdAsync_TrimsInput()
    {
        var entry = new HashDbEntry
        {
            FlacKey = HashDbEntry.GenerateFlacKey("test.flac", 123456),
            ByteHash = "abcdef",
            Size = 123456,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        };

        await service.StoreHashAsync(entry);
        await service.UpdateHashRecordingIdAsync($" {entry.FlacKey} ", " mb:trimmed ", CancellationToken.None);

        var matches = await service.LookupHashesByRecordingIdAsync("  mb:trimmed  ");

        var match = Assert.Single(matches);
        Assert.Equal(entry.FlacKey, match.FlacKey);
    }

    [Fact]
    public async Task LookupHashesByRecordingIdsAsync_ReturnsRequestedMatches()
    {
        var first = new HashDbEntry
        {
            FlacKey = HashDbEntry.GenerateFlacKey("first.flac", 123),
            ByteHash = "first-hash",
            Size = 123,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        };
        var second = new HashDbEntry
        {
            FlacKey = HashDbEntry.GenerateFlacKey("second.flac", 456),
            ByteHash = "second-hash",
            Size = 456,
            FirstSeenAt = 1,
            LastUpdatedAt = 2,
            SeqId = 2,
            UseCount = 1,
        };
        await service.StoreHashAsync(first);
        await service.StoreHashAsync(second);
        await service.UpdateHashRecordingIdAsync(first.FlacKey, "recording-1");
        await service.UpdateHashRecordingIdAsync(second.FlacKey, "recording-2");

        var matches = (await service.LookupHashesByRecordingIdsAsync(new[]
        {
            " recording-1 ",
            "recording-1",
            "recording-2",
            "missing",
        })).ToList();

        Assert.Equal(2, matches.Count);
        Assert.Contains(matches, match => match.FlacKey == first.FlacKey && match.MusicBrainzId == "recording-1");
        Assert.Contains(matches, match => match.FlacKey == second.FlacKey && match.MusicBrainzId == "recording-2");
    }

    [Fact]
    public async Task GetVariantsByRecordingsAsync_ReturnsRequestedVariants()
    {
        var first = new HashDbEntry
        {
            FlacKey = "variant-key-1",
            ByteHash = "variant-hash-1",
            Size = 123,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        };
        var second = new HashDbEntry
        {
            FlacKey = "variant-key-2",
            ByteHash = "variant-hash-2",
            Size = 456,
            FirstSeenAt = 1,
            LastUpdatedAt = 2,
            SeqId = 2,
            UseCount = 1,
        };
        await service.StoreHashAsync(first);
        await service.StoreHashAsync(second);
        await service.UpdateHashRecordingIdAsync(first.FlacKey, "recording-1");
        await service.UpdateHashRecordingIdAsync(second.FlacKey, "recording-2");
        await service.UpdateVariantMetadataAsync(first.FlacKey, new AudioVariant
        {
            VariantId = "variant-1",
            MusicBrainzRecordingId = "recording-1",
            QualityScore = 0.8,
        });
        await service.UpdateVariantMetadataAsync(second.FlacKey, new AudioVariant
        {
            VariantId = "variant-2",
            MusicBrainzRecordingId = "recording-2",
            QualityScore = 0.9,
        });

        var variants = await service.GetVariantsByRecordingsAsync(new[]
        {
            " recording-1 ",
            "recording-1",
            "recording-2",
            "missing",
        });

        Assert.Equal(2, variants.Count);
        Assert.Contains(variants, variant => variant.VariantId == "variant-1" && variant.MusicBrainzRecordingId == "recording-1");
        Assert.Contains(variants, variant => variant.VariantId == "variant-2" && variant.MusicBrainzRecordingId == "recording-2");
    }

    [Fact]
    public async Task GetVariantsByRecordingAsync_DuplicateHeavyRecordingHasBoundedAllocation()
    {
        const int variantsPerRecording = 1_000;
        const int copiesPerVariant = 10;
        await InsertDuplicateHeavyVariantsAsync(
            recordingCount: 1,
            variantsPerRecording,
            copiesPerVariant);
        _ = await service.GetVariantsByRecordingAsync("recording-001");

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var variants = await service.GetVariantsByRecordingAsync("recording-001");
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(variantsPerRecording, variants.Count);
        Assert.All(variants, variant => Assert.Equal(1.0, variant.QualityScore));
        Assert.True(
            allocatedBytes < 4_700_000,
            $"Duplicate-heavy recording allocated {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task GetVariantsByRecordingsAsync_DuplicateHeavyPageHasBoundedAllocation()
    {
        const int recordingCount = 100;
        const int variantsPerRecording = 10;
        const int copiesPerVariant = 10;
        await InsertDuplicateHeavyVariantsAsync(recordingCount, variantsPerRecording, copiesPerVariant);

        var recordingIds = Enumerable.Range(1, recordingCount)
            .Select(index => $"recording-{index:D3}")
            .ToArray();
        _ = await service.GetVariantsByRecordingsAsync(recordingIds);

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var variants = await service.GetVariantsByRecordingsAsync(recordingIds);
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(recordingCount * variantsPerRecording, variants.Count);
        Assert.All(variants, variant => Assert.Equal(1.0, variant.QualityScore));
        Assert.True(
            allocatedBytes < 4_750_000,
            $"Duplicate-heavy variant page allocated {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task VariantRecordingReaders_PreserveTheirWinnerAndOrderSemantics()
    {
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = """
                INSERT INTO HashDb (
                    flac_key,
                    byte_hash,
                    size,
                    first_seen_at,
                    last_updated_at,
                    seq_id,
                    use_count,
                    musicbrainz_id,
                    variant_id,
                    quality_score,
                    seen_count)
                VALUES
                    ('a-first', 'hash-a-first', 1, 1, 10, 1, 1, 'recording-semantics', 'variant-a', 0.5, 1),
                    ('b-null', 'hash-b-null', 1, 1, 20, 2, 1, 'recording-semantics', 'variant-b', NULL, 1),
                    ('a-old-winner', 'hash-a-old', 1, 1, 5, 3, 1, 'recording-semantics', 'variant-a', 0.9, 1),
                    ('a-winner', 'hash-a-winner', 1, 1, 8, 4, 1, 'recording-semantics', 'variant-a', 0.9, 1),
                    ('a-later-tie', 'hash-a-tie', 1, 1, 8, 5, 1, 'recording-semantics', 'variant-a', 0.9, 1),
                    ('b-negative', 'hash-b-negative', 1, 1, 30, 6, 1, 'recording-semantics', 'variant-b', -0.1, 1),
                    ('whitespace-1', 'hash-space-1', 1, 1, 1, 7, 1, 'recording-semantics', char(32) || char(9), 0.1, 1),
                    ('whitespace-2', 'hash-space-2', 1, 1, 1, 8, 1, 'recording-semantics', char(160) || char(8199), 0.1, 1)
                """;
            await command.ExecuteNonQueryAsync();
        }

        var batchedVariants = await service.GetVariantsByRecordingsAsync(new[] { "recording-semantics" });
        var scalarVariants = await service.GetVariantsByRecordingAsync("recording-semantics");

        Assert.Equal(
            new[] { "a-winner", "b-null", "whitespace-1", "whitespace-2" },
            batchedVariants.Select(variant => variant.FlacKey));
        Assert.Equal(0, batchedVariants[1].QualityScore);
        Assert.Equal(
            new[] { "a-winner", "whitespace-1", "whitespace-2", "b-negative" },
            scalarVariants.Select(variant => variant.FlacKey));
        Assert.Equal(-0.1, scalarVariants[^1].QualityScore);
    }

    [Fact]
    public async Task GetVariantsByRecordingsAsync_KeepsDelimiterContainingIdentityTuplesDistinct()
    {
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = """
                INSERT INTO HashDb (
                    flac_key,
                    byte_hash,
                    size,
                    first_seen_at,
                    last_updated_at,
                    seq_id,
                    use_count,
                    musicbrainz_id,
                    variant_id,
                    quality_score)
                VALUES
                    ('delimiter-first', 'hash-first', 1, 1, 1, 1, 1,
                     'recording', 'part' || char(31) || 'variant', 0.8),
                    ('delimiter-second', 'hash-second', 1, 1, 1, 2, 1,
                     'recording' || char(31) || 'part', 'variant', 0.9)
                """;
            await command.ExecuteNonQueryAsync();
        }

        var variants = await service.GetVariantsByRecordingsAsync(new[]
        {
            "recording",
            "recording\u001fpart",
        });

        Assert.Equal(2, variants.Count);
        Assert.Contains(variants, variant => variant.FlacKey == "delimiter-first");
        Assert.Contains(variants, variant => variant.FlacKey == "delimiter-second");
    }

    [Fact]
    public async Task GetRecentVariantsAsync_PreservesRecordingRecencyAndVariantQualityWithinLimit()
    {
        var entries = new[]
        {
            CreateVariantEntry("old-best-key", "recording-a-old", "old-best", 20, 0.9),
            CreateVariantEntry("old-other-key", "recording-a-old", "old-other", 20, 0.8),
            CreateVariantEntry("new-a-other-key", "recording-z-new", "new-other", 30, 0.7),
            CreateVariantEntry("new-z-best-key", "recording-z-new", "new-best", 30, 0.7),
            CreateVariantEntry("case-shadow-key", "RECORDING-Z-NEW", "case-shadow", 10, 1.0),
        };
        foreach (var entry in entries)
        {
            await service.StoreHashAsync(entry);
            await service.UpdateHashRecordingIdAsync(entry.FlacKey, entry.MusicBrainzId);
            await service.UpdateVariantMetadataAsync(entry.FlacKey, new AudioVariant
            {
                FlacKey = entry.FlacKey,
                VariantId = entry.VariantId,
                MusicBrainzRecordingId = entry.MusicBrainzId,
                QualityScore = entry.QualityScore ?? 0,
            });
        }
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = """
                UPDATE HashDb
                SET
                    last_updated_at = CASE musicbrainz_id
                        WHEN 'recording-z-new' THEN 30
                        WHEN 'recording-a-old' THEN 20
                        ELSE 10
                    END,
                    seen_count = CASE flac_key
                        WHEN 'new-z-best-key' THEN 5
                        ELSE 1
                    END
                """;
            await command.ExecuteNonQueryAsync();
        }

        var variants = await service.GetRecentVariantsAsync(3);
        var bestVariants = await service.GetRecentBestVariantsByRecordingAsync(2);

        Assert.Equal(new[] { "new-other", "new-best", "old-best" }, variants.Select(variant => variant.VariantId));
        Assert.Equal(new[] { "new-best", "old-best" }, bestVariants.Select(variant => variant.VariantId));
    }

    [Fact]
    public async Task GetBestVariantByRecordingAsync_ReturnsOneDeduplicatedBestVariant()
    {
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = """
                WITH RECURSIVE sequence(value) AS (
                    SELECT 1
                    UNION ALL
                    SELECT value + 1 FROM sequence WHERE value < 1000
                )
                INSERT INTO HashDb (
                    flac_key,
                    byte_hash,
                    size,
                    first_seen_at,
                    last_updated_at,
                    seq_id,
                    use_count,
                    musicbrainz_id,
                    variant_id,
                    quality_score,
                    seen_count)
                SELECT
                    printf('filler-key-%04d', value),
                    printf('filler-hash-%04d', value),
                    123,
                    1,
                    value,
                    value,
                    1,
                    'recording-target',
                    printf('filler-variant-%04d', value),
                    0.1,
                    value
                FROM sequence
                UNION ALL
                SELECT 'winner-new-key', 'winner-new-hash', 123, 1, 30, 1001, 1,
                       'recording-target', 'duplicate-winner', 0.9, 1
                UNION ALL
                SELECT 'winner-old-key', 'winner-old-hash', 123, 1, 20, 1002, 1,
                       'recording-target', 'duplicate-winner', 0.9, 100
                UNION ALL
                SELECT 'competitor-key', 'competitor-hash', 123, 1, 25, 1003, 1,
                       'recording-target', 'competitor', 0.9, 50
                """;
            await command.ExecuteNonQueryAsync();
        }

        var result = await service.GetBestVariantByRecordingAsync("recording-target");

        Assert.NotNull(result);
        Assert.Equal("competitor", result.VariantId);
        Assert.Equal(50, result.SeenCount);
        Assert.Null(await service.GetBestVariantByRecordingAsync("RECORDING-TARGET"));

        await using var planConnection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await planConnection.OpenAsync();
        await using var planCommand = planConnection.CreateCommand();
        planCommand.CommandText = """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM HashDb
            WHERE musicbrainz_id = 'recording-target'
            ORDER BY quality_score DESC, seen_count DESC
            LIMIT 1
            """;
        await using var reader = await planCommand.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH HashDb USING INDEX idx_hashdb_musicbrainz_id", StringComparison.Ordinal));
    }

    private async Task InsertDuplicateHeavyVariantsAsync(
        int recordingCount,
        int variantsPerRecording,
        int copiesPerVariant)
    {
        await using var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = $"""
            WITH RECURSIVE sequence(value) AS (
                SELECT 1
                UNION ALL
                SELECT value + 1
                FROM sequence
                WHERE value < {recordingCount * variantsPerRecording * copiesPerVariant}
            )
            INSERT INTO HashDb (
                flac_key,
                byte_hash,
                size,
                first_seen_at,
                last_updated_at,
                seq_id,
                use_count,
                musicbrainz_id,
                variant_id,
                quality_score,
                seen_count)
            SELECT
                printf('wide-key-%05d', value),
                printf('wide-hash-%05d', value),
                123,
                1,
                ((value - 1) % {copiesPerVariant}) + 1,
                value,
                1,
                printf('recording-%03d', ((value - 1) / {variantsPerRecording * copiesPerVariant}) + 1),
                printf('variant-%04d', ((value - 1) / {copiesPerVariant}) % {variantsPerRecording}),
                (((value - 1) % {copiesPerVariant}) + 1) / 10.0,
                value
            FROM sequence
            """;
        await command.ExecuteNonQueryAsync();
    }

    private async Task InsertProfileHeavyVariantsAsync(
        int variantsPerProfile,
        int profilesPerVariant)
    {
        await using var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = $"""
            WITH RECURSIVE sequence(value) AS (
                SELECT 1
                UNION ALL
                SELECT value + 1
                FROM sequence
                WHERE value < {variantsPerProfile * profilesPerVariant}
            )
            INSERT INTO HashDb (
                flac_key,
                byte_hash,
                size,
                first_seen_at,
                last_updated_at,
                seq_id,
                use_count,
                musicbrainz_id,
                variant_id,
                codec,
                sample_rate_hz,
                bit_depth,
                channels,
                quality_score,
                seen_count)
            SELECT
                printf('profile-wide-key-%05d', value),
                printf('profile-wide-hash-%05d', value),
                123,
                1,
                value,
                value,
                1,
                'recording-profile-heavy',
                printf('profile-variant-%04d', (value - 1) / {profilesPerVariant}),
                CASE WHEN value % {profilesPerVariant} = 0 THEN 'FLAC' ELSE 'MP3' END,
                44100,
                CASE WHEN value % {profilesPerVariant} = 0 THEN 16 ELSE NULL END,
                2,
                value / 10000.0,
                value
            FROM sequence
            """;
        await command.ExecuteNonQueryAsync();
    }

    private static HashDbEntry CreateVariantEntry(
        string flacKey,
        string recordingId,
        string variantId,
        long lastUpdatedAt,
        double qualityScore) =>
        new()
        {
            FlacKey = flacKey,
            ByteHash = $"hash-{flacKey}",
            Size = 123,
            FirstSeenAt = 1,
            LastUpdatedAt = lastUpdatedAt,
            SeqId = lastUpdatedAt,
            UseCount = 1,
            MusicBrainzId = recordingId,
            VariantId = variantId,
            QualityScore = qualityScore,
        };

    [Fact]
    public async Task UpdateVariantAnalysisAsync_WithLargeBatch_UpdatesAnalysisOnly()
    {
        var entries = Enumerable.Range(1, 201)
            .Select(index => new HashDbEntry
            {
                FlacKey = $"analysis-key-{index}",
                ByteHash = $"analysis-hash-{index}",
                Size = index,
                FirstSeenAt = 1,
                LastUpdatedAt = 1,
                SeqId = index,
                UseCount = 1,
            })
            .ToList();
        foreach (var entry in entries)
        {
            await service.StoreHashAsync(entry);
        }
        await service.UpdateVariantMetadataAsync(entries[0].FlacKey, new AudioVariant
        {
            FlacKey = entries[0].FlacKey,
            VariantId = "preserved-variant",
            Codec = "FLAC",
            SampleRateHz = 96000,
            BitDepth = 24,
            Channels = 2,
            QualityScore = 0.1,
            AnalyzerVersion = "old",
        });
        var updates = entries.Select((entry, index) => new AudioVariant
        {
            FlacKey = $" {entry.FlacKey} ",
            QualityScore = index / 201.0,
            TranscodeSuspect = index % 2 == 0,
            TranscodeReason = " recalculated ",
            AnalyzerVersion = " audioqa-2 ",
        })
            .Append(new AudioVariant
            {
                FlacKey = entries[0].FlacKey,
                QualityScore = 0.99,
                TranscodeSuspect = true,
                TranscodeReason = " replacement ",
                AnalyzerVersion = " audioqa-3 ",
            })
            .ToList();

        await service.UpdateVariantAnalysisAsync(updates);

        await using var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await connection.OpenAsync();
        await using var countCommand = connection.CreateCommand();
        countCommand.CommandText = "SELECT COUNT(*) FROM HashDb WHERE analyzer_version = 'audioqa-2'";
        Assert.Equal(200L, (long)(await countCommand.ExecuteScalarAsync())!);
        await using var firstCommand = connection.CreateCommand();
        firstCommand.CommandText = "SELECT variant_id, codec, sample_rate_hz, bit_depth, quality_score, transcode_suspect, transcode_reason, analyzer_version FROM HashDb WHERE flac_key = 'analysis-key-1'";
        await using var reader = await firstCommand.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Equal("preserved-variant", reader.GetString(0));
        Assert.Equal("FLAC", reader.GetString(1));
        Assert.Equal(96000, reader.GetInt32(2));
        Assert.Equal(24, reader.GetInt32(3));
        Assert.Equal(0.99, reader.GetDouble(4), precision: 6);
        Assert.True(reader.GetBoolean(5));
        Assert.Equal("replacement", reader.GetString(6));
        Assert.Equal("audioqa-3", reader.GetString(7));
    }

    [Fact]
    public async Task GetRecordingIdsWithHashesAsync_ReturnsRequestedMatchesInOneBatchShape()
    {
        var first = new HashDbEntry
        {
            FlacKey = HashDbEntry.GenerateFlacKey("first.flac", 123),
            ByteHash = "first-hash",
            Size = 123,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        };
        var second = new HashDbEntry
        {
            FlacKey = HashDbEntry.GenerateFlacKey("second.flac", 456),
            ByteHash = "second-hash",
            Size = 456,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 2,
            UseCount = 1,
        };
        await service.StoreHashAsync(first);
        await service.StoreHashAsync(second);
        await service.UpdateHashRecordingIdAsync(first.FlacKey, "mb:first");
        await service.UpdateHashRecordingIdAsync(second.FlacKey, "MB:SECOND");

        var matches = await service.GetRecordingIdsWithHashesAsync(new[]
        {
            " mb:first ",
            "MB:FIRST",
            "mb:second",
            "mb:missing",
        });

        Assert.Equal(2, matches.Count);
        Assert.Contains("MB:FIRST", matches);
        Assert.Contains("mb:second", matches);
    }

    [Fact]
    public async Task GetDiscographyJobAsync_TrimsStoredAndLookupJobId()
    {
        await service.UpsertDiscographyJobAsync(new slskd.Jobs.DiscographyJob
        {
            JobId = "  job-1  ",
            ArtistId = " artist-1 ",
            ArtistName = " Artist ",
            TargetDirectory = " /tmp/test ",
        });

        var job = await service.GetDiscographyJobAsync(" job-1 ");

        Assert.NotNull(job);
        Assert.Equal("job-1", job!.JobId);
        Assert.Equal("artist-1", job.ArtistId);
        Assert.Equal("Artist", job.ArtistName);
        Assert.Equal("/tmp/test", job.TargetDirectory);
    }

    [Fact]
    public async Task GetDiscographyJobAsync_NormalizesDeserializedJsonPayload()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = @"
            INSERT INTO DiscographyJobs (job_id, artist_id, artist_name, profile, target_directory, total_releases, completed_releases, failed_releases, status, created_at, json_data)
            VALUES (@job_id, @artist_id, @artist_name, @profile, @target_directory, @total_releases, @completed_releases, @failed_releases, @status, @created_at, @json_data)";
        cmd.Parameters.AddWithValue("@job_id", "job-json");
        cmd.Parameters.AddWithValue("@artist_id", "artist-json");
        cmd.Parameters.AddWithValue("@artist_name", "Artist Json");
        cmd.Parameters.AddWithValue("@profile", "CoreDiscography");
        cmd.Parameters.AddWithValue("@target_directory", "/tmp/json");
        cmd.Parameters.AddWithValue("@total_releases", 0);
        cmd.Parameters.AddWithValue("@completed_releases", 0);
        cmd.Parameters.AddWithValue("@failed_releases", 0);
        cmd.Parameters.AddWithValue("@status", "Pending");
        cmd.Parameters.AddWithValue("@created_at", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
        cmd.Parameters.AddWithValue("@json_data", "{\"JobId\":\" job-json \",\"ArtistId\":\" artist-json \",\"ArtistName\":\" Artist Json \",\"TargetDirectory\":\" /tmp/json \",\"Status\":\"Pending\"}");
        await cmd.ExecuteNonQueryAsync();

        var job = await service.GetDiscographyJobAsync("job-json");

        Assert.NotNull(job);
        Assert.Equal("job-json", job!.JobId);
        Assert.Equal("artist-json", job.ArtistId);
        Assert.Equal("Artist Json", job.ArtistName);
        Assert.Equal("/tmp/json", job.TargetDirectory);
    }

    [Fact]
    public async Task GetWarmCacheEntryAndJobFallbacks_ReturnTrimmedValues()
    {
        await service.UpsertWarmCacheEntryAsync(new slskd.HashDb.Models.WarmCacheEntry
        {
            ContentId = "  content:mb:recording:1  ",
            Path = "  /tmp/media.flac  ",
            SizeBytes = 123,
            Pinned = true,
            LastAccessed = 456,
        });

        var warmEntry = await service.GetWarmCacheEntryAsync(" content:mb:recording:1 ");
        Assert.NotNull(warmEntry);
        Assert.Equal("content:mb:recording:1", warmEntry!.ContentId);
        Assert.Equal("/tmp/media.flac", warmEntry.Path);

        await service.UpsertDiscographyJobAsync(new slskd.Jobs.DiscographyJob
        {
            JobId = "  job-row  ",
            ArtistId = " artist-row ",
            ArtistName = " Artist Row ",
            TargetDirectory = " /tmp/row ",
        });
        var discographyJob = await service.GetDiscographyJobAsync(" job-row ");
        Assert.NotNull(discographyJob);
        Assert.Equal("job-row", discographyJob!.JobId);
        Assert.Equal("artist-row", discographyJob.ArtistId);
        Assert.Equal("Artist Row", discographyJob.ArtistName);
        Assert.Equal("/tmp/row", discographyJob.TargetDirectory);

        await service.UpsertLabelCrateJobAsync(new slskd.Jobs.LabelCrateJob
        {
            JobId = "  label-row  ",
            LabelId = " label-row-id ",
            LabelName = " Label Row ",
        });
        var labelJob = await service.GetLabelCrateJobAsync(" label-row ");
        Assert.NotNull(labelJob);
        Assert.Equal("label-row", labelJob!.JobId);
        Assert.Equal("label-row-id", labelJob.LabelId);
        Assert.Equal("Label Row", labelJob.LabelName);
    }

    [Fact]
    public async Task WarmCachePopularityBatch_BoundsCommandsAndPreservesDuplicateHits()
    {
        var contentIds = Enumerable.Range(0, 401)
            .Select(index => $"content-{index}")
            .Append(" content-0 ")
            .ToList();
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        using var transaction = conn.BeginTransaction();

        var commandCount = await HashDbService.UpsertPopularityInBatchesAsync(
            conn,
            transaction,
            contentIds,
            CancellationToken.None);
        transaction.Commit();

        Assert.Equal(2, commandCount);
        await using var countCommand = conn.CreateCommand();
        countCommand.CommandText = "SELECT COUNT(*) FROM WarmCachePopularity";
        Assert.Equal(401L, (long)(await countCommand.ExecuteScalarAsync())!);
        await using var hitsCommand = conn.CreateCommand();
        hitsCommand.CommandText = "SELECT hits FROM WarmCachePopularity WHERE content_id = 'content-0'";
        Assert.Equal(2L, (long)(await hitsCommand.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task IncrementPopularitiesAsync_EmptyInputDoesNotOpenDatabase()
    {
        var dbPath = Path.Combine(testDir, "hashdb.db");
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={dbPath}");
        File.Delete(dbPath);

        await service.IncrementPopularitiesAsync(new[] { " ", string.Empty });

        Assert.False(File.Exists(dbPath));
    }

    [Fact]
    public async Task EvictWarmCacheEntriesAsync_DeletesOldestUnpinnedEntriesInOneCall()
    {
        await service.UpsertWarmCacheEntryAsync(CreateWarmCacheEntry("pinned", 80, 1, pinned: true));
        await service.UpsertWarmCacheEntryAsync(CreateWarmCacheEntry("oldest", 30, 2));
        await service.UpsertWarmCacheEntryAsync(CreateWarmCacheEntry("middle", 40, 3));
        await service.UpsertWarmCacheEntryAsync(CreateWarmCacheEntry("newest", 50, 4));

        var deleted = await service.EvictWarmCacheEntriesAsync(130);
        var deletedAgain = await service.EvictWarmCacheEntriesAsync(130);
        var remaining = await service.ListWarmCacheEntriesAsync();

        Assert.Equal(2, deleted);
        Assert.Equal(0, deletedAgain);
        Assert.Equal(new[] { "newest", "pinned" }, remaining.Select(entry => entry.ContentId).OrderBy(id => id));
        Assert.Equal(130, await service.GetWarmCacheTotalSizeAsync());
    }

    [Fact]
    public async Task TouchWarmCacheEntryAsync_UpdatesExistingWithoutCreatingMissingEntry()
    {
        await service.UpsertWarmCacheEntryAsync(CreateWarmCacheEntry("existing", 10, 1));

        var updated = await service.TouchWarmCacheEntryAsync(" existing ", 123);
        var missing = await service.TouchWarmCacheEntryAsync("missing", 456);

        Assert.True(updated);
        Assert.False(missing);
        Assert.Equal(123, (await service.GetWarmCacheEntryAsync("existing"))!.LastAccessed);
        Assert.Null(await service.GetWarmCacheEntryAsync("missing"));
    }

    private static WarmCacheEntry CreateWarmCacheEntry(string contentId, long sizeBytes, long lastAccessed, bool pinned = false) =>
        new()
        {
            ContentId = contentId,
            Path = $"/cache/{contentId}",
            SizeBytes = sizeBytes,
            Pinned = pinned,
            LastAccessed = lastAccessed,
        };

    [Fact]
    public async Task GetLabelCrateJobAsync_NormalizesDeserializedJsonPayload()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = @"
            INSERT INTO LabelCrateJobs (job_id, label_id, label_name, limit_count, total_releases, completed_releases, failed_releases, status, created_at, json_data)
            VALUES (@job_id, @label_id, @label_name, @limit_count, @total_releases, @completed_releases, @failed_releases, @status, @created_at, @json_data)";
        cmd.Parameters.AddWithValue("@job_id", "label-json");
        cmd.Parameters.AddWithValue("@label_id", "label-id");
        cmd.Parameters.AddWithValue("@label_name", "Label Json");
        cmd.Parameters.AddWithValue("@limit_count", 0);
        cmd.Parameters.AddWithValue("@total_releases", 0);
        cmd.Parameters.AddWithValue("@completed_releases", 0);
        cmd.Parameters.AddWithValue("@failed_releases", 0);
        cmd.Parameters.AddWithValue("@status", "Pending");
        cmd.Parameters.AddWithValue("@created_at", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
        cmd.Parameters.AddWithValue("@json_data", "{\"JobId\":\" label-json \",\"LabelId\":\" label-id \",\"LabelName\":\" Label Json \",\"Status\":\"Pending\"}");
        await cmd.ExecuteNonQueryAsync();

        var job = await service.GetLabelCrateJobAsync("label-json");

        Assert.NotNull(job);
        Assert.Equal("label-json", job!.JobId);
        Assert.Equal("label-id", job.LabelId);
        Assert.Equal("Label Json", job.LabelName);
    }

    [Fact]
    public async Task GetLabelCrateJobAsync_TrimsStoredAndLookupJobId()
    {
        await service.UpsertLabelCrateJobAsync(new slskd.Jobs.LabelCrateJob
        {
            JobId = "  label-job  ",
            LabelId = " label-1 ",
            LabelName = " Label Name ",
            ReleaseIds = new List<string> { " rel-1 ", "rel-1", "  " },
        });

        var job = await service.GetLabelCrateJobAsync(" label-job ");

        Assert.NotNull(job);
        Assert.Equal("label-job", job!.JobId);
        Assert.Equal("label-1", job.LabelId);
        Assert.Equal("Label Name", job.LabelName);
        Assert.Single(job.ReleaseIds);
        Assert.Equal("rel-1", job.ReleaseIds[0]);
    }

    [Fact]
    public async Task GetFlacEntriesBySizeAsync_FindsMatchingEntries()
    {
        // Arrange
        var size = 50000000L;
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "user1",
            Path = "/music/test1.flac",
            Size = size,
        });
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "user2",
            Path = "/music/test2.flac",
            Size = size,
        });
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "user3",
            Path = "/music/different.flac",
            Size = 60000000,
        });

        // Act
        var entries = await service.GetFlacEntriesBySizeAsync(size);

        // Assert
        Assert.Equal(2, ((List<FlacInventoryEntry>)entries).Count);
    }

    [Fact]
    public async Task GetUnhashedFlacFilesAsync_ReturnsOnlyUnhashed()
    {
        // Arrange
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "user1",
            Path = "/music/unhashed.flac",
            Size = 50000000,
            HashStatusStr = "none",
        });
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "user2",
            Path = "/music/hashed.flac",
            Size = 50000000,
            HashStatusStr = "known",
            HashValue = "abc123",
        });

        // Act
        var unhashed = await service.GetUnhashedFlacFilesAsync();

        // Assert
        var list = (List<FlacInventoryEntry>)unhashed;
        Assert.Single(list);
        Assert.Equal("user1", list[0].PeerId);
    }

    [Fact]
    public async Task UpdateFlacHashAsync_SetsHashAndStatus()
    {
        // Arrange
        var entry = new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
            HashStatusStr = "none",
        };
        await service.UpsertFlacEntryAsync(entry);

        // Act
        await service.UpdateFlacHashAsync(entry.FileId, "newhash123", HashSource.LocalScan);

        // Assert
        var updated = await service.GetFlacEntryAsync(entry.FileId);
        Assert.Equal("known", updated.HashStatusStr);
        Assert.Equal("newhash123", updated.HashValue);
    }

    [Fact]
    public async Task UpdateFlacHashAsync_TrimsFileIdAndHashValue()
    {
        var entry = new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
            HashStatusStr = "none",
        };
        await service.UpsertFlacEntryAsync(entry);

        await service.UpdateFlacHashAsync($" {entry.FileId} ", " trimmedhash ", HashSource.LocalScan);

        var updated = await service.GetFlacEntryAsync(entry.FileId);
        Assert.Equal("known", updated.HashStatusStr);
        Assert.Equal("trimmedhash", updated.HashValue);
    }

    [Fact]
    public async Task MarkFlacHashFailedAsync_SetsFailedStatus()
    {
        // Arrange
        var entry = new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
            HashStatusStr = "none",
        };
        await service.UpsertFlacEntryAsync(entry);

        // Act
        await service.MarkFlacHashFailedAsync(entry.FileId);

        // Assert
        var updated = await service.GetFlacEntryAsync(entry.FileId);
        Assert.Equal("failed", updated.HashStatusStr);
    }

    [Fact]
    public async Task GetRecordingIdsWithVariantsAsync_TrimsAndDeduplicatesIds()
    {
        var entry1 = new HashDbEntry
        {
            FlacKey = "flac-key-1",
            ByteHash = "hash-1",
            Size = 123,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        };

        var entry2 = new HashDbEntry
        {
            FlacKey = "flac-key-2",
            ByteHash = "hash-2",
            Size = 456,
            FirstSeenAt = 2,
            LastUpdatedAt = 2,
            SeqId = 2,
            UseCount = 1,
        };

        await service.StoreHashAsync(entry1);
        await service.StoreHashAsync(entry2);
        await service.UpdateHashRecordingIdAsync(entry1.FlacKey, " mb:rec1 ");
        await service.UpdateHashRecordingIdAsync(entry2.FlacKey, "mb:rec1");

        var ids = await service.GetRecordingIdsWithVariantsAsync();

        var id = Assert.Single(ids);
        Assert.Equal("mb:rec1", id);
    }

    [Fact]
    public async Task GetRecordingIdsWithVariantsPageAsync_NormalizesDeduplicatesAndUsesKeysetCursor()
    {
        foreach (var (key, recordingId, sequence) in new[]
        {
            ("flac-page-z", " z-recording ", 1L),
            ("flac-page-a-upper", "A-recording", 2L),
            ("flac-page-a-lower", " a-recording ", 3L),
            ("flac-page-m", "m-recording", 4L),
        })
        {
            await service.StoreHashAsync(new HashDbEntry
            {
                FlacKey = key,
                ByteHash = $"hash-{key}",
                Size = 123,
                FirstSeenAt = sequence,
                LastUpdatedAt = sequence,
                SeqId = sequence,
                UseCount = 1,
            });
            await service.UpdateHashRecordingIdAsync(key, recordingId);
        }

        var firstPage = await service.GetRecordingIdsWithVariantsPageAsync(afterRecordingId: null, limit: 2);
        var secondPage = await service.GetRecordingIdsWithVariantsPageAsync(firstPage[^1], limit: 2);
        var emptyPage = await service.GetRecordingIdsWithVariantsPageAsync(afterRecordingId: null, limit: 0);

        Assert.Equal(new[] { "a-recording", "m-recording" }, firstPage.Select(id => id.ToLowerInvariant()));
        Assert.Equal(new[] { "z-recording" }, secondPage.Select(id => id.ToLowerInvariant()));
        Assert.Empty(emptyPage);
    }

    [Fact]
    public async Task GetCodecProfilesForRecordingAsync_TrimsRecordingId()
    {
        var entry = new HashDbEntry
        {
            FlacKey = "flac-key-codec",
            ByteHash = "hash-codec",
            Size = 321,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
            Codec = "flac",
            SampleRateHz = 44100,
            BitDepth = 16,
            Channels = 2,
        };

        await service.StoreHashAsync(entry);
        await service.UpdateHashRecordingIdAsync(entry.FlacKey, "mb:codec1");

        var profiles = await service.GetCodecProfilesForRecordingAsync(" mb:codec1 ");

        Assert.Single(profiles);
    }

    [Fact]
    public async Task GetVariantsByRecordingAndProfileAsync_FiltersExactProfileKey()
    {
        foreach (var (flacKey, variantId, codec, sampleRate, bitDepth, qualityScore) in new[]
        {
            ("profile-key-16", "variant-16", "FLAC", 44_100, (int?)16, 0.8),
            ("profile-key-16-old", "variant-16", "FLAC", 44_100, (int?)16, 0.7),
            ("profile-key-24", "variant-24", "FLAC", 48_000, (int?)24, 0.8),
            ("profile-key-mp3", "variant-16", "MP3", 44_100, (int?)null, 0.95),
        })
        {
            await service.StoreHashAsync(new HashDbEntry
            {
                FlacKey = flacKey,
                ByteHash = $"hash-{flacKey}",
                Size = 321,
                FirstSeenAt = 1,
                LastUpdatedAt = 1,
                SeqId = sampleRate,
                UseCount = 1,
            });
            await service.UpdateHashRecordingIdAsync(flacKey, "recording-profile");
            await service.UpdateVariantMetadataAsync(flacKey, new AudioVariant
            {
                VariantId = variantId,
                MusicBrainzRecordingId = "recording-profile",
                Codec = codec,
                SampleRateHz = sampleRate,
                BitDepth = bitDepth,
                Channels = 2,
                QualityScore = qualityScore,
            });
        }

        var variants = await service.GetVariantsByRecordingAndProfileAsync(
            "recording-profile",
            "FLAC-16bit-44100Hz-2ch");

        var variant = Assert.Single(variants);
        Assert.Equal("variant-16", variant.VariantId);
        Assert.Equal("profile-key-16", variant.FlacKey);
    }

    [Fact]
    public async Task GetVariantsByRecordingAndProfileAsync_PreservesCurrentCultureProfileKey()
    {
        const string flacKey = "profile-culture-key";
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = flacKey,
            ByteHash = "profile-culture-hash",
            Size = 321,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        });
        await service.UpdateHashRecordingIdAsync(flacKey, "recording-profile-culture");
        await service.UpdateVariantMetadataAsync(flacKey, new AudioVariant
        {
            VariantId = "variant-culture",
            MusicBrainzRecordingId = "recording-profile-culture",
            Codec = "FLAC",
            SampleRateHz = -96_000,
            BitDepth = -24,
            Channels = -2,
            QualityScore = 0.8,
        });

        var originalCulture = System.Globalization.CultureInfo.CurrentCulture;
        var culture = (System.Globalization.CultureInfo)System.Globalization.CultureInfo.InvariantCulture.Clone();
        culture.NumberFormat.NegativeSign = "minus";
        try
        {
            System.Globalization.CultureInfo.CurrentCulture = culture;
            var variants = await service.GetVariantsByRecordingAndProfileAsync(
                "recording-profile-culture",
                "FLAC-minus24bit-minus96000Hz-minus2ch");

            Assert.Equal("variant-culture", Assert.Single(variants).VariantId);
        }
        finally
        {
            System.Globalization.CultureInfo.CurrentCulture = originalCulture;
        }
    }

    [Fact]
    public async Task GetVariantsByRecordingAndProfileAsync_ProfileHeavyRecordingHasBoundedAllocation()
    {
        const int variantsPerProfile = 1_000;
        const int profilesPerVariant = 10;
        await InsertProfileHeavyVariantsAsync(variantsPerProfile, profilesPerVariant);
        _ = await service.GetVariantsByRecordingAndProfileAsync(
            "recording-profile-heavy",
            "FLAC-16bit-44100Hz-2ch");

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var variants = await service.GetVariantsByRecordingAndProfileAsync(
            "recording-profile-heavy",
            "FLAC-16bit-44100Hz-2ch");
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(variantsPerProfile, variants.Count);
        Assert.True(
            allocatedBytes < 4_800_000,
            $"Profile-heavy recording allocated {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task GetLabelCrateReleaseJobsAsync_SkipsBlankReleaseIds()
    {
        await service.UpsertLabelCrateJobAsync(new slskd.Jobs.LabelCrateJob
        {
            JobId = "job-1",
            LabelId = "label-1",
            LabelName = "Label",
            Status = JobStatus.Pending
        });

        await service.UpsertLabelCrateReleaseJobsAsync("job-1", new[]
        {
            new DiscographyReleaseJobStatus { ReleaseId = " rel-1 ", Status = JobStatus.Pending },
            new DiscographyReleaseJobStatus { ReleaseId = "   ", Status = JobStatus.Failed },
        });

        var jobs = await service.GetLabelCrateReleaseJobsAsync(" job-1 ");

        var job = Assert.Single(jobs);
        Assert.Equal("rel-1", job.ReleaseId);
    }

    [Fact]
    public async Task ReleaseJobUpserts_BatchNormalizeAndApplyLaterDuplicateStatus()
    {
        await service.UpsertDiscographyJobAsync(new slskd.Jobs.DiscographyJob
        {
            JobId = "discography-job",
            ArtistId = "artist-1",
            ArtistName = "Artist",
        });
        await service.UpsertLabelCrateJobAsync(new slskd.Jobs.LabelCrateJob
        {
            JobId = "label-job",
            LabelId = "label-1",
            LabelName = "Label",
        });
        var releases = Enumerable.Range(1, 201)
            .Select(index => new DiscographyReleaseJobStatus
            {
                ReleaseId = $" release-{index} ",
                Status = JobStatus.Pending,
            })
            .Append(new DiscographyReleaseJobStatus
            {
                ReleaseId = "release-1",
                Status = JobStatus.Failed,
            })
            .Append(new DiscographyReleaseJobStatus
            {
                ReleaseId = "   ",
                Status = JobStatus.Completed,
            })
            .ToList();

        await service.UpsertDiscographyReleaseJobsAsync(" discography-job ", releases);
        await service.UpsertLabelCrateReleaseJobsAsync(" label-job ", releases);

        var discography = await service.GetDiscographyReleaseJobsAsync("discography-job");
        var label = await service.GetLabelCrateReleaseJobsAsync("label-job");
        Assert.Equal(201, discography.Count);
        Assert.Equal(201, label.Count);
        Assert.All(discography, release => Assert.Equal(release.ReleaseId.Trim(), release.ReleaseId));
        Assert.All(label, release => Assert.Equal(release.ReleaseId.Trim(), release.ReleaseId));
        Assert.Equal(JobStatus.Failed, Assert.Single(discography, release => release.ReleaseId == "release-1").Status);
        Assert.Equal(JobStatus.Failed, Assert.Single(label, release => release.ReleaseId == "release-1").Status);
    }

    // ========== Hash Database Tests ==========

    [Fact]
    public async Task StoreHashAsync_StoresAndIncrementsSeqId()
    {
        // Arrange
        var entry = new HashDbEntry
        {
            FlacKey = "testkey",
            ByteHash = "testhash",
            Size = 50000000,
        };

        // Act
        await service.StoreHashAsync(entry);

        // Assert
        Assert.Equal(1, service.CurrentSeqId);
        var stats = service.GetStats();
        Assert.Equal(1, stats.TotalHashEntries);
    }

    [Fact]
    public async Task LookupHashAsync_FindsStoredHash()
    {
        // Arrange
        var entry = new HashDbEntry
        {
            FlacKey = "testkey",
            ByteHash = "testhash",
            Size = 50000000,
        };
        await service.StoreHashAsync(entry);

        // Act
        var found = await service.LookupHashAsync("testkey");

        // Assert
        Assert.NotNull(found);
        Assert.Equal("testhash", found.ByteHash);
        Assert.Equal(50000000, found.Size);
    }

    [Fact]
    public async Task LookupHashAsync_ReturnsNullForMissingKey()
    {
        // Act
        var found = await service.LookupHashAsync("nonexistent");

        // Assert
        Assert.Null(found);
    }

    [Fact]
    public async Task LookupHashesByFlacKeysAsync_ReturnsNormalizedExactMatches()
    {
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "exact-key-1",
            ByteHash = "hash-1",
            Size = 1,
            FirstSeenAt = 1,
            LastUpdatedAt = 1,
            SeqId = 1,
            UseCount = 1,
        });
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "exact-key-2",
            VariantId = "variant-key-2",
            ByteHash = "hash-2",
            Size = 2,
            FirstSeenAt = 1,
            LastUpdatedAt = 2,
            SeqId = 2,
            UseCount = 1,
        });

        var entries = await service.LookupHashesByFlacKeysAsync(new[]
        {
            " exact-key-1 ",
            "exact-key-1",
            "exact-key-2",
            "variant-key-2",
            "missing",
        });

        Assert.Equal(2, entries.Count);
        Assert.Equal(new[] { "exact-key-1", "exact-key-2" }, entries.Select(entry => entry.FlacKey).OrderBy(key => key));
    }

    [Fact]
    public async Task LookupHashesBySizeAsync_FindsMatchingHashes()
    {
        // Arrange
        var size = 50000000L;
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "key1",
            ByteHash = "hash1",
            Size = size,
        });
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "key2",
            ByteHash = "hash2",
            Size = size,
        });

        // Act
        var hashes = await service.LookupHashesBySizeAsync(size);

        // Assert
        Assert.Equal(2, ((List<HashDbEntry>)hashes).Count);
    }

    [Fact]
    public async Task StoreHashFromVerificationAsync_CreatesCorrectKey()
    {
        // Arrange - hash needs to be at least 16 chars for logging substring
        var hash = "0123456789abcdef0123456789abcdef";

        // Act
        await service.StoreHashFromVerificationAsync("/music/test.flac", 50000000, hash);

        // Assert
        var expectedKey = HashDbEntry.GenerateFlacKey("/music/test.flac", 50000000);
        var found = await service.LookupHashAsync(expectedKey);
        Assert.NotNull(found);
        Assert.Equal(hash, found.ByteHash);
    }

    [Fact]
    public async Task DownloadCompleteAsync_SkipsNonAudioSidecar()
    {
        var sidecar = Path.Combine(testDir, "booklet.pdf");
        await File.WriteAllBytesAsync(sidecar, new byte[32769]);

        await InvokeDownloadCompleteAsync(new DownloadFileCompleteEvent
        {
            LocalFilename = sidecar,
            RemoteFilename = @"Album\booklet.pdf",
            Transfer = new slskd.Transfers.Transfer
            {
                Size = 32769,
            },
        });

        var stats = service.GetStats();
        Assert.Equal(0, stats.TotalHashEntries);
    }

    [Fact]
    public async Task IncrementHashUseCountAsync_IncrementsCount()
    {
        // Arrange
        var entry = new HashDbEntry
        {
            FlacKey = "testkey",
            ByteHash = "testhash",
            Size = 50000000,
        };
        await service.StoreHashAsync(entry);

        // Act
        await service.IncrementHashUseCountAsync("testkey");
        await service.IncrementHashUseCountAsync("testkey");

        // Assert
        var found = await service.LookupHashAsync("testkey");
        Assert.Equal(3, found.UseCount); // Initial 1 + 2 increments
    }

    private async Task InvokeDownloadCompleteAsync(DownloadFileCompleteEvent evt)
    {
        var method = typeof(HashDbService).GetMethod(
            "OnDownloadCompleteAsync",
            BindingFlags.Instance | BindingFlags.NonPublic);

        var task = Assert.IsAssignableFrom<Task>(method?.Invoke(service, new object[] { evt }));
        await task;
    }

    [Fact]
    public async Task IncrementHashUseCountAsync_TrimsKeyAndIgnoresBlank()
    {
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "trim-key",
            ByteHash = "trim-hash",
            Size = 123,
        });

        await service.IncrementHashUseCountAsync(" trim-key ");
        await service.IncrementHashUseCountAsync("   ");

        var found = await service.LookupHashAsync("trim-key");
        Assert.Equal(2, found!.UseCount);
    }

    // ========== Mesh Sync Tests ==========

    [Fact]
    public async Task GetEntriesSinceSeqAsync_ReturnsEntriesAfterSeq()
    {
        // Arrange
        await service.StoreHashAsync(new HashDbEntry { FlacKey = "key1", ByteHash = "hash1", Size = 100 });
        await service.StoreHashAsync(new HashDbEntry { FlacKey = "key2", ByteHash = "hash2", Size = 200 });
        await service.StoreHashAsync(new HashDbEntry { FlacKey = "key3", ByteHash = "hash3", Size = 300 });

        // Act
        var entries = await service.GetEntriesSinceSeqAsync(1);

        // Assert
        var list = (List<HashDbEntry>)entries;
        Assert.Equal(2, list.Count);
        Assert.Contains(list, e => e.FlacKey == "key2");
        Assert.Contains(list, e => e.FlacKey == "key3");
    }

    [Fact]
    public async Task MergeEntriesFromMeshAsync_MergesNewEntries()
    {
        var entries = Enumerable.Range(1, 201)
            .Select(index => new HashDbEntry
            {
                FlacKey = $"mesh-{index}",
                ByteHash = $"meshhash-{index}",
                Size = index,
            })
            .ToList();
        entries.Add(new HashDbEntry { FlacKey = "mesh-1", ByteHash = "meshhash-1", Size = 1 });

        var merged = await service.MergeEntriesFromMeshAsync(entries);

        Assert.Equal(201, merged);
        Assert.Equal(201, service.CurrentSeqId);
        var stored = (await service.GetEntriesSinceSeqAsync(0, 250)).ToList();
        Assert.Equal(201, stored.Count);
        Assert.Equal(201, stored.Select(entry => entry.SeqId).Distinct().Count());
        Assert.Equal(1, (await service.LookupHashAsync("mesh-1"))!.UseCount);
    }

    [Fact]
    public async Task MergeEntriesFromMeshAsync_SkipsExistingEntries()
    {
        // Arrange
        await service.StoreHashAsync(new HashDbEntry { FlacKey = "existing", ByteHash = "localhash", Size = 100 });

        var entries = new List<HashDbEntry>
        {
            new HashDbEntry { FlacKey = "existing", ByteHash = "localhash", Size = 100 }, // Same hash
            new HashDbEntry { FlacKey = "new", ByteHash = "newhash", Size = 200 },
        };

        // Act
        var merged = await service.MergeEntriesFromMeshAsync(entries);

        // Assert
        Assert.Equal(1, merged); // Only the new one should be merged
    }

    [Fact]
    public async Task MergeEntriesFromMeshAsync_PreservesVariantAliasConflictLookup()
    {
        await service.StoreHashAsync(new HashDbEntry
        {
            FlacKey = "local-key",
            ByteHash = "local-hash",
            Size = 100,
        });
        await using (var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await conn.OpenAsync();
            await using var cmd = conn.CreateCommand();
            cmd.CommandText = "UPDATE HashDb SET variant_id = 'variant-alias' WHERE flac_key = 'local-key'";
            await cmd.ExecuteNonQueryAsync();
        }

        var merged = await service.MergeEntriesFromMeshAsync(new[]
        {
            new HashDbEntry { FlacKey = "variant-alias", ByteHash = "remote-hash", Size = 100 },
        });

        Assert.Equal(0, merged);
        Assert.Equal(1, service.CurrentSeqId);
        Assert.Equal("local-hash", (await service.LookupHashAsync("local-key"))!.ByteHash);
        await using var verifyConn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await verifyConn.OpenAsync();
        await using var verifyCmd = verifyConn.CreateCommand();
        verifyCmd.CommandText = "SELECT COUNT(*) FROM HashDb WHERE flac_key = 'variant-alias'";
        Assert.Equal(0L, (long)(await verifyCmd.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task Constructor_IndexesMeshMergeExactAndVariantLookup()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT flac_key, variant_id, byte_hash, use_count, last_updated_at
            FROM HashDb
            WHERE flac_key IN ('key-1', 'key-2')
               OR variant_id IN ('key-1', 'key-2')
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail => detail.Contains("sqlite_autoindex_HashDb_1", StringComparison.Ordinal));
        Assert.Contains(plan, detail => detail.Contains("idx_hashdb_variant", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("SCAN HashDb", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Constructor_IndexesBatchedExactFlacKeyLookup()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "EXPLAIN QUERY PLAN SELECT * FROM HashDb WHERE flac_key IN ('key-1', 'key-2')";

        await using var reader = await cmd.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        var plan = reader.GetString(3);

        Assert.Contains("SEARCH HashDb USING INDEX sqlite_autoindex_HashDb_1", plan, StringComparison.Ordinal);
    }

    [Fact]
    public async Task UpdatePeerLastSeqSeenAsync_TracksSeqPerPeer()
    {
        // Act
        await service.UpdatePeerLastSeqSeenAsync("peer1", 100);
        await service.UpdatePeerLastSeqSeenAsync("peer2", 200);

        // Assert
        Assert.Equal(100, await service.GetPeerLastSeqSeenAsync("peer1"));
        Assert.Equal(200, await service.GetPeerLastSeqSeenAsync("peer2"));
    }

    [Fact]
    public async Task UpdatePeerLastSeqSeenAsync_TrimsPeerIdAndBlankLookupsReturnZero()
    {
        await service.UpdatePeerLastSeqSeenAsync(" peer-trim ", 321);

        Assert.Equal(321, await service.GetPeerLastSeqSeenAsync(" peer-trim "));
        Assert.Equal(0, await service.GetPeerLastSeqSeenAsync("   "));
    }

    // ========== Backfill Tests ==========

    [Fact]
    public async Task GetBackfillCandidatesAsync_ReturnsUnhashedFiles()
    {
        // Arrange
        await service.GetOrCreatePeerAsync("testuser");
        await service.UpsertFlacEntryAsync(new FlacInventoryEntry
        {
            PeerId = "testuser",
            Path = "/music/test.flac",
            Size = 50000000,
            HashStatusStr = "none",
        });

        // Act
        var candidates = await service.GetBackfillCandidatesAsync();

        // Assert
        Assert.Single(candidates);
    }

    [Fact]
    public async Task GetBackfillCandidatesAsync_NonPositiveLimitReturnsEmpty()
    {
        var candidates = await service.GetBackfillCandidatesAsync(0);

        Assert.Empty(candidates);
    }

    [Fact]
    public async Task IncrementPeerBackfillCountAsync_IncrementsCount()
    {
        // Arrange
        await service.GetOrCreatePeerAsync("testuser");

        // Act
        await service.IncrementPeerBackfillCountAsync("testuser");
        await service.IncrementPeerBackfillCountAsync("testuser");

        // Assert
        var count = await service.GetPeerBackfillCountTodayAsync("testuser");
        Assert.Equal(2, count);
    }

    [Fact]
    public async Task IncrementPeerBackfillCountAsync_TrimsPeerId()
    {
        await service.GetOrCreatePeerAsync("testuser");

        await service.IncrementPeerBackfillCountAsync(" testuser ");

        var count = await service.GetPeerBackfillCountTodayAsync(" testuser ");
        Assert.Equal(1, count);
    }

    [Fact]
    public async Task GetPeerBackfillCountsTodayAsync_ReturnsAllRequestedCountsInOneSnapshot()
    {
        await service.GetOrCreatePeerAsync("alice");
        await service.GetOrCreatePeerAsync("bob");
        await service.IncrementPeerBackfillCountAsync("alice");
        await service.IncrementPeerBackfillCountAsync("alice");
        await service.IncrementPeerBackfillCountAsync("bob");

        var counts = await service.GetPeerBackfillCountsTodayAsync(
            new[] { " alice ", "BOB", "missing", "alice" });

        Assert.Equal(2, counts["alice"]);
        Assert.Equal(1, counts["bob"]);
        Assert.False(counts.ContainsKey("missing"));
        Assert.Equal(2, counts.Count);
    }

    [Fact]
    public async Task GetLabelPresenceAndReleaseIds_NormalizeTrimAndDeduplicate()
    {
        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = " release-1 ",
            DiscogsReleaseId = " discogs-1 ",
            Title = "Album 1",
            Artist = "Artist 1",
            Metadata = new ReleaseMetadata
            {
                Label = " Label One ",
            },
        });

        await service.UpsertAlbumTargetAsync(new AlbumTarget
        {
            MusicBrainzReleaseId = "release-1",
            DiscogsReleaseId = "discogs-1",
            Title = "Album 1 Dup",
            Artist = "Artist 1",
            Metadata = new ReleaseMetadata
            {
                Label = "label one",
            },
        });

        var labels = await service.GetLabelPresenceAsync();
        var releasesByLabel = await service.GetReleaseIdsByLabelAsync("  LABEL ONE  ", 10);

        Assert.Single(labels);
        Assert.Equal("label one", labels[0].Label, ignoreCase: true);
        Assert.Single(releasesByLabel);
        Assert.Equal("release-1", releasesByLabel[0]);
    }

    [Fact]
    public async Task GetEntriesSinceSeqAsync_NonPositiveLimitReturnsEmpty()
    {
        await service.StoreHashAsync(new HashDbEntry { FlacKey = "seq-key", ByteHash = "seq-hash", Size = 1 });

        var entries = await service.GetEntriesSinceSeqAsync(0, 0);

        Assert.Empty(entries);
    }

    [Fact]
    public async Task PeerMetrics_NormalizePeerIdOnWriteAndRead()
    {
        await service.UpsertPeerMetricsAsync(new slskd.Transfers.MultiSource.Metrics.PeerPerformanceMetrics
        {
            PeerId = " peer-metrics ",
            Source = slskd.Transfers.MultiSource.Metrics.PeerSource.Soulseek,
            FirstSeen = DateTimeOffset.UtcNow,
            LastUpdated = DateTimeOffset.UtcNow,
        });

        var metric = await service.GetPeerMetricsAsync(" peer-metrics ");
        var all = await service.GetAllPeerMetricsAsync();

        Assert.NotNull(metric);
        Assert.Equal("peer-metrics", metric!.PeerId);
        var single = Assert.Single(all);
        Assert.Equal("peer-metrics", single.PeerId);
    }

    [Fact]
    public async Task GetPeerMetricsAsync_BatchesDistinctNormalizedIdsAcrossSqliteBoundary()
    {
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = """
                WITH RECURSIVE sequence(value) AS (
                    SELECT 1
                    UNION ALL
                    SELECT value + 1 FROM sequence WHERE value < 501
                )
                INSERT INTO PeerMetrics (peer_id, source)
                SELECT printf('peer-%03d', value), 'Soulseek'
                FROM sequence
                """;
            await command.ExecuteNonQueryAsync();
        }

        var requested = Enumerable.Range(1, 501)
            .Select(index => $"peer-{index:D3}")
            .Concat(new[] { " peer-001 ", "missing" })
            .ToArray();
        var metrics = await service.GetPeerMetricsAsync(requested);

        Assert.Equal(501, metrics.Count);
        Assert.Equal(501, metrics.Select(item => item.PeerId).Distinct(StringComparer.Ordinal).Count());
        Assert.DoesNotContain(metrics, item => item.PeerId == "missing");

        await using var planConnection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await planConnection.OpenAsync();
        await using var planCommand = planConnection.CreateCommand();
        planCommand.CommandText = "EXPLAIN QUERY PLAN SELECT * FROM PeerMetrics WHERE peer_id IN ('peer-001', 'peer-501')";
        await using var reader = await planCommand.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Contains("sqlite_autoindex_PeerMetrics_1", reader.GetString(3), StringComparison.Ordinal);
    }

    [Fact]
    public async Task GetTopPeerMetricsAsync_MatchesCanonicalCostRankingAndBoundsResults()
    {
        var now = DateTimeOffset.UtcNow;
        var metrics = Enumerable.Range(0, 12)
            .Select(index => new PeerPerformanceMetrics
            {
                PeerId = $"peer-{index:D2}",
                Source = PeerSource.Soulseek,
                RttAvgMs = index % 4 == 0 ? 0 : 25 + (index * 17),
                ThroughputAvgBytesPerSec = index % 5 == 0 ? 0 : 128_000 + (index * 91_000),
                ThroughputStdDevBytesPerSec = index % 3 == 0 ? 0 : 10_000 + (index * 1_000),
                ChunksRequested = index % 6 == 0 ? 0 : 10 + index,
                ChunksFailed = index % 6 == 0 ? 0 : index % 4,
                ChunksTimedOut = index % 6 == 0 ? 0 : index % 3,
                ReputationScore = index == 10 ? -0.5 : index == 11 ? 1.5 : index % 4 * 0.3,
                FirstSeen = now.AddMinutes(-index),
                LastUpdated = now,
            })
            .ToList();

        foreach (var metric in metrics)
        {
            await service.UpsertPeerMetricsAsync(metric);
        }

        var expected = new PeerCostFunction()
            .RankPeers(await service.GetAllPeerMetricsAsync())
            .Take(5)
            .Select(peer => peer.PeerId);

        var actual = await service.GetTopPeerMetricsAsync(5);

        Assert.Equal(expected, actual.Select(metric => metric.PeerId));
        Assert.Equal(5, actual.Count);
    }

    [Fact]
    public async Task GetTopPeerMetricsAsync_PreservesCaseInsensitiveFirstRowDeduplication()
    {
        var now = DateTimeOffset.UtcNow;
        await service.UpsertPeerMetricsAsync(new PeerPerformanceMetrics
        {
            PeerId = "Peer-A",
            Source = PeerSource.Soulseek,
            ThroughputAvgBytesPerSec = 1_000,
            FirstSeen = now,
            LastUpdated = now,
        });
        await service.UpsertPeerMetricsAsync(new PeerPerformanceMetrics
        {
            PeerId = "peer-a",
            Source = PeerSource.Soulseek,
            ThroughputAvgBytesPerSec = 10_000_000,
            FirstSeen = now,
            LastUpdated = now,
        });
        await service.UpsertPeerMetricsAsync(new PeerPerformanceMetrics
        {
            PeerId = "peer-b",
            Source = PeerSource.Soulseek,
            ThroughputAvgBytesPerSec = 2_000,
            FirstSeen = now,
            LastUpdated = now,
        });
        await service.UpsertPeerMetricsAsync(new PeerPerformanceMetrics
        {
            PeerId = "peer-c",
            Source = PeerSource.Soulseek,
            ThroughputAvgBytesPerSec = 2_000,
            FirstSeen = now,
            LastUpdated = now,
        });

        var top = await service.GetTopPeerMetricsAsync(2);

        Assert.Equal(new[] { "peer-b", "peer-c" }, top.Select(metric => metric.PeerId));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    public async Task GetTopPeerMetricsAsync_NonPositiveLimitReturnsEmpty(int limit)
    {
        var metrics = await service.GetTopPeerMetricsAsync(limit);

        Assert.Empty(metrics);
    }

    [Fact]
    public async Task GetJobListPageAsync_FiltersSortsAndBoundsWithoutReadingJobJson()
    {
        var createdAt = DateTimeOffset.FromUnixTimeSeconds(1_700_000_000);
        for (var index = 0; index < 120; index++)
        {
            await service.UpsertDiscographyJobAsync(new slskd.Jobs.DiscographyJob
            {
                JobId = $"disc-{index:D3}",
                ArtistId = $"artist-{index:D3}",
                Status = index % 2 == 0 ? slskd.Jobs.JobStatus.Running : slskd.Jobs.JobStatus.Pending,
                CreatedAt = createdAt.AddSeconds(index),
                TotalReleases = index + 10,
                CompletedReleases = index,
                FailedReleases = index % 3,
            });
            await service.UpsertLabelCrateJobAsync(new slskd.Jobs.LabelCrateJob
            {
                JobId = $"label-{index:D3}",
                LabelName = $"Label {index:D3}",
                Status = index % 2 == 0 ? slskd.Jobs.JobStatus.Running : slskd.Jobs.JobStatus.Completed,
                CreatedAt = createdAt.AddSeconds(index),
                TotalReleases = index + 20,
                CompletedReleases = index + 1,
                FailedReleases = index % 5,
            });
        }

        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection(
            $"Data Source={Path.Combine(testDir, "hashdb.db")}"))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText =
                """
                UPDATE DiscographyJobs SET json_data = 'invalid-json';
                UPDATE LabelCrateJobs SET json_data = 'invalid-json';
                """;
            await command.ExecuteNonQueryAsync();
        }

        var page = await service.GetJobListPageAsync(
            type: null,
            status: "running",
            limit: 25,
            offset: 10,
            sortBy: "created_at",
            descending: true);

        Assert.Equal(120, page.Total);
        Assert.Equal(25, page.Items.Count);
        Assert.All(page.Items, item => Assert.Equal("running", item.Status));
        Assert.Equal("disc-108", page.Items[0].Id);
        Assert.Equal("label-108", page.Items[1].Id);
        Assert.Equal(108, page.Items[0].CompletedReleases);

        var labelPage = await service.GetJobListPageAsync(
            type: "label_crate",
            status: "completed",
            limit: 3,
            offset: 0,
            sortBy: "id",
            descending: false);
        Assert.Equal(60, labelPage.Total);
        Assert.Equal(new[] { "label-001", "label-003", "label-005" }, labelPage.Items.Select(item => item.Id));

        var unknownType = await service.GetJobListPageAsync(
            type: "unknown",
            status: null,
            limit: 100,
            offset: 0,
            sortBy: null,
            descending: false);
        Assert.Equal(0, unknownType.Total);
        Assert.Empty(unknownType.Items);
    }

    [Fact]
    public async Task Constructor_IndexesBoundedJobStatusPages()
    {
        await using var connection = new Microsoft.Data.Sqlite.SqliteConnection(
            $"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT job_id
            FROM DiscographyJobs
            WHERE LOWER(status) = 'running'
            ORDER BY created_at DESC
            LIMIT 100
            """;

        await using var reader = await command.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("INDEX idx_discography_jobs_status_created", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task LibraryHealthDashboard_AggregatesBeyondDefaultPageAndBoundsDetails()
    {
        for (var index = 0; index < 157; index++)
        {
            var inSelectedLibrary = index < 150;
            await service.InsertLibraryIssueAsync(new LibraryIssue
            {
                IssueId = $"issue-{index:D3}",
                Type = index % 2 == 0 ? LibraryIssueType.CorruptedFile : LibraryIssueType.MissingMetadata,
                Severity = index % 3 == 0 ? LibraryIssueSeverity.High : LibraryIssueSeverity.Medium,
                FilePath = inSelectedLibrary ? $"/music/track-{index:D3}.flac" : $"/other/track-{index:D3}.flac",
                Artist = index % 2 == 0 ? "Artist A" : "Artist B",
                Album = "Fixture Album",
                MusicBrainzReleaseId = "fixture-release",
                Status = index < 120
                    ? LibraryIssueStatus.Detected
                    : index < 140
                        ? LibraryIssueStatus.Resolved
                        : LibraryIssueStatus.Ignored,
                DetectedAt = DateTimeOffset.FromUnixTimeSeconds(1_700_000_000 + index),
                Metadata = new Dictionary<string, object>
                {
                    ["codec"] = index % 2 == 0 ? "flac" : "mp3",
                    ["payload"] = new string('x', 256),
                    ["transcode_suspect"] = index % 10 == 0,
                },
            });
        }

        var dashboard = await service.GetLibraryHealthDashboardAsync("/music", artistLimit: 1, issueLimit: 25);

        Assert.Equal(150, dashboard.Summary.TotalIssues);
        Assert.Equal(120, dashboard.Summary.IssuesOpen);
        Assert.Equal(20, dashboard.Summary.IssuesResolved);
        Assert.Equal(150, dashboard.IssuesByType.Sum(group => group.Count));
        var artist = Assert.Single(dashboard.IssuesByArtist);
        Assert.Equal("Artist A", artist.Artist);
        Assert.Equal(75, artist.Count);
        Assert.Equal(25, dashboard.Issues.Count);
        Assert.Equal("issue-149", dashboard.Issues[0].IssueId);
        Assert.All(dashboard.Issues, issue => Assert.StartsWith("/music/", issue.FilePath, StringComparison.Ordinal));

        var releases = await service.GetLibraryIssueReleaseSummariesAsync("/music", limit: 2);
        Assert.Equal(2, releases.Count);
        Assert.All(releases, release => Assert.Equal(75, release.Count));
        Assert.Equal(150, releases.Sum(release => release.ByType.Values.Sum()));

        var codecs = await service.GetLibraryIssueCodecSummariesAsync("/music");
        Assert.Equal(150, codecs.Sum(group => group.Count));
        Assert.Contains(codecs, group => group.Codec == "FLAC" && group.Count == 75);
        Assert.Contains(codecs, group => group.Codec == "MP3" && group.Count == 75);
    }

    [Fact]
    public async Task LibraryHealthIssuePage_ReturnsFullFilteredCountWithBoundedRows()
    {
        for (var index = 0; index < 120; index++)
        {
            await service.InsertLibraryIssueAsync(new LibraryIssue
            {
                IssueId = $"page-issue-{index:D3}",
                FilePath = $"/music/track-{index:D3}.flac",
                DetectedAt = DateTimeOffset.FromUnixTimeSeconds(1_700_000_000 + index),
            });
        }

        var page = await service.GetLibraryIssuePageAsync(new LibraryHealthIssueFilter
        {
            LibraryPath = "/music",
            Limit = 20,
        });

        Assert.Equal(120, page.TotalCount);
        Assert.Equal(20, page.Issues.Count);
    }

    [Fact]
    public async Task Constructor_IndexesLibraryHealthRecentIssueQuery()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "EXPLAIN QUERY PLAN SELECT * FROM LibraryHealthIssues WHERE file_path LIKE @path ORDER BY detected_at DESC LIMIT 100";
        cmd.Parameters.AddWithValue("@path", "/music/%");

        await using var reader = await cmd.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());

        Assert.Contains("idx_issues_detected", reader.GetString(3), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Constructor_IndexesRemediationJobIssueQueryWithoutTemporarySort()
    {
        await using var conn = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText =
            """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM LibraryHealthIssues
            WHERE remediation_job_id IS NOT NULL
              AND remediation_job_id <> ''
              AND remediation_job_id = 'job-1'
              AND status = 'fixing'
            ORDER BY detected_at DESC
            """;

        await using var reader = await cmd.ExecuteReaderAsync();
        var plan = new List<string>();
        while (await reader.ReadAsync())
        {
            plan.Add(reader.GetString(3));
        }

        Assert.Contains(plan, detail =>
            detail.Contains("SEARCH LibraryHealthIssues USING INDEX idx_issues_remediation_status", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail => detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task LibraryHealthRemediationBatch_RoundTripsLinkAndStatus()
    {
        for (var index = 1; index <= 3; index++)
        {
            await service.InsertLibraryIssueAsync(new LibraryIssue
            {
                IssueId = $"remediation-{index}",
                FilePath = $"/music/{index}.flac",
                Status = LibraryIssueStatus.Detected,
                DetectedAt = DateTimeOffset.FromUnixTimeSeconds(index),
            });
        }

        var requested = await service.GetLibraryIssuesByIdsAsync(new[]
        {
            "remediation-2",
            " remediation-1 ",
            "remediation-2",
            "missing",
        });
        var linkedCount = await service.UpdateLibraryIssueStatusesAsync(
            requested.Select(issue => issue.IssueId),
            LibraryIssueStatus.Fixing,
            " job-1 ");
        var linked = await service.GetLibraryIssuesByRemediationJobAsync(" job-1 ", LibraryIssueStatus.Fixing);
        var resolvedCount = await service.UpdateLibraryIssueStatusesAsync(
            linked.Select(issue => issue.IssueId),
            LibraryIssueStatus.Resolved);
        var resolved = await service.GetLibraryIssuesByIdsAsync(linked.Select(issue => issue.IssueId));

        Assert.Equal(2, requested.Count);
        Assert.Equal(new[] { "remediation-2", "remediation-1" }, requested.Select(issue => issue.IssueId));
        Assert.Equal(2, linkedCount);
        Assert.Equal(2, linked.Count);
        Assert.All(linked, issue =>
        {
            Assert.Equal("job-1", issue.RemediationJobId);
            Assert.Equal(LibraryIssueStatus.Fixing, issue.Status);
        });
        Assert.Equal(2, resolvedCount);
        Assert.All(resolved, issue =>
        {
            Assert.Equal("job-1", issue.RemediationJobId);
            Assert.Equal(LibraryIssueStatus.Resolved, issue.Status);
            Assert.NotNull(issue.ResolvedAt);
        });
        var untouched = Assert.Single(await service.GetLibraryIssuesByIdsAsync(new[] { "remediation-3" }));
        Assert.Equal(LibraryIssueStatus.Detected, untouched.Status);
        Assert.Empty(untouched.RemediationJobId);
    }

    // ========== FlacInventoryEntry Tests ==========

    [Fact]
    public void FlacInventoryEntry_GenerateFileId_IsConsistent()
    {
        // Act
        var id1 = FlacInventoryEntry.GenerateFileId("user", "/path/file.flac", 12345);
        var id2 = FlacInventoryEntry.GenerateFileId("user", "/path/file.flac", 12345);

        // Assert
        Assert.Equal(id1, id2);
    }

    [Fact]
    public void FlacInventoryEntry_GenerateFileId_DifferentInputsProduceDifferentIds()
    {
        // Act
        var id1 = FlacInventoryEntry.GenerateFileId("user1", "/path/file.flac", 12345);
        var id2 = FlacInventoryEntry.GenerateFileId("user2", "/path/file.flac", 12345);
        var id3 = FlacInventoryEntry.GenerateFileId("user1", "/path/other.flac", 12345);
        var id4 = FlacInventoryEntry.GenerateFileId("user1", "/path/file.flac", 99999);

        // Assert
        Assert.NotEqual(id1, id2);
        Assert.NotEqual(id1, id3);
        Assert.NotEqual(id1, id4);
    }

    // ========== HashDbEntry Tests ==========

    [Fact]
    public void HashDbEntry_GenerateFlacKey_IsConsistent()
    {
        // Act
        var key1 = HashDbEntry.GenerateFlacKey("/path/file.flac", 12345);
        var key2 = HashDbEntry.GenerateFlacKey("/path/file.flac", 12345);

        // Assert
        Assert.Equal(key1, key2);
    }

    [Fact]
    public void HashDbEntry_PackUnpackMetaFlags_RoundTrips()
    {
        // Arrange
        var sampleRate = 44100;
        var channels = 2;
        var bitDepth = 16;

        // Act
        var packed = HashDbEntry.PackMetaFlags(sampleRate, channels, bitDepth);
        var (unpackedRate, unpackedChannels, unpackedDepth) = HashDbEntry.UnpackMetaFlags(packed);

        // Assert
        Assert.Equal(sampleRate, unpackedRate);
        Assert.Equal(channels, unpackedChannels);
        Assert.Equal(bitDepth, unpackedDepth);
    }
}
