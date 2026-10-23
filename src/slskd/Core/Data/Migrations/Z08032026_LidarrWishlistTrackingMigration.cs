// <copyright file="Z08032026_LidarrWishlistTrackingMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the Lidarr album and track identifiers used to reconcile partial albums.
/// </summary>
public sealed class Z08032026_LidarrWishlistTrackingMigration
{
    public Z08032026_LidarrWishlistTrackingMigration(string connectionString)
    {
        ConnectionString = connectionString;
    }

    private string ConnectionString { get; }

    private ILogger Log { get; } = Serilog.Log.ForContext<Z08032026_LidarrWishlistTrackingMigration>();

    public void Apply()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        var columns = GetExistingColumns(connection);
        if (columns.Count == 0)
        {
            return;
        }

        using var transaction = connection.BeginTransaction();
        try
        {
            AddColumnIfMissing(connection, transaction, columns, "LidarrAlbumId");
            AddColumnIfMissing(connection, transaction, columns, "LidarrTrackId");
            transaction.Commit();
            Log.Information("> Lidarr Wishlist tracking columns are ready.");
        }
        catch
        {
            transaction.Rollback();
            throw;
        }
    }

    private static HashSet<string> GetExistingColumns(SqliteConnection connection)
    {
        var columns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using var table = connection.CreateCommand();
        table.CommandText = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'WishlistItems'";
        if (table.ExecuteScalar() is null)
        {
            return columns;
        }

        using var command = connection.CreateCommand();
        command.CommandText = "PRAGMA table_info(WishlistItems)";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            columns.Add(reader.GetString(1));
        }

        return columns;
    }

    private static void AddColumnIfMissing(
        SqliteConnection connection,
        SqliteTransaction transaction,
        ISet<string> columns,
        string columnName)
    {
        if (columns.Contains(columnName))
        {
            return;
        }

        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = columnName switch
        {
            "LidarrAlbumId" => "ALTER TABLE WishlistItems ADD COLUMN LidarrAlbumId INTEGER",
            "LidarrTrackId" => "ALTER TABLE WishlistItems ADD COLUMN LidarrTrackId INTEGER",
            _ => throw new ArgumentException("Unsupported WishlistItems column migration.", nameof(columnName)),
        };
        command.ExecuteNonQuery();
        columns.Add(columnName);
    }
}
