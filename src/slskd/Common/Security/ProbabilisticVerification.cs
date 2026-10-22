// <copyright file="ProbabilisticVerification.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Common.Security;

using System;
using System.Buffers;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

/// <summary>
/// Implements probabilistic verification with random sampling.
/// SECURITY: Unpredictable verification makes attacks harder to optimize against.
/// </summary>
public sealed class ProbabilisticVerification : IDisposable
{
    private readonly ILogger<ProbabilisticVerification> _logger;
    private readonly ConcurrentDictionary<string, VerificationSession> _sessions = new();
    private readonly Queue<string> _sessionOrder = new(MaxSessions);
    private readonly Timer _cleanupTimer;

    /// <summary>
    /// Maximum sessions to track.
    /// </summary>
    public const int MaxSessions = 1000;

    /// <summary>
    /// Default sample percentage (0.0-1.0).
    /// </summary>
    public double DefaultSampleRate { get; init; } = 0.1; // 10%

    /// <summary>
    /// Minimum chunks to always verify.
    /// </summary>
    public int MinimumChunksToVerify { get; init; } = 3;

    /// <summary>
    /// Maximum chunks to verify per file.
    /// </summary>
    public int MaximumChunksToVerify { get; init; } = 50;

    /// <summary>
    /// Session TTL.
    /// </summary>
    public TimeSpan SessionTtl { get; init; } = TimeSpan.FromHours(1);

    /// <summary>
    /// Initializes a new instance of the <see cref="ProbabilisticVerification"/> class.
    /// </summary>
    public ProbabilisticVerification(ILogger<ProbabilisticVerification> logger)
    {
        _logger = logger;
        _cleanupTimer = new Timer(CleanupExpired, null, TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(5));
    }

    /// <summary>
    /// Dispose timer resources.
    /// </summary>
    public void Dispose()
    {
        Common.TimerDisposer.DisposeWithWait(_cleanupTimer);
        GC.SuppressFinalize(this);
    }

    /// <summary>
    /// Start a verification session for a file.
    /// </summary>
    /// <param name="filename">File being verified.</param>
    /// <param name="totalChunks">Total number of chunks.</param>
    /// <param name="sampleRate">Optional sample rate override.</param>
    /// <returns>Session with selected chunks to verify.</returns>
    public VerificationSession StartSession(string filename, int totalChunks, double? sampleRate = null)
    {
        var sessionId = Guid.NewGuid().ToString("N")[..16];
        var rate = sampleRate ?? DefaultSampleRate;

        // Calculate how many chunks to verify
        var targetCount = (int)Math.Ceiling(totalChunks * rate);
        targetCount = Math.Max(targetCount, MinimumChunksToVerify);
        targetCount = Math.Min(targetCount, MaximumChunksToVerify);
        targetCount = Math.Min(targetCount, totalChunks);

        // Randomly select chunk indices
        var selectedChunks = SelectRandomChunks(totalChunks, targetCount);

        var session = new VerificationSession
        {
            Id = sessionId,
            Filename = filename,
            TotalChunks = totalChunks,
            SelectedChunks = selectedChunks,
            SampleRate = rate,
            CreatedAt = DateTimeOffset.UtcNow,
            ExpiresAt = DateTimeOffset.UtcNow.Add(SessionTtl),
        };

        // Keep eviction O(1) and serialize the count check with insertion so
        // concurrent starts cannot exceed the session cap.
        lock (_sessionOrder)
        {
            while (_sessions.Count >= MaxSessions && _sessionOrder.TryDequeue(out var oldestSessionId))
            {
                _sessions.TryRemove(oldestSessionId, out _);
            }

            _sessions[sessionId] = session;
            _sessionOrder.Enqueue(sessionId);
        }

        _logger.LogDebug(
            "Started verification session {Id}: {Selected}/{Total} chunks selected ({Rate:P0})",
            sessionId, targetCount, totalChunks, rate);

        return session;
    }

    /// <summary>
    /// Check if a specific chunk should be verified.
    /// </summary>
    /// <param name="sessionId">Session ID.</param>
    /// <param name="chunkIndex">Chunk index.</param>
    /// <returns>True if chunk should be verified.</returns>
    public bool ShouldVerifyChunk(string sessionId, int chunkIndex)
    {
        if (!_sessions.TryGetValue(sessionId, out var session))
        {
            // No session - verify everything
            return true;
        }

        return session.SelectedChunks.Contains(chunkIndex);
    }

