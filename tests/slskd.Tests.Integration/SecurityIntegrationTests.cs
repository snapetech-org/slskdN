// <copyright file="SecurityIntegrationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Integration;

using System;
using System.Net;
using slskd.Common.Security;
using Xunit;

/// <summary>
/// Integration tests for security components.
/// Tests the security services working together.
/// </summary>
public class SecurityIntegrationTests
{
    [Fact]
    public void NetworkGuard_BlocksExcessiveConnections()
    {
        // Arrange
        using var guard = new NetworkGuard(new Microsoft.Extensions.Logging.Abstractions.NullLogger<NetworkGuard>())
        {
            MaxConnectionsPerIp = 3,
            MaxGlobalConnections = 10,
        };

        var testIp = IPAddress.Parse("192.168.1.100");

        // Act - register max connections
        for (int i = 0; i < 3; i++)
        {
            guard.RegisterConnection(testIp);
        }

        // Assert - next connection should be blocked
        Assert.False(guard.AllowConnection(testIp));
    }

    [Fact]
    public void ViolationTracker_EscalatesBans()
    {
        // Arrange
        using var tracker = new ViolationTracker(new Microsoft.Extensions.Logging.Abstractions.NullLogger<ViolationTracker>())
        {
            ViolationsBeforeAutoBan = 3,
            BaseBanDuration = TimeSpan.FromMinutes(1),
        };

        var testIp = IPAddress.Parse("10.0.0.1");

        // Act - record violations up to threshold
        for (int i = 0; i < 3; i++)
        {
            tracker.RecordIpViolation(testIp, ViolationType.InvalidMessage);
        }

        // Assert - should be banned after threshold
        Assert.True(tracker.IsIpBanned(testIp));
    }

    [Fact]
    public void PeerReputation_TracksSuccessAndFailure()
    {
        // Arrange
        var reputation = new PeerReputation(new Microsoft.Extensions.Logging.Abstractions.NullLogger<PeerReputation>());

        // Act
        reputation.RecordSuccessfulTransfer("goodpeer", 1000000);
        reputation.RecordSuccessfulTransfer("goodpeer", 1000000);
        reputation.RecordFailedTransfer("badpeer");
        reputation.RecordFailedTransfer("badpeer");
        reputation.RecordFailedTransfer("badpeer");

        // Assert
        var goodScore = reputation.GetScore("goodpeer");
        var badScore = reputation.GetScore("badpeer");

        Assert.NotNull(goodScore);
        Assert.NotNull(badScore);
        Assert.True(goodScore > badScore);
    }

