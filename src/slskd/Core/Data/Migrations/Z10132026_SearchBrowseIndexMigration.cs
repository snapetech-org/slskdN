// <copyright file="Z10132026_SearchBrowseIndexMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the ordered index used to continue search-history pages.
/// </summary>
public sealed class Z10132026_SearchBrowseIndexMigration : IMigration
{
    private const string IndexName = "IDX_Searches_StartedAt_Id";

    public Z10132026_SearchBrowseIndexMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Search];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z10132026_SearchBrowseIndexMigration>();

    public bool NeedsToBeApplied()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        if (!TableExists(connection))
        {
            return false;
        }

        return !HasDefinition(connection);
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z10132026_SearchBrowseIndexMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();

        try
        {
            using (var dropIndex = new SqliteCommand($"DROP INDEX IF EXISTS {IndexName}", connection, transaction))
            {
                dropIndex.ExecuteNonQuery();
            }

            using (var createIndex = new SqliteCommand(
                $"CREATE INDEX {IndexName} ON Searches (StartedAt DESC, Id DESC)",
                connection,
                transaction))
            {
                createIndex.ExecuteNonQuery();
            }

            transaction.Commit();
            Log.Information("> Added search-history browse index");
        }
        catch (Exception)
        {
            transaction.Rollback();
            throw;
        }
    }

    private static bool TableExists(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Searches')";
        return Convert.ToBoolean(command.ExecuteScalar());
    }

    private static bool HasDefinition(SqliteConnection connection)
    {
        using (var command = connection.CreateCommand())
        {
            command.CommandText = $"PRAGMA index_info('{IndexName}')";
            using var reader = command.ExecuteReader();
            var columns = new List<string>();
            while (reader.Read())
            {
                columns.Add(reader.GetString(reader.GetOrdinal("name")));
            }

            if (columns.Count != 2 ||
                !columns[0].Equals("StartedAt", StringComparison.OrdinalIgnoreCase) ||
                !columns[1].Equals("Id", StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
        }

        using var definitionCommand = connection.CreateCommand();
        definitionCommand.CommandText = "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = $name";
        definitionCommand.Parameters.AddWithValue("$name", IndexName);
        var definition = definitionCommand.ExecuteScalar() as string;
        return definition?.Contains("StartedAt DESC", StringComparison.OrdinalIgnoreCase) == true &&
            definition.Contains("Id DESC", StringComparison.OrdinalIgnoreCase);
    }
}
