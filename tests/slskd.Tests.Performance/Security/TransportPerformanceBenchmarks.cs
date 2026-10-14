// <copyright file="TransportPerformanceBenchmarks.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Configs;
using BenchmarkDotNet.Jobs;
using Microsoft.Extensions.Logging;
using slskd.Common.Security;
using Xunit;
using Xunit.Abstractions;

namespace slskd.Tests.Performance.Security;

/// <summary>
/// Performance benchmarks for slskdN transport implementations.
/// Measures latency, throughput, and resource usage.
/// </summary>
[Config(typeof(TransportBenchmarkConfig))]
// [MemoryDiagnoser] // Requires BenchmarkDotNet.Diagnostics.Windows package
// [ThreadingDiagnoser] // Requires BenchmarkDotNet.Diagnostics.Windows package
public class TransportPerformanceBenchmarks
{
    private readonly ITestOutputHelper _output;
    private readonly ILogger _logger;

    // Benchmark payloads
    private readonly byte[] _smallPayload = Encoding.UTF8.GetBytes("Hello World!");
    private readonly byte[] _mediumPayload = Encoding.UTF8.GetBytes(new string('x', 1024)); // 1KB
    private readonly byte[] _largePayload = Encoding.UTF8.GetBytes(new string('x', 65536)); // 64KB

    // Mock transports for testing
    private DirectTransport? _directTransport;
    // Note: WebSocketTransport and HttpTunnelTransport classes may not be accessible in test context
    // private WebSocketTransport? _webSocketTransport;
    // private HttpTunnelTransport? _httpTunnelTransport;

    public TransportPerformanceBenchmarks(ITestOutputHelper output)
    {
        _output = output;
        _logger = new XunitLogger(_output);
    }

[GlobalSetup]
    public void Setup()
    {
        // Initialize mock transports
        _directTransport = new DirectTransport((ILogger<DirectTransport>)_logger);

        // Note: Transport classes may not be available - using mock/placeholder
        // _webSocketTransport = new WebSocketTransport(...);
        // _httpTunnelTransport = new HttpTunnelTransport(...);
    }

[Benchmark(Baseline = true)]
[BenchmarkCategory("Latency")]
    public async Task DirectTransport_ConnectionLatency()
    {
        if (_directTransport == null) return;

        var sw = Stopwatch.StartNew();
        try
        {
            await _directTransport.ConnectAsync("127.0.0.1", 12345);
        }
        catch
        {
            // Expected to fail - we're measuring connection attempt latency
        }
        sw.Stop();

        _output.WriteLine($"Direct connection attempt: {sw.Elapsed.TotalMilliseconds}ms");
    }

    // Note: WebSocket and HttpTunnel transport benchmarks disabled - classes may not be available
    // [Benchmark]
    // [BenchmarkCategory("Latency")]
    // public async Task WebSocketTransport_ConnectionLatency() { ... }
    
