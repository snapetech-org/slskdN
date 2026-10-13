// <copyright file="UserDataServiceCollectionExtensionsTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Bootstrap;

using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using slskd.Bootstrap;
using slskd.Sharing;
using Xunit;

public sealed class UserDataServiceCollectionExtensionsTests : IDisposable
{
    private readonly string _tempDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-user-data-tests-{Guid.NewGuid():N}");

    public UserDataServiceCollectionExtensionsTests()
    {
        System.IO.Directory.CreateDirectory(_tempDirectory);
    }

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(_tempDirectory, "user_notes.db")}");
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(_tempDirectory, "collections.db")}");
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(_tempDirectory, "identity.db")}");
        if (System.IO.Directory.Exists(_tempDirectory))
        {
            System.IO.Directory.Delete(_tempDirectory, recursive: true);
        }
    }

    [Fact]
    public void AddSlskdUserData_UpgradesOnlyMissingSharingColumns()
    {
        var databasePath = Path.Combine(_tempDirectory, "collections.db");
        using (var context = CreateCollectionsContext(databasePath))
        {
            context.Database.EnsureCreated();
        }

        using (var connection = new SqliteConnection($"Data Source={databasePath}"))
        {
            connection.Open();
            using var command = connection.CreateCommand();
            command.CommandText =
                "ALTER TABLE ShareGrants DROP COLUMN OwnerEndpoint; " +
                "ALTER TABLE ShareGrants DROP COLUMN ShareToken; " +
                "ALTER TABLE CollectionItems DROP COLUMN FileName; " +
                "ALTER TABLE CollectionItems DROP COLUMN Title; " +
                "ALTER TABLE CollectionItems DROP COLUMN Artist; " +
                "ALTER TABLE CollectionItems DROP COLUMN Album;";
            command.ExecuteNonQuery();
        }

        UserDataServiceCollectionExtensions.AddSlskdUserData(new ServiceCollection(), _tempDirectory);

        Assert.Contains("OwnerEndpoint", GetColumnNames(databasePath, "ShareGrants"));
        Assert.Contains("ShareToken", GetColumnNames(databasePath, "ShareGrants"));
        var collectionItemColumns = GetColumnNames(databasePath, "CollectionItems");
        Assert.Contains("FileName", collectionItemColumns);
        Assert.Contains("Title", collectionItemColumns);
        Assert.Contains("Artist", collectionItemColumns);
        Assert.Contains("Album", collectionItemColumns);
    }

    [Fact]
    public void AddSlskdUserData_WhenExistingDatabaseHasMissingTable_ThrowsAtMigrationBoundary()
    {
        var databasePath = Path.Combine(_tempDirectory, "collections.db");
        using (var connection = new SqliteConnection($"Data Source={databasePath}"))
        {
            connection.Open();
            using var command = connection.CreateCommand();
            command.CommandText = "CREATE TABLE LegacyMarker (Id INTEGER PRIMARY KEY)";
            command.ExecuteNonQuery();
        }

        Assert.Throws<SqliteException>(() =>
            UserDataServiceCollectionExtensions.AddSlskdUserData(new ServiceCollection(), _tempDirectory));
    }

    private static CollectionsDbContext CreateCollectionsContext(string databasePath)
    {
        var options = new DbContextOptionsBuilder<CollectionsDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        return new CollectionsDbContext(options);
    }

    private static HashSet<string> GetColumnNames(string databasePath, string tableName)
    {
        using var connection = new SqliteConnection($"Data Source={databasePath}");
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = $"PRAGMA table_info(\"{tableName}\")";
        using var reader = command.ExecuteReader();
        var columns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        while (reader.Read())
        {
            columns.Add(reader.GetString(1));
        }

        return columns;
    }
}
