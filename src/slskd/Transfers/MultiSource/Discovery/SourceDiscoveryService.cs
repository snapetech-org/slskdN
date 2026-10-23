// <copyright file="SourceDiscoveryService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Transfers.MultiSource.Discovery
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Linq;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.Data.Sqlite;
    using Microsoft.Extensions.Hosting;
    using Serilog;
    using Soulseek;
    using slskd.Common.Security;

    /// <summary>
    ///     Service for continuous background discovery of file sources.
    /// </summary>
    public sealed class SourceDiscoveryService : IHostedService, ISourceDiscoveryService, IDisposable
    {
        /// <summary>
        ///     Search window duration in milliseconds (4 minutes 30 seconds).
        /// </summary>
        private const int SearchWindowMs = 270000;

        /// <summary>
        ///     Pause between search cycles in milliseconds (1 second).
        /// </summary>
        private const int CyclePauseMs = 1000;

        private const int UpsertBatchSize = 100;

        private readonly ISoulseekClient client;
        private readonly ISoulseekSafetyLimiter safetyLimiter;
        private readonly IContentVerificationService verificationService;
        private readonly string dbPath;
        private readonly ILogger log = Log.ForContext<SourceDiscoveryService>();

        private CancellationTokenSource? cts;
        private Task? discoveryTask;
        private int searchCycles;
        private int lastCycleNewFiles;
        private bool enableHashVerification;

        /// <summary>
        ///     Initializes a new instance of the <see cref="SourceDiscoveryService"/> class.
        /// </summary>
        /// <param name="appDirectory">The application data directory.</param>
        /// <param name="soulseekClient">The Soulseek client.</param>
        /// <param name="verificationService">The content verification service.</param>
        /// <param name="safetyLimiter">The shared Soulseek safety limiter.</param>
        public SourceDiscoveryService(
            string appDirectory,
            ISoulseekClient soulseekClient,
            IContentVerificationService verificationService,
            ISoulseekSafetyLimiter safetyLimiter)
        {
            client = soulseekClient;
            this.verificationService = verificationService;
            this.safetyLimiter = safetyLimiter;
            CurrentSearchTerm = string.Empty;

            // Store DB in the app data directory (not LocalApplicationData which can be /slskd in containers)
            var slskdPath = Path.Combine(appDirectory, "discovery");
            if (!System.IO.Directory.Exists(slskdPath))
            {
                System.IO.Directory.CreateDirectory(slskdPath);
            }

            dbPath = Path.Combine(slskdPath, "discovery.db");

            InitializeDatabase();
        }

        /// <inheritdoc/>
        public Task StartAsync(CancellationToken cancellationToken)
        {
            log.Information("[Discovery] Service started.");
            return Task.CompletedTask;
        }

        /// <inheritdoc/>
        public async Task StopAsync(CancellationToken cancellationToken)
        {
            log.Information("[Discovery] Service stopping.");
            await StopDiscoveryAsync();
        }

        /// <inheritdoc/>
        public bool IsRunning => discoveryTask != null && !discoveryTask.IsCompleted;

        /// <inheritdoc/>
        public string CurrentSearchTerm { get; private set; }

        /// <inheritdoc/>
        public async Task StartDiscoveryAsync(string searchTerm, bool enableHashVerification = true, CancellationToken cancellationToken = default)
        {
            if (IsRunning)
            {
                log.Warning("[Discovery] Already running. Stop first before starting a new discovery.");
                return;
            }

            CurrentSearchTerm = searchTerm;
            this.enableHashVerification = enableHashVerification;
            searchCycles = 0;
            lastCycleNewFiles = 0;

            cts?.Dispose();
            cts = new CancellationTokenSource();

            log.Information("[Discovery] Starting continuous discovery for: {SearchTerm} (hash verification: {HashEnabled})",
                searchTerm, enableHashVerification);

            discoveryTask = Task.Run(() => DiscoveryLoopAsync(cts.Token), CancellationToken.None);

            await Task.CompletedTask;
        }

        /// <inheritdoc/>
        public async Task StopDiscoveryAsync()
        {
            if (!IsRunning)
            {
                return;
            }

            log.Information("[Discovery] Stopping discovery...");
            cts?.Cancel();

            if (discoveryTask != null)
            {
                await discoveryTask;
            }

            discoveryTask = null;
            cts?.Dispose();
            cts = null;
            log.Information("[Discovery] Stopped. Total cycles: {Cycles}", searchCycles);
        }

        /// <inheritdoc/>
        public void Dispose()
        {
            cts?.Cancel();
            cts?.Dispose();
            cts = null;
        }

        /// <inheritdoc/>
        public DiscoveryStats GetStats()
        {
            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            var stats = new DiscoveryStats
            {
                SearchCycles = searchCycles,
                LastCycleNewFiles = lastCycleNewFiles,
                HashVerificationEnabled = enableHashVerification,
            };

            // Total files
            using (var cmd = connection.CreateCommand())
            {
                cmd.CommandText = "SELECT COUNT(*) FROM DiscoveredFiles";
                stats.TotalFiles = Convert.ToInt32(cmd.ExecuteScalar());
            }

            // Total users
            using (var cmd = connection.CreateCommand())
            {
                cmd.CommandText = "SELECT COUNT(DISTINCT Username) FROM DiscoveredFiles";
                stats.TotalUsers = Convert.ToInt32(cmd.ExecuteScalar());
            }

            // Files with hash
            using (var cmd = connection.CreateCommand())
            {
                cmd.CommandText = "SELECT COUNT(*) FROM DiscoveredFiles WHERE Hash IS NOT NULL";
                stats.FilesWithHash = Convert.ToInt32(cmd.ExecuteScalar());
            }

            return stats;
        }

        /// <inheritdoc/>
        public List<DiscoveredSource> GetSourcesBySize(long size, int limit = 100)
        {
            var results = new List<DiscoveredSource>();

            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                SELECT Username, Filename, Size, Hash, UploadSpeed, FirstSeenUnix, LastSeenUnix
                FROM DiscoveredFiles
                WHERE Size = @size
                ORDER BY UploadSpeed DESC
                LIMIT @limit";
            cmd.Parameters.AddWithValue("@size", size);
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                results.Add(new DiscoveredSource
                {
                    Username = reader.GetString(0),
                    Filename = reader.GetString(1),
                    Size = reader.GetInt64(2),
                    Hash = reader.IsDBNull(3) ? null : reader.GetString(3),
                    UploadSpeed = reader.GetInt32(4),
                    FirstSeenUnix = reader.GetInt64(5),
                    LastSeenUnix = reader.GetInt64(6),
                });
            }

            return results;
        }

        /// <inheritdoc/>
        public List<DiscoveredSource> GetSourcesByFilename(string filenamePattern, int limit = 100)
        {
            var results = new List<DiscoveredSource>();

            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                SELECT Username, Filename, Size, Hash, UploadSpeed, FirstSeenUnix, LastSeenUnix
                FROM DiscoveredFiles
                WHERE Filename LIKE @pattern
                ORDER BY UploadSpeed DESC
                LIMIT @limit";
            cmd.Parameters.AddWithValue("@pattern", $"%{filenamePattern}%");
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                results.Add(new DiscoveredSource
                {
                    Username = reader.GetString(0),
                    Filename = reader.GetString(1),
                    Size = reader.GetInt64(2),
                    Hash = reader.IsDBNull(3) ? null : reader.GetString(3),
                    UploadSpeed = reader.GetInt32(4),
                    FirstSeenUnix = reader.GetInt64(5),
                    LastSeenUnix = reader.GetInt64(6),
                });
            }

            return results;
        }

        /// <inheritdoc/>
        public List<FileSizeSummary> GetFileSizeSummaries(int minSources = 2)
        {
            var results = new List<FileSizeSummary>();

            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                SELECT Size, COUNT(DISTINCT Username) as SourceCount, MIN(Filename) as SampleFilename
                FROM DiscoveredFiles
                GROUP BY Size
                HAVING SourceCount >= @minSources
                ORDER BY SourceCount DESC
                LIMIT 100";
            cmd.Parameters.AddWithValue("@minSources", minSources);

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                results.Add(new FileSizeSummary
                {
                    Size = reader.GetInt64(0),
                    SourceCount = reader.GetInt32(1),
                    SampleFilename = reader.GetString(2),
                });
            }

            return results;
        }

        /// <inheritdoc/>
        public int GetNoPartialSupportCount()
        {
            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var cmd = connection.CreateCommand();
            cmd.CommandText = "SELECT COUNT(*) FROM DiscoveredFiles WHERE SupportsPartial = 0";

            var result = cmd.ExecuteScalar();
            return Convert.ToInt32(result ?? 0);
        }

        /// <inheritdoc/>
        public void ResetPartialSupportFlags()
        {
            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var cmd = connection.CreateCommand();
            cmd.CommandText = "UPDATE DiscoveredFiles SET SupportsPartial = 1 WHERE SupportsPartial = 0";
            var affected = cmd.ExecuteNonQuery();

            log.Information("[Discovery] Reset partial support flags for {Count} entries", affected);
        }

        private void InitializeDatabase()
        {
            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS DiscoveredFiles (
                    Username TEXT NOT NULL,
                    Filename TEXT NOT NULL,
                    Size INTEGER NOT NULL,
                    Hash TEXT,
                    UploadSpeed INTEGER DEFAULT 0,
                    FirstSeenUnix INTEGER NOT NULL,
                    LastSeenUnix INTEGER NOT NULL,
                    PRIMARY KEY (Username, Filename, Size)
                );
                CREATE INDEX IF NOT EXISTS idx_size ON DiscoveredFiles(Size);
                CREATE INDEX IF NOT EXISTS idx_filename ON DiscoveredFiles(Filename);
                CREATE INDEX IF NOT EXISTS idx_hash ON DiscoveredFiles(Hash);
            ";
            cmd.ExecuteNonQuery();

            log.Information("[Discovery] Database initialized at {Path}", dbPath);
        }

        private async Task DiscoveryLoopAsync(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    var cycle = Interlocked.Increment(ref searchCycles);
                    log.Information("[Discovery] Starting search cycle #{Cycle} for: {Term}", cycle, CurrentSearchTerm);

                    // Collect responses during the search window
                    var responses = new List<SearchResponse>();
                    var searchStarted = DateTime.UtcNow;

                    if (!safetyLimiter.TryConsumeSearch("source-discovery"))
                    {
                        log.Warning("[SAFETY] Discovery search cycle #{Cycle} skipped: rate limit exceeded", cycle);
                        await Task.Delay(CyclePauseMs, cancellationToken);
                        continue;
                    }

                    try
                    {
                        await client.SearchAsync(
                            SearchQuery.FromText(CurrentSearchTerm),
                            responseHandler: (response) => responses.Add(response),
                            options: new SearchOptions(
                                searchTimeout: SearchWindowMs,
                                responseLimit: 10000,
                                fileLimit: 1000000,
                                filterResponses: true,
                                minimumResponseFileCount: 1),
                            cancellationToken: cancellationToken);
                    }
                    catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
                    {
                        // Search timeout is expected
                    }

                    var searchDuration = DateTime.UtcNow - searchStarted;
                    log.Information("[Discovery] Search cycle #{Cycle} collected {Count} responses in {Duration:F1}s",
                        cycle, responses.Count, searchDuration.TotalSeconds);

                    // Process responses and store in DB
                    var newFiles = await ProcessResponsesAsync(responses, cancellationToken);
                    Interlocked.Exchange(ref lastCycleNewFiles, newFiles);

                    log.Information("[Discovery] Cycle #{Cycle} complete. New files: {New}. Total in DB: {Total}",
                        cycle, newFiles, GetStats().TotalFiles);

                    // Small pause before next cycle
                    await Task.Delay(CyclePauseMs, cancellationToken);
                }
                catch (OperationCanceledException ex) when (
                    cancellationToken.IsCancellationRequested &&
                    ex.CancellationToken == cancellationToken)
                {
                    break;
                }
                catch (Exception ex)
                {
                    log.Error(ex, "[Discovery] Error in discovery loop: {Message}", ex.Message);
                    await Task.Delay(5000, cancellationToken); // Wait before retry
                }
            }
        }

        private async Task<int> ProcessResponsesAsync(List<SearchResponse> responses, CancellationToken cancellationToken)
        {
            var nowUnix = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

            using var connection = new SqliteConnection($"Data Source={dbPath}");
            connection.Open();

            using var transaction = connection.BeginTransaction();
            (int AffectedRows, int CommandCount) ingestion;

            try
            {
                ingestion = UpsertResponses(connection, transaction, responses, nowUnix, cancellationToken);

                transaction.Commit();
            }
            catch (Exception ex)
            {
                transaction.Rollback();
                log.Error(ex, "[Discovery] Failed to process responses: {Message}", ex.Message);
                throw;
            }

            log.Debug(
                "[Discovery] Persisted {FileCount} response files with {CommandCount} batched upsert commands",
                ingestion.AffectedRows,
                ingestion.CommandCount);

            // Future: Hash verification for FLAC files
            if (enableHashVerification)
            {
                await VerifyFlacHashesAsync(connection, cancellationToken);
            }

            return ingestion.AffectedRows;
        }

        internal static (int AffectedRows, int CommandCount) UpsertResponses(
            SqliteConnection connection,
            SqliteTransaction transaction,
            IEnumerable<SearchResponse> responses,
            long nowUnix,
            CancellationToken cancellationToken)
        {
            var batch = new List<(string Username, string Filename, long Size, int UploadSpeed)>(UpsertBatchSize);
            var affectedRows = 0;
            var commandCount = 0;
            var cancelled = false;

            foreach (var response in responses)
            {
                foreach (var file in response.Files)
                {
                    if (cancellationToken.IsCancellationRequested)
                    {
                        cancelled = true;
                        break;
                    }

                    batch.Add((response.Username, file.Filename, file.Size, response.UploadSpeed));
                    if (batch.Count < UpsertBatchSize)
                    {
                        continue;
                    }

                    affectedRows += ExecuteUpsertBatch(connection, transaction, batch, nowUnix);
                    commandCount++;
                    batch.Clear();
                }

                if (cancelled)
                {
                    break;
                }
            }

            if (batch.Count > 0)
            {
                affectedRows += ExecuteUpsertBatch(connection, transaction, batch, nowUnix);
                commandCount++;
            }

            return (affectedRows, commandCount);
        }

        private static int ExecuteUpsertBatch(
            SqliteConnection connection,
            SqliteTransaction transaction,
            IReadOnlyList<(string Username, string Filename, long Size, int UploadSpeed)> batch,
            long nowUnix)
        {
            using var cmd = connection.CreateCommand();
            cmd.Transaction = transaction;
            var values = Enumerable.Range(0, batch.Count)
                .Select(index => $"(@username{index}, @filename{index}, @size{index}, @speed{index}, @now{index}, @now{index})");

            // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- the interpolated VALUES list contains generated parameter markers only; row values are bound below.
            cmd.CommandText = $"""
                INSERT INTO DiscoveredFiles (Username, Filename, Size, UploadSpeed, FirstSeenUnix, LastSeenUnix)
                VALUES {string.Join(", ", values)}
                ON CONFLICT(Username, Filename, Size) DO UPDATE SET
                    LastSeenUnix = excluded.LastSeenUnix,
                    UploadSpeed = excluded.UploadSpeed
                """;

            for (var index = 0; index < batch.Count; index++)
            {
                var row = batch[index];
                cmd.Parameters.AddWithValue($"@username{index}", row.Username);
                cmd.Parameters.AddWithValue($"@filename{index}", row.Filename);
                cmd.Parameters.AddWithValue($"@size{index}", row.Size);
                cmd.Parameters.AddWithValue($"@speed{index}", row.UploadSpeed);
                cmd.Parameters.AddWithValue($"@now{index}", nowUnix);
            }

            return cmd.ExecuteNonQuery();
        }

        private async Task VerifyFlacHashesAsync(SqliteConnection connection, CancellationToken cancellationToken)
        {
            // Get FLAC files without hash
            var filesToVerify = new List<(string Username, string Filename, long Size)>();

            using (var cmd = connection.CreateCommand())
            {
                cmd.CommandText = @"
                    SELECT Username, Filename, Size
                    FROM DiscoveredFiles
                    WHERE Hash IS NULL
                      AND LOWER(Filename) LIKE '%.flac'
                    LIMIT 10"; // Process in batches

                using var reader = cmd.ExecuteReader();
                while (reader.Read())
                {
                    filesToVerify.Add((reader.GetString(0), reader.GetString(1), reader.GetInt64(2)));
                }
            }

            if (filesToVerify.Count == 0)
            {
                return;
            }

            log.Debug("[Discovery] Verifying hashes for {Count} FLAC files", filesToVerify.Count);

            foreach (var (username, filename, size) in filesToVerify)
            {
                if (cancellationToken.IsCancellationRequested)
                {
                    break;
                }

                try
                {
                    var hash = await verificationService.GetContentHashAsync(username, filename, size, cancellationToken);

                    if (!string.IsNullOrEmpty(hash))
                    {
                        using var updateCmd = connection.CreateCommand();
                        updateCmd.CommandText = @"
                            UPDATE DiscoveredFiles
                            SET Hash = @hash
                            WHERE Username = @username AND Filename = @filename AND Size = @size";
                        updateCmd.Parameters.AddWithValue("@hash", hash);
                        updateCmd.Parameters.AddWithValue("@username", username);
                        updateCmd.Parameters.AddWithValue("@filename", filename);
                        updateCmd.Parameters.AddWithValue("@size", size);
                        updateCmd.ExecuteNonQuery();

                        log.Debug("[Discovery] Verified hash for {Filename} from {Username}: {Hash}",
                            filename, username, hash);
                    }
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    log.Warning("[Discovery] Failed to verify hash for {Filename} from {Username}: {Message}",
                        filename, username, ex.Message);
                }
            }
        }
    }
}
