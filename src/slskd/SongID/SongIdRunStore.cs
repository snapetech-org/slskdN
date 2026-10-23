// <copyright file="SongIdRunStore.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.SongID;

using System.Text.Json;
using Microsoft.Data.Sqlite;

public interface ISongIdRunStore
{
    SongIdRun Upsert(SongIdRun run);

    SongIdRun? Get(Guid id);

    IReadOnlyList<SongIdRun> List(int limit = 25);

    IReadOnlyList<SongIdRun> ListByStatuses(IReadOnlyCollection<string> statuses, int limit = 1000);
}

public sealed class SongIdRunStore : ISongIdRunStore
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = false,
    };

    private readonly string _connectionString;
    private readonly object _gate = new();

    public SongIdRunStore()
    {
        var databasePath = Path.Combine(Program.AppDirectory, "songid.db");
        _connectionString = $"Data Source={databasePath}";
        EnsureCreated();
    }

    public SongIdRun Upsert(SongIdRun run)
    {
        lock (_gate)
        {
            using var connection = OpenConnection();
            using var command = connection.CreateCommand();
            command.CommandText = """
                INSERT INTO songid_runs (id, created_at, completed_at, status, source_type, payload_json)
                VALUES (@id, @createdAt, @completedAt, @status, @sourceType, @payload)
                ON CONFLICT(id) DO UPDATE SET
                    completed_at = excluded.completed_at,
                    status = excluded.status,
                    source_type = excluded.source_type,
                    payload_json = excluded.payload_json
                """;
            command.Parameters.AddWithValue("@id", run.Id.ToString("D"));
            command.Parameters.AddWithValue("@createdAt", run.CreatedAt.UtcDateTime.ToString("O"));
            command.Parameters.AddWithValue("@completedAt", run.CompletedAt?.UtcDateTime.ToString("O") ?? (object)DBNull.Value);
            command.Parameters.AddWithValue("@status", run.Status);
            command.Parameters.AddWithValue("@sourceType", run.SourceType);
            command.Parameters.AddWithValue("@payload", JsonSerializer.Serialize(run, SerializerOptions));
            command.ExecuteNonQuery();
        }

        return run;
    }

    public SongIdRun? Get(Guid id)
    {
        lock (_gate)
        {
            using var connection = OpenConnection();
            using var command = connection.CreateCommand();
            command.CommandText = "SELECT payload_json FROM songid_runs WHERE id = @id LIMIT 1";
            command.Parameters.AddWithValue("@id", id.ToString("D"));
            using var reader = command.ExecuteReader();
            if (!reader.Read())
            {
                return null;
            }

            return Deserialize(reader.GetString(0));
        }
    }

    public IReadOnlyList<SongIdRun> List(int limit = 25)
    {
        var effectiveLimit = Math.Max(1, limit);
        var runs = new List<SongIdRun>();

        lock (_gate)
        {
            using var connection = OpenConnection();
            using var command = connection.CreateCommand();
            command.CommandText = """
                SELECT payload_json
                FROM songid_runs
                ORDER BY datetime(created_at) DESC
                LIMIT @limit
                """;
            command.Parameters.AddWithValue("@limit", effectiveLimit);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var run = Deserialize(reader.GetString(0));
                if (run != null)
                {
                    runs.Add(run);
                }
            }
        }

        return runs;
    }

    public IReadOnlyList<SongIdRun> ListByStatuses(IReadOnlyCollection<string> statuses, int limit = 1000)
    {
        if (statuses == null || statuses.Count == 0)
        {
            return Array.Empty<SongIdRun>();
        }

        var effectiveLimit = Math.Max(1, limit);
        var runs = new List<SongIdRun>();

        lock (_gate)
        {
            using var connection = OpenConnection();
            using var command = connection.CreateCommand();
            var parameterNames = statuses
                .Select((status, index) =>
                {
                    var parameterName = $"@status{index}";
                    command.Parameters.AddWithValue(parameterName, status);
                    return parameterName;
                })
                .ToArray();

            // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- only generated @statusN placeholders are interpolated; every status value and the limit are bound parameters.
            command.CommandText = $"""
                SELECT payload_json
                FROM songid_runs
                WHERE status IN ({string.Join(", ", parameterNames)})
                ORDER BY datetime(created_at) ASC
                LIMIT @limit
                """;
            command.Parameters.AddWithValue("@limit", effectiveLimit);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var run = Deserialize(reader.GetString(0));
                if (run != null)
                {
                    runs.Add(run);
                }
            }
        }

        return runs;
    }

    private static SongIdRun? Deserialize(string payload)
    {
        return JsonSerializer.Deserialize<SongIdRun>(payload, SerializerOptions);
    }

    private SqliteConnection OpenConnection()
    {
        var connection = new SqliteConnection(_connectionString);
        connection.Open();
        return connection;
    }

    private void EnsureCreated()
    {
        using var connection = OpenConnection();
        using var command = connection.CreateCommand();
        command.CommandText = """
            CREATE TABLE IF NOT EXISTS songid_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                completed_at TEXT NULL,
                status TEXT NOT NULL,
                source_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS ix_songid_runs_created_at ON songid_runs(created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_songid_runs_status ON songid_runs(status);
            """;
        command.ExecuteNonQuery();
    }
}
