// <copyright file="EnvironmentVariableConfigurationSourceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Configuration;

using System;
using System.Collections.Generic;
using Microsoft.Extensions.Configuration;
using slskd.Configuration;
using Utility.EnvironmentVariables;
using Xunit;

public sealed class EnvironmentVariableConfigurationSourceTests
{
    [Fact]
    public void AddEnvironmentVariables_IgnoresEmptyOptionalOverrides()
    {
        const string variableName = "SLSKDN_TEST_EMPTY_BOOLEAN";
        var previousValue = Environment.GetEnvironmentVariable(variableName);

        try
        {
            Environment.SetEnvironmentVariable(variableName, string.Empty);

            var configuration = new ConfigurationBuilder()
                .AddInMemoryCollection(new Dictionary<string, string?>
                {
                    ["slskd:emptyvalue"] = "true",
                })
                .AddEnvironmentVariables(typeof(EnvironmentVariableTestOptions), "SLSKDN_TEST_")
                .Build();

            var options = new EnvironmentVariableTestOptions();
            configuration.GetSection("slskd").Bind(options);

            Assert.True(options.EmptyValue);
        }
        finally
        {
            Environment.SetEnvironmentVariable(variableName, previousValue);
        }
    }

    [Fact]
    public void AddEnvironmentVariables_PreservesNonEmptyOverrides()
    {
        const string variableName = "SLSKDN_TEST_BOOLEAN";
        var previousValue = Environment.GetEnvironmentVariable(variableName);

        try
        {
            Environment.SetEnvironmentVariable(variableName, "true");

            var configuration = new ConfigurationBuilder()
                .AddInMemoryCollection(new Dictionary<string, string?>
                {
                    ["slskd:value"] = "false",
                })
                .AddEnvironmentVariables(typeof(EnvironmentVariableTestOptions), "SLSKDN_TEST_")
                .Build();

            var options = new EnvironmentVariableTestOptions();
            configuration.GetSection("slskd").Bind(options);

            Assert.True(options.Value);
        }
        finally
        {
            Environment.SetEnvironmentVariable(variableName, previousValue);
        }
    }

    [Fact]
    public void AddEnvironmentVariables_BindsDownloadRetryAndEveryRetentionLeaf()
    {
        const string prefix = "SLSKDN_BINDING_TEST_";
        var previousValues = new Dictionary<string, string?>();

        void Set(string name, string value)
        {
            var variableName = prefix + name;
            previousValues[variableName] = Environment.GetEnvironmentVariable(variableName);
            Environment.SetEnvironmentVariable(variableName, value);
        }

        Set("DOWNLOAD_RETRY_INCOMPLETE", "overwrite");
        Set("DOWNLOAD_RETRY_PARTIAL", "resume");
        Set("DOWNLOAD_RETRY_ATTEMPTS", "3");
        Set("DOWNLOAD_RETRY_DELAY", "1250");
        Set("DOWNLOAD_RETRY_MAX_DELAY", "8000");
        Set("DOWNLOAD_DESTINATION_SUBDIRECTORY", "${SOURCE_USERNAME}/${SOURCE_PATH}");
        Set("DOWNLOAD_DESTINATION_EXISTS", "overwrite");
        Set("DOWNLOAD_DESTINATION_PERMISSIONS_MODE", "0750");
        Set("RETENTION_SEARCH", "90");
        Set("RETENTION_EVENTS", "21");
        Set("RETENTION_EVENTS_MAX_COUNT", "7500");
        Set("RETENTION_TRANSFERS_REMOVED", "1440");
        Set("RETENTION_TRANSFERS_UPLOAD_SUCCEEDED", "60");
        Set("RETENTION_TRANSFERS_UPLOAD_ERRORED", "70");
        Set("RETENTION_TRANSFERS_UPLOAD_CANCELLED", "80");
        Set("RETENTION_TRANSFERS_DOWNLOAD_SUCCEEDED", "90");
        Set("RETENTION_TRANSFERS_DOWNLOAD_ERRORED", "100");
        Set("RETENTION_TRANSFERS_DOWNLOAD_CANCELLED", "110");
        Set("RETENTION_FILES_COMPLETE", "120");
        Set("RETENTION_FILES_INCOMPLETE", "130");
        Set("RETENTION_LOGS", "15");

        try
        {
            var configuration = new ConfigurationBuilder()
                .AddEnvironmentVariables(typeof(slskd.Options), prefix)
                .Build();
            var options = new slskd.Options();
            configuration.GetSection("slskd").Bind(options);

            Assert.Equal("overwrite", options.Global.Download.Retry.Incomplete);
            Assert.Equal("resume", options.Global.Download.Retry.Partial);
            Assert.Equal("resume", options.Global.Download.Retry.Partial ?? options.Global.Download.Retry.Incomplete);
            Assert.Equal(3, options.Global.Download.Retry.Attempts);
            Assert.Equal(1250, options.Global.Download.Retry.Delay);
            Assert.Equal(8000, options.Global.Download.Retry.MaxDelay);
            Assert.Equal("${SOURCE_USERNAME}/${SOURCE_PATH}", options.Global.Download.Destination.Subdirectory);
            Assert.Equal("overwrite", options.Global.Download.Destination.Exists);
            Assert.Equal("0750", options.Global.Download.Destination.Permissions.Mode);
            Assert.Equal(90, options.Retention.Search);
            Assert.Equal(21, options.Retention.Events);
            Assert.Equal(7500, options.Retention.EventsMaxCount);
            Assert.Equal(1440, options.Retention.Transfers.Removed);
            Assert.Equal(60, options.Retention.Transfers.Upload.Succeeded);
            Assert.Equal(70, options.Retention.Transfers.Upload.Errored);
            Assert.Equal(80, options.Retention.Transfers.Upload.Cancelled);
            Assert.Equal(90, options.Retention.Transfers.Download.Succeeded);
            Assert.Equal(100, options.Retention.Transfers.Download.Errored);
            Assert.Equal(110, options.Retention.Transfers.Download.Cancelled);
            Assert.Equal(120, options.Retention.Files.Complete);
            Assert.Equal(130, options.Retention.Files.Incomplete);
            Assert.Equal(15, options.Retention.Logs);
        }
        finally
        {
            foreach (var (name, value) in previousValues)
            {
                Environment.SetEnvironmentVariable(name, value);
            }
        }
    }

