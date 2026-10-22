// <copyright file="ByzantineConsensus.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Common.Security;

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Microsoft.Extensions.Logging;

/// <summary>
/// Implements Byzantine fault-tolerant consensus for multi-source downloads.
/// SECURITY: Ensures data integrity when peers may be malicious or faulty.
/// </summary>
public sealed class ByzantineConsensus : IDisposable
{
    private readonly ILogger<ByzantineConsensus> _logger;
    private readonly ConcurrentDictionary<string, ConsensusSession> _sessions = new();

    // All queue access is locked; it preserves insertion order for bounded eviction.
    private readonly Queue<string> _sessionOrder = new(MaxSessions);
    private readonly Timer _cleanupTimer;

    /// <summary>
    /// Maximum sessions to track.
    /// </summary>
    public const int MaxSessions = 1000;

    /// <summary>
    /// How long sessions remain valid.
    /// </summary>
    public TimeSpan SessionTtl { get; init; } = TimeSpan.FromHours(1);

    /// <summary>
    /// Minimum sources required for consensus.
    /// </summary>
    public int MinimumSources { get; init; } = 3;

    /// <summary>
    /// Initializes a new instance of the <see cref="ByzantineConsensus"/> class.
    /// </summary>
    public ByzantineConsensus(ILogger<ByzantineConsensus> logger)
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
    /// Start a consensus session for a file.
    /// </summary>
    /// <param name="filename">The file being downloaded.</param>
    /// <param name="expectedHash">Expected file hash if known.</param>
    /// <returns>Session ID.</returns>
    public string StartSession(string filename, string? expectedHash = null)
    {
        var sessionId = Guid.NewGuid().ToString("N")[..16];
        ConsensusSession session;

        lock (_sessionOrder)
        {

            // Serialize insertion and eviction so concurrent starts cannot exceed capacity.
            while (_sessions.Count >= MaxSessions && _sessionOrder.TryDequeue(out var oldestSessionId))
            {
                _sessions.TryRemove(oldestSessionId, out _);
            }

            while (_sessions.ContainsKey(sessionId))
            {
                sessionId = Guid.NewGuid().ToString("N")[..16];
            }

            var createdAt = DateTimeOffset.UtcNow;
            session = new ConsensusSession
            {
                Id = sessionId,
                Filename = filename,
                ExpectedHash = expectedHash,
                CreatedAt = createdAt,
                ExpiresAt = createdAt.Add(SessionTtl),
                State = ConsensusState.Collecting,
            };

            _sessions[sessionId] = session;
            _sessionOrder.Enqueue(sessionId);
        }

        _logger.LogDebug("Started consensus session {Id} for {File}", sessionId, LoggingSanitizer.SanitizeFilePath(filename));

        return sessionId;
    }

    /// <summary>
    /// Submit a vote (chunk hash) from a source.
    /// </summary>
    /// <param name="sessionId">Session ID.</param>
    /// <param name="source">Source identifier (username).</param>
    /// <param name="chunkIndex">Chunk index.</param>
    /// <param name="chunkHash">Hash of the chunk.</param>
    /// <returns>Vote result.</returns>
    public VoteResult SubmitVote(string sessionId, string source, int chunkIndex, string chunkHash)
    {
        if (!_sessions.TryGetValue(sessionId, out var session))
        {
            return VoteResult.Failed("Session not found");
        }

        lock (session)
        {
            // Re-check state under lock; FinalizeSession mutates it while holding the same lock
            if (session.State != ConsensusState.Collecting)
            {
                return VoteResult.Failed($"Session is {session.State}, not collecting");
            }

            // Get or create chunk votes
            if (!session.ChunkVotes.TryGetValue(chunkIndex, out var votes))
            {
                votes = new ChunkVotes { ChunkIndex = chunkIndex };
                session.ChunkVotes[chunkIndex] = votes;
            }

            // Record vote
            var normalizedHash = chunkHash.ToLowerInvariant();
            votes.Votes[source] = normalizedHash;

            // Update hash counts
            if (!votes.HashCounts.TryGetValue(normalizedHash, out var count))
            {
                count = 0;
            }

            votes.HashCounts[normalizedHash] = count + 1;

            _logger.LogDebug(
                "Vote from {Source} for chunk {Index}: {Hash}",
                LoggingSanitizer.SanitizeExternalIdentifier(source),
                chunkIndex,
                LoggingSanitizer.SanitizeHash(normalizedHash[..Math.Min(16, normalizedHash.Length)]));

            return VoteResult.Succeeded();
        }
    }

