// <copyright file="HashDbOptimizationService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.HashDb.Optimization;

using System;
using System.Collections.Generic;
using System.Data;
using System.Diagnostics;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Logging;

/// <summary>
///     Service for HashDb database optimization and performance profiling.
/// </summary>
public interface IHashDbOptimizationService
{
    /// <summary>
    ///     Analyzes and optimizes database indexes.
    /// </summary>
    Task OptimizeIndexesAsync(CancellationToken cancellationToken = default);

    /// <summary>
    ///     Profiles query performance and identifies slow queries.
    /// </summary>
    Task<QueryProfileResult> ProfileQueryAsync(string query, Dictionary<string, object>? parameters = null, CancellationToken cancellationToken = default);

    /// <summary>
    ///     Analyzes database statistics and provides optimization recommendations.
    /// </summary>
    Task<OptimizationRecommendations> AnalyzeDatabaseAsync(CancellationToken cancellationToken = default);

    /// <summary>
    ///     Runs VACUUM and ANALYZE to optimize database.
    /// </summary>
    Task VacuumAndAnalyzeAsync(CancellationToken cancellationToken = default);

    /// <summary>
    ///     Records a query performance metric.
    /// </summary>
    void RecordQueryMetric(string query, long executionTimeMs, int rowsReturned);

    /// <summary>
    ///     Gets slow query statistics.
    /// </summary>
    Task<SlowQueryStats> GetSlowQueryStatsAsync(int limit = 20, CancellationToken cancellationToken = default);
}

/// <summary>
///     HashDb optimization service implementation.
/// </summary>
public class HashDbOptimizationService : IHashDbOptimizationService
{
    private static readonly string[] ForbiddenProfileQueryPrefixes =
    {
        "ALTER",
        "ANALYZE",
        "ATTACH",
        "CREATE",
        "DELETE",
        "DETACH",
        "DROP",
        "INSERT",
        "PRAGMA",
        "REINDEX",
        "REPLACE",
        "UPDATE",
        "VACUUM",
    };

    private readonly string _dbPath;
    private readonly ILogger<HashDbOptimizationService> _logger;
    private readonly object _metricsLock = new();
    private readonly List<QueryMetric> _queryMetrics = new();
    private const int MaxMetricsHistory = 1000; // Keep last 1000 query metrics

    /// <summary>
    ///     Initializes a new instance of the <see cref="HashDbOptimizationService"/> class.
    /// </summary>
    public HashDbOptimizationService(string dbPath, ILogger<HashDbOptimizationService> logger)
    {
        _dbPath = dbPath;
        _logger = logger;
    }

    /// <inheritdoc/>
    public async Task OptimizeIndexesAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("[HashDbOptimization] Starting index optimization");

            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            await conn.OpenAsync(cancellationToken).ConfigureAwait(false);

            // Check existing indexes
            var existingIndexes = await GetExistingIndexesAsync(conn, cancellationToken).ConfigureAwait(false);

            // Define recommended indexes
            var recommendedIndexes = new[]
            {
                // HashDb table indexes
                ("idx_hashdb_flac_key", "HashDb", "flac_key", "CREATE UNIQUE INDEX IF NOT EXISTS idx_hashdb_flac_key ON HashDb(flac_key)"),
                ("idx_hashdb_size", "HashDb", "size", "CREATE INDEX IF NOT EXISTS idx_hashdb_size ON HashDb(size)"),
                ("idx_hashdb_seq_id", "HashDb", "seq_id", "CREATE INDEX IF NOT EXISTS idx_hashdb_seq_id ON HashDb(seq_id)"),
                ("idx_hashdb_size_seq_id", "HashDb", "size, seq_id", "CREATE INDEX IF NOT EXISTS idx_hashdb_size_seq_id ON HashDb(size, seq_id DESC)"),

                // FlacInventory table indexes
                ("idx_inventory_file_id", "FlacInventory", "file_id", "CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_file_id ON FlacInventory(file_id)"),
                ("idx_inventory_size", "FlacInventory", "size", "CREATE INDEX IF NOT EXISTS idx_inventory_size ON FlacInventory(size)"),
                ("idx_inventory_discovered_at", "FlacInventory", "discovered_at", "CREATE INDEX IF NOT EXISTS idx_inventory_discovered_at ON FlacInventory(discovered_at DESC)"),
                ("idx_inventory_size_discovered", "FlacInventory", "size, discovered_at", "CREATE INDEX IF NOT EXISTS idx_inventory_size_discovered ON FlacInventory(size, discovered_at DESC)"),
                ("idx_inventory_hash_status_discovered", "FlacInventory", "hash_status, discovered_at", "CREATE INDEX IF NOT EXISTS idx_inventory_hash_status_discovered ON FlacInventory(hash_status, discovered_at DESC)"),
                ("idx_inventory_peer_id", "FlacInventory", "peer_id", "CREATE INDEX IF NOT EXISTS idx_inventory_peer_id ON FlacInventory(peer_id)"),

                // Peers table indexes
                ("idx_peers_peer_id", "Peers", "peer_id", "CREATE UNIQUE INDEX IF NOT EXISTS idx_peers_peer_id ON Peers(peer_id)"),
                ("idx_peers_caps", "Peers", "caps", "CREATE INDEX IF NOT EXISTS idx_peers_caps ON Peers(caps)"),
            };

