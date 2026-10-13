// <copyright file="SoulseekOptionsValidationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit;

using System.ComponentModel.DataAnnotations;
using System.Linq;
using slskd.Shares;
using Xunit;

public class SoulseekOptionsValidationTests
{
    [Fact]
    public void Options_RejectsLoopbackSoulseekListenAddress_WhenConnecting()
    {
        var options = new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                ListenIpAddress = "127.0.0.1",
            },
            Flags = new Options.FlagsOptions
            {
                NoConnect = false,
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.Contains(
            results,
            result => result.ErrorMessage!.Contains(
                "Soulseek.ListenIpAddress must not be a loopback address",
                System.StringComparison.Ordinal));
    }

    [Fact]
    public void Options_AllowsLoopbackSoulseekListenAddress_WhenNoConnectIsEnabled()
    {
        var options = new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                ListenIpAddress = "127.0.0.1",
            },
            Flags = new Options.FlagsOptions
            {
                NoConnect = true,
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.DoesNotContain(
            results,
            result => result.ErrorMessage?.Contains(
                "Soulseek.ListenIpAddress must not be a loopback address",
                System.StringComparison.Ordinal) == true);
    }

    [Fact]
    public void Options_RejectsObfuscationListenPortThatMatchesRegularListenPort()
    {
        var options = new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                ListenPort = 50300,
                Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
                {
                    Enabled = true,
                    ListenPort = 50300,
                },
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.Contains(
            results,
            result => result.ErrorMessage!.Contains(
                "dedicated listen port different from soulseek.listen_port",
                System.StringComparison.Ordinal));
    }

    [Fact]
    public void Options_RejectsObfuscationOnlyModeWithoutExplicitDedicatedPort()
    {
        var options = new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
                {
                    Enabled = true,
                    Mode = SoulseekObfuscationMode.Only.ToString(),
                    ListenPort = 0,
                    AdvertiseRegularPort = false,
                },
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        AssertRejectsUnsupportedOnlyMode(results);
    }

    [Fact]
    public void Options_RejectsObfuscationOnlyModeWithRegularFallback()
    {
        var options = new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
                {
                    Enabled = true,
                    Mode = SoulseekObfuscationMode.Only.ToString(),
                    ListenPort = 50301,
                    AdvertiseRegularPort = true,
                },
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        AssertRejectsUnsupportedOnlyMode(results);
    }

    [Fact]
    public void Options_RejectsEnabledObfuscationWithoutRegularPortAdvertisement()
    {
        var options = new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
                {
                    Enabled = true,
                    Mode = SoulseekObfuscationMode.Compatibility.ToString(),
                    AdvertiseRegularPort = false,
                },
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.Contains(
            results,
            result => result.ErrorMessage!.Contains(
                "regular peer port to remain advertised",
                System.StringComparison.Ordinal));
    }

    [Fact]
    public void SoulseekObfuscationPlan_ReportsConfiguredActiveRuntime()
    {
        var plan = SoulseekObfuscationSupport.BuildPlan(new Options.SoulseekOptions
        {
            ListenPort = 50300,
            Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
            {
                Enabled = true,
                Mode = SoulseekObfuscationMode.Prefer.ToString(),
                ListenPort = 50301,
            },
        });

        Assert.True(plan.Enabled);
        Assert.Equal("prefer", plan.Mode);
        Assert.Equal(1, plan.Type);
        Assert.Equal(50301, plan.EffectiveListenPort);
        Assert.Equal(["P", "D", "F"], plan.SupportedConnectionTypes);
        Assert.True(plan.RuntimeSupported);
        Assert.Equal("active", plan.RuntimeState);
        Assert.Contains("peer/distributed/transfer", plan.Summary);
    }

    [Fact]
    public void SoulseekObfuscationPlan_CompatibilityModeDoesNotPreferOutbound()
    {
        var plan = SoulseekObfuscationSupport.BuildPlan(new Options.SoulseekOptions
        {
            ListenPort = 50300,
            Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
            {
                Enabled = true,
                Mode = SoulseekObfuscationMode.Compatibility.ToString(),
                PreferOutbound = true,
            },
        });

        var runtime = SoulseekObfuscationSupport.BuildRuntimeOptions(new Options.SoulseekOptions
        {
            ListenPort = 50300,
            Obfuscation = new Options.SoulseekOptions.ObfuscationOptions
            {
                Enabled = true,
                Mode = SoulseekObfuscationMode.Compatibility.ToString(),
                PreferOutbound = true,
            },
        });

        Assert.False(plan.PreferOutbound);
        Assert.False(runtime.PreferOutbound);
    }