    /// <summary>
    /// Get consensus result for a chunk.
    /// Uses simple majority voting.
    /// </summary>
    /// <param name="sessionId">Session ID.</param>
    /// <param name="chunkIndex">Chunk index.</param>
    /// <returns>Consensus result.</returns>
    public ConsensusResult GetConsensus(string sessionId, int chunkIndex)
    {
        if (!_sessions.TryGetValue(sessionId, out var session))
        {
            return ConsensusResult.Failed("Session not found");
        }

        lock (session)
        {
            if (!session.ChunkVotes.TryGetValue(chunkIndex, out var votes))
            {
                return ConsensusResult.Failed("No votes for chunk");
            }

            var totalVotes = votes.Votes.Count;

            if (totalVotes < MinimumSources)
            {
                return ConsensusResult.Inconclusive(
                    $"Insufficient sources: {totalVotes} < {MinimumSources}",
                    totalVotes);
            }

            // Find majority hash
            var (majorityHash, majorityCount) = votes.HashCounts
                .OrderByDescending(kvp => kvp.Value)
                .First();

            // Byzantine tolerance: need > 2/3 agreement
            var requiredVotes = (totalVotes * 2 / 3) + 1;
            var agreementRatio = (double)majorityCount / totalVotes;

            if (majorityCount >= requiredVotes)
            {
                // Find dissenting sources
                var dissenters = votes.Votes
                    .Where(kvp => kvp.Value != majorityHash)
                    .Select(kvp => kvp.Key)
                    .ToList();

                return ConsensusResult.Reached(
                    majorityHash,
                    majorityCount,
                    totalVotes,
                    agreementRatio,
                    dissenters);
            }
            else
            {
                return ConsensusResult.NoConsensus(
                    $"No majority: best has {majorityCount}/{totalVotes} ({agreementRatio:P0})",
                    totalVotes,
                    agreementRatio);
            }
        }
    }

    /// <summary>
    /// Finalize a session with overall file hash verification.
    /// </summary>
    /// <param name="sessionId">Session ID.</param>
    /// <param name="actualFileHash">Actual hash of downloaded file.</param>
    /// <returns>Finalization result.</returns>
    public SessionResult FinalizeSession(string sessionId, string actualFileHash)
    {
        if (!_sessions.TryGetValue(sessionId, out var session))
        {
            return SessionResult.Failed("Session not found");
        }

        lock (session)
        {
            var result = new SessionResult
            {
                SessionId = sessionId,
                Filename = session.Filename,
                TotalChunks = session.ChunkVotes.Count,
                ChunksWithConsensus = session.ChunkVotes.Values
                    .Count(v => GetChunkConsensusInternal(v).HasConsensus),
            };

            // Verify expected hash if provided
            if (!string.IsNullOrEmpty(session.ExpectedHash))
            {
                result.ExpectedHash = session.ExpectedHash;
                result.ActualHash = actualFileHash;
                result.HashMatch = string.Equals(
                    session.ExpectedHash.ToLowerInvariant(),
                    actualFileHash.ToLowerInvariant(),
                    StringComparison.Ordinal);

                if (!result.HashMatch)
                {
                    session.State = ConsensusState.Failed;
                    result.Success = false;
                    result.Error = "File hash mismatch";
                    _logger.LogWarning(
                        "Session {Id} failed: expected {Expected}, got {Actual}",
                        sessionId,
                        LoggingSanitizer.SanitizeHash(session.ExpectedHash[..Math.Min(16, session.ExpectedHash.Length)]),
                        LoggingSanitizer.SanitizeHash(actualFileHash[..Math.Min(16, actualFileHash.Length)]));
                }
                else
                {
                    session.State = ConsensusState.Verified;
                    result.Success = true;
                }
            }
            else
            {
                session.State = ConsensusState.Completed;
                result.Success = true;
            }

            // Identify bad actors (sources that consistently disagreed with consensus)
            result.BadActors = IdentifyBadActors(session);

            return result;
        }
    }

    /// <summary>
    /// Get session info.
    /// </summary>
    public ConsensusSession? GetSession(string sessionId)
    {
        return _sessions.TryGetValue(sessionId, out var s) ? s : null;
    }