    /// <summary>
    /// Record verification result for a chunk.
    /// </summary>
    /// <param name="sessionId">Session ID.</param>
    /// <param name="chunkIndex">Chunk index.</param>
    /// <param name="expectedHash">Expected hash.</param>
    /// <param name="actualHash">Actual hash.</param>
    /// <returns>Verification result.</returns>
    public ChunkVerificationResult RecordResult(
        string sessionId,
        int chunkIndex,
        string expectedHash,
        string actualHash)
    {
        if (!_sessions.TryGetValue(sessionId, out var session))
        {
            return ChunkVerificationResult.Failed("Session not found");
        }

        var matches = string.Equals(
            expectedHash.ToLowerInvariant(),
            actualHash.ToLowerInvariant(),
            StringComparison.Ordinal);

        lock (session)
        {
            session.Results[chunkIndex] = new ChunkResult
            {
                ChunkIndex = chunkIndex,
                ExpectedHash = expectedHash,
                ActualHash = actualHash,
                Matches = matches,
                VerifiedAt = DateTimeOffset.UtcNow,
            };

            if (matches)
            {
                session.PassedChunks++;
            }
            else
            {
                session.FailedChunks++;
                _logger.LogWarning(
                    "Chunk {Index} verification failed: expected {Expected}, got {Actual}",
                    chunkIndex,
                    expectedHash[..Math.Min(16, expectedHash.Length)],
                    actualHash[..Math.Min(16, actualHash.Length)]);
            }
        }

        return matches
            ? ChunkVerificationResult.Passed()
            : ChunkVerificationResult.Failed("Hash mismatch");
    }

    /// <summary>
    /// Finalize a verification session.
    /// </summary>
    /// <param name="sessionId">Session ID.</param>
    /// <returns>Final verification result.</returns>
    public SessionVerificationResult FinalizeSession(string sessionId)
    {
        if (!_sessions.TryGetValue(sessionId, out var session))
        {
            return SessionVerificationResult.Failed("Session not found");
        }

        lock (session)
        {
            var verifiedCount = session.Results.Count;
            var expectedCount = session.SelectedChunks.Count;

            // Calculate confidence based on sample size
            var confidence = CalculateConfidence(
                session.TotalChunks,
                verifiedCount,
                session.PassedChunks);

            var result = new SessionVerificationResult
            {
                SessionId = sessionId,
                TotalChunks = session.TotalChunks,
                VerifiedChunks = verifiedCount,
                PassedChunks = session.PassedChunks,
                FailedChunks = session.FailedChunks,
                SkippedChunks = session.TotalChunks - verifiedCount,
                SampleRate = session.SampleRate,
                Confidence = confidence,
                IsValid = session.FailedChunks == 0,
                FailedIndices = session.Results
                    .Where(kvp => !kvp.Value.Matches)
                    .Select(kvp => kvp.Key)
                    .ToList(),
            };

            session.IsFinalized = true;

            _logger.LogInformation(
                "Verification session {Id} complete: {Passed}/{Verified} passed, {Failed} failed, confidence={Confidence:P0}",
                sessionId, session.PassedChunks, verifiedCount, session.FailedChunks, confidence);

            return result;
        }
    }

    /// <summary>
    /// Perform spot-check verification on a file.
    /// Randomly selects and verifies chunks.
    /// </summary>
    /// <param name="filePath">Path to file.</param>
    /// <param name="chunkSize">Chunk size in bytes.</param>
    /// <param name="expectedHashes">Expected hashes for each chunk.</param>
    /// <param name="sampleRate">Sample rate (0.0-1.0).</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>Spot check result.</returns>
    public async Task<SpotCheckResult> SpotCheckFileAsync(
        string filePath,
        int chunkSize,
        IReadOnlyDictionary<int, string> expectedHashes,
        double sampleRate,
        CancellationToken cancellationToken = default)
    {
        var totalChunks = expectedHashes.Count;
        var session = StartSession(filePath, totalChunks, sampleRate);

        await using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
        byte[]? buffer = null;
        var bytesToClear = 0;

        try
        {
            foreach (var chunkIndex in session.SelectedChunks)
            {
                cancellationToken.ThrowIfCancellationRequested();

                if (!expectedHashes.TryGetValue(chunkIndex, out var expectedHash))
                {
                    continue;
                }

                // Read chunk
                var offset = (long)chunkIndex * chunkSize;
                stream.Seek(offset, SeekOrigin.Begin);

                var actualSize = (int)Math.Min(chunkSize, stream.Length - offset);
                buffer ??= ArrayPool<byte>.Shared.Rent(chunkSize);
                bytesToClear = Math.Max(bytesToClear, actualSize);
                await stream.ReadExactlyAsync(buffer.AsMemory(0, actualSize), cancellationToken);

                // Hash chunk
                var actualHash = ComputeSha256LowerHex(buffer, actualSize);

                RecordResult(session.Id, chunkIndex, expectedHash, actualHash);
            }
        }
        finally
        {
            if (buffer != null)
            {
                Array.Clear(buffer, 0, bytesToClear);
                ArrayPool<byte>.Shared.Return(buffer);
            }
        }

        var result = FinalizeSession(session.Id);

        return new SpotCheckResult
        {
            FilePath = filePath,
            TotalChunks = totalChunks,
            VerifiedChunks = result.VerifiedChunks,
            PassedChunks = result.PassedChunks,
            FailedChunks = result.FailedChunks,
            IsValid = result.IsValid,
            Confidence = result.Confidence,
            FailedIndices = result.FailedIndices,
        };
    }