    private static void AssertRejectsUnsupportedOnlyMode(
        System.Collections.Generic.IReadOnlyCollection<ValidationResult> results)
    {
        Assert.Contains(
            results,
            result => result.ErrorMessage!.Contains(
                "obfuscation only mode is not currently supported",
                System.StringComparison.Ordinal));
    }

    [Fact]
    public void Options_RejectsMissingStableDhtPort_WhenDhtRendezvousIsEnabled()
    {
        var options = new Options
        {
            DhtRendezvous = new slskd.DhtRendezvous.DhtRendezvousOptions
            {
                Enabled = true,
                DhtPort = 0,
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.Contains(
            results,
            result => result.ErrorMessage!.Contains(
                "DHT rendezvous requires an explicit UDP port",
                System.StringComparison.Ordinal));
    }

    [Fact]
    public void Options_RejectsMissingBootstrapRouters_WhenDhtRendezvousIsEnabled()
    {
        var options = new Options
        {
            DhtRendezvous = new slskd.DhtRendezvous.DhtRendezvousOptions
            {
                Enabled = true,
                DhtPort = 50306,
                BootstrapRouters = [],
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.Contains(
            results,
            result => result.ErrorMessage!.Contains(
                "DHT rendezvous requires at least one bootstrap router",
                System.StringComparison.Ordinal));
    }

    [Fact]
    public void Options_AllowsStableDhtPortAndBootstrapRouters_WhenDhtRendezvousIsEnabled()
    {
        var options = new Options
        {
            DhtRendezvous = new slskd.DhtRendezvous.DhtRendezvousOptions
            {
                Enabled = true,
                DhtPort = 50306,
                BootstrapRouters =
                [
                    "router.bittorrent.com",
                    "router.utorrent.com",
                    "dht.transmissionbt.com",
                ],
            },
        };

        var results = options.Validate(new ValidationContext(options)).ToList();

        Assert.DoesNotContain(
            results,
            result => result.ErrorMessage?.Contains(
                "DHT rendezvous requires an explicit UDP port",
                System.StringComparison.Ordinal) == true);
        Assert.DoesNotContain(
            results,
            result => result.ErrorMessage?.Contains(
                "DHT rendezvous requires at least one bootstrap router",
                System.StringComparison.Ordinal) == true);
    }

    [Fact]
    public void SharesOptions_AllowsClosingBracketInAliasedLocalPath()
    {
        var localDirectory = Path.Combine(Path.GetTempPath(), $"music]archive-{Guid.NewGuid():N}");
        Directory.CreateDirectory(localDirectory);

        try
        {
            var options = new Options.SharesOptions
            {
                Directories = new[] { $"[music]{localDirectory}" },
            };

            var results = options.Validate(new ValidationContext(options)).ToList();

            Assert.Empty(results);
        }
        finally
        {
            Directory.Delete(localDirectory, recursive: true);
        }
    }

    [Theory]
    [InlineData("[music]/tmp/music]archive", "music", "/tmp/music]archive", false)]
    [InlineData("-[music]/tmp/music]archive", "music", "/tmp/music]archive", true)]
    [InlineData("![music]/tmp/music]archive", "music", "/tmp/music]archive", true)]
    public void Share_UsesFirstClosingBracketAsAliasDelimiter(
        string raw,
        string expectedAlias,
        string expectedPath,
        bool expectedExcluded)
    {
        var share = new Share(raw);

        Assert.Equal(raw, share.Raw);
        Assert.Equal(expectedAlias, share.Alias);
        Assert.Equal(expectedPath, share.LocalPath);
        Assert.Equal(expectedAlias, share.RemotePath);
        Assert.Equal(expectedExcluded, share.IsExcluded);
    }

    [Fact]
    public void Share_DerivesUnaliasedDirectoryNameIncludingClosingBracket()
    {
        var share = new Share("/tmp/music]archive");

        Assert.Equal("music]archive", share.Alias);
        Assert.Equal("/tmp/music]archive", share.LocalPath);
        Assert.Equal("music]archive", share.RemotePath);
    }
}
