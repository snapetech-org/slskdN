// <copyright file="HashDbPerformanceBenchmarks.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Performance.HashDb;

using slskd.HashDb.Models;

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Configs;
using BenchmarkDotNet.Jobs;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using slskd.HashDb;

/// <summary>
/// Performance benchmarks for HashDb operations.
/// Measures query performance, caching effectiveness, and memory usage.
/// </summary>
[Config(typeof(HashDbBenchmarkConfig))]
// [MemoryDiagnoser] // Requires BenchmarkDotNet.Diagnostics.Windows package
public class HashDbPerformanceBenchmarks
{
    private readonly ILogger<HashDbService> _logger;
    private HashDbService? _hashDbService;
    private HashDbService? _hashDbServiceWithCache;
    private string? _tempDir;
    private readonly string[] _testKeys = new string[1000];

    public HashDbPerformanceBenchmarks()
    {
        _logger = NullLogger<HashDbService>.Instance;
    }

[GlobalSetup]
    public void Setup()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"hashdb-bench-{Guid.NewGuid()}");
        Directory.CreateDirectory(_tempDir);

        // Create HashDb service without cache
        _hashDbService = new HashDbService(
            _tempDir,
            eventBus: null,
            serviceProvider: null,
            fingerprintExtractionService: null,
            acoustIdClient: null,
            autoTaggingService: null,
            musicBrainzClient: null,
            optionsMonitor: null,
            hashCache: null);

        // Create HashDb service with cache
        var memoryCache = new MemoryCache(new MemoryCacheOptions());
        _hashDbServiceWithCache = new HashDbService(
            _tempDir,
            eventBus: null,
            serviceProvider: null,
            fingerprintExtractionService: null,
            acoustIdClient: null,
            autoTaggingService: null,
            musicBrainzClient: null,
            optionsMonitor: null,
            hashCache: memoryCache);

        // Populate database with test data
        Console.WriteLine("[BENCH] Populating HashDb with test data...");
        for (int i = 0; i < 1000; i++)
        {
            var key = $"test-key-{i:D6}";
            _testKeys[i] = key;
            
            var entry = new HashDbEntry
            {
                FlacKey = key,
                ByteHash = $"hash-{i:X64}",
                Size = 1024 * 1024 * (i % 100 + 1), // 1MB to 100MB
                MetaFlags = i % 256,
                FirstSeenAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                LastUpdatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                UseCount = i % 100
            };

            _hashDbService.StoreHashAsync(entry).Wait();
        }

        Console.WriteLine("[BENCH] HashDb populated with 1000 entries");
    }

[GlobalCleanup]
    public void Cleanup()
    {
        // HashDbService doesn't implement IDisposable - no cleanup needed
        
        if (_tempDir != null && Directory.Exists(_tempDir))
        {
            try
            {
                Directory.Delete(_tempDir, recursive: true);
            }
            catch
            {
                // Ignore cleanup errors
            }
        }
    }

[Benchmark(Baseline = true)]
[BenchmarkCategory("Lookup")]
    public async Task LookupHash_WithoutCache()
    {
        var key = _testKeys[500]; // Middle entry
        await _hashDbService!.LookupHashAsync(key);
    }

[Benchmark]
[BenchmarkCategory("Lookup")]
    public async Task LookupHash_WithCache()
    {
        var key = _testKeys[500]; // Middle entry
        await _hashDbServiceWithCache!.LookupHashAsync(key);
    }

[Benchmark]
[BenchmarkCategory("Lookup")]
    public async Task LookupHash_CacheHit()
    {
        // First call populates cache
        var key = _testKeys[600];
        await _hashDbServiceWithCache!.LookupHashAsync(key);
        
        // Second call hits cache
        await _hashDbServiceWithCache.LookupHashAsync(key);
    }

[Benchmark]
[BenchmarkCategory("Query")]
    public async Task LookupHashesBySize()
    {
        // Query for a common size (50MB)
        var size = 50 * 1024 * 1024;
        var results = await _hashDbService!.LookupHashesBySizeAsync(size);
        var count = results.Count();
        Console.WriteLine($"[BENCH] Found {count} entries for size {size / 1024 / 1024}MB");
    }

[Benchmark]
[BenchmarkCategory("Query")]
[Arguments(10)]
[Arguments(100)]
[Arguments(1000)]
    public async Task SequentialLookups(int count)
    {
        for (int i = 0; i < count; i++)
        {
            var key = _testKeys[i % _testKeys.Length];
            await _hashDbService!.LookupHashAsync(key);
        }
    }

[Benchmark]
[BenchmarkCategory("Query")]
[Arguments(10)]
[Arguments(100)]
    public async Task ParallelLookups(int concurrency)
    {
        var tasks = Enumerable.Range(0, concurrency)
            .Select(i => _hashDbService!.LookupHashAsync(_testKeys[i % _testKeys.Length]));
        
        await Task.WhenAll(tasks);
    }

[Benchmark]
[BenchmarkCategory("Write")]
    public async Task StoreHash()
    {
        var entry = new HashDbEntry
        {
            FlacKey = $"bench-key-{Guid.NewGuid()}",
            ByteHash = "bench-hash",
            Size = 1024 * 1024,
            MetaFlags = 0,
            FirstSeenAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            LastUpdatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            UseCount = 1
        };

        await _hashDbService!.StoreHashAsync(entry);
    }

[Benchmark]
[BenchmarkCategory("Write")]
[Arguments(10)]
[Arguments(100)]
    public async Task BatchStoreHashes(int count)
    {
        var tasks = Enumerable.Range(0, count)
            .Select(i => Task.Run(async () =>
            {
                var entry = new HashDbEntry
                {
                    FlacKey = $"batch-key-{Guid.NewGuid()}",
                    ByteHash = $"batch-hash-{i}",
                    Size = 1024 * 1024 * (i % 10 + 1),
                    MetaFlags = 0,
                    FirstSeenAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    LastUpdatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    UseCount = 1
                };

                await _hashDbService!.StoreHashAsync(entry);
            }));

        await Task.WhenAll(tasks);
    }

[Benchmark]
[BenchmarkCategory("Stats")]
    public void GetStats()
    {
        var stats = _hashDbService!.GetStats();
        Console.WriteLine($"[BENCH] Stats: {stats.TotalHashEntries} entries");
    }


    /// <summary>
    /// Benchmark configuration for HashDb performance testing.
    /// </summary>
    public class HashDbBenchmarkConfig : ManualConfig
    {
        public HashDbBenchmarkConfig()
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