    private static string ComputeSha256LowerHex(byte[] bytes, int length)
    {
        Span<byte> hash = stackalloc byte[32];
        SHA256.HashData(bytes.AsSpan(0, length), hash);
        return Convert.ToHexStringLower(hash);
    }

    /// <summary>
    /// Get a session.
    /// </summary>
    public VerificationSession? GetSession(string sessionId)
    {
        return _sessions.TryGetValue(sessionId, out var s) ? s : null;
    }

    /// <summary>
    /// Get statistics.
    /// </summary>
    public VerificationStats GetStats()
    {
        var totalSessions = 0;
        var activeSessions = 0;
        var totalChunksVerified = 0;
        var totalChunksPassed = 0;
        var totalChunksFailed = 0;
        double totalSampleRate = 0;
        foreach (var session in _sessions.Values)
        {
            totalSessions++;
            if (!session.IsFinalized)
            {
                activeSessions++;
            }

            totalChunksVerified += session.Results.Count;
            totalChunksPassed += session.PassedChunks;
            totalChunksFailed += session.FailedChunks;
            totalSampleRate += session.SampleRate;
        }

        return new VerificationStats
        {
            TotalSessions = totalSessions,
            ActiveSessions = activeSessions,
            TotalChunksVerified = totalChunksVerified,
            TotalChunksPassed = totalChunksPassed,
            TotalChunksFailed = totalChunksFailed,
            AverageSampleRate = totalSessions > 0 ? totalSampleRate / totalSessions : 0,
        };
    }

    private static HashSet<int> SelectRandomChunks(int totalChunks, int count)
    {
        var selected = new HashSet<int>();

        if (count >= totalChunks)
        {
            // Select all
            for (int i = 0; i < totalChunks; i++)
            {
                selected.Add(i);
            }

            return selected;
        }

        // Use Fisher-Yates partial shuffle
        var indices = Enumerable.Range(0, totalChunks).ToArray();

        for (int i = 0; i < count; i++)
        {
            var j = RandomNumberGenerator.GetInt32(i, totalChunks);
            (indices[i], indices[j]) = (indices[j], indices[i]);
            selected.Add(indices[i]);
        }

        return selected;
    }

    private static double CalculateConfidence(int totalChunks, int verified, int passed)
    {
        if (verified == 0)
        {
            return 0;
        }

        // Simple confidence model:
        // - Base confidence from pass rate
        // - Scaled by coverage
        var passRate = (double)passed / verified;
        var coverage = (double)verified / totalChunks;

        // If all verified chunks passed, confidence increases with coverage
        if (passRate >= 1.0)
        {
            // 95% confidence at 5% coverage, approaches 100% as coverage increases
            return 0.95 + (0.05 * coverage);
        }

        // If some failed, confidence drops
        return passRate * (0.5 + 0.5 * coverage);
    }

    private void CleanupExpired(object? state)
    {
        var now = DateTimeOffset.UtcNow;
        lock (_sessionOrder)
        {
            while (_sessionOrder.TryPeek(out var id))
            {
                if (!_sessions.TryGetValue(id, out var session))
                {
                    _sessionOrder.Dequeue();
                    continue;
                }

                if (session.ExpiresAt >= now)
                {
                    break;
                }

                _sessionOrder.Dequeue();
                _sessions.TryRemove(id, out _);
            }
        }
    }

}

/// <summary>
/// A verification session.
/// </summary>
public sealed class VerificationSession
{
    /// <summary>Gets the session ID.</summary>
    public required string Id { get; init; }

    /// <summary>Gets the filename.</summary>
    public required string Filename { get; init; }

    /// <summary>Gets total chunks.</summary>
    public required int TotalChunks { get; init; }

    /// <summary>Gets selected chunk indices.</summary>
    public required HashSet<int> SelectedChunks { get; init; }

    /// <summary>Gets the sample rate used.</summary>
    public required double SampleRate { get; init; }

