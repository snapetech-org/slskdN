// <copyright file="SecurityStatsAggregationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Common.Security;

using System;
using System.Linq;
using System.Net;
using Microsoft.Extensions.Logging.Abstractions;
using slskd.Common.Security;
using Xunit;

[Collection(AllocationTestCollection.Name)]
public class SecurityStatsAggregationTests
{
    [Fact]
    public void CryptographicCommitment_CreateCommitment_WidePopulationBoundsAllocation()
    {
        using var commitments = new CryptographicCommitment();
        var fileHash = new string('A', 64);

        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();

        var before = GC.GetAllocatedBytesForCurrentThread();
        for (var index = 0; index < CryptographicCommitment.MaxCommitments; index++)
        {
            _ = commitments.CreateCommitment(fileHash, "peer", "track.flac");
        }

        var allocated = GC.GetAllocatedBytesForCurrentThread() - before;
        Assert.Equal(CryptographicCommitment.MaxCommitments, commitments.GetStats().TotalCommitments);
        Assert.InRange(allocated, 0, 12_000_000);
    }

    [Fact]
    public void SecurityEventsAndCanaries_GetStats_ReturnExactAggregates()
    {
        using var events = new SecurityEventAggregator(NullLogger<SecurityEventAggregator>.Instance);
        events.Report(CreateEvent(SecuritySeverity.Critical, "198.51.100.1", "alice"));
        events.Report(CreateEvent(SecuritySeverity.High, "198.51.100.1", "alice"));
        events.Report(CreateEvent(SecuritySeverity.Medium, "198.51.100.2", "bob", DateTimeOffset.UtcNow.AddHours(-2)));
        events.Report(CreateEvent(SecuritySeverity.Low, null, null));

        var eventStats = events.GetStats();

        Assert.Equal(4, eventStats.TotalEvents);
        Assert.Equal(3, eventStats.EventsLastHour);
        Assert.Equal(1, eventStats.CriticalEvents);
        Assert.Equal(1, eventStats.HighEvents);
        Assert.Equal(1, eventStats.MediumEvents);
        Assert.Equal(1, eventStats.LowEvents);
        Assert.Equal(2, eventStats.UniqueIps);
        Assert.Equal(2, eventStats.UniqueUsers);

        var canaries = new CanaryTraps(NullLogger<CanaryTraps>.Instance, new byte[32]);
        var first = canaries.GenerateCanary("alice", "one.flac");
        var second = canaries.GenerateCanary("alice", "two.flac");
        canaries.GenerateCanary("bob", "three.flac");
        canaries.ReportSighting(first.CanaryId, "first");
        canaries.ReportSighting(first.CanaryId, "second");
        canaries.ReportSighting(second.CanaryId, "third");

        var canaryStats = canaries.GetStats();

        Assert.Equal(3, canaryStats.TotalCanaries);
        Assert.Equal(2, canaryStats.CanariesWithSightings);
        Assert.Equal(3, canaryStats.TotalSightings);
        Assert.Equal(2, canaryStats.UniqueUsersTracked);
    }

    [Fact]
    public void SessionCollectors_GetStats_ReturnExactAggregates()
    {
        using var consensus = new ByzantineConsensus(NullLogger<ByzantineConsensus>.Instance);
        var finalizedConsensus = consensus.StartSession("one.flac", "expected");
        consensus.SubmitVote(finalizedConsensus, "alice", 0, "chunk");
        consensus.SubmitVote(finalizedConsensus, "bob", 0, "chunk");
        consensus.FinalizeSession(finalizedConsensus, "expected");
        consensus.StartSession("two.flac");

        var consensusStats = consensus.GetStats();

        Assert.Equal(2, consensusStats.TotalSessions);
        Assert.Equal(1, consensusStats.ActiveSessions);
        Assert.Equal(1, consensusStats.VerifiedSessions);
        Assert.Equal(0, consensusStats.FailedSessions);
        Assert.Equal(2, consensusStats.TotalVotes);

        using var verification = new ProbabilisticVerification(NullLogger<ProbabilisticVerification>.Instance);
        var finalizedVerification = verification.StartSession("one.flac", 10, 0.2);
        var selectedChunks = finalizedVerification.SelectedChunks.Take(2).ToArray();
        verification.RecordResult(finalizedVerification.Id, selectedChunks[0], "same", "same");
        verification.RecordResult(finalizedVerification.Id, selectedChunks[1], "expected", "actual");
        verification.FinalizeSession(finalizedVerification.Id);
        verification.StartSession("two.flac", 10, 0.4);

        var verificationStats = verification.GetStats();

        Assert.Equal(2, verificationStats.TotalSessions);
        Assert.Equal(1, verificationStats.ActiveSessions);
        Assert.Equal(2, verificationStats.TotalChunksVerified);
        Assert.Equal(1, verificationStats.TotalChunksPassed);
        Assert.Equal(1, verificationStats.TotalChunksFailed);
        Assert.Equal(0.3, verificationStats.AverageSampleRate, 10);
    }

