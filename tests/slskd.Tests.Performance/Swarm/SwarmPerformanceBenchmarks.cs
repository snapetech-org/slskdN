// <copyright file="SwarmPerformanceBenchmarks.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Performance.Swarm;

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Configs;
using BenchmarkDotNet.Jobs;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using slskd.Transfers.MultiSource;
using slskd.Transfers.MultiSource.Optimization;

/// <summary>
/// Performance benchmarks for swarm download operations.
/// Measures chunk scheduling, peer selection, and optimization performance.
/// </summary>
[Config(typeof(SwarmBenchmarkConfig))]
// [MemoryDiagnoser] // Requires BenchmarkDotNet.Diagnostics.Windows package
public class SwarmPerformanceBenchmarks
{
    private readonly ILogger<ChunkSizeOptimizer> _logger;
    private ChunkSizeOptimizer? _optimizer;

    public SwarmPerformanceBenchmarks()
    {
        _logger = NullLogger<ChunkSizeOptimizer>.Instance;
    }

[GlobalSetup]
    public void Setup()
    {
        _optimizer = new ChunkSizeOptimizer(_logger);
    }

[Benchmark]
[BenchmarkCategory("Optimization")]
[Arguments(100 * 1024 * 1024, 5)] // 100MB, 5 peers
[Arguments(500 * 1024 * 1024, 10)] // 500MB, 10 peers
[Arguments(1024 * 1024 * 1024, 20)] // 1GB, 20 peers
    public async Task ChunkSizeOptimization(long fileSize, int peerCount)
    {
        var chunkSize = await _optimizer!.RecommendChunkSizeAsync(
            fileSize,
            peerCount,
            averageThroughputBps: 5 * 1024 * 1024, // 5 MB/s
            averageRttMs: 100,
            CancellationToken.None);

        Console.WriteLine($"[BENCH] File: {fileSize / 1024 / 1024}MB, Peers: {peerCount}, Chunk: {chunkSize / 1024}KB");
    }

[Benchmark]
[BenchmarkCategory("Optimization")]
[Arguments(100, 10)]
[Arguments(200, 20)]
[Arguments(500, 50)]
    public int CalculateChunkSizeForTargetCount(long fileSize, int targetChunkCount)
    {
        return _optimizer!.CalculateChunkSizeForTargetCount(fileSize, targetChunkCount);
    }

[Benchmark]
[BenchmarkCategory("Scheduling")]
[Arguments(10)]
[Arguments(50)]
[Arguments(100)]
    public void ChunkAssignment_Sequential(int chunkCount)
    {
        // Simulate chunk assignment logic
        var chunks = Enumerable.Range(0, chunkCount)
            .Select(i => new { ChunkIndex = i, PeerId = $"peer-{i % 5}" })
            .ToList();

        Console.WriteLine($"[BENCH] Assigned {chunks.Count} chunks to peers");
    }

[Benchmark]
[BenchmarkCategory("Scheduling")]
[Arguments(10, 5)]
[Arguments(50, 10)]
[Arguments(100, 20)]
    public void ChunkAssignment_Parallel(int chunkCount, int peerCount)
    {
        // Simulate parallel chunk assignment
        var chunks = new List<(int ChunkIndex, string PeerId)>();
        var lockObj = new object();

        Parallel.For(0, chunkCount, i =>
        {
            var peerId = $"peer-{i % peerCount}";
            lock (lockObj)
            {
                chunks.Add((i, peerId));
            }
        });

        Console.WriteLine($"[BENCH] Assigned {chunks.Count} chunks to {peerCount} peers in parallel");
    }

[Benchmark]
[BenchmarkCategory("Selection")]
[Arguments(10)]
[Arguments(50)]
[Arguments(100)]
    public void PeerSelection(int candidateCount)
    {
        // Simulate peer selection based on metrics
        var peers = Enumerable.Range(0, candidateCount)
            .Select(i => new
            {
                PeerId = $"peer-{i}",
                Throughput = 1024 * 1024 * (i % 10 + 1), // 1-10 MB/s
                QueueLength = i % 5,
                FreeSlots = (i % 3) + 1,
                Reputation = 50.0 + (i % 50)
            })
            .OrderByDescending(p => p.Throughput)
            .ThenBy(p => p.QueueLength)
            .ThenByDescending(p => p.FreeSlots)
            .ThenByDescending(p => p.Reputation)
            .Take(5)
            .ToList();

        Console.WriteLine($"[BENCH] Selected {peers.Count} peers from {candidateCount} candidates");
    }

    /// <summary>
    /// Benchmark configuration for swarm performance testing.
    /// </summary>
    public class SwarmBenchmarkConfig : ManualConfig
    {
        public SwarmBenchmarkConfig()
        {
            AddJob(Job.Default
                .WithLaunchCount(1)
                .WithWarmupCount(3)
                .WithIterationCount(10));

            // Note: MemoryDiagnoser and ThreadingDiagnoser require BenchmarkDotNet.Diagnostics.Windows package
            // AddDiagnoser(MemoryDiagnoser.Default);
            // AddDiagnoser(ThreadingDiagnoser.Default);

            // AddColumnProvider(DefaultColumnProviders.Metrics);
            // AddColumnProvider(DefaultColumnProviders.Statistics);
        }
    }
}
