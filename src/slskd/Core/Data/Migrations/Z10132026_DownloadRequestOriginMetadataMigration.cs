// <copyright file="Z10132026_DownloadRequestOriginMetadataMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Linq;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Stores optional batch and search context with download requests for completed-path templates.
/// </summary>
public sealed class Z10132026_DownloadRequestOriginMetadataMigration : IMigration
{
    private static readonly (string Name, string SqlType)[] Columns =
    [
        ("BatchExternalId", "TEXT NULL"),
        ("SearchId", "TEXT NULL"),
        ("SearchText", "TEXT NULL"),
    ];

    public Z10132026_DownloadRequestOriginMetadataMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Transfers];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z10132026_DownloadRequestOriginMetadataMigration>();

    public bool NeedsToBeApplied()
    {
        var schema = SchemaInspector.GetDatabaseSchema(ConnectionString);
        if (!schema.TryGetValue("DownloadRequests", out var columns))
        {
            return true;
        }

        return Columns.Any(required => !columns.Any(column => column.Name.Equals(required.Name, StringComparison.OrdinalIgnoreCase)));
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z10132026_DownloadRequestOriginMetadataMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        var schema = SchemaInspector.GetDatabaseSchema(ConnectionString);
        if (!schema.TryGetValue("DownloadRequests", out var existingColumns))
        {
            throw new InvalidOperationException("DownloadRequests must exist before origin metadata can be added");
        }

        foreach (var column in Columns.Where(required => !existingColumns.Any(existing => existing.Name.Equals(required.Name, StringComparison.OrdinalIgnoreCase))))
        {
            using var command = new SqliteCommand($"ALTER TABLE DownloadRequests ADD COLUMN {column.Name} {column.SqlType}", connection);
            command.ExecuteNonQuery();
            Log.Information("> Added {Column} to DownloadRequests", column.Name);
        }
    }
}
