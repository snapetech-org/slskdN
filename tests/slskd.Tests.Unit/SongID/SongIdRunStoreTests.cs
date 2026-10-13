// <copyright file="SongIdRunStoreTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
#nullable enable

namespace slskd.Tests.Unit.SongID;

using System.Reflection;
using slskd.SongID;
using slskd.Tests.Unit;
using Xunit;

[Collection("ProgramAppDirectory")]
public sealed class SongIdRunStoreTests : IDisposable
{
    private readonly string _tempDir;
    private readonly string? _originalAppDirectory;

    public SongIdRunStoreTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), "slskdn-songid-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempDir);

        _originalAppDirectory = Program.AppDirectory;
        SetAppDirectory(_tempDir);
    }

    [Fact]
    public void UpsertAndGet_RoundTripsRunPayload()
    {
        var store = new SongIdRunStore();
        var run = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "https://youtube.com/watch?v=test",
            SourceType = "youtube_url",
            Status = "running",
            Summary = "Running SongID analysis.",
            CurrentStage = "evidence_pipeline",
            PercentComplete = 0.52,
            QueuePosition = 4,
            WorkerSlot = 2,
            Query = "artist title",
            ArtifactDirectory = Path.Combine(_tempDir, "artifacts"),
            Evidence = new List<string> { "initial evidence" },
            ForensicMatrix = new SongIdForensicMatrix
            {
                IdentityScore = 82,
                SyntheticScore = 11,
                ConfidenceScore = 79,
                FamilyLabel = "none",
                QualityClass = "clean_excerpt",
                TopEvidenceFor = new List<string> { "recognizer agreement" },
                TopEvidenceAgainst = new List<string> { "short excerpt" },
                Notes = new List<string> { "identity beats synthetic" },
                LaneScores = new Dictionary<string, double>
                {
                    ["identity"] = 0.82,
                },
                ConfidenceLane = new SongIdForensicLane
                {
                    Label = "medium",
                    Score = 0.79,
                    Confidence = 79,
                    Summary = "stable enough for review",
                },
            },
        };

        store.Upsert(run);
        var stored = store.Get(run.Id);

        Assert.NotNull(stored);
        Assert.Equal(run.Id, stored!.Id);
        Assert.Equal(run.Source, stored.Source);
        Assert.Equal(run.Status, stored.Status);
        Assert.Equal(run.CurrentStage, stored.CurrentStage);
        Assert.Equal(run.PercentComplete, stored.PercentComplete);
        Assert.Equal(run.QueuePosition, stored.QueuePosition);
        Assert.Equal(run.WorkerSlot, stored.WorkerSlot);
        Assert.Equal(run.Query, stored.Query);
        Assert.Single(stored.Evidence);
        Assert.NotNull(stored.ForensicMatrix);
        Assert.Equal(82, stored.ForensicMatrix!.IdentityScore);
        Assert.Equal("clean_excerpt", stored.ForensicMatrix.QualityClass);
        Assert.Equal(0.79, stored.ForensicMatrix.ConfidenceLane.Score);
        Assert.Contains("identity", stored.ForensicMatrix.LaneScores.Keys);
    }

    [Fact]
    public void List_ReturnsNewestRunsFirst()
    {
        var store = new SongIdRunStore();
        var older = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "older",
            CreatedAt = DateTimeOffset.UtcNow.AddMinutes(-5),
        };
        var newer = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "newer",
            CreatedAt = DateTimeOffset.UtcNow,
        };

        store.Upsert(older);
        store.Upsert(newer);

        var listed = store.List(2);

        Assert.Equal(2, listed.Count);
        Assert.Equal(newer.Id, listed[0].Id);
        Assert.Equal(older.Id, listed[1].Id);
    }

    [Fact]
    public void ListByStatuses_FiltersAndReturnsOldestQueuedFirst()
    {
        var store = new SongIdRunStore();
        var queuedOlder = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "queued-older",
            Status = "queued",
            QueuePosition = 2,
            CreatedAt = DateTimeOffset.UtcNow.AddMinutes(-4),
        };
        var running = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "running",
            Status = "running",
            WorkerSlot = 1,
            CreatedAt = DateTimeOffset.UtcNow.AddMinutes(-3),
        };
        var queuedNewer = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "queued-newer",
            Status = "queued",
            QueuePosition = 1,
            CreatedAt = DateTimeOffset.UtcNow.AddMinutes(-2),
        };
        var completed = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "completed",
            Status = "completed",
            CreatedAt = DateTimeOffset.UtcNow.AddMinutes(-1),
        };

        store.Upsert(queuedOlder);
        store.Upsert(running);
        store.Upsert(queuedNewer);
        store.Upsert(completed);

        var active = store.ListByStatuses(new[] { "queued", "running" }, 10);

        Assert.Equal(3, active.Count);
        Assert.Equal(queuedOlder.Id, active[0].Id);
        Assert.Equal(running.Id, active[1].Id);
        Assert.Equal(queuedNewer.Id, active[2].Id);
        Assert.Equal(2, active[0].QueuePosition);
        Assert.Equal(1, active[1].WorkerSlot);
    }

    public void Dispose()
    {
        SetAppDirectory(_originalAppDirectory);
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(_tempDir, "songid.db")}");

        if (Directory.Exists(_tempDir))
        {
            Directory.Delete(_tempDir, true);
        }
    }

    private static void SetAppDirectory(string? value)
    {
        var property = typeof(Program).GetProperty(nameof(Program.AppDirectory), BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        Assert.NotNull(property);
        var setter = property!.GetSetMethod(nonPublic: true);
        Assert.NotNull(setter);
        setter!.Invoke(null, new object[] { value ?? string.Empty });
    }
}
