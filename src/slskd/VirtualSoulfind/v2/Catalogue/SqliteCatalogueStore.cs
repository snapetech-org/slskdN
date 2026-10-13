// <copyright file="SqliteCatalogueStore.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.VirtualSoulfind.v2.Catalogue
{
    using System;
    using System.Collections.Generic;
    using System.Data;
    using System.Globalization;
    using System.Linq;
    using System.Threading;
    using System.Threading.Tasks;
    using Dapper;
    using Microsoft.Data.Sqlite;

    /// <summary>
    ///     SQLite implementation of <see cref="ICatalogueStore"/>.
    /// </summary>
    /// <remarks>
    ///     Production-ready persistent storage for VirtualSoulfind v2.
    ///     Uses Dapper for efficient SQL operations.
    /// </remarks>
    public sealed class SqliteCatalogueStore : ICatalogueStore, IDisposable
    {
        private const int TrackBatchSize = 500;
        private readonly string _connectionString;
        private bool _disposed;

        static SqliteCatalogueStore()
        {
            // Register DateTimeOffset handler for SQLite + Dapper
            SqlMapper.AddTypeHandler(new DateTimeOffsetHandler());
        }

        public SqliteCatalogueStore(string databasePath, bool pooling = true)
        {
            _connectionString = $"Data Source={databasePath};Pooling={pooling};";
            InitializeDatabase();
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _disposed = true;
            }
        }

        private IDbConnection CreateConnection() => new SqliteConnection(_connectionString);

        private void InitializeDatabase()
        {
            using var connection = CreateConnection();
            connection.Open();

            connection.Execute(@"
                CREATE TABLE IF NOT EXISTS Artists (
                    ArtistId TEXT PRIMARY KEY,
                    MusicBrainzId TEXT,
                    Name TEXT NOT NULL,
                    SortName TEXT,
                    Tags TEXT,
                    CreatedAt TEXT NOT NULL,
                    UpdatedAt TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS IX_Artists_MusicBrainzId ON Artists(MusicBrainzId);
                CREATE INDEX IF NOT EXISTS IX_Artists_Name ON Artists(Name);

                CREATE TABLE IF NOT EXISTS ReleaseGroups (
                    ReleaseGroupId TEXT PRIMARY KEY,
                    MusicBrainzId TEXT,
                    ArtistId TEXT NOT NULL,
                    Title TEXT NOT NULL,
                    PrimaryType INTEGER NOT NULL,
                    Year INTEGER,
                    CreatedAt TEXT NOT NULL,
                    UpdatedAt TEXT NOT NULL,
                    FOREIGN KEY (ArtistId) REFERENCES Artists(ArtistId)
                );

                CREATE INDEX IF NOT EXISTS IX_ReleaseGroups_MusicBrainzId ON ReleaseGroups(MusicBrainzId);
                CREATE INDEX IF NOT EXISTS IX_ReleaseGroups_ArtistId ON ReleaseGroups(ArtistId);

                CREATE TABLE IF NOT EXISTS Releases (
                    ReleaseId TEXT PRIMARY KEY,
                    MusicBrainzId TEXT,
                    ReleaseGroupId TEXT NOT NULL,
                    Title TEXT NOT NULL,
                    Year INTEGER,
                    Country TEXT,
                    Label TEXT,
                    CatalogNumber TEXT,
                    MediaCount INTEGER,
                    CreatedAt TEXT NOT NULL,
                    UpdatedAt TEXT NOT NULL,
                    FOREIGN KEY (ReleaseGroupId) REFERENCES ReleaseGroups(ReleaseGroupId)
                );

                CREATE INDEX IF NOT EXISTS IX_Releases_MusicBrainzId ON Releases(MusicBrainzId);
                CREATE INDEX IF NOT EXISTS IX_Releases_ReleaseGroupId ON Releases(ReleaseGroupId);

                CREATE TABLE IF NOT EXISTS Tracks (
                    TrackId TEXT PRIMARY KEY,
                    MusicBrainzRecordingId TEXT,
                    ReleaseId TEXT NOT NULL,
                    DiscNumber INTEGER NOT NULL,
                    TrackNumber INTEGER NOT NULL,
                    Title TEXT NOT NULL,
                    DurationSeconds INTEGER,
                    Isrc TEXT,
                    Tags TEXT,
                    CreatedAt TEXT NOT NULL,
                    UpdatedAt TEXT NOT NULL,
                    FOREIGN KEY (ReleaseId) REFERENCES Releases(ReleaseId)
                );

                CREATE INDEX IF NOT EXISTS IX_Tracks_MusicBrainzRecordingId ON Tracks(MusicBrainzRecordingId);
                CREATE INDEX IF NOT EXISTS IX_Tracks_ReleaseId ON Tracks(ReleaseId);

                CREATE TABLE IF NOT EXISTS LocalFiles (
                    LocalFileId TEXT PRIMARY KEY,
                    Path TEXT NOT NULL,
                    SizeBytes INTEGER NOT NULL,
                    DurationSeconds INTEGER NOT NULL,
                    Codec TEXT NOT NULL,
                    Bitrate INTEGER NOT NULL,
                    Channels INTEGER NOT NULL,
                    HashPrimary TEXT NOT NULL,
                    HashSecondary TEXT NOT NULL,
                    AudioFingerprintId TEXT,
                    InferredTrackId TEXT,
                    AddedAt TEXT NOT NULL,
                    UpdatedAt TEXT NOT NULL,
                    FOREIGN KEY (InferredTrackId) REFERENCES Tracks(TrackId)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS IX_LocalFiles_Path ON LocalFiles(Path);
                CREATE INDEX IF NOT EXISTS IX_LocalFiles_HashPrimary ON LocalFiles(HashPrimary);
                CREATE INDEX IF NOT EXISTS IX_LocalFiles_InferredTrackId ON LocalFiles(InferredTrackId);

                CREATE TABLE IF NOT EXISTS VerifiedCopies (
                    VerifiedCopyId TEXT PRIMARY KEY,
                    TrackId TEXT NOT NULL,
                    LocalFileId TEXT NOT NULL,
                    HashPrimary TEXT NOT NULL,
                    DurationSeconds INTEGER NOT NULL,
                    VerificationSource INTEGER NOT NULL,
                    VerifiedAt TEXT NOT NULL,
                    Notes TEXT,
                    FOREIGN KEY (TrackId) REFERENCES Tracks(TrackId),
                    FOREIGN KEY (LocalFileId) REFERENCES LocalFiles(LocalFileId)
                );

                CREATE INDEX IF NOT EXISTS IX_VerifiedCopies_TrackId ON VerifiedCopies(TrackId);
                CREATE INDEX IF NOT EXISTS IX_VerifiedCopies_LocalFileId ON VerifiedCopies(LocalFileId);
                CREATE INDEX IF NOT EXISTS IX_VerifiedCopies_LocalFileId_VerifiedAt ON VerifiedCopies(LocalFileId, VerifiedAt DESC);
            ");
        }

        // Artist operations
        public async Task<Artist?> FindArtistByIdAsync(string artistId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<Artist>(
                "SELECT * FROM Artists WHERE ArtistId = @ArtistId",
                new { ArtistId = artistId });
        }

        public async Task<IReadOnlyDictionary<string, Artist>> GetArtistsByIdsAsync(
            IReadOnlyCollection<string> artistIds,
            CancellationToken ct = default)
        {
            var artists = new Dictionary<string, Artist>(StringComparer.Ordinal);
            using var connection = CreateConnection();

            foreach (var batch in artistIds.Distinct(StringComparer.Ordinal).Chunk(TrackBatchSize))
            {
                var parameters = CreateIdParameters(batch, "ArtistId", out var placeholders);
                var rows = await connection.QueryAsync<Artist>(new CommandDefinition(
                    $"SELECT * FROM Artists WHERE ArtistId IN ({placeholders})",
                    parameters,
                    cancellationToken: ct));
                foreach (var artist in rows)
                {
                    artists[artist.ArtistId] = artist;
                }
            }

            return artists;
        }

        public async Task<Artist?> FindArtistByMBIDAsync(string mbid, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<Artist>(
                "SELECT * FROM Artists WHERE MusicBrainzId = @MusicBrainzId",
                new { MusicBrainzId = mbid });
        }

        public async Task<IReadOnlyList<Artist>> SearchArtistsAsync(string query, int limit = 50, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Artist>(
                "SELECT * FROM Artists WHERE Name LIKE @Query OR SortName LIKE @Query LIMIT @Limit",
                new { Query = $"%{query}%", Limit = limit });
            return results.ToList();
        }

        public async Task UpsertArtistAsync(Artist artist, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(@"
                INSERT INTO Artists (ArtistId, MusicBrainzId, Name, SortName, Tags, CreatedAt, UpdatedAt)
                VALUES (@ArtistId, @MusicBrainzId, @Name, @SortName, @Tags, @CreatedAt, @UpdatedAt)
                ON CONFLICT(ArtistId) DO UPDATE SET
                    MusicBrainzId = @MusicBrainzId,
                    Name = @Name,
                    SortName = @SortName,
                    Tags = @Tags,
                    UpdatedAt = @UpdatedAt",
                artist);
        }

        public async Task<IReadOnlyList<Artist>> ListArtistsAsync(int offset = 0, int limit = 100, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Artist>(
                "SELECT * FROM Artists ORDER BY Name LIMIT @Limit OFFSET @Offset",
                new { Limit = limit, Offset = offset });
            return results.ToList();
        }

        // ReleaseGroup operations
        public async Task<ReleaseGroup?> FindReleaseGroupByIdAsync(string releaseGroupId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<ReleaseGroup>(
                "SELECT * FROM ReleaseGroups WHERE ReleaseGroupId = @ReleaseGroupId",
                new { ReleaseGroupId = releaseGroupId });
        }

        public async Task<IReadOnlyDictionary<string, ReleaseGroup>> GetReleaseGroupsByIdsAsync(
            IReadOnlyCollection<string> releaseGroupIds,
            CancellationToken ct = default)
        {
            var releaseGroups = new Dictionary<string, ReleaseGroup>(StringComparer.Ordinal);
            using var connection = CreateConnection();

            foreach (var batch in releaseGroupIds.Distinct(StringComparer.Ordinal).Chunk(TrackBatchSize))
            {
                var parameters = CreateIdParameters(batch, "ReleaseGroupId", out var placeholders);
                var rows = await connection.QueryAsync<ReleaseGroup>(new CommandDefinition(
                    $"SELECT * FROM ReleaseGroups WHERE ReleaseGroupId IN ({placeholders})",
                    parameters,
                    cancellationToken: ct));
                foreach (var releaseGroup in rows)
                {
                    releaseGroups[releaseGroup.ReleaseGroupId] = releaseGroup;
                }
            }

            return releaseGroups;
        }

        public async Task<ReleaseGroup?> FindReleaseGroupByMBIDAsync(string mbid, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<ReleaseGroup>(
                "SELECT * FROM ReleaseGroups WHERE MusicBrainzId = @MusicBrainzId",
                new { MusicBrainzId = mbid });
        }

        public async Task<IReadOnlyList<ReleaseGroup>> SearchReleaseGroupsAsync(string query, int limit = 50, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<ReleaseGroup>(
                "SELECT * FROM ReleaseGroups WHERE Title LIKE @Query LIMIT @Limit",
                new { Query = $"%{query}%", Limit = limit });
            return results.ToList();
        }

        public async Task UpsertReleaseGroupAsync(ReleaseGroup releaseGroup, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(@"
                INSERT INTO ReleaseGroups (ReleaseGroupId, MusicBrainzId, ArtistId, Title, PrimaryType, Year, CreatedAt, UpdatedAt)
                VALUES (@ReleaseGroupId, @MusicBrainzId, @ArtistId, @Title, @PrimaryType, @Year, @CreatedAt, @UpdatedAt)
                ON CONFLICT(ReleaseGroupId) DO UPDATE SET
                    MusicBrainzId = @MusicBrainzId,
                    ArtistId = @ArtistId,
                    Title = @Title,
                    PrimaryType = @PrimaryType,
                    Year = @Year,
                    UpdatedAt = @UpdatedAt",
                releaseGroup);
        }

        public async Task<IReadOnlyList<ReleaseGroup>> ListReleaseGroupsForArtistAsync(string artistId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<ReleaseGroup>(
                "SELECT * FROM ReleaseGroups WHERE ArtistId = @ArtistId ORDER BY Year DESC, Title",
                new { ArtistId = artistId });
            return results.ToList();
        }

        // Release operations
        public async Task<Release?> FindReleaseByIdAsync(string releaseId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<Release>(
                "SELECT * FROM Releases WHERE ReleaseId = @ReleaseId",
                new { ReleaseId = releaseId });
        }

        public async Task<Release?> FindReleaseByMBIDAsync(string mbid, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<Release>(
                "SELECT * FROM Releases WHERE MusicBrainzId = @MusicBrainzId",
                new { MusicBrainzId = mbid });
        }

        public async Task<IReadOnlyList<Release>> SearchReleasesAsync(string query, int limit = 50, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Release>(
                "SELECT * FROM Releases WHERE Title LIKE @Query LIMIT @Limit",
                new { Query = $"%{query}%", Limit = limit });
            return results.ToList();
        }

        public async Task UpsertReleaseAsync(Release release, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(@"
                INSERT INTO Releases (ReleaseId, MusicBrainzId, ReleaseGroupId, Title, Year, Country, Label, CatalogNumber, MediaCount, CreatedAt, UpdatedAt)
                VALUES (@ReleaseId, @MusicBrainzId, @ReleaseGroupId, @Title, @Year, @Country, @Label, @CatalogNumber, @MediaCount, @CreatedAt, @UpdatedAt)
                ON CONFLICT(ReleaseId) DO UPDATE SET
                    MusicBrainzId = @MusicBrainzId,
                    ReleaseGroupId = @ReleaseGroupId,
                    Title = @Title,
                    Year = @Year,
                    Country = @Country,
                    Label = @Label,
                    CatalogNumber = @CatalogNumber,
                    MediaCount = @MediaCount,
                    UpdatedAt = @UpdatedAt",
                release);
        }

        public async Task<IReadOnlyList<Release>> ListReleasesAsync(int offset = 0, int limit = 100, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Release>(
                "SELECT * FROM Releases ORDER BY Year DESC, Title LIMIT @Limit OFFSET @Offset",
                new { Limit = limit, Offset = offset });
            return results.ToList();
        }

        public async Task<IReadOnlyList<Release>> ListReleasesForReleaseGroupAsync(string releaseGroupId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Release>(
                "SELECT * FROM Releases WHERE ReleaseGroupId = @ReleaseGroupId ORDER BY Year DESC, Title",
                new { ReleaseGroupId = releaseGroupId });
            return results.ToList();
        }

        // Track operations
        public async Task<Track?> FindTrackByIdAsync(string trackId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<Track>(
                "SELECT * FROM Tracks WHERE TrackId = @TrackId",
                new { TrackId = trackId });
        }

        public async Task<IReadOnlyDictionary<string, Track>> GetTracksByIdsAsync(
            IReadOnlyCollection<string> trackIds,
            CancellationToken ct = default)
        {
            var tracks = new Dictionary<string, Track>(StringComparer.Ordinal);
            using var connection = CreateConnection();

            foreach (var batch in trackIds.Distinct(StringComparer.Ordinal).Chunk(TrackBatchSize))
            {
                var parameters = new DynamicParameters();
                var parameterNames = batch.Select((trackId, index) =>
                {
                    var name = $"TrackId{index}";
                    parameters.Add(name, trackId);
                    return $"@{name}";
                });
                var rows = await connection.QueryAsync<Track>(new CommandDefinition(
                    $"SELECT * FROM Tracks WHERE TrackId IN ({string.Join(", ", parameterNames)})",
                    parameters,
                    cancellationToken: ct));

                foreach (var track in rows)
                {
                    tracks[track.TrackId] = track;
                }
            }

            return tracks;
        }

        public async Task<Track?> FindTrackByMBIDAsync(string mbid, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<Track>(
                "SELECT * FROM Tracks WHERE MusicBrainzRecordingId = @MusicBrainzRecordingId",
                new { MusicBrainzRecordingId = mbid });
        }

        public async Task<IReadOnlyList<Track>> SearchTracksAsync(string query, int limit = 50, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Track>(
                "SELECT * FROM Tracks WHERE Title LIKE @Query LIMIT @Limit",
                new { Query = $"%{query}%", Limit = limit });
            return results.ToList();
        }

        public async Task UpsertTrackAsync(Track track, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(@"
                INSERT INTO Tracks (TrackId, MusicBrainzRecordingId, ReleaseId, DiscNumber, TrackNumber, Title, DurationSeconds, Isrc, Tags, CreatedAt, UpdatedAt)
                VALUES (@TrackId, @MusicBrainzRecordingId, @ReleaseId, @DiscNumber, @TrackNumber, @Title, @DurationSeconds, @Isrc, @Tags, @CreatedAt, @UpdatedAt)
                ON CONFLICT(TrackId) DO UPDATE SET
                    MusicBrainzRecordingId = @MusicBrainzRecordingId,
                    ReleaseId = @ReleaseId,
                    DiscNumber = @DiscNumber,
                    TrackNumber = @TrackNumber,
                    Title = @Title,
                    DurationSeconds = @DurationSeconds,
                    Isrc = @Isrc,
                    Tags = @Tags,
                    UpdatedAt = @UpdatedAt",
                track);
        }

        public async Task<IReadOnlyList<Track>> ListTracksAsync(int offset = 0, int limit = 100, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Track>(
                "SELECT * FROM Tracks ORDER BY ReleaseId, DiscNumber, TrackNumber, Title LIMIT @Limit OFFSET @Offset",
                new { Limit = limit, Offset = offset });
            return results.ToList();
        }

        public async Task<IReadOnlyList<Track>> ListTracksForReleaseAsync(string releaseId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<Track>(
                "SELECT * FROM Tracks WHERE ReleaseId = @ReleaseId ORDER BY DiscNumber, TrackNumber",
                new { ReleaseId = releaseId });
            return results.ToList();
        }

        public async Task<IReadOnlyDictionary<string, IReadOnlyList<Track>>> GetTracksByReleaseIdsAsync(
            IReadOnlyCollection<string> releaseIds,
            CancellationToken ct = default)
        {
            var tracks = new Dictionary<string, List<Track>>(StringComparer.Ordinal);
            using var connection = CreateConnection();

            foreach (var batch in releaseIds.Distinct(StringComparer.Ordinal).Chunk(TrackBatchSize))
            {
                var parameters = CreateIdParameters(batch, "ReleaseId", out var placeholders);
                var rows = await connection.QueryAsync<Track>(new CommandDefinition($@"
                    SELECT * FROM Tracks
                    WHERE ReleaseId IN ({placeholders})
                    ORDER BY ReleaseId, DiscNumber, TrackNumber",
                    parameters,
                    cancellationToken: ct));
                foreach (var track in rows)
                {
                    if (!tracks.TryGetValue(track.ReleaseId, out var releaseTracks))
                    {
                        releaseTracks = [];
                        tracks[track.ReleaseId] = releaseTracks;
                    }

                    releaseTracks.Add(track);
                }
            }

            return tracks.ToDictionary(
                pair => pair.Key,
                pair => (IReadOnlyList<Track>)pair.Value,
                StringComparer.Ordinal);
        }

        // Count operations
        public async Task<int> CountArtistsAsync(CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM Artists");
        }

        public async Task<int> CountReleasesAsync(CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM Releases");
        }

        public async Task<int> CountTracksAsync(CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM Tracks");
        }

        // LocalFile operations
        public async Task<LocalFile?> FindLocalFileByPathAsync(string path, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<LocalFile>(
                "SELECT * FROM LocalFiles WHERE Path = @Path",
                new { Path = path });
        }

        public async Task<LocalFile?> FindLocalFileByIdAsync(string localFileId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<LocalFile>(
                "SELECT * FROM LocalFiles WHERE LocalFileId = @LocalFileId",
                new { LocalFileId = localFileId });
        }

        public async Task<IReadOnlyList<LocalFile>> ListLocalFilesForTrackAsync(string trackId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<LocalFile>(
                @"SELECT DISTINCT lf.*
                  FROM LocalFiles lf
                  LEFT JOIN VerifiedCopies vc ON vc.LocalFileId = lf.LocalFileId
                  WHERE lf.InferredTrackId = @TrackId OR vc.TrackId = @TrackId
                  ORDER BY lf.UpdatedAt DESC, lf.Path",
                new { TrackId = trackId });
            return results.ToList();
        }

        public async Task<IReadOnlyDictionary<string, TrackCopyState>> GetTrackCopyStatesAsync(
            IReadOnlyCollection<string> trackIds,
            CancellationToken ct = default)
        {
            var uniqueTrackIds = trackIds.Distinct(StringComparer.Ordinal).ToList();
            var states = new Dictionary<string, TrackCopyState>(StringComparer.Ordinal);
            using var connection = CreateConnection();

            foreach (var batch in uniqueTrackIds.Chunk(TrackBatchSize))
            {
                var parameters = new DynamicParameters();
                var parameterNames = batch.Select((trackId, index) =>
                {
                    var name = $"TrackId{index}";
                    parameters.Add(name, trackId);
                    return $"@{name}";
                });
                var placeholders = string.Join(", ", parameterNames);
                var rows = await connection.QueryAsync<TrackCopyStateRow>(new CommandDefinition($@"
                    SELECT TrackId,
                           MAX(HasLocalFile) AS HasLocalFile,
                           MAX(HasVerifiedCopy) AS HasVerifiedCopy
                    FROM (
                        SELECT InferredTrackId AS TrackId,
                               1 AS HasLocalFile,
                               0 AS HasVerifiedCopy
                        FROM LocalFiles
                        WHERE InferredTrackId IN ({placeholders})

                        UNION ALL

                        SELECT vc.TrackId,
                               CASE WHEN lf.LocalFileId IS NULL THEN 0 ELSE 1 END AS HasLocalFile,
                               1 AS HasVerifiedCopy
                        FROM VerifiedCopies vc
                        LEFT JOIN LocalFiles lf ON lf.LocalFileId = vc.LocalFileId
                        WHERE vc.TrackId IN ({placeholders})
                    )
                    GROUP BY TrackId",
                    parameters,
                    cancellationToken: ct));

                foreach (var row in rows)
                {
                    states[row.TrackId] = new TrackCopyState(row.HasLocalFile != 0, row.HasVerifiedCopy != 0);
                }
            }

            return states;
        }

        public async Task<IReadOnlyList<LocalFile>> FindLocalFilesByHashAsync(string hashPrimary, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<LocalFile>(
                "SELECT * FROM LocalFiles WHERE HashPrimary = @HashPrimary",
                new { HashPrimary = hashPrimary });
            return results.ToList();
        }

        public async Task UpsertLocalFileAsync(LocalFile localFile, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(@"
                INSERT INTO LocalFiles (
                    LocalFileId, Path, SizeBytes, DurationSeconds, Codec, Bitrate, Channels,
                    HashPrimary, HashSecondary, AudioFingerprintId, InferredTrackId,
                    AddedAt, UpdatedAt
                )
                VALUES (
                    @LocalFileId, @Path, @SizeBytes, @DurationSeconds, @Codec, @Bitrate, @Channels,
                    @HashPrimary, @HashSecondary, @AudioFingerprintId, @InferredTrackId,
                    @AddedAt, @UpdatedAt
                )
                ON CONFLICT(LocalFileId) DO UPDATE SET
                    Path = @Path,
                    SizeBytes = @SizeBytes,
                    DurationSeconds = @DurationSeconds,
                    Codec = @Codec,
                    Bitrate = @Bitrate,
                    Channels = @Channels,
                    HashPrimary = @HashPrimary,
                    HashSecondary = @HashSecondary,
                    AudioFingerprintId = @AudioFingerprintId,
                    InferredTrackId = @InferredTrackId,
                    UpdatedAt = @UpdatedAt",
                localFile);
        }

        public async Task<IReadOnlyList<LocalFile>> ListLocalFilesAsync(int offset = 0, int limit = 100, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<LocalFile>(
                "SELECT * FROM LocalFiles ORDER BY UpdatedAt DESC, Path LIMIT @Limit OFFSET @Offset",
                new { Limit = limit, Offset = offset });
            return results.ToList();
        }

        public async Task<int> CountLocalFilesAsync(CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM LocalFiles");
        }

        // VerifiedCopy operations
        public async Task<VerifiedCopy?> FindVerifiedCopyForTrackAsync(string trackId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<VerifiedCopy>(
                "SELECT * FROM VerifiedCopies WHERE TrackId = @TrackId ORDER BY VerifiedAt DESC LIMIT 1",
                new { TrackId = trackId });
        }

        public async Task<IReadOnlyList<VerifiedCopy>> ListVerifiedCopiesForTrackAsync(string trackId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<VerifiedCopy>(
                "SELECT * FROM VerifiedCopies WHERE TrackId = @TrackId ORDER BY VerifiedAt DESC",
                new { TrackId = trackId });
            return results.ToList();
        }

        public async Task<IReadOnlyDictionary<string, VerifiedCopy>> GetLatestVerifiedCopiesByLocalFileIdsAsync(
            IReadOnlyCollection<string> localFileIds,
            CancellationToken ct = default)
        {
            var verifiedCopies = new Dictionary<string, VerifiedCopy>(StringComparer.Ordinal);
            using var connection = CreateConnection();

            foreach (var batch in localFileIds.Distinct(StringComparer.Ordinal).Chunk(TrackBatchSize))
            {
                var parameters = CreateIdParameters(batch, "LocalFileId", out var placeholders);
                var rows = await connection.QueryAsync<VerifiedCopy>(new CommandDefinition($@"
                    SELECT * FROM VerifiedCopies
                    WHERE LocalFileId IN ({placeholders})
                    ORDER BY LocalFileId, VerifiedAt DESC",
                    parameters,
                    cancellationToken: ct));
                foreach (var verifiedCopy in rows)
                {
                    verifiedCopies.TryAdd(verifiedCopy.LocalFileId, verifiedCopy);
                }
            }

            return verifiedCopies;
        }

        public async Task<IReadOnlyList<VerifiedCopy>> ListVerifiedCopiesAsync(int offset = 0, int limit = 100, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            var results = await connection.QueryAsync<VerifiedCopy>(
                "SELECT * FROM VerifiedCopies ORDER BY VerifiedAt DESC LIMIT @Limit OFFSET @Offset",
                new { Limit = limit, Offset = offset });
            return results.ToList();
        }

        public async Task<VerifiedCopy?> FindVerifiedCopyByIdAsync(string verifiedCopyId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.QuerySingleOrDefaultAsync<VerifiedCopy>(
                "SELECT * FROM VerifiedCopies WHERE VerifiedCopyId = @VerifiedCopyId",
                new { VerifiedCopyId = verifiedCopyId });
        }

        public async Task UpsertVerifiedCopyAsync(VerifiedCopy verifiedCopy, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(@"
                INSERT INTO VerifiedCopies (
                    VerifiedCopyId, TrackId, LocalFileId, HashPrimary, DurationSeconds,
                    VerificationSource, VerifiedAt, Notes
                )
                VALUES (
                    @VerifiedCopyId, @TrackId, @LocalFileId, @HashPrimary, @DurationSeconds,
                    @VerificationSource, @VerifiedAt, @Notes
                )
                ON CONFLICT(VerifiedCopyId) DO UPDATE SET
                    TrackId = @TrackId,
                    LocalFileId = @LocalFileId,
                    HashPrimary = @HashPrimary,
                    DurationSeconds = @DurationSeconds,
                    VerificationSource = @VerificationSource,
                    VerifiedAt = @VerifiedAt,
                    Notes = @Notes",
                verifiedCopy);
        }

        public async Task DeleteVerifiedCopyAsync(string verifiedCopyId, CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            await connection.ExecuteAsync(
                "DELETE FROM VerifiedCopies WHERE VerifiedCopyId = @VerifiedCopyId",
                new { VerifiedCopyId = verifiedCopyId });
        }

        public async Task<int> CountVerifiedCopiesAsync(CancellationToken ct = default)
        {
            using var connection = CreateConnection();
            return await connection.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM VerifiedCopies");
        }

        private sealed class TrackCopyStateRow
        {
            public string TrackId { get; init; } = string.Empty;

            public int HasLocalFile { get; init; }

            public int HasVerifiedCopy { get; init; }
        }

        private static DynamicParameters CreateIdParameters(
            IEnumerable<string> ids,
            string prefix,
            out string placeholders)
        {
            var parameters = new DynamicParameters();
            placeholders = string.Join(", ", ids.Select((id, index) =>
            {
                var name = $"{prefix}{index}";
                parameters.Add(name, id);
                return $"@{name}";
            }));
            return parameters;
        }

        /// <summary>
        ///     Dapper type handler for DateTimeOffset with SQLite.
        /// </summary>
        private class DateTimeOffsetHandler : SqlMapper.TypeHandler<DateTimeOffset>
        {
            public override DateTimeOffset Parse(object value)
            {
                if (value is string str)
                {
                    return DateTimeOffset.TryParse(
                        str,
                        CultureInfo.InvariantCulture,
                        DateTimeStyles.RoundtripKind,
                        out var parsed) ? parsed : DateTimeOffset.MinValue;
                }

                return DateTimeOffset.MinValue;
            }

            public override void SetValue(IDbDataParameter parameter, DateTimeOffset value)
            {
                parameter.Value = value.ToString("O"); // ISO 8601 format
            }
        }
    }
}