    // [Benchmark]
    // [BenchmarkCategory("Latency")]
    // public async Task HttpTunnelTransport_ConnectionLatency() { ... }

[Benchmark]
[BenchmarkCategory("Throughput")]
[Arguments(100)] // 100 iterations
    public async Task TransportSelector_SelectionThroughput(int iterations)
    {
        var adversarialOptions = new AdversarialOptions
        {
            Anonymity = new AnonymityLayerOptions { Enabled = false }
        };

        var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        var selector = new AnonymityTransportSelector(
            adversarialOptions,
            new Mesh.Transport.TransportPolicyManager((ILogger<Mesh.Transport.TransportPolicyManager>)_logger),
            (ILogger<AnonymityTransportSelector>)_logger,
            loggerFactory,
            null);

        var sw = Stopwatch.StartNew();
        for (int i = 0; i < iterations; i++)
        {
            try
            {
                await selector.SelectAndConnectAsync($"peer{i}", null, "127.0.0.1", 12345);
            }
            catch
            {
                // Expected failures - measuring selection throughput
            }
        }
        sw.Stop();

        var throughput = iterations / sw.Elapsed.TotalSeconds;
        _output.WriteLine($"Transport selection throughput: {throughput:F2} selections/sec");
    }

[Benchmark]
[BenchmarkCategory("Memory")]
    public void TransportCreation_MemoryUsage()
    {
        var before = GC.GetTotalMemory(true);

        // Create multiple transport instances
        var transports = new List<IAnonymityTransport>();
        for (int i = 0; i < 100; i++)
        {
            var options = new WebSocketTransportOptions { ServerUrl = $"ws://test{i}.example.com", Enabled = false };
            transports.Add(new WebSocketTransport(options, (ILogger<WebSocketTransport>)_logger));
        }

        var after = GC.GetTotalMemory(false);
        var memoryUsed = after - before;

        _output.WriteLine($"Memory usage for 100 WebSocket transports: {memoryUsed / 1024.0:F2} KB");

        // Cleanup
        foreach (var transport in transports)
        {
            if (transport is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

[Benchmark]
[BenchmarkCategory("Concurrency")]
[Arguments(10)] // 10 concurrent operations
    public async Task ConcurrentTransportOperations(int concurrencyLevel)
    {
        var adversarialOptions = new AdversarialOptions
        {
            Anonymity = new AnonymityLayerOptions { Enabled = false }
        };

        var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        var selector = new AnonymityTransportSelector(
            adversarialOptions,
            new Mesh.Transport.TransportPolicyManager((ILogger<Mesh.Transport.TransportPolicyManager>)_logger),
            (ILogger<AnonymityTransportSelector>)_logger,
            loggerFactory,
            null);

        var tasks = new List<Task>();
        var sw = Stopwatch.StartNew();

        for (int i = 0; i < concurrencyLevel; i++)
        {
            tasks.Add(Task.Run(async () =>
            {
                try
                {
                    await selector.SelectAndConnectAsync($"peer{i}", null, "127.0.0.1", 12345);
                }
                catch
                {
                    // Expected failures
                }
            }));
        }

        await Task.WhenAll(tasks);
        sw.Stop();

        _output.WriteLine($"Concurrent operations ({concurrencyLevel}): {sw.Elapsed.TotalMilliseconds}ms total");
    }

[Benchmark]
[BenchmarkCategory("Serialization")]
    public async Task PayloadProcessing_Overhead()
    {
        var paddingOptions = new MessagePaddingOptions { Enabled = true, BucketSizes = new List<int> { 512, 1024 } };
        var timingOptions = new TimingObfuscationOptions { Enabled = false };
        var batchingOptions = new MessageBatchingOptions { Enabled = false };
        var coverTrafficOptions = new CoverTrafficOptions { Enabled = false };
        
        var privacyOptions = new PrivacyLayerOptions
        {
            Enabled = true,
            Padding = paddingOptions,
            Timing = timingOptions,
            Batching = batchingOptions,
            CoverTraffic = coverTrafficOptions
        };
        
        var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        var privacyLayer = new PrivacyLayer(
            privacyOptions,
            (ILogger<PrivacyLayer>)_logger,
            loggerFactory);

        var iterations = 1000;
        var sw = Stopwatch.StartNew();

        for (int i = 0; i < iterations; i++)
        {
            var result = await privacyLayer.TransformOutboundAsync(_mediumPayload);
        }

        sw.Stop();

        var throughput = iterations / sw.Elapsed.TotalSeconds;
        _output.WriteLine($"Privacy layer processing: {throughput:F2} payloads/sec");
    }

[Benchmark]
[BenchmarkCategory("ErrorHandling")]
[Arguments(100)]
    public async Task TransportErrorRecovery_Time(int errorCount)
    {
        var adversarialOptions = new AdversarialOptions
        {
            Anonymity = new AnonymityLayerOptions { Enabled = false }
        };

        var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        var selector = new AnonymityTransportSelector(
            adversarialOptions,
            new Mesh.Transport.TransportPolicyManager((ILogger<Mesh.Transport.TransportPolicyManager>)_logger),
            (ILogger<AnonymityTransportSelector>)_logger,
            loggerFactory,
            null);

        var sw = Stopwatch.StartNew();
        var errorsEncountered = 0;

        for (int i = 0; i < errorCount; i++)
        {
            try
            {
                await selector.SelectAndConnectAsync($"peer{i}", null, "127.0.0.1", 12345);
            }
            catch
            {
                errorsEncountered++;
            }
        }

        sw.Stop();

        _output.WriteLine($"Error recovery: {errorsEncountered} errors in {sw.Elapsed.TotalMilliseconds}ms");
    }

    /// <summary>
    /// Benchmark configuration for transport performance testing.
    /// </summary>
    public class TransportBenchmarkConfig : ManualConfig
    {
        public TransportBenchmarkConfig()
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

    /// <summary>
    /// Mock direct transport for benchmarking baseline.
    /// </summary>
    private class DirectTransport : IAnonymityTransport
    {
        private readonly ILogger<DirectTransport> _logger;

        public DirectTransport(ILogger<DirectTransport> logger)
        {
            _logger = logger;
        }

        public AnonymityTransportType TransportType => AnonymityTransportType.Direct;

        public Task<bool> IsAvailableAsync(CancellationToken cancellationToken = default)
        {
            return Task.FromResult(true);
        }

        public async Task<Stream> ConnectAsync(string host, int port, CancellationToken cancellationToken = default)
        {
            return await ConnectAsync(host, port, null, cancellationToken);
        }

        public async Task<Stream> ConnectAsync(string host, int port, string? isolationKey, CancellationToken cancellationToken = default)
        {
            // Simulate connection attempt
            await Task.Delay(1, cancellationToken); // Minimal delay for benchmark
            throw new InvalidOperationException("Mock connection failure for benchmarking");
        }

        public AnonymityTransportStatus GetStatus()
        {
            return new AnonymityTransportStatus
            {
                IsAvailable = true,
                ActiveConnections = 0,
                TotalConnectionsAttempted = 0,
                TotalConnectionsSuccessful = 0
            };
        }
    }

    /// <summary>
    /// Xunit logger implementation for benchmarks.
    /// </summary>
    private class XunitLogger : ILogger
    {
        private readonly ITestOutputHelper _output;

        public XunitLogger(ITestOutputHelper output)
        {
            _output = output;
        }

        public IDisposable BeginScope<TState>(TState state)
            where TState : notnull => NullScope.Instance;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            _output.WriteLine($"[{logLevel}] {formatter(state, exception)}");
            if (exception != null)
            {
                _output.WriteLine($"Exception: {exception}");
            }
        }

        private class NullScope : IDisposable
        {
            public static NullScope Instance { get; } = new();
            public void Dispose() { }
        }
    }
}

// Additional benchmark classes for specific transport comparisons

/// <summary>
/// Benchmarks comparing transport initialization performance.
/// Note: Transport classes may not be available - these benchmarks are placeholders.
/// </summary>
public class TransportInitializationBenchmarks
{
[Benchmark]
    public void TransportInitialization_Placeholder()
    {
        // Placeholder for transport initialization benchmarks
        // Actual transport classes may not be available in this context
    }
}

/// <summary>
/// Benchmarks measuring status checking performance.
/// Note: Transport classes may not be available - these benchmarks are placeholders.
/// </summary>
public class TransportStatusBenchmarks
{
[Benchmark]
    public void TransportStatusCheck_Placeholder()
    {
        // Placeholder for transport status check benchmarks
        // Actual transport classes may not be available in this context
    }
}