    [Fact]
    public void PathGuard_BlocksTraversal()
    {
        // Arrange
        var testRoot = Path.Combine(Path.GetTempPath(), "slskdn-security-integration-downloads");
        var maliciousPath = "../../../etc/passwd";

        // Act
        var result = PathGuard.NormalizeAndValidate(maliciousPath, testRoot);

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public void PathGuard_AllowsValidPaths()
    {
        // Arrange
        var testRoot = Path.Combine(Path.GetTempPath(), "slskdn-security-integration-downloads");
        var validPath = "music/album/track.flac";

        // Act
        var result = PathGuard.NormalizeAndValidate(validPath, testRoot);

        // Assert
        Assert.NotNull(result);
        Assert.Equal(Path.Combine(testRoot, "music", "album", "track.flac"), result);
    }

    [Fact]
    public void ContentSafety_DetectsExecutableDisguise()
    {
        // Arrange - PE/DOS executable magic bytes
        var peHeader = new byte[] { 0x4D, 0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

        // Act
        var result = ContentSafety.VerifyHeader(peHeader, ".flac");

        // Assert
        Assert.False(result.IsValid);
        Assert.Equal(ContentThreatLevel.Dangerous, result.ThreatLevel);
    }

    [Fact]
    public void ContentSafety_AcceptsValidFlac()
    {
        // Arrange - FLAC magic bytes
        var flacHeader = new byte[] { 0x66, 0x4C, 0x61, 0x43, 0x00, 0x00, 0x00, 0x00 };

        // Act
        var result = ContentSafety.VerifyHeader(flacHeader, ".flac");

        // Assert
        Assert.True(result.IsValid);
        Assert.Equal(ContentThreatLevel.Safe, result.ThreatLevel);
    }

    [Fact]
    public void SecurityServices_AssessesTrustCorrectly()
    {
        // Arrange
        var reputation = new PeerReputation(new Microsoft.Extensions.Logging.Abstractions.NullLogger<PeerReputation>());
        using var violationTracker = new ViolationTracker(new Microsoft.Extensions.Logging.Abstractions.NullLogger<ViolationTracker>());

        var services = new SecurityServices
        {
            PeerReputation = reputation,
            ViolationTracker = violationTracker,
        };

        // Set up a trusted peer
        reputation.SetScore("trusteduser", 85, "test");

        // Set up a banned peer
        violationTracker.BanUsername("banneduser", "test");

        // Act
        var trustedAssessment = services.AssessTrust("trusteduser");
        var bannedAssessment = services.AssessTrust("banneduser");
        var unknownAssessment = services.AssessTrust("unknownuser");

        // Assert
        Assert.True(trustedAssessment.IsTrusted);
        Assert.False(trustedAssessment.IsBanned);

        Assert.False(bannedAssessment.IsTrusted);
        Assert.True(bannedAssessment.IsBanned);

        Assert.False(unknownAssessment.IsTrusted);
        Assert.False(unknownAssessment.IsBanned);
    }

    [Fact]
    public void NetworkGuard_And_ViolationTracker_Integration()
    {
        // Arrange - Create both services
        using var guard = new NetworkGuard(new Microsoft.Extensions.Logging.Abstractions.NullLogger<NetworkGuard>())
        {
            MaxConnectionsPerIp = 2,
            MaxMessagesPerMinute = 5,
        };

        using var tracker = new ViolationTracker(new Microsoft.Extensions.Logging.Abstractions.NullLogger<ViolationTracker>())
        {
            ViolationsBeforeAutoBan = 2,
        };

        var attackerIp = IPAddress.Parse("10.10.10.10");

        // Act - Simulate attack: exceed connection limit
        guard.RegisterConnection(attackerIp);
        guard.RegisterConnection(attackerIp);

        // Connection blocked - record as violation
        if (!guard.AllowConnection(attackerIp))
        {
            tracker.RecordIpViolation(attackerIp, ViolationType.RateLimitExceeded);
        }

        // Another violation
        tracker.RecordIpViolation(attackerIp, ViolationType.RateLimitExceeded);

        // Assert - Should be banned after 2 violations
        Assert.True(tracker.IsIpBanned(attackerIp));
    }

    [Fact]
    public void PathGuard_And_ContentSafety_EndToEnd()
    {
        // Arrange
        var downloadRoot = "/home/user/downloads";

        // Simulate receiving a file from peer
        var peerFilename = "music/album/track.flac";
        var maliciousFilename = "../../../etc/passwd";

        // Act & Assert - Valid path should work
        var validPath = PathGuard.NormalizeAndValidate(peerFilename, downloadRoot);
        Assert.NotNull(validPath);

        // Malicious path should be blocked
        var maliciousPath = PathGuard.NormalizeAndValidate(maliciousFilename, downloadRoot);
        Assert.Null(maliciousPath);

        // Valid content should pass
        var flacHeader = new byte[] { 0x66, 0x4C, 0x61, 0x43, 0x00, 0x00, 0x00, 0x00 };
        var contentCheck = ContentSafety.VerifyHeader(flacHeader, ".flac");
        Assert.True(contentCheck.IsValid);

        // Malicious content should fail
        var peHeader = new byte[] { 0x4D, 0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
        var maliciousCheck = ContentSafety.VerifyHeader(peHeader, ".flac");
        Assert.False(maliciousCheck.IsValid);
    }

    [Fact]
    public void PeerReputation_AffectsTrustAssessment()
    {
        // Arrange
        var reputation = new PeerReputation(new Microsoft.Extensions.Logging.Abstractions.NullLogger<PeerReputation>());
        var services = new SecurityServices { PeerReputation = reputation };

        // Act - Build up reputation through successful transfers
        for (int i = 0; i < 20; i++)
        {
            reputation.RecordSuccessfulTransfer("reliablepeer", 1000000);
        }

        // Damage reputation through failures
        for (int i = 0; i < 20; i++)
        {
            reputation.RecordFailedTransfer("unreliablepeer");
        }

        // Assert
        var reliable = services.AssessTrust("reliablepeer");
        var unreliable = services.AssessTrust("unreliablepeer");

        Assert.True(reliable.IsTrusted);
        Assert.False(unreliable.IsTrusted);
    }

    [Fact]
    public void SecurityServices_AggregatesStats()
    {
        // Arrange
        using var guard = new NetworkGuard(new Microsoft.Extensions.Logging.Abstractions.NullLogger<NetworkGuard>());
        var reputation = new PeerReputation(new Microsoft.Extensions.Logging.Abstractions.NullLogger<PeerReputation>());
        using var tracker = new ViolationTracker(new Microsoft.Extensions.Logging.Abstractions.NullLogger<ViolationTracker>());

        var services = new SecurityServices
        {
            NetworkGuard = guard,
            PeerReputation = reputation,
            ViolationTracker = tracker,
        };

        // Add some data
        guard.RegisterConnection(IPAddress.Parse("1.2.3.4"));
        reputation.GetOrCreateProfile("testpeer");
        tracker.RecordIpViolation(IPAddress.Parse("5.6.7.8"), ViolationType.InvalidMessage);

        // Act
        var stats = services.GetAggregateStats();

        // Assert
        Assert.NotNull(stats);
        Assert.NotNull(stats.NetworkGuardStats);
        Assert.NotNull(stats.ReputationStats);
        Assert.NotNull(stats.ViolationStats);
        Assert.True(stats.NetworkGuardStats.TotalConnections > 0);
        Assert.True(stats.ReputationStats.TotalPeers > 0);
    }
}
