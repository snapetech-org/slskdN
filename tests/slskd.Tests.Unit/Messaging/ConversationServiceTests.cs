// <copyright file="ConversationServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Tests.Unit.Messaging;

using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Moq;
using slskd.Events;
using slskd.Messaging;
using slskd.Migrations;
using slskd.PodCore;
using Soulseek;
using Xunit;

public class ConversationServiceTests
{
    [Fact]
    public void TimelineIndexMigration_Adds_Ordered_Index_And_Is_Idempotent()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-messaging-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = """
                    CREATE TABLE PrivateMessages (
                        Username TEXT NOT NULL,
                        Id INTEGER NOT NULL,
                        Timestamp TEXT NOT NULL,
                        PRIMARY KEY (Username, Id, Timestamp)
                    );
                    """;
                command.ExecuteNonQuery();
            }

            var connectionStrings = new ConnectionStringDictionary(new()
            {
                [Database.Messaging] = connectionString,
            });
            var migration = new Z07152026_PrivateMessageTimelineIndexMigration(connectionStrings);

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = "PRAGMA index_info('IDX_PrivateMessages_Username_Timestamp')";
                using var reader = command.ExecuteReader();
                var columns = new List<string>();
                while (reader.Read())
                {
                    columns.Add(reader.GetString(reader.GetOrdinal("name")));
                }

                Assert.Equal(["Username", "Timestamp"], columns);
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public void AcknowledgementIndexMigration_Upgrades_Single_Column_Index_And_Is_Idempotent()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-messaging-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = """
                    CREATE TABLE PrivateMessages (
                        Username TEXT NOT NULL,
                        Id INTEGER NOT NULL,
                        Timestamp TEXT NOT NULL,
                        IsAcknowledged INTEGER NOT NULL,
                        PRIMARY KEY (Username, Id, Timestamp)
                    );
                    CREATE INDEX IDX_PrivateMessages_IsAcknowledged
                        ON PrivateMessages (IsAcknowledged);
                    """;
                command.ExecuteNonQuery();
            }

            var connectionStrings = new ConnectionStringDictionary(new()
            {
                [Database.Messaging] = connectionString,
            });
            var migration = new Z07152026_PrivateMessageAcknowledgementIndexMigration(connectionStrings);

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = "PRAGMA index_info('IDX_PrivateMessages_IsAcknowledged')";
                using var reader = command.ExecuteReader();
                var columns = new List<string>();
                while (reader.Read())
                {
                    columns.Add(reader.GetString(reader.GetOrdinal("name")));
                }

                Assert.Equal(["IsAcknowledged", "Username"], columns);
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public async Task ListAsync_Projects_Unacknowledged_Counts_Without_Message_Payloads()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var options = new DbContextOptionsBuilder<MessagingDbContext>()
            .UseSqlite(connection)
            .Options;
        var factory = new TestDbContextFactory(options);

        await using (var context = factory.CreateDbContext())
        {
            await context.Database.EnsureCreatedAsync();
            context.Conversations.AddRange(
                new Conversation { Username = "active-unread", IsActive = true },
                new Conversation { Username = "active-read", IsActive = true },
                new Conversation { Username = "inactive-unread", IsActive = false });
            context.PrivateMessages.AddRange(
                new PrivateMessage { Id = 1, Username = "active-unread", IsAcknowledged = false, Message = new string('x', 4_096) },
                new PrivateMessage { Id = 2, Username = "active-unread", IsAcknowledged = false, Message = new string('y', 4_096) },
                new PrivateMessage { Id = 3, Username = "active-read", IsAcknowledged = true, Message = new string('z', 4_096) },
                new PrivateMessage { Id = 4, Username = "inactive-unread", IsAcknowledged = false, Message = new string('q', 4_096) });
            await context.SaveChangesAsync();
        }

        var service = CreateService(factory);

        var conversations = (await service.ListAsync(conversation => conversation.IsActive)).ToList();

        Assert.Collection(
            conversations,
            conversation =>
            {
                Assert.Equal("active-read", conversation.Username);
                Assert.Equal(0, conversation.UnAcknowledgedMessageCount);
                Assert.Empty(conversation.Messages);
            },
            conversation =>
            {
                Assert.Equal("active-unread", conversation.Username);
                Assert.Equal(2, conversation.UnAcknowledgedMessageCount);
                Assert.Empty(conversation.Messages);
            });
    }

    [Fact]
    public async Task HasUnAcknowledgedMessagesAsync_Returns_Existence_Without_Loading_Conversations()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var options = new DbContextOptionsBuilder<MessagingDbContext>()
            .UseSqlite(connection)
            .Options;
        var factory = new TestDbContextFactory(options);

        await using (var context = factory.CreateDbContext())
        {
            await context.Database.EnsureCreatedAsync();
            context.PrivateMessages.AddRange(
                new PrivateMessage
                {
                    Id = 1,
                    Username = "acknowledged",
                    IsAcknowledged = true,
                },
                new PrivateMessage
                {
                    Id = 2,
                    Username = "unacknowledged",
                    IsAcknowledged = false,
                });
            await context.SaveChangesAsync();
        }

        var service = CreateService(factory);

        Assert.True(await service.HasUnAcknowledgedMessagesAsync());

        await using (var context = factory.CreateDbContext())
        {
            await context.PrivateMessages.ExecuteUpdateAsync(update => update.SetProperty(message => message.IsAcknowledged, true));
        }

        Assert.False(await service.HasUnAcknowledgedMessagesAsync());
    }

    [Fact]
    public async Task FindAsync_Counts_All_Unacknowledged_Messages_While_Bounding_Message_Window()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var options = new DbContextOptionsBuilder<MessagingDbContext>()
            .UseSqlite(connection)
            .Options;
        var factory = new TestDbContextFactory(options);

        await using (var context = factory.CreateDbContext())
        {
            await context.Database.EnsureCreatedAsync();
            context.Conversations.Add(new Conversation { Username = "listener", IsActive = true });
            context.PrivateMessages.AddRange(
                Enumerable.Range(1, 150).Select(index => new PrivateMessage
                {
                    Id = index,
                    IsAcknowledged = false,
                    Message = $"message-{index}",
                    Timestamp = new DateTime(2026, 7, 15, 0, 0, 0, DateTimeKind.Utc).AddSeconds(index),
                    Username = "listener",
                }));
            await context.SaveChangesAsync();
        }

        var service = CreateService(factory);

        var conversation = await service.FindAsync("listener", includeMessages: true);

        Assert.NotNull(conversation);
        Assert.Equal(150, conversation.UnAcknowledgedMessageCount);
        Assert.Equal(100, conversation.Messages.Count());
        Assert.Equal("message-51", conversation.Messages.First().Message);
        Assert.Equal("message-150", conversation.Messages.Last().Message);
    }

    [Fact]
    public async Task MessagingSchema_Uses_Covering_Acknowledgement_Index_For_Conversation_Counts()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var options = new DbContextOptionsBuilder<MessagingDbContext>()
            .UseSqlite(connection)
            .Options;
        await using var context = new MessagingDbContext(options);
        await context.Database.EnsureCreatedAsync();

        await using var command = connection.CreateCommand();
        command.CommandText = """
            EXPLAIN QUERY PLAN
            SELECT c.Username,
                (SELECT COUNT(*)
                 FROM PrivateMessages AS p
                 WHERE p.IsAcknowledged = 0 AND p.Username = c.Username)
            FROM Conversations AS c
            WHERE c.IsActive = 1
            ORDER BY c.Username
            """;
        await using var reader = await command.ExecuteReaderAsync();

        var details = new List<string>();
        while (await reader.ReadAsync())
        {
            details.Add(reader.GetString(3));
        }

        Assert.Contains(details, detail =>
            detail.Contains("COVERING INDEX IDX_PrivateMessages_IsAcknowledged", StringComparison.Ordinal));
    }

    [Fact]
    public async Task MessagingSchema_Uses_Timeline_Index_For_Incremental_Message_Window()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var options = new DbContextOptionsBuilder<MessagingDbContext>()
            .UseSqlite(connection)
            .Options;
        await using var context = new MessagingDbContext(options);
        await context.Database.EnsureCreatedAsync();

        await using var command = connection.CreateCommand();
        command.CommandText = """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM PrivateMessages
            WHERE Username = 'listener' AND Timestamp > '2026-07-15 12:00:00'
            ORDER BY Timestamp DESC
            LIMIT 100
            """;
        await using var reader = await command.ExecuteReaderAsync();

        var details = new List<string>();
        while (await reader.ReadAsync())
        {
            details.Add(reader.GetString(3));
        }

        Assert.Contains(details, detail =>
            detail.Contains("INDEX IDX_PrivateMessages_Username_Timestamp", StringComparison.Ordinal));
        Assert.DoesNotContain(details, detail =>
            detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    private static ConversationService CreateService(IDbContextFactory<MessagingDbContext> contextFactory)
    {
        return new ConversationService(
            Mock.Of<ISoulseekClient>(),
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())),
            contextFactory,
            Mock.Of<IPodService>());
    }

    private sealed class TestDbContextFactory : IDbContextFactory<MessagingDbContext>
    {
        public TestDbContextFactory(DbContextOptions<MessagingDbContext> options)
        {
            Options = options;
        }

        private DbContextOptions<MessagingDbContext> Options { get; }

        public MessagingDbContext CreateDbContext()
        {
            return new MessagingDbContext(Options);
        }
    }
}