    /// <summary>
    /// Get statistics.
    /// </summary>
    public ConsensusStats GetStats()
    {
        var totalSessions = 0;
        var activeSessions = 0;
        var verifiedSessions = 0;
        var failedSessions = 0;
        var totalVotes = 0;
        foreach (var session in _sessions.Values)
        {
            totalSessions++;
            switch (session.State)
            {
                case ConsensusState.Collecting:
                    activeSessions++;
                    break;
                case ConsensusState.Verified:
                    verifiedSessions++;
                    break;
                case ConsensusState.Failed:
                    failedSessions++;
                    break;
            }

            foreach (var chunkVotes in session.ChunkVotes.Values)
            {
                totalVotes += chunkVotes.Votes.Count;
            }
        }

        return new ConsensusStats
        {
            TotalSessions = totalSessions,
            ActiveSessions = activeSessions,
            VerifiedSessions = verifiedSessions,
            FailedSessions = failedSessions,
            TotalVotes = totalVotes,
        };
    }

    private (bool HasConsensus, string? Hash) GetChunkConsensusInternal(ChunkVotes votes)
    {
        var totalVotes = votes.Votes.Count;
        if (totalVotes < MinimumSources)
        {
            return (false, null);
        }

        var (majorityHash, majorityCount) = votes.HashCounts
            .OrderByDescending(kvp => kvp.Value)
            .First();

        var requiredVotes = (totalVotes * 2 / 3) + 1;

        return (majorityCount >= requiredVotes, majorityHash);
    }

    private List<string> IdentifyBadActors(ConsensusSession session)
    {
        var dissenterCounts = new Dictionary<string, int>();

        foreach (var votes in session.ChunkVotes.Values)
        {
            var (hasConsensus, consensusHash) = GetChunkConsensusInternal(votes);

            if (hasConsensus && consensusHash != null)
            {
                foreach (var (source, hash) in votes.Votes)
                {
                    if (hash != consensusHash)
                    {
                        dissenterCounts[source] = dissenterCounts.GetValueOrDefault(source) + 1;
                    }
                }
            }
        }

        // Flag sources that disagreed with consensus on > 30% of chunks
        var threshold = session.ChunkVotes.Count * 0.3;
        return dissenterCounts
            .Where(kvp => kvp.Value > threshold)
            .OrderByDescending(kvp => kvp.Value)
            .Select(kvp => kvp.Key)
            .ToList();
    }

    private void CleanupExpired(object? state)
    {
        lock (_sessionOrder)
        {
            var now = DateTimeOffset.UtcNow;
            var queuedSessions = _sessionOrder.Count;

            // Remove expired entries and compact the queue without allocating a snapshot.
            for (var index = 0; index < queuedSessions; index++)
            {
                var sessionId = _sessionOrder.Dequeue();
                if (!_sessions.TryGetValue(sessionId, out var session))
                {
                    continue;
                }

                if (session.ExpiresAt < now)
                {
                    _sessions.TryRemove(sessionId, out _);
                    continue;
                }

                _sessionOrder.Enqueue(sessionId);
            }
        }
    }

}

/// <summary>
/// A consensus session for a file.
/// </summary>
public sealed class ConsensusSession
{
    /// <summary>Gets the session ID.</summary>
    public required string Id { get; init; }

    /// <summary>Gets the filename.</summary>
    public required string Filename { get; init; }

    /// <summary>Gets the expected file hash if known.</summary>
    public string? ExpectedHash { get; init; }

    /// <summary>Gets when created.</summary>
    public required DateTimeOffset CreatedAt { get; init; }

    /// <summary>Gets when expires.</summary>
    public required DateTimeOffset ExpiresAt { get; init; }

    /// <summary>Gets or sets the state.</summary>
    public ConsensusState State { get; set; }

    /// <summary>Gets votes per chunk.</summary>
    public Dictionary<int, ChunkVotes> ChunkVotes { get; } = new();
}

/// <summary>
/// Votes for a single chunk.
/// </summary>
public sealed class ChunkVotes
{
    /// <summary>Gets or sets the chunk index.</summary>
    public required int ChunkIndex { get; init; }

    /// <summary>Gets votes by source.</summary>
    public Dictionary<string, string> Votes { get; } = new();

    /// <summary>Gets hash counts.</summary>
    public Dictionary<string, int> HashCounts { get; } = new();
}

/// <summary>
/// Consensus session state.
/// </summary>
public enum ConsensusState
{
    /// <summary>Collecting votes.</summary>
    Collecting,

    /// <summary>Completed without verification.</summary>
    Completed,