            int created = 0;
            foreach (var (indexName, table, columns, createSql) in recommendedIndexes)
            {
                if (!existingIndexes.Contains(indexName))
                {
                    using var cmd = conn.CreateCommand();
                    cmd.CommandText = createSql;
                    await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
                    _logger.LogDebug("[HashDbOptimization] Created index {IndexName} on {Table}({Columns})", indexName, table, columns);
                    created++;
                }
            }

            _logger.LogInformation("[HashDbOptimization] Index optimization complete. Created {Count} new indexes", created);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[HashDbOptimization] Error optimizing indexes");
            throw;
        }
    }

    /// <inheritdoc/>
    public async Task<QueryProfileResult> ProfileQueryAsync(string query, Dictionary<string, object>? parameters = null, CancellationToken cancellationToken = default)
    {
        if (!TryNormalizeProfileQuery(query, out var normalizedQuery, out var validationError))
        {
            throw new ArgumentException(validationError, nameof(query));
        }

        try
        {
            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            await conn.OpenAsync(cancellationToken).ConfigureAwait(false);

            // Enable query plan
            using var enableCmd = conn.CreateCommand();
            enableCmd.CommandText = "EXPLAIN QUERY PLAN " + normalizedQuery;
            if (parameters != null)
            {
                foreach (var param in parameters)
                {
                    enableCmd.Parameters.AddWithValue($"@{param.Key}", param.Value);
                }
            }

            var planLines = new List<string>();
            await using var planReader = await enableCmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await planReader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                planLines.Add(planReader.GetString(3)); // detail column
            }

            // Measure execution time
            var stopwatch = Stopwatch.StartNew();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = normalizedQuery;
            if (parameters != null)
            {
                foreach (var param in parameters)
                {
                    cmd.Parameters.AddWithValue($"@{param.Key}", param.Value);
                }
            }

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            int rowCount = 0;
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                rowCount++;
            }

            stopwatch.Stop();

            return new QueryProfileResult
            {
                Query = normalizedQuery,
                ExecutionTimeMs = stopwatch.ElapsedMilliseconds,
                RowsReturned = rowCount,
                QueryPlan = string.Join("\n", planLines),
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[HashDbOptimization] Error profiling query");
            throw;
        }
    }

    internal static bool TryNormalizeProfileQuery(string query, out string normalizedQuery, out string error)
    {
        normalizedQuery = string.Empty;
        error = string.Empty;

        if (string.IsNullOrWhiteSpace(query))
        {
            error = "Query is required.";
            return false;
        }

        normalizedQuery = Regex.Replace(query.Trim(), @"\s+", " ");
        var upperQuery = normalizedQuery.ToUpperInvariant();

        if (normalizedQuery.Length > 2000)
        {
            error = "Query is too long.";
            return false;
        }

        if (normalizedQuery.Contains(';'))
        {
            error = "Only single-statement SELECT queries are allowed.";
            return false;
        }

        if (!(upperQuery.StartsWith("SELECT ", StringComparison.Ordinal) || upperQuery.StartsWith("WITH ", StringComparison.Ordinal)))
        {
            error = "Only read-only SELECT queries are allowed.";
            return false;
        }

        if (ForbiddenProfileQueryPrefixes.Any(prefix => upperQuery.StartsWith(prefix + " ", StringComparison.Ordinal)))
        {
            error = "Mutating or administrative SQL statements are not allowed.";
            return false;
        }

        return true;
    }

    /// <inheritdoc/>
    public async Task<OptimizationRecommendations> AnalyzeDatabaseAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            await conn.OpenAsync(cancellationToken).ConfigureAwait(false);

            var recommendations = new OptimizationRecommendations();

            // Analyze table sizes
            using var sizeCmd = conn.CreateCommand();
            sizeCmd.CommandText = @"
                SELECT 
                    name,
                    (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as table_exists
                FROM sqlite_master m
                WHERE type='table' AND name IN ('HashDb', 'FlacInventory', 'Peers')";

            var tableStats = new Dictionary<string, long>();
            var knownTables = new HashSet<string>(StringComparer.Ordinal)
            {
                "HashDb",
                "FlacInventory",
                "Peers",
            };

            await using var sizeReader = await sizeCmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await sizeReader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var tableName = sizeReader.GetString(0);
                if (!knownTables.Contains(tableName))
                {
                    continue;
                }

                using var countCmd = conn.CreateCommand();
                countCmd.CommandText = $"SELECT COUNT(*) FROM \"{tableName}\""; // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- tableName is checked against a fixed allowlist and quoted as a SQLite identifier.
                var count = (long)(await countCmd.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false) ?? 0L);
                tableStats[tableName] = count;
            }

            recommendations.HashDbEntryCount = tableStats.GetValueOrDefault("HashDb", 0);
            recommendations.FlacInventoryEntryCount = tableStats.GetValueOrDefault("FlacInventory", 0);
            recommendations.PeerCount = tableStats.GetValueOrDefault("Peers", 0);

            // Check for missing indexes
            var existingIndexes = await GetExistingIndexesAsync(conn, cancellationToken).ConfigureAwait(false);
            var criticalIndexes = new[]
            {
                "idx_hashdb_flac_key",
                "idx_hashdb_size",
                "idx_inventory_file_id",
                "idx_inventory_size",
                "idx_peers_caps",
            };

            foreach (var indexName in criticalIndexes)
            {
                if (!existingIndexes.Contains(indexName))
                {
                    recommendations.MissingIndexes.Add(indexName);
                }
            }

            // Analyze database file size
            if (System.IO.File.Exists(_dbPath))
            {
                var fileInfo = new System.IO.FileInfo(_dbPath);
                recommendations.DatabaseSizeBytes = fileInfo.Length;
            }

            // Generate recommendations
            if (recommendations.HashDbEntryCount > 100000)
            {
                recommendations.Recommendations.Add("Large HashDb table detected. Consider running VACUUM to reclaim space.");
            }

            if (recommendations.MissingIndexes.Count > 0)
            {
                recommendations.Recommendations.Add($"Missing {recommendations.MissingIndexes.Count} critical indexes. Run OptimizeIndexesAsync to create them.");
            }

            // > 100 MB.
            if (recommendations.DatabaseSizeBytes > 100 * 1024 * 1024)
            {
                recommendations.Recommendations.Add("Database size exceeds 100MB. Consider running VACUUM to optimize.");
            }

            return recommendations;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[HashDbOptimization] Error analyzing database");
            throw;
        }
    }

    /// <inheritdoc/>
    public async Task VacuumAndAnalyzeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("[HashDbOptimization] Starting VACUUM and ANALYZE");

            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            await conn.OpenAsync(cancellationToken).ConfigureAwait(false);

            // Run VACUUM to reclaim space
            using var vacuumCmd = conn.CreateCommand();
            vacuumCmd.CommandText = "VACUUM";
            await vacuumCmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            _logger.LogInformation("[HashDbOptimization] VACUUM completed");

            // Run ANALYZE to update statistics
            using var analyzeCmd = conn.CreateCommand();
            analyzeCmd.CommandText = "ANALYZE";
            await analyzeCmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            _logger.LogInformation("[HashDbOptimization] ANALYZE completed");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[HashDbOptimization] Error running VACUUM/ANALYZE");
            throw;
        }
    }

    /// <inheritdoc/>
    public void RecordQueryMetric(string query, long executionTimeMs, int rowsReturned)
    {
        lock (_metricsLock)
        {
            // Normalize query for grouping (remove parameter values)
            var normalizedQuery = NormalizeQuery(query);

            _queryMetrics.Add(new QueryMetric
            {
                Query = normalizedQuery,
                OriginalQuery = query,
                ExecutionTimeMs = executionTimeMs,
                RowsReturned = rowsReturned,
                Timestamp = DateTimeOffset.UtcNow,
            });

            // Keep only last N metrics
            if (_queryMetrics.Count > MaxMetricsHistory)
            {
                _queryMetrics.RemoveRange(0, _queryMetrics.Count - MaxMetricsHistory);
            }
        }
    }

    /// <inheritdoc/>
    public Task<SlowQueryStats> GetSlowQueryStatsAsync(int limit = 20, CancellationToken cancellationToken = default)
    {
        lock (_metricsLock)
        {
            var stats = new SlowQueryStats
            {
                TotalQueries = _queryMetrics.Count,
                SlowQueries = new List<SlowQueryInfo>(),
            };

            // Group by normalized query and calculate statistics
            var queryGroups = _queryMetrics
                .GroupBy(m => m.Query)
                .Select(g => new
                {
                    Query = g.Key,
                    Count = g.Count(),
                    AvgTimeMs = g.Average(m => m.ExecutionTimeMs),
                    MaxTimeMs = g.Max(m => m.ExecutionTimeMs),
                    MinTimeMs = g.Min(m => m.ExecutionTimeMs),
                    TotalRows = g.Sum(m => m.RowsReturned),
                    LastExecuted = g.Max(m => m.Timestamp),
                })
                .OrderByDescending(x => x.AvgTimeMs)
                .Take(limit)
                .ToList();

            foreach (var group in queryGroups)
            {
                stats.SlowQueries.Add(new SlowQueryInfo
                {
                    Query = group.Query,
                    ExecutionCount = group.Count,
                    AverageTimeMs = (long)group.AvgTimeMs,
                    MaxTimeMs = group.MaxTimeMs,
                    MinTimeMs = group.MinTimeMs,
                    TotalRowsReturned = group.TotalRows,
                    LastExecuted = group.LastExecuted,
                });
            }

            return Task.FromResult(stats);
        }
    }

    private string NormalizeQuery(string query)
    {
        // Simple normalization: replace parameter placeholders with @param
        // This groups similar queries together
        var normalized = System.Text.RegularExpressions.Regex.Replace(
            query,
            @"@\w+",
            "@param",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase);

        // Remove extra whitespace
        normalized = System.Text.RegularExpressions.Regex.Replace(
            normalized,
            @"\s+",
            " ",
            System.Text.RegularExpressions.RegexOptions.Multiline);

        return normalized.Trim();
    }

    private async Task<HashSet<string>> GetExistingIndexesAsync(SqliteConnection conn, CancellationToken cancellationToken)
    {
        var indexes = new HashSet<string>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'";

        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            indexes.Add(reader.GetString(0));
        }

        return indexes;
    }
}