    [Fact]
    public void AddCommandLine_BindsDownloadRetryAndRetentionOptions()
    {
        var configuration = new ConfigurationBuilder()
            .AddCommandLine(
                typeof(slskd.Options),
                commandLine: "slskdn --download-retry-attempts 4 --download-retry-partial resume --download-retry-incomplete overwrite --download-destination-subdirectory ${SOURCE_USERNAME}/${SOURCE_PATH} --download-destination-exists overwrite --download-destination-permissions-mode 0750 --retention-search 120 --retention-events-max-count 9000 --retention-transfers-upload-succeeded 60 --retention-transfers-download-errored 180 --retention-files-complete 240 --retention-logs 30")
            .Build();
        var options = new slskd.Options();
        configuration.GetSection("slskd").Bind(options);

        Assert.Equal("overwrite", options.Global.Download.Retry.Incomplete);
        Assert.Equal("resume", options.Global.Download.Retry.Partial);
        Assert.Equal("resume", options.Global.Download.Retry.Partial ?? options.Global.Download.Retry.Incomplete);
        Assert.Equal("${SOURCE_USERNAME}/${SOURCE_PATH}", options.Global.Download.Destination.Subdirectory);
        Assert.Equal("overwrite", options.Global.Download.Destination.Exists);
        Assert.Equal("0750", options.Global.Download.Destination.Permissions.Mode);
        Assert.Equal(4, options.Global.Download.Retry.Attempts);
        Assert.Equal(120, options.Retention.Search);
        Assert.Equal(9000, options.Retention.EventsMaxCount);
        Assert.Equal(60, options.Retention.Transfers.Upload.Succeeded);
        Assert.Equal(180, options.Retention.Transfers.Download.Errored);
        Assert.Equal(240, options.Retention.Files.Complete);
        Assert.Equal(30, options.Retention.Logs);
    }

    private sealed class EnvironmentVariableTestOptions
    {
        [EnvironmentVariable("EMPTY_BOOLEAN")]
        public bool EmptyValue { get; init; }

        [EnvironmentVariable("BOOLEAN")]
        public bool Value { get; init; }
    }
}
