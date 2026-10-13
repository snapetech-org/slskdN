// <copyright file="SqliteTestDatabaseCleanup.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit;

using System.IO;
using Microsoft.Data.Sqlite;

internal static class SqliteTestDatabaseCleanup
{
    public static void ClearPool(string databasePath)
    {
        using var connection = new SqliteConnection($"Data Source={databasePath}");
        connection.Open();
        SqliteConnection.ClearPool(connection);
    }

    public static void ClearPoolForConnectionString(string connectionString)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();
        SqliteConnection.ClearPool(connection);
    }

    public static void ClearPools(string directory)
    {
        if (!Directory.Exists(directory))
        {
            return;
        }

        foreach (var databasePath in Directory.EnumerateFiles(directory, "*.db", SearchOption.AllDirectories))
        {
            ClearPool(databasePath);
        }
    }
}