    /// <summary>Verified against expected hash.</summary>
    Verified,

    /// <summary>Failed verification.</summary>
    Failed,
}

/// <summary>
/// Result of submitting a vote.
/// </summary>
public sealed class VoteResult
{
    /// <summary>Gets whether successful.</summary>
    public bool Success { get; init; }

    /// <summary>Gets error if failed.</summary>
    public string? Error { get; init; }

    /// <summary>Create success result.</summary>
    public static VoteResult Succeeded() => new() { Success = true };

    /// <summary>Create failure result.</summary>
    public static VoteResult Failed(string error) => new() { Success = false, Error = error };
}

/// <summary>
/// Result of consensus check.
/// </summary>
public sealed class ConsensusResult
{
    /// <summary>Gets whether consensus was reached.</summary>
    public bool HasConsensus { get; init; }

    /// <summary>Gets the majority hash if consensus reached.</summary>
    public string? MajorityHash { get; init; }

    /// <summary>Gets the majority count.</summary>
    public int MajorityCount { get; init; }

    /// <summary>Gets the total votes.</summary>
    public int TotalVotes { get; init; }

    /// <summary>Gets the agreement ratio.</summary>
    public double AgreementRatio { get; init; }

    /// <summary>Gets sources that disagreed.</summary>
    public List<string> Dissenters { get; init; } = new();

    /// <summary>Gets any message.</summary>
    public string? Message { get; init; }

    /// <summary>Create a reached consensus result.</summary>
    public static ConsensusResult Reached(
        string hash,
        int majorityCount,
        int totalVotes,
        double ratio,
        List<string> dissenters) => new()
        {
            HasConsensus = true,
            MajorityHash = hash,
            MajorityCount = majorityCount,
            TotalVotes = totalVotes,
            AgreementRatio = ratio,
            Dissenters = dissenters,
        };

    /// <summary>Create a no-consensus result.</summary>
    public static ConsensusResult NoConsensus(string message, int totalVotes, double ratio) => new()
    {
        HasConsensus = false,
        Message = message,
        TotalVotes = totalVotes,
        AgreementRatio = ratio,
    };

    /// <summary>Create an inconclusive result.</summary>
    public static ConsensusResult Inconclusive(string message, int totalVotes) => new()
    {
        HasConsensus = false,
        Message = message,
        TotalVotes = totalVotes,
    };

    /// <summary>Create a failed result.</summary>
    public static ConsensusResult Failed(string error) => new()
    {
        HasConsensus = false,
        Message = error,
    };
}

/// <summary>
/// Result of finalizing a session.
/// </summary>
public sealed class SessionResult
{
    /// <summary>Gets or sets the session ID.</summary>
    public required string SessionId { get; init; }

    /// <summary>Gets or sets the filename.</summary>
    public required string Filename { get; init; }

    /// <summary>Gets or sets whether successful.</summary>
    public bool Success { get; set; }

    /// <summary>Gets or sets any error.</summary>
    public string? Error { get; set; }

    /// <summary>Gets or sets total chunks.</summary>
    public int TotalChunks { get; init; }

    /// <summary>Gets or sets chunks with consensus.</summary>
    public int ChunksWithConsensus { get; init; }

    /// <summary>Gets or sets expected hash.</summary>
    public string? ExpectedHash { get; set; }

    /// <summary>Gets or sets actual hash.</summary>
    public string? ActualHash { get; set; }

    /// <summary>Gets or sets whether hash matched.</summary>
    public bool HashMatch { get; set; }

    /// <summary>Gets or sets identified bad actors.</summary>
    public List<string> BadActors { get; set; } = new();

    /// <summary>Create a failed result.</summary>
    public static SessionResult Failed(string error) => new()
    {
        SessionId = string.Empty,
        Filename = string.Empty,
        Success = false,
        Error = error,
    };
}

/// <summary>
/// Statistics about consensus.
/// </summary>
public sealed class ConsensusStats
{
    /// <summary>Gets total sessions.</summary>
    public int TotalSessions { get; init; }

    /// <summary>Gets active sessions.</summary>
    public int ActiveSessions { get; init; }

    /// <summary>Gets verified sessions.</summary>
    public int VerifiedSessions { get; init; }

    /// <summary>Gets failed sessions.</summary>
    public int FailedSessions { get; init; }

    /// <summary>Gets total votes.</summary>
    public long TotalVotes { get; init; }
}
