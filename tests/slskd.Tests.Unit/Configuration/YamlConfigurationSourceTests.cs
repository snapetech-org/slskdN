// <copyright file="YamlConfigurationSourceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Configuration;

using System;
using System.IO;
using System.Linq;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.FileProviders;
using slskd;
using slskd.Configuration;
using Xunit;

public class YamlConfigurationSourceTests
{
    [Fact]
    public void ShippedExample_AcceptsAppendedLiveConfiguration()
    {
        var examplePath = FindRepositoryFile("config", "slskd.example.yml");
        var yaml = File.ReadAllText(examplePath) + """

            feature:
              Mesh: false
              Dht: false
              Pods: false
            dht:
              enabled: false
            """;

        var options = ReadOptions(yaml);

        Assert.False(options.Feature.Mesh);
        Assert.False(options.Feature.Dht);
        Assert.False(options.Feature.Pods);
        Assert.False(options.DhtRendezvous.Enabled);
    }

    [Fact]
    public void ShippedExample_AcceptsSectionsUncommentedByRemovingHashMarker()
    {
        var examplePath = FindRepositoryFile("config", "slskd.example.yml");
        var yaml = File.ReadAllText(examplePath)
            .Replace("#feature:", "feature:", StringComparison.Ordinal)
            .Replace("#  Mesh: true", "  Mesh: true", StringComparison.Ordinal)
            .Replace("#  Dht: true", "  Dht: true", StringComparison.Ordinal)
            .Replace("#  Pods: true", "  Pods: true", StringComparison.Ordinal);

        var options = ReadOptions(yaml);

        Assert.True(options.Feature.Mesh);
        Assert.True(options.Feature.Dht);
        Assert.True(options.Feature.Pods);
    }

    [Fact]
    public void AddYamlFile_BindsPublicDhtAliasToDhtRendezvousOptions()
    {
        var options = ReadOptions("""
            dht:
              enabled: true
              lan_only: true
              dht_port: 50406
            """);

        Assert.True(options.DhtRendezvous.Enabled);
        Assert.True(options.DhtRendezvous.LanOnly);
        Assert.Equal(50406, options.DhtRendezvous.DhtPort);
    }

    [Fact]
    public void AddYamlFile_StillBindsInternalDhtRendezvousKey()
    {
        var options = ReadOptions("""
            dhtRendezvous:
              enabled: false
            """);

        Assert.False(options.DhtRendezvous.Enabled);
    }

    [Fact]
    public void AddYamlFile_BindsLanDiscoveryAdvertisingSetting()
    {
        var options = ReadOptions("""
            lan_discovery:
              advertise: true
            """);

        Assert.True(options.LanDiscovery.Advertise);
    }

    [Fact]
    public void AddYamlFile_BindsTransfersAliasToGlobalOptions()
    {
        var options = ReadOptions("""
            transfers:
              upload:
                slots: 3
              download:
                retry:
                  attempts: 4
            """);

        Assert.Equal(3, options.Global.Upload.Slots);
        Assert.Equal(4, options.Global.Download.Retry.Attempts);
    }

    [Fact]
    public void AddYamlFile_BindsDownloadDestinationPolicyAndTemplate()
    {
        var options = ReadOptions("""
            global:
              download:
                destination:
                  subdirectory: '${SOURCE_USERNAME}/${SOURCE_PATH}'
                  exists: overwrite
                  permissions:
                    mode: '0750'
            """);

        Assert.Equal("${SOURCE_USERNAME}/${SOURCE_PATH}", options.Global.Download.Destination.Subdirectory);
        Assert.Equal("overwrite", options.Global.Download.Destination.Exists);
        Assert.Equal("0750", options.Global.Download.Destination.Permissions.Mode);
    }

    [Fact]
    public void AddYamlFile_BindsUpstreamStyleTransferUploadLimitsToGlobalLimits()
    {
        var options = ReadOptions("""
            transfers:
              upload:
                limits:
                  queued:
                    files: 12
                  weekly:
                    megabytes: 4096
            """);

        Assert.Equal(12, options.Global.Limits.Queued.Files);
        Assert.Equal(4096, options.Global.Limits.Weekly.Megabytes);
    }