/// <summary>
///     Query performance metric.
/// </summary>
internal class QueryMetric
{
    public string Query { get; set; } = string.Empty;
    public string OriginalQuery { get; set; } = string.Empty;
    public long ExecutionTimeMs { get; set; }
    public int RowsReturned { get; set; }
    public DateTimeOffset Timestamp { get; set; }
}

/// <summary>
///     Slow query statistics.
/// </summary>
public class SlowQueryStats
{
    /// <summary>
    ///     Total number of queries recorded.
    /// </summary>
    public int TotalQueries { get; set; }

    /// <summary>
    ///     List of slow queries with statistics.
    /// </summary>
    public List<SlowQueryInfo> SlowQueries { get; set; } = new();
}

/// <summary>
///     Information about a slow query.
/// </summary>
public class SlowQueryInfo
{
    /// <summary>
    ///     Normalized query text.
    /// </summary>
    public string Query { get; set; } = string.Empty;

    /// <summary>
    ///     Number of times this query was executed.
    /// </summary>
    public int ExecutionCount { get; set; }

    /// <summary>
    ///     Average execution time in milliseconds.
    /// </summary>
    public long AverageTimeMs { get; set; }

    /// <summary>
    ///     Maximum execution time in milliseconds.
    /// </summary>
    public long MaxTimeMs { get; set; }