    [Fact]
    public void PeerAndNetworkCollectors_GetStats_ReturnExactAggregates()
    {
        var disclosure = new AsymmetricDisclosure(NullLogger<AsymmetricDisclosure>.Instance);
        disclosure.RecordPositiveInteraction("alice", InteractionType.SuccessfulTransfer, 5);
        disclosure.RecordNegativeInteraction("bob", InteractionType.ProtocolViolation, 2);

        var disclosureStats = disclosure.GetStats();

        Assert.Equal(2, disclosureStats.TotalPeers);
        Assert.Equal(1, disclosureStats.UnknownPeers);
        Assert.Equal(1, disclosureStats.BasicPeers);
        Assert.Equal(5, disclosureStats.TotalPositiveInteractions);
        Assert.Equal(2, disclosureStats.TotalNegativeInteractions);

        using var temporal = new TemporalConsistency();
        temporal.RecordMetadata("alice", "one.flac", Metadata("first"));
        temporal.RecordMetadata("alice", "one.flac", Metadata("second"));
        temporal.RecordMetadata("bob", "two.flac", Metadata("stable"));

        var temporalStats = temporal.GetStats();

        Assert.Equal(2, temporalStats.TrackedFiles);
        Assert.Equal(2, temporalStats.TrackedPeers);
        Assert.Equal(1, temporalStats.TotalChangesRecorded);
        Assert.Equal(1, temporalStats.SuspiciousChanges);
        Assert.Equal(0, temporalStats.SuspiciousPeers);

        using var honeypot = new Honeypot(NullLogger<Honeypot>.Instance);
        var firstIp = IPAddress.Parse("198.51.100.10");
        honeypot.RecordInteraction(firstIp, "alice", HoneypotAction.Browse, Honeypot.GenerateHoneypotPath(DecoyType.ConfigFile));
        honeypot.RecordInteraction(firstIp, "alice", HoneypotAction.Download, Honeypot.GenerateHoneypotPath(DecoyType.CredentialFile));
        honeypot.RecordInteraction(IPAddress.Parse("198.51.100.11"), null, HoneypotAction.Search, "ordinary.flac");

        var honeypotStats = honeypot.GetStats();

        Assert.Equal(3, honeypotStats.TotalInteractions);
        Assert.Equal(1, honeypotStats.TotalThreats);
        Assert.Equal(1, honeypotStats.HighThreats);
        Assert.Equal(0, honeypotStats.CriticalThreats);
        Assert.Equal(3, honeypotStats.EventCount);
        Assert.Equal(1, honeypotStats.InteractionsByType[nameof(DecoyType.ConfigFile)]);
        Assert.Equal(1, honeypotStats.InteractionsByType[nameof(DecoyType.CredentialFile)]);
        Assert.Equal(1, honeypotStats.InteractionsByType[nameof(DecoyType.Unknown)]);

        using var fingerprint = new FingerprintDetection(NullLogger<FingerprintDetection>.Instance);
        var scannerIp = IPAddress.Parse("198.51.100.20");
        for (var index = 0; index < 4; index++)
        {
            fingerprint.RecordConnection(scannerIp, 5000 + index, $"v{index}", $"agent-{index}", succeeded: false);
        }

        fingerprint.RecordAnomalousRequest(scannerIp, "probe", "test");
        var fingerprintStats = fingerprint.GetStats();

        Assert.Equal(1, fingerprintStats.TrackedIps);
        Assert.Equal(1, fingerprintStats.KnownScanners);
        Assert.Equal(4, fingerprintStats.TotalConnectionAttempts);
        Assert.Equal(1, fingerprintStats.TotalAnomalousRequests);
    }

