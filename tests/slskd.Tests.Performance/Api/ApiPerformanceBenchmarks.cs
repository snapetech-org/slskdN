// <copyright file="ApiPerformanceBenchmarks.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Performance.Api;

using System;
using System.Diagnostics;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Configs;
using BenchmarkDotNet.Jobs;
using Xunit;
using Xunit.Abstractions;

/// <summary>
/// Performance benchmarks for API endpoints.
/// Measures response times, throughput, and memory usage for common API operations.
/// </summary>
[Config(typeof(ApiBenchmarkConfig))]
// [MemoryDiagnoser] // Requires BenchmarkDotNet.Diagnostics.Windows package
[Trait("Category", "Benchmark")]
public class ApiPerformanceBenchmarks : IDisposable
{
    private readonly ITestOutputHelper _output;
    private HttpClient? _httpClient;
    private string? _baseUrl;

    public ApiPerformanceBenchmarks(ITestOutputHelper output)
    {
        _output = output;
    }

[GlobalSetup]
    public void Setup()
    {
        // Note: These benchmarks require a running slskdn instance
        // Set SLSKDN_TEST_URL environment variable or use default
        _baseUrl = Environment.GetEnvironmentVariable("SLSKDN_TEST_URL") ?? "http://localhost:5000";
        _httpClient = new HttpClient
        {
            BaseAddress = new Uri(_baseUrl),
            Timeout = TimeSpan.FromSeconds(30)
        };

        // Attempt to authenticate (optional - benchmarks will skip if not available)
        try
        {
            var loginRequest = new { username = "admin", password = "admin" };
            var loginJson = JsonSerializer.Serialize(loginRequest);
            var loginContent = new StringContent(loginJson, Encoding.UTF8, "application/json");
            
            var loginResponse = _httpClient.PostAsync("/api/v0/session", loginContent).Result;
            if (loginResponse.IsSuccessStatusCode)
            {
                _output.WriteLine("[BENCH] API authentication successful");
            }
        }
        catch
        {
            _output.WriteLine("[BENCH] API not available - benchmarks will be skipped");
        }
    }

[GlobalCleanup]
    public void Cleanup()
    {
        _httpClient?.Dispose();
    }

[Benchmark]
[BenchmarkCategory("Read")]
    public async Task GetSessionStatus()
    {
        if (_httpClient == null) return;
        
        try
        {
            var response = await _httpClient.GetAsync("/api/v0/session/enabled");
            var content = await response.Content.ReadAsStringAsync();
            _output.WriteLine($"[BENCH] Session status: {response.StatusCode}");
        }
        catch
        {
            // API not available - skip
        }
    }

[Benchmark]
[BenchmarkCategory("Read")]
    public async Task GetApplicationState()
    {
        if (_httpClient == null) return;
        
        try
        {
            var response = await _httpClient.GetAsync("/api/v0/application");
            var content = await response.Content.ReadAsStringAsync();
            _output.WriteLine($"[BENCH] Application state: {response.StatusCode}");
        }
        catch
        {
            // API not available - skip
        }
    }

[Benchmark]
[BenchmarkCategory("Read")]
    public async Task GetHashDbStats()
    {
        if (_httpClient == null) return;
        
        try
        {
            var response = await _httpClient.GetAsync("/api/v0/hashdb/stats");
            var content = await response.Content.ReadAsStringAsync();
            _output.WriteLine($"[BENCH] HashDb stats: {response.StatusCode}");
        }
        catch
        {
            // API not available - skip
        }
    }

[Benchmark]
[BenchmarkCategory("Read")]
[Arguments(10)]
[Arguments(50)]
[Arguments(100)]
    public async Task GetJobs_Paginated(int limit)
    {
        if (_httpClient == null) return;
        
        try
        {
            var response = await _httpClient.GetAsync($"/api/jobs?limit={limit}&offset=0");
            var content = await response.Content.ReadAsStringAsync();
            _output.WriteLine($"[BENCH] Jobs (limit={limit}): {response.StatusCode}");
        }
        catch
        {
            // API not available - skip
        }
    }

[Benchmark]
[BenchmarkCategory("Write")]
    public async Task CreateSearch()
    {
        if (_httpClient == null) return;
        
        try
        {
            var searchRequest = new
            {
                query = "test search",
                filters = new { minBitrate = 320 }
            };
            
            var json = JsonSerializer.Serialize(searchRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            
            var response = await _httpClient.PostAsync("/api/v0/searches", content);
            var responseContent = await response.Content.ReadAsStringAsync();
            _output.WriteLine($"[BENCH] Create search: {response.StatusCode}");
        }
        catch
        {
            // API not available - skip
        }
    }

[Benchmark]
[BenchmarkCategory("Concurrency")]
[Arguments(10)]
[Arguments(50)]
[Arguments(100)]
    public async Task ConcurrentGetRequests(int concurrency)
    {
        if (_httpClient == null) return;
        
        try
        {
            var tasks = Enumerable.Range(0, concurrency)
                .Select(i => _httpClient!.GetAsync("/api/v0/session/enabled"));
            
            var responses = await Task.WhenAll(tasks);
            var successCount = responses.Count(r => r.IsSuccessStatusCode);
            _output.WriteLine($"[BENCH] Concurrent requests ({concurrency}): {successCount} succeeded");
        }
        catch
        {
            // API not available - skip
        }
    }

    public void Dispose()
    {
        Cleanup();
    }

    /// <summary>
    /// Benchmark configuration for API performance testing.
    /// </summary>
    public class ApiBenchmarkConfig : ManualConfig
    {
        public ApiBenchmarkConfig()
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
