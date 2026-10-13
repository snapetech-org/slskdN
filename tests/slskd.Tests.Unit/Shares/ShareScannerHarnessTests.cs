// <copyright file="ShareScannerHarnessTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Shares;

using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Moq;
using slskd.Files;
using slskd.Shares;
using Xunit;
using Xunit.Abstractions;

public class ShareScannerHarnessTests
{
    private readonly ITestOutputHelper output;

    public ShareScannerHarnessTests(ITestOutputHelper output)
    {
        this.output = output;
    }

    [Fact]
    public void SqliteRepository_StreamsOrderedShareRowsAndReleasesReadersWhenEnumerationStops()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"share-enumeration-{Guid.NewGuid():N}.db");

        try
        {
            using var repository = new SqliteShareRepository($"Data Source={databasePath};Pooling=False");
            repository.Create(discardExisting: true);
            repository.InsertDirectory("music\\Album", 1);
            repository.InsertDirectory("music\\Empty", 1);
            repository.InsertFile(
                "music\\Album\\track.mp3",
                "/tmp/track.mp3",
                DateTime.UtcNow,
                new Soulseek.File(1, "music\\Album\\track.mp3", 42, "mp3"),
                1);

            using (var directories = repository.EnumerateDirectories("music\\").GetEnumerator())
            {
                Assert.True(directories.MoveNext());
                Assert.Equal("music\\Album", directories.Current);
            }

            using (var files = repository.EnumerateFiles("music\\", includeFullPath: true).GetEnumerator())
            {
                Assert.True(files.MoveNext());
                Assert.Equal("music\\Album\\track.mp3", files.Current.Filename);
            }

            Assert.Equal(repository.ListDirectories("music\\"), repository.EnumerateDirectories("music\\"));
            Assert.Equal(
                repository.ListFiles("music\\", includeFullPath: true).Select(file => file.Filename),
                repository.EnumerateFiles("music\\", includeFullPath: true).Select(file => file.Filename));
        }
        finally
        {
            foreach (var filename in new[] { databasePath, $"{databasePath}-wal", $"{databasePath}-shm" })
            {
                if (File.Exists(filename))
                {
                    DeleteTestFileWithWindowsLockRetry(filename);
                }
            }
        }
    }

    [Fact]
    public async Task ScanAsync_WithLargeSyntheticTree_CompletesAndIndexesAllFilesWithoutHashing()
    {
        var shareRoot = Path.Combine(Path.GetTempPath(), $"share-scan-harness-{Guid.NewGuid():N}");
        var databasePath = Path.Combine(Path.GetTempPath(), $"share-scan-harness-{Guid.NewGuid():N}.db");
        var databaseCopyPath = $"{databasePath}.copy";
        var backupDatabasePath = $"{databasePath}.backup";
        var backupCopyPath = $"{backupDatabasePath}.copy";
        SqliteShareRepository? repository = null;
        SqliteShareRepository? backupRepository = null;

        try
        {
            var expectedFiles = await CreateSyntheticShareTreeAsync(shareRoot).ConfigureAwait(false);
            var scanner = new ShareScanner(
                workerCount: 1,
                fileService: CreateNoHashFileService(),
                moderationProvider: new slskd.Common.Moderation.NoopModerationProvider());

            repository = new SqliteShareRepository($"Data Source={databasePath};Pooling=False");
            repository.Create(discardExisting: true);

            var snapshots = new ConcurrentQueue<slskd.SharedFileCacheState>();
            using var registration = scanner.StateMonitor.OnChange(change => snapshots.Enqueue(change.Current));

            var stopwatch = Stopwatch.StartNew();
            await RunScanWithTimeoutAsync(
                scanner,
                shareRoot,
                repository,
                TimeSpan.FromSeconds(30),
                "Synthetic share-scan harness").ConfigureAwait(false);
            stopwatch.Stop();

            // A raw copy intentionally excludes the WAL sidecar. Its file rows must still reflect the completed scan.
            File.Copy(databasePath, databaseCopyPath);
            using (var copiedDatabase = new SqliteConnection($"Data Source={databaseCopyPath};Pooling=False"))
            {
                copiedDatabase.Open();
                using var command = copiedDatabase.CreateCommand();
                command.CommandText = "SELECT COUNT(*) FROM files;";
                Assert.Equal(expectedFiles, Convert.ToInt32(command.ExecuteScalar()));
            }

            backupRepository = new SqliteShareRepository($"Data Source={backupDatabasePath};Pooling=False");
            repository.BackupTo(backupRepository);
            File.Copy(backupDatabasePath, backupCopyPath);
            using (var copiedBackup = new SqliteConnection($"Data Source={backupCopyPath};Pooling=False"))
            {
                copiedBackup.Open();
                using var command = copiedBackup.CreateCommand();
                command.CommandText = "SELECT COUNT(*) FROM files;";
                Assert.Equal(expectedFiles, Convert.ToInt32(command.ExecuteScalar()));
            }

            var indexedFiles = repository.CountFiles();
            var finalSnapshot = snapshots.LastOrDefault();

            output.WriteLine($"Synthetic share-scan harness indexed {indexedFiles} files in {stopwatch.ElapsedMilliseconds}ms.");

            Assert.Equal(expectedFiles, indexedFiles);
            Assert.Contains(snapshots, snapshot => snapshot.Filling);
            Assert.NotNull(finalSnapshot);
            Assert.True(finalSnapshot!.Filled);
            Assert.False(finalSnapshot.Faulted);
            Assert.Equal(1d, finalSnapshot.FillProgress);
            Assert.Equal(expectedFiles, finalSnapshot.Files);
        }
        finally
        {
            backupRepository?.Dispose();
            repository?.Dispose();

            if (Directory.Exists(shareRoot))
            {
                Directory.Delete(shareRoot, recursive: true);
            }

            if (File.Exists(databasePath))
            {
                DeleteTestFileWithWindowsLockRetry(databasePath);
            }

            if (File.Exists(databaseCopyPath))
            {
                DeleteTestFileWithWindowsLockRetry(databaseCopyPath);
            }

            if (File.Exists(backupDatabasePath))
            {
                DeleteTestFileWithWindowsLockRetry(backupDatabasePath);
            }

            if (File.Exists(backupCopyPath))
            {
                DeleteTestFileWithWindowsLockRetry(backupCopyPath);
            }
        }
    }

    [Fact]
    public async Task ScanAsync_WhenCancelled_MarksThePartialScanAsSuspect()
    {
        var shareRoot = Path.Combine(Path.GetTempPath(), $"share-scan-cancel-{Guid.NewGuid():N}");
        var databasePath = Path.Combine(Path.GetTempPath(), $"share-scan-cancel-{Guid.NewGuid():N}.db");

        try
        {
            Directory.CreateDirectory(shareRoot);
            await File.WriteAllTextAsync(Path.Combine(shareRoot, "track.mp3"), "audio").ConfigureAwait(false);

            var scanner = new ShareScanner(
                workerCount: 1,
                fileService: CreateNoHashFileService(),
                moderationProvider: new slskd.Common.Moderation.NoopModerationProvider());

            using var repository = new SqliteShareRepository($"Data Source={databasePath};Pooling=False");
            repository.Create(discardExisting: true);

            var cancelRequested = 0;
            var observedCancelledState = false;
            using var registration = scanner.StateMonitor.OnChange(change =>
            {
                if (change.Current.Filling && Interlocked.Exchange(ref cancelRequested, 1) == 0)
                {
                    scanner.TryCancelScan();
                }

                observedCancelledState |= change.Current.Cancelled;
            });

            await scanner.ScanAsync(
                new[] { new Share(shareRoot) },
                new slskd.Options.SharesOptions(),
                repository).ConfigureAwait(false);

            var latestScan = repository.FindLatestScan();

            Assert.NotNull(latestScan);
            Assert.True(latestScan!.EndedAt.HasValue);
            Assert.True(latestScan.Suspect);
            Assert.True(observedCancelledState);
        }
        finally
        {
            if (Directory.Exists(shareRoot))
            {
                Directory.Delete(shareRoot, recursive: true);
            }

            if (File.Exists(databasePath))
            {
                DeleteTestFileWithWindowsLockRetry(databasePath);
            }
        }
    }

    [Fact]
    [Trait("Category", "Manual-ShareScan")]
    public async Task ScanAsync_WithManualShareRoot_IndexesAllFiles()
    {
        var shareRoot = Environment.GetEnvironmentVariable("SLSKDN_SHARE_SCAN_ROOT");
        if (string.IsNullOrWhiteSpace(shareRoot))
        {
            output.WriteLine("Set SLSKDN_SHARE_SCAN_ROOT to run the manual share-scan harness.");
            return;
        }

        Assert.True(Directory.Exists(shareRoot), $"Manual share root does not exist: {shareRoot}");

        var workerCount = int.TryParse(Environment.GetEnvironmentVariable("SLSKDN_SHARE_SCAN_WORKERS"), out var configuredWorkers) && configuredWorkers > 0
            ? configuredWorkers
            : 1;
        var timeoutSeconds = int.TryParse(Environment.GetEnvironmentVariable("SLSKDN_SHARE_SCAN_TIMEOUT_SECONDS"), out var configuredTimeoutSeconds) && configuredTimeoutSeconds > 0
            ? configuredTimeoutSeconds
            : 120;
        var skipMediaAttributes = string.Equals(Environment.GetEnvironmentVariable("SLSKDN_SHARE_SCAN_SKIP_MEDIA_ATTRIBUTES"), "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Environment.GetEnvironmentVariable("SLSKDN_SHARE_SCAN_SKIP_MEDIA_ATTRIBUTES"), "true", StringComparison.OrdinalIgnoreCase);
        var databasePath = Path.Combine(Path.GetTempPath(), $"share-scan-manual-{Guid.NewGuid():N}.db");

        try
        {
            var expectedFiles = CountVisibleFiles(shareRoot);
            var fileService = new FileService(new TestOptionsMonitor<slskd.Options>(new slskd.Options()));
            var scanner = new ShareScanner(
                workerCount: workerCount,
                fileService: fileService,
                moderationProvider: new slskd.Common.Moderation.NoopModerationProvider(),
                soulseekFileFactory: skipMediaAttributes ? new FastSoulseekFileFactory(fileService) : null);

            using var repository = new SqliteShareRepository($"Data Source={databasePath};Pooling=False");
            repository.Create(discardExisting: true);

            var snapshots = new ConcurrentQueue<slskd.SharedFileCacheState>();
            using var registration = scanner.StateMonitor.OnChange(change => snapshots.Enqueue(change.Current));

            output.WriteLine($"Manual share-scan harness root: {shareRoot}");
            output.WriteLine($"Expected visible files: {expectedFiles}");
            output.WriteLine($"Worker count: {workerCount}");
            output.WriteLine($"Skip media attributes: {skipMediaAttributes}");
            output.WriteLine($"Timeout seconds: {timeoutSeconds}");

            var stopwatch = Stopwatch.StartNew();
            await RunScanWithTimeoutAsync(
                scanner,
                shareRoot,
                repository,
                TimeSpan.FromSeconds(timeoutSeconds),
                "Manual share-scan harness").ConfigureAwait(false);
            stopwatch.Stop();

            var indexedFiles = repository.CountFiles();
            var finalSnapshot = snapshots.LastOrDefault();

            output.WriteLine($"Manual share-scan harness indexed {indexedFiles} files in {stopwatch.ElapsedMilliseconds}ms.");

            Assert.Equal(expectedFiles, indexedFiles);
            Assert.NotNull(finalSnapshot);
            Assert.True(finalSnapshot!.Filled);
            Assert.False(finalSnapshot.Faulted);
            Assert.Equal(expectedFiles, finalSnapshot.Files);
        }
        finally
        {
            if (File.Exists(databasePath))
            {
                DeleteTestFileWithWindowsLockRetry(databasePath);
            }
        }
    }

    private static FileService CreateNoHashFileService()
    {
        var fileService = new Mock<FileService>(new TestOptionsMonitor<slskd.Options>(new slskd.Options()))
        {
            CallBase = true,
        };

        fileService
            .Setup(service => service.ComputeHashAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Throws(new Xunit.Sdk.XunitException("ComputeHashAsync should not be called in the no-op moderation scan harness."));

        return fileService.Object;
    }

    private static async Task<int> CreateSyntheticShareTreeAsync(string root)
    {
        Directory.CreateDirectory(root);

        var expectedFiles = 0;

        for (var artistIndex = 0; artistIndex < 12; artistIndex++)
        {
            var artistDirectory = Path.Combine(root, $"artist-{artistIndex:00}");
            Directory.CreateDirectory(artistDirectory);

            for (var albumIndex = 0; albumIndex < 2; albumIndex++)
            {
                var albumDirectory = Path.Combine(artistDirectory, $"album-{albumIndex:00}");
                Directory.CreateDirectory(albumDirectory);

                for (var trackIndex = 0; trackIndex < 20; trackIndex++)
                {
                    var filename = Path.Combine(albumDirectory, $"track-{trackIndex:00}.txt");
                    var contents = new string((char)('a' + (trackIndex % 26)), 2048);
                    await File.WriteAllTextAsync(filename, contents).ConfigureAwait(false);
                    expectedFiles++;
                }
            }
        }

        return expectedFiles;
    }

    private static int CountVisibleFiles(string root)
    {
        return Directory.GetFiles(
            root,
            "*",
            new EnumerationOptions
            {
                AttributesToSkip = FileAttributes.Hidden | FileAttributes.System,
                IgnoreInaccessible = true,
                RecurseSubdirectories = true,
            }).Length;
    }

    private static async Task RunScanWithTimeoutAsync(
        ShareScanner scanner,
        string shareRoot,
        SqliteShareRepository repository,
        TimeSpan timeout,
        string operationName)
    {
        var scanTask = scanner.ScanAsync(
            new[] { new Share(shareRoot) },
            new slskd.Options.SharesOptions(),
            repository);

        var completedTask = await Task.WhenAny(scanTask, Task.Delay(timeout)).ConfigureAwait(false);
        if (completedTask != scanTask)
        {
            scanner.TryCancelScan();

            try
            {
                await scanTask.ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                // Cancellation is expected after the timeout; wait for the scanner to release its resources before cleanup.
            }

            var indexedFiles = repository.CountFiles();
            Assert.True(false, $"{operationName} did not finish within {timeout.TotalSeconds:N0}s. Indexed files before timeout: {indexedFiles}.");
        }

        await scanTask.ConfigureAwait(false);
    }

    private void DeleteTestFileWithWindowsLockRetry(string filename)
    {
        const int maximumAttempts = 6;

        for (var attempt = 0; ; attempt++)
        {
            try
            {
                File.Delete(filename);

                if (attempt > 0)
                {
                    output.WriteLine(
                        $"Deleted {Path.GetFileName(filename)} after {attempt} Windows sharing-lock retries.");
                }

                return;
            }
            catch (IOException exception) when (
                OperatingSystem.IsWindows()
                && attempt < maximumAttempts - 1
                && ((exception.HResult & 0xFFFF) is 32 or 33))
            {
                Thread.Sleep(TimeSpan.FromMilliseconds(50 * (1 << attempt)));
            }
        }
    }

    private sealed class FastSoulseekFileFactory : ISoulseekFileFactory
    {
        private readonly FileService fileService;

        public FastSoulseekFileFactory(FileService fileService)
        {
            this.fileService = fileService;
        }

        public Soulseek.File Create(string filename, string maskedFilename)
        {
            var info = fileService.ResolveFileInfo(filename);
            var extension = Path.GetExtension(filename).TrimStart('.').ToLowerInvariant();
            return new Soulseek.File(1, maskedFilename, info.Length, extension, null);
        }
    }
}