    [Fact]
    public void AddYamlFile_BindsTransfersGroupsToCurrentGroupOptions()
    {
        var options = ReadOptions("""
            transfers:
              groups:
                default:
                  upload:
                    slots: 7
                    limits:
                      daily:
                        files: 25
                user_defined:
                  friends:
                    members:
                      - alice
                    upload:
                      allowed_file_types:
                        - .flac
            """);

        Assert.Equal(7, options.Groups.Default.Upload.Slots);
        Assert.Equal(25, options.Groups.Default.Limits.Daily.Files);
        Assert.Equal(new[] { "alice" }, options.Groups.UserDefined["friends"].Members);
        Assert.Equal(new[] { ".flac" }, options.Groups.UserDefined["friends"].Upload.AllowedFileTypes);
    }

    [Fact]
    public void AddYamlFile_BindsIntegrationsAliasToIntegrationOptions()
    {
        var options = ReadOptions("""
            integrations:
              musicBrainz:
                base_url: https://musicbrainz.example.invalid
            """);

        Assert.Equal("https://musicbrainz.example.invalid", options.Integration.MusicBrainz.BaseUrl);
    }

    [Fact]
    public void AddYamlFile_BindsGroupLimitsNestedUnderUpload()
    {
        var options = ReadOptions("""
            groups:
              default:
                upload:
                  limits:
                    queued:
                      files: 2
              user_defined:
                friends:
                  upload:
                    limits:
                      daily:
                        megabytes: 512
            """);

        Assert.Equal(2, options.Groups.Default.Limits.Queued.Files);
        Assert.Equal(512, options.Groups.UserDefined["friends"].Limits.Daily.Megabytes);
    }

    [Fact]
    public void Reload_RemovesStaleSequenceKeys()
    {
        var directory = Path.Combine(Path.GetTempPath(), "slskd-yaml-reload-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);

        try
        {
            var path = Path.Combine(directory, "slskd.yml");
            File.WriteAllText(path, """
                rooms:
                  - alpha
                  - beta
                """);

            using var provider = new PhysicalFileProvider(directory);
            var configuration = new ConfigurationBuilder()
                .AddYamlFile(
                    path: Path.GetFileName(path),
                    targetType: typeof(Options),
                    optional: false,
                    provider: provider)
                .Build();

            var initial = new Options();
            configuration.GetSection("slskd").Bind(initial, o => { o.BindNonPublicProperties = true; });
            Assert.Equal(new[] { "alpha", "beta" }, initial.Rooms);

            File.WriteAllText(path, """
                rooms:
                  - gamma
                """);

            ((IConfigurationRoot)configuration).Reload();

            var reloaded = new Options();
            configuration.GetSection("slskd").Bind(reloaded, o => { o.BindNonPublicProperties = true; });
            Assert.Equal(new[] { "gamma" }, reloaded.Rooms);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static Options ReadOptions(string yaml)
    {
        var directory = Path.Combine(Path.GetTempPath(), "slskd-yaml-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);

        try
        {
            var path = Path.Combine(directory, "slskd.yml");
            File.WriteAllText(path, yaml);

            using var provider = new PhysicalFileProvider(directory);
            var configuration = new ConfigurationBuilder()
                .AddYamlFile(
                    path: Path.GetFileName(path),
                    targetType: typeof(Options),
                    optional: false,
                    provider: provider)
                .Build();

            var options = new Options();
            configuration.GetSection("slskd").Bind(options, o => { o.BindNonPublicProperties = true; });
            return options;
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static string FindRepositoryFile(params string[] pathSegments)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var candidate = Path.Combine(new[] { directory.FullName }.Concat(pathSegments).ToArray());
            if (File.Exists(candidate))
            {
                return candidate;
            }

            directory = directory.Parent;
        }

        throw new FileNotFoundException($"Repository file was not found: {Path.Combine(pathSegments)}");
    }
}