    /// <summary>
    ///     Minimum execution time in milliseconds.
    /// </summary>
    public long MinTimeMs { get; set; }

    /// <summary>
    ///     Total rows returned across all executions.
    /// </summary>
    public long TotalRowsReturned { get; set; }

    /// <summary>
    ///     When this query was last executed.
    /// </summary>
    public DateTimeOffset LastExecuted { get; set; }
}

/// <summary>
///     Query profiling result.
/// </summary>
public class QueryProfileResult
{
    /// <summary>
    ///     The SQL query that was profiled.
    /// </summary>
    public string Query { get; set; } = string.Empty;

    /// <summary>
    ///     Execution time in milliseconds.
    /// </summary>
    public long ExecutionTimeMs { get; set; }

    /// <summary>
    ///     Number of rows returned.
    /// </summary>
    public int RowsReturned { get; set; }

    /// <summary>
    ///     Query execution plan.
    /// </summary>
    public string QueryPlan { get; set; } = string.Empty;
}

/// <summary>
///     Database optimization recommendations.
/// </summary>
public class OptimizationRecommendations
{
    /// <summary>
    ///     Number of entries in HashDb table.
    /// </summary>
    public long HashDbEntryCount { get; set; }

    /// <summary>
    ///     Number of entries in FlacInventory table.
    /// </summary>
    public long FlacInventoryEntryCount { get; set; }

    /// <summary>
    ///     Number of entries in Peers table.
    /// </summary>
    public long PeerCount { get; set; }

    /// <summary>
    ///     Database file size in bytes.
    /// </summary>
    public long DatabaseSizeBytes { get; set; }

    /// <summary>
    ///     List of missing critical indexes.
    /// </summary>
    public List<string> MissingIndexes { get; set; } = new();

    /// <summary>
    ///     Optimization recommendations.
    /// </summary>
    public List<string> Recommendations { get; set; } = new();
}
