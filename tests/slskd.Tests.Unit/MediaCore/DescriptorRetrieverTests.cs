// <copyright file="DescriptorRetrieverTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.MediaCore;

using System.Collections.Concurrent;
using System.Reflection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using slskd.MediaCore;
using slskd.Mesh.Dht;
using Xunit;

public class DescriptorRetrieverTests
{
    [Fact]
    public async Task QueryByDomainAsync_WithMbDomainAndNoType_DoesNotThrow()
    {
        var retriever = CreateRetriever();

        var result = await retriever.QueryByDomainAsync("mb");

        Assert.NotNull(result);
        Assert.Empty(result.Descriptors);
        Assert.Equal("audio", result.Domain);
        Assert.Null(result.Type);
    }

    [Fact]
    public async Task QueryByDomainAsync_WithWhitespaceType_TreatsTypeAsMissing()
    {
        var retriever = CreateRetriever();

        var result = await retriever.QueryByDomainAsync("audio", "   ");

        Assert.NotNull(result);
        Assert.Empty(result.Descriptors);
        Assert.Equal("audio", result.Domain);
        Assert.Null(result.Type);
    }

    [Fact]
    public async Task RetrieveBatchAsync_TrimsAndDeduplicatesContentIds()
    {
        var dht = new Mock<IMeshDhtClient>();
        var retriever = CreateRetriever(dht.Object);

        await retriever.RetrieveBatchAsync(new[] { " content:mb:recording:1 ", "content:mb:recording:1", "", "   " });

        dht.Verify(client => client.GetAsync<ContentDescriptor>("mesh:content:content:mb:recording:1", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task RetrieveBatchAsync_LargeBatchAvoidsPerItemWaitingTasks()
    {
        const int contentIdCount = 10_000;
        var dht = new Mock<IMeshDhtClient>();
        dht.Setup(client => client.GetAsync<ContentDescriptor>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((ContentDescriptor?)null);
        var retriever = CreateRetriever(dht.Object);
        var contentIds = Enumerable.Range(0, contentIdCount)
            .Select(index => $"content:audio:track:{index}")
            .ToArray();
        _ = await retriever.RetrieveBatchAsync(contentIds.AsSpan(0, 1).ToArray());

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var result = await retriever.RetrieveBatchAsync(contentIds);
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(contentIdCount, result.Requested);
        Assert.Equal(contentIdCount, result.Results.Count);
        Assert.Equal(0, result.Found);
        Assert.Equal(0, result.Failed);
        Assert.True(
            allocatedBytes < 12 * 1024 * 1024,
            $"Expected fixed-worker batch retrieval below 12 MiB allocated, got {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task RetrieveBatchAsync_UsesExactlyBoundedWorkerConcurrency()
    {
        var active = 0;
        var maximumActive = 0;
        var dht = new Mock<IMeshDhtClient>();
        dht.Setup(client => client.GetAsync<ContentDescriptor>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(async () =>
            {
                var currentActive = Interlocked.Increment(ref active);
                var observedMaximum = Volatile.Read(ref maximumActive);
                while (currentActive > observedMaximum)
                {
                    var priorMaximum = Interlocked.CompareExchange(
                        ref maximumActive,
                        currentActive,
                        observedMaximum);
                    if (priorMaximum == observedMaximum)
                    {
                        break;
                    }

                    observedMaximum = priorMaximum;
                }

                await Task.Delay(5);
                Interlocked.Decrement(ref active);
                return null;
            });
        var retriever = CreateRetriever(dht.Object);
        var contentIds = Enumerable.Range(0, 100)
            .Select(index => $"content:audio:track:{index}")
            .ToArray();

        var result = await retriever.RetrieveBatchAsync(contentIds);

        Assert.Equal(100, result.Results.Count);
        Assert.Equal(10, maximumActive);
        Assert.Equal(0, active);
    }

    [Fact]
    public async Task RetrieveAsync_TrimsContentIdBeforeLookup()
    {
        var dht = new Mock<IMeshDhtClient>();
        var retriever = CreateRetriever(dht.Object);

        await retriever.RetrieveAsync(" content:mb:recording:2 ");

        dht.Verify(client => client.GetAsync<ContentDescriptor>("mesh:content:content:mb:recording:2", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task RetrieveAsync_WhenDhtLookupThrows_ReturnsSanitizedErrorMessage()
    {
        var dht = new Mock<IMeshDhtClient>();
        dht.Setup(client => client.GetAsync<ContentDescriptor>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive DHT detail"));

        var retriever = CreateRetriever(dht.Object);

        var result = await retriever.RetrieveAsync("content:mb:recording:3");

        Assert.False(result.Found);
        Assert.Equal("Failed to retrieve descriptor from DHT", result.ErrorMessage);
        Assert.DoesNotContain("sensitive", result.ErrorMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task RetrieveAsync_WhenDhtLookupIsCanceled_PropagatesCallerCancellation()
    {
        using var cancellation = new CancellationTokenSource();
        var dht = new Mock<IMeshDhtClient>();
        dht
            .Setup(client => client.GetAsync<ContentDescriptor>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns((string _, CancellationToken _) =>
            {
                cancellation.Cancel();
                return Task.FromCanceled<ContentDescriptor?>(cancellation.Token);
            });
        var retriever = CreateRetriever(dht.Object);

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            retriever.RetrieveAsync("content:mb:recording:canceled", cancellationToken: cancellation.Token));
    }

    [Fact]
    public async Task RetrieveBatchAsync_WhenCanceled_RetainsCompletedResultsWithoutReportingLookupFailure()
    {
        using var cancellation = new CancellationTokenSource();
        var dht = new Mock<IMeshDhtClient>();
        dht
            .Setup(client => client.GetAsync<ContentDescriptor>(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns((string _, CancellationToken _) =>
            {
                cancellation.Cancel();
                return Task.FromResult<ContentDescriptor?>(null);
            });
        var retriever = CreateRetriever(dht.Object);

        var result = await retriever.RetrieveBatchAsync(
            new[] { "content:mb:recording:completed" },
            cancellation.Token);

        Assert.Equal(1, result.Requested);
        Assert.Equal(1, result.Results.Count);
        Assert.Equal(0, result.Failed);
    }

    [Fact]
    public async Task VerifyAsync_WhenCallerIsCanceled_PropagatesCancellation()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var retriever = CreateRetriever();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            retriever.VerifyAsync(
                new ContentDescriptor { ContentId = "content:a" },
                DateTimeOffset.UtcNow,
                cancellation.Token));
    }

    [Fact]
    public async Task VerifyAsync_WhenValidatorThrows_ReturnsSanitizedValidationError()
    {
        var validator = new Mock<IDescriptorValidator>();
        validator.Setup(v => v.Validate(It.IsAny<ContentDescriptor>(), out It.Ref<string?>.IsAny!))
            .Throws(new InvalidOperationException("sensitive validation detail"));

        var retriever = new DescriptorRetriever(
            NullLogger<DescriptorRetriever>.Instance,
            Mock.Of<IMeshDhtClient>(),
            validator.Object,
            Options.Create(new MediaCoreOptions()));

        var result = await retriever.VerifyAsync(new ContentDescriptor { ContentId = "content:a" }, DateTimeOffset.UtcNow);

        Assert.False(result.IsValid);
        Assert.Equal("Descriptor verification failed", result.ValidationError);
        Assert.DoesNotContain("sensitive", result.ValidationError, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task GetStatsAsync_LargeMixedCacheAvoidsSnapshotsAndCleanupKeyBuffer()
    {
        const int entryCount = 10_000;
        var retriever = CreateRetriever();
        var cacheField = typeof(DescriptorRetriever).GetField(
            "_cache",
            BindingFlags.Instance | BindingFlags.NonPublic)!;
        var cache = (ConcurrentDictionary<string, CachedDescriptor>)cacheField.GetValue(retriever)!;
        var now = DateTimeOffset.UtcNow;
        var descriptor = new ContentDescriptor
        {
            ContentId = "content:audio:track:cached",
            Hashes = new List<ContentHash> { new("sha256", "abcd") },
            Codec = "flac",
        };

        cache["content:audio:track:warmup"] = new CachedDescriptor(
            descriptor,
            now,
            now.AddMinutes(-5));
        _ = await retriever.GetStatsAsync();
        Assert.Empty(cache);

        for (var index = 0; index < entryCount; index++)
        {
            cache[$"content:audio:track:{index}"] = new CachedDescriptor(
                descriptor,
                now,
                index % 2 == 0 ? now.AddMinutes(5) : now.AddMinutes(-5));
        }

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var stats = await retriever.GetStatsAsync();
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(entryCount / 2, stats.ActiveCacheEntries);
        Assert.Equal(entryCount / 2, cache.Count);
        Assert.Equal(900_000, stats.CacheSizeBytes);
        Assert.True(
            allocatedBytes < 4 * 1024,
            $"Expected direct cache cleanup/statistics below 4 KiB allocated, got {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task ClearCacheAsync_LargeCacheAvoidsValuesSnapshot()
    {
        const int entryCount = 10_000;
        var retriever = CreateRetriever();
        var cacheField = typeof(DescriptorRetriever).GetField(
            "_cache",
            BindingFlags.Instance | BindingFlags.NonPublic)!;
        var cache = (ConcurrentDictionary<string, CachedDescriptor>)cacheField.GetValue(retriever)!;
        var now = DateTimeOffset.UtcNow;
        var descriptor = new ContentDescriptor
        {
            ContentId = "content:audio:track:cached",
            Hashes = new List<ContentHash> { new("sha256", "abcd") },
            Codec = "flac",
        };

        for (var index = 0; index < entryCount; index++)
        {
            cache[$"content:audio:track:{index}"] = new CachedDescriptor(
                descriptor,
                now,
                now.AddMinutes(5));
        }

        var warmupRetriever = CreateRetriever();
        var warmupCache = (ConcurrentDictionary<string, CachedDescriptor>)cacheField.GetValue(warmupRetriever)!;
        warmupCache["content:audio:track:warmup"] = new CachedDescriptor(
            descriptor,
            now,
            now.AddMinutes(5));
        _ = await warmupRetriever.ClearCacheAsync();
        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var result = await retriever.ClearCacheAsync();
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.True(result.Success);
        Assert.Equal(entryCount, result.EntriesCleared);
        Assert.Equal(1_800_000, result.BytesFreed);
        Assert.Empty(cache);
        Assert.True(
            allocatedBytes < 8 * 1024,
            $"Expected direct cache-clear accounting below 8 KiB allocated, got {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task QueryByDomainAsync_LargeCacheBoundsOrderedResultMaterialization()
    {
        const int entryCount = 10_000;
        const int maxResults = 50;
        var retriever = CreateRetriever();
        var cacheField = typeof(DescriptorRetriever).GetField(
            "_cache",
            BindingFlags.Instance | BindingFlags.NonPublic)!;
        var cache = (ConcurrentDictionary<string, CachedDescriptor>)cacheField.GetValue(retriever)!;
        var now = DateTimeOffset.UtcNow;

        for (var index = 0; index < entryCount; index++)
        {
            var contentId = $"content:audio:track:{index:D5}";
            cache[contentId] = new CachedDescriptor(
                new ContentDescriptor { ContentId = contentId },
                now.AddSeconds(index),
                now.AddHours(1));
        }

        _ = await retriever.QueryByDomainAsync("audio", "track", 1);
        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var result = await retriever.QueryByDomainAsync("audio", "track", maxResults);
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(maxResults, result.TotalFound);
        Assert.True(result.HasMoreResults);
        Assert.Equal(
            Enumerable.Range(entryCount - maxResults, maxResults)
                .Reverse()
                .Select(index => $"content:audio:track:{index:D5}"),
            result.Descriptors.Select(descriptor => descriptor.ContentId));
        Assert.True(
            allocatedBytes < 2 * 1024 * 1024,
            $"Expected bounded domain query below 2 MiB allocated, got {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public async Task QueryByDomainAsync_PreservesNewestDistinctExpiryAndNormalizationSemantics()
    {
        var retriever = CreateRetriever();
        var cacheField = typeof(DescriptorRetriever).GetField(
            "_cache",
            BindingFlags.Instance | BindingFlags.NonPublic)!;
        var cache = (ConcurrentDictionary<string, CachedDescriptor>)cacheField.GetValue(retriever)!;
        var now = DateTimeOffset.UtcNow;
        var duplicateOld = new ContentDescriptor { ContentId = "content:audio:track:duplicate" };
        var duplicateNew = new ContentDescriptor { ContentId = "CONTENT:AUDIO:TRACK:DUPLICATE" };
        var newest = new ContentDescriptor { ContentId = "content:audio:track:newest" };
        var musicBrainz = new ContentDescriptor { ContentId = "content:mb:recording:recording" };

        cache["content:audio:track:duplicate-old"] = new CachedDescriptor(
            duplicateOld, now.AddMinutes(-4), now.AddMinutes(10));
        cache["content:audio:track:duplicate-new"] = new CachedDescriptor(
            duplicateNew, now.AddMinutes(-1), now.AddMinutes(10));
        cache["content:audio:track:newest"] = new CachedDescriptor(
            newest, now, now.AddMinutes(10));
        cache["content:mb:recording:recording"] = new CachedDescriptor(
            musicBrainz, now.AddMinutes(-2), now.AddMinutes(10));
        cache["content:audio:album:not-a-track"] = new CachedDescriptor(
            new ContentDescriptor { ContentId = "content:audio:album:not-a-track" },
            now.AddMinutes(1),
            now.AddMinutes(10));
        cache["content:audio:track:expired"] = new CachedDescriptor(
            new ContentDescriptor { ContentId = "content:audio:track:expired" },
            now.AddMinutes(2),
            now.AddMinutes(-1));

        var result = await retriever.QueryByDomainAsync("audio", "track", maxResults: 2);

        Assert.True(result.HasMoreResults);
        Assert.Equal(newest, result.Descriptors[0]);
        Assert.Equal(duplicateNew, result.Descriptors[1]);
        Assert.DoesNotContain(duplicateOld, result.Descriptors);
        Assert.DoesNotContain(cache.Keys, key => key.EndsWith("expired", StringComparison.Ordinal));

        var complete = await retriever.QueryByDomainAsync("audio", "track", maxResults: 10);
        Assert.False(complete.HasMoreResults);
        Assert.Equal(new[] { newest, duplicateNew, musicBrainz }, complete.Descriptors);
    }

    private static DescriptorRetriever CreateRetriever(IMeshDhtClient? dht = null)
    {
        return new DescriptorRetriever(
            NullLogger<DescriptorRetriever>.Instance,
            dht ?? Mock.Of<IMeshDhtClient>(),
            Mock.Of<IDescriptorValidator>(),
            Options.Create(new MediaCoreOptions()));
    }
}