    /// <summary>Gets when created.</summary>
    public required DateTimeOffset CreatedAt { get; init; }

    /// <summary>Gets when expires.</summary>
    public required DateTimeOffset ExpiresAt { get; init; }

    /// <summary>Gets results per chunk.</summary>
    public Dictionary<int, ChunkResult> Results { get; } = new();

    /// <summary>Gets or sets passed chunks count.</summary>
    public int PassedChunks { get; set; }

    /// <summary>Gets or sets failed chunks count.</summary>
    public int FailedChunks { get; set; }

    /// <summary>Gets or sets whether finalized.</summary>
    public bool IsFinalized { get; set; }
}

/// <summary>
/// Result for a single chunk.
/// </summary>
public sealed class ChunkResult
{
    /// <summary>Gets the chunk index.</summary>
    public required int ChunkIndex { get; init; }

    /// <summary>Gets the expected hash.</summary>
    public required string ExpectedHash { get; init; }

    /// <summary>Gets the actual hash.</summary>
    public required string ActualHash { get; init; }

    /// <summary>Gets whether hashes matched.</summary>
    public required bool Matches { get; init; }

    /// <summary>Gets when verified.</summary>
    public required DateTimeOffset VerifiedAt { get; init; }
}

/// <summary>
/// Result of chunk verification.
/// </summary>
public sealed class ChunkVerificationResult
{
    /// <summary>Gets whether verification passed.</summary>
    public bool Success { get; init; }

    /// <summary>Gets error if failed.</summary>
    public string? Error { get; init; }

    /// <summary>Create passed result.</summary>
    public static ChunkVerificationResult Passed() => new() { Success = true };

    /// <summary>Create failed result.</summary>
    public static ChunkVerificationResult Failed(string error) => new() { Success = false, Error = error };
}

/// <summary>
/// Result of session verification.
/// </summary>
public sealed class SessionVerificationResult
{
    /// <summary>Gets the session ID.</summary>
    public required string SessionId { get; init; }

    /// <summary>Gets total chunks.</summary>
    public int TotalChunks { get; init; }

    /// <summary>Gets verified chunks.</summary>
    public int VerifiedChunks { get; init; }

    /// <summary>Gets passed chunks.</summary>
    public int PassedChunks { get; init; }

    /// <summary>Gets failed chunks.</summary>
    public int FailedChunks { get; init; }

    /// <summary>Gets skipped chunks.</summary>
    public int SkippedChunks { get; init; }

    /// <summary>Gets sample rate.</summary>
    public double SampleRate { get; init; }

    /// <summary>Gets confidence (0.0-1.0).</summary>
    public double Confidence { get; init; }

    /// <summary>Gets whether valid.</summary>
    public bool IsValid { get; init; }

    /// <summary>Gets failed chunk indices.</summary>
    public List<int> FailedIndices { get; init; } = new();

    /// <summary>Gets error if failed.</summary>
    public string? Error { get; init; }

    /// <summary>Create failed result.</summary>
    public static SessionVerificationResult Failed(string error) => new()
    {
        SessionId = string.Empty,
        Error = error,
    };
}

/// <summary>
/// Result of spot check.
/// </summary>
public sealed class SpotCheckResult
{
    /// <summary>Gets the file path.</summary>
    public required string FilePath { get; init; }

    /// <summary>Gets total chunks.</summary>
    public required int TotalChunks { get; init; }

    /// <summary>Gets verified chunks.</summary>
    public required int VerifiedChunks { get; init; }

    /// <summary>Gets passed chunks.</summary>
    public required int PassedChunks { get; init; }

    /// <summary>Gets failed chunks.</summary>
    public required int FailedChunks { get; init; }

    /// <summary>Gets whether valid.</summary>
    public required bool IsValid { get; init; }

    /// <summary>Gets confidence.</summary>
    public required double Confidence { get; init; }

    /// <summary>Gets failed indices.</summary>
    public required List<int> FailedIndices { get; init; }
}

/// <summary>
/// Verification statistics.
/// </summary>
public sealed class VerificationStats
{
    /// <summary>Gets total sessions.</summary>
    public int TotalSessions { get; init; }

    /// <summary>Gets active sessions.</summary>
    public int ActiveSessions { get; init; }

    /// <summary>Gets total chunks verified.</summary>
    public long TotalChunksVerified { get; init; }

    /// <summary>Gets total chunks passed.</summary>
    public long TotalChunksPassed { get; init; }

    /// <summary>Gets total chunks failed.</summary>
    public long TotalChunksFailed { get; init; }

    /// <summary>Gets average sample rate.</summary>
    public double AverageSampleRate { get; init; }
}