    [Fact]
    public void CryptographicCommitment_GetStats_WidePopulationBoundsAllocation()
    {
        using var commitments = new CryptographicCommitment();
        var fileHash = new string('a', 64);
        for (var index = 0; index < CryptographicCommitment.MaxCommitments; index++)
        {
            var result = commitments.CreateCommitment(fileHash, "peer", $"track-{index:D5}.flac");
            commitments.GetCommitment(result.CommitmentId)!.State = (CommitmentState)(index % 5);
        }

        for (var iteration = 0; iteration < 8; iteration++)
        {
            _ = commitments.GetStats();
        }

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var stats = commitments.GetStats();
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(10_000, stats.TotalCommitments);
        Assert.Equal(2_000, stats.PendingCommitments);
        Assert.Equal(2_000, stats.VerifiedCommitments);
        Assert.Equal(2_000, stats.FailedCommitments);
        Assert.Equal(2_000, stats.ExpiredCommitments);
        Assert.True(allocatedBytes < 1_024, $"Allocated {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public void ProofOfStorage_GetStats_WidePopulationBoundsAllocation()
    {
        using var challenges = new ProofOfStorage();
        string? oldestChallengeId = null;
        for (var index = 0; index < ProofOfStorage.MaxPendingChallenges; index++)
        {
            var result = challenges.CreateChallenge($"track-{index:D4}.flac", 10_000, "peer");
            if (index == 0)
            {
                oldestChallengeId = result.ChallengeId;
                System.Threading.Thread.Sleep(1);
            }

            challenges.GetChallenge(result.ChallengeId)!.State = (ChallengeState)(index % 5);
        }

        for (var iteration = 0; iteration < 8; iteration++)
        {
            _ = challenges.GetStats();
        }

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var stats = challenges.GetStats();
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

        Assert.Equal(1_000, stats.TotalChallenges);
        Assert.Equal(200, stats.PendingChallenges);
        Assert.Equal(200, stats.VerifiedChallenges);
        Assert.Equal(200, stats.FailedChallenges);
        Assert.Equal(200, stats.ExpiredChallenges);
        Assert.True(allocatedBytes < 1_024, $"Allocated {allocatedBytes:N0} bytes.");

        _ = challenges.CreateChallenge("overflow.flac", 10_000, "peer");
        Assert.Null(challenges.GetChallenge(oldestChallengeId!));
        for (var iteration = 0; iteration < 8; iteration++)
        {
            _ = challenges.CreateChallenge($"warm-{iteration}.flac", 10_000, "peer");
        }

        allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        _ = challenges.CreateChallenge("measured.flac", 10_000, "peer");
        allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;
        Assert.True(allocatedBytes < 2_048, $"Overflow allocated {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public void SecuritySessions_FullCapacityOverflowBoundsAllocation()
    {
        using var consensus = new ByzantineConsensus(NullLogger<ByzantineConsensus>.Instance);
        var oldestConsensusId = consensus.StartSession("oldest.flac");
        System.Threading.Thread.Sleep(1);
        for (var index = 1; index < ByzantineConsensus.MaxSessions; index++)
        {
            _ = consensus.StartSession($"consensus-{index:D4}.flac");
        }

        _ = consensus.StartSession("overflow.flac");
        Assert.Null(consensus.GetSession(oldestConsensusId));
        for (var iteration = 0; iteration < 8; iteration++)
        {
            _ = consensus.StartSession($"warm-{iteration}.flac");
        }

        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        _ = consensus.StartSession("measured.flac");
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;
        Assert.True(allocatedBytes < 1_536, $"Consensus overflow allocated {allocatedBytes:N0} bytes.");

        using var verification = new ProbabilisticVerification(NullLogger<ProbabilisticVerification>.Instance);
        var oldestVerificationId = verification.StartSession("oldest.flac", 1, 1).Id;
        System.Threading.Thread.Sleep(1);
        for (var index = 1; index < ProbabilisticVerification.MaxSessions; index++)
        {
            _ = verification.StartSession($"verification-{index:D4}.flac", 1, 1);
        }

        _ = verification.StartSession("overflow.flac", 1, 1);
        Assert.Null(verification.GetSession(oldestVerificationId));
        for (var iteration = 0; iteration < 8; iteration++)
        {
            _ = verification.StartSession($"warm-{iteration}.flac", 1, 1);
        }

        allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        _ = verification.StartSession("measured.flac", 1, 1);
        allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;
        Assert.True(allocatedBytes < 2_048, $"Verification overflow allocated {allocatedBytes:N0} bytes.");
    }

    [Fact]
    public void VerificationSessions_ConcurrentCreationRemainsBounded()
    {
        using var verification = new ProbabilisticVerification(NullLogger<ProbabilisticVerification>.Instance);
        var sessionIds = new string[ProbabilisticVerification.MaxSessions + 100];

        System.Threading.Tasks.Parallel.For(
            0,
            sessionIds.Length,
            index => sessionIds[index] = verification.StartSession($"parallel-{index}.flac", 1, 1).Id);

        var retainedSessions = 0;
        foreach (var sessionId in sessionIds)
        {
            if (verification.GetSession(sessionId) != null)
            {
                retainedSessions++;
            }
        }

        Assert.Equal(ProbabilisticVerification.MaxSessions, retainedSessions);
    }

    [Fact]
    public void SecuritySessions_ConcurrentCreationRemainsBounded()
    {
        using var consensus = new ByzantineConsensus(NullLogger<ByzantineConsensus>.Instance);
        var sessionIds = new string[ByzantineConsensus.MaxSessions + 100];

        System.Threading.Tasks.Parallel.For(
            0,
            sessionIds.Length,
            index => sessionIds[index] = consensus.StartSession($"parallel-{index}.flac"));

        var retainedSessions = 0;
        foreach (var sessionId in sessionIds)
        {
            if (consensus.GetSession(sessionId) != null)
            {
                retainedSessions++;
            }
        }

        Assert.Equal(ByzantineConsensus.MaxSessions, retainedSessions);
    }

    private static SecurityEvent CreateEvent(
        SecuritySeverity severity,
        string? ipAddress,
        string? username,
        DateTimeOffset? timestamp = null)
    {
        return new SecurityEvent
        {
            Type = SecurityEventType.Other,
            Severity = severity,
            Message = "test",
            Timestamp = timestamp ?? DateTimeOffset.UtcNow,
            IpAddress = ipAddress,
            Username = username,
        };
    }

    private static FileMetadata Metadata(string hash)
    {
        return new FileMetadata
        {
            Size = 100,
            Hash = hash,
            Bitrate = 320,
            Duration = 180,
            SampleRate = 44100,
            Codec = "FLAC",
        };
    }
}
