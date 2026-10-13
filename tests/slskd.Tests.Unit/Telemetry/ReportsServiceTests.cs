// <copyright file="ReportsServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Telemetry;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using slskd;
using slskd.Telemetry;
using Xunit;

public sealed class ReportsServiceTests
{
    [Fact]
    public void GetTransferSummary_UsesBytesActuallyTransferredForEachState()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"reports-service-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath};Pooling=False";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = """
                    CREATE TABLE Transfers (
                        Direction TEXT NOT NULL,
                        StateDescription TEXT NOT NULL,
                        Size INTEGER NOT NULL,
                        BytesTransferred INTEGER NOT NULL,
                        Username TEXT NOT NULL,
                        AverageSpeed REAL NOT NULL,
                        EnqueuedAt TEXT NOT NULL,
                        StartedAt TEXT NOT NULL,
                        EndedAt TEXT NOT NULL
                    );
                    INSERT INTO Transfers VALUES
                        ('Upload', 'Completed, Errored', 1000, 250, 'alice', 125.0, '2026-10-01T00:00:00Z', '2026-10-01T00:00:01Z', '2026-10-01T00:00:03Z'),
                        ('Upload', 'Completed, Succeeded', 1000, 1000, 'bob', 500.0, '2026-10-01T00:00:00Z', '2026-10-01T00:00:01Z', '2026-10-01T00:00:03Z');
                    """;
                command.ExecuteNonQuery();
            }

            var service = new ReportsService(new ConnectionStringDictionary(new Dictionary<Database, ConnectionString>
            {
                [Database.Transfers] = connectionString,
            }));
            var summary = service.GetTransferSummary(
                start: new DateTime(2026, 10, 1, 0, 0, 0, DateTimeKind.Utc),
                end: new DateTime(2026, 10, 2, 0, 0, 0, DateTimeKind.Utc),
                direction: Soulseek.TransferDirection.Upload);

            Assert.Equal(250, summary[Soulseek.TransferDirection.Upload][Soulseek.TransferStates.Errored].TotalBytes);
            Assert.Equal(1000, summary[Soulseek.TransferDirection.Upload][Soulseek.TransferStates.Succeeded].TotalBytes);
        }
        finally
        {
            if (System.IO.File.Exists(databasePath))
            {
                System.IO.File.Delete(databasePath);
            }
        }
    }
}
