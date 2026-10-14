// <copyright file="TwoNodeMeshFullInstanceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Integration.DhtRendezvous;

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Logging;
using slskd.Common.Security.API;
using slskd.DhtRendezvous.API;
using slskd.DhtRendezvous.Security;
using slskd.Mesh;
using slskd.Shares;
using slskd.Tests.Integration.Harness;
using Xunit;

[Trait("Category", "L2-Integration")]
[Trait("Category", "DhtRendezvous")]
[Trait("Category", "FullInstance")]
public class TwoNodeMeshFullInstanceTests
{
    [Fact]
    public async Task TwoFullInstances_CanFormOverlayMeshConnection()
    {
        using var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        await using var alpha = new SlskdnFullInstanceRunner(
            loggerFactory.CreateLogger<SlskdnFullInstanceRunner>(),
            $"mesh-alpha-{Guid.NewGuid():N}"[..19]);
        await using var beta = new SlskdnFullInstanceRunner(
            loggerFactory.CreateLogger<SlskdnFullInstanceRunner>(),
            $"mesh-beta-{Guid.NewGuid():N}"[..18]);

        await alpha.StartAsync(
            disableAuthentication: true,
            soulseekUsername: "mesh-alpha",
            soulseekPassword: "mesh-alpha-pass");
        await beta.StartAsync(
            disableAuthentication: true,
            soulseekUsername: "mesh-beta",
            soulseekPassword: "mesh-beta-pass");

        Assert.True(alpha.OverlayPort.HasValue);
        Assert.True(beta.OverlayPort.HasValue);

        using var alphaClient = new HttpClient { BaseAddress = new Uri(alpha.ApiUrl) };
        using var betaClient = new HttpClient { BaseAddress = new Uri(beta.ApiUrl) };
        alphaClient.DefaultRequestHeaders.TryAddWithoutValidation("X-API-Key", "integration-test");
        betaClient.DefaultRequestHeaders.TryAddWithoutValidation("X-API-Key", "integration-test");

        var connectBody = await WaitForOverlayConnectAsync(
            alphaClient,
            beta.OverlayAddress,
            beta.OverlayPort.Value,
            TimeSpan.FromSeconds(20));
        Assert.True(connectBody.Connected);
        Assert.Equal(beta.OverlayPort.Value, connectBody.Port);

        string? overlayFailureDetails = null;
        await WaitForAsync(
            async () =>
            {
                var alphaConnections = await alphaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");
                var betaConnections = await betaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");

                var alphaConnected = alphaConnections?.Exists(peer =>
                    string.Equals(peer.Username, "mesh-beta", StringComparison.OrdinalIgnoreCase)) == true;
                var betaConnected = betaConnections?.Exists(peer =>
                    string.Equals(peer.Username, "mesh-alpha", StringComparison.OrdinalIgnoreCase)) == true;

                overlayFailureDetails = await BuildFailureDetailsAsync(alphaClient, betaClient, alphaConnections, betaConnections);
                return alphaConnected && betaConnected;
            },
            TimeSpan.FromSeconds(20),
            () => "full-instance overlay mesh neighbors did not appear on both nodes\n" + overlayFailureDetails);

        string? peerStatsFailureDetails = null;
        await WaitForAsync(
            async () =>
            {
                var alphaPeerStats = await alphaClient.GetFromJsonAsync<PeerStatistics>("/api/v0/security/peers/stats");
                var betaPeerStats = await betaClient.GetFromJsonAsync<PeerStatistics>("/api/v0/security/peers/stats");
                peerStatsFailureDetails = await BuildFailureDetailsAsync(alphaClient, betaClient, alphaPeerStats: alphaPeerStats, betaPeerStats: betaPeerStats);
                return alphaPeerStats is { TotalPeers: >= 1, OnionRoutingPeers: >= 1 }
                    && betaPeerStats is { TotalPeers: >= 1, OnionRoutingPeers: >= 1 };
            },
            TimeSpan.FromSeconds(20),
            () => "mesh peer inventory did not reflect the full-instance overlay connection\n" + peerStatsFailureDetails);

        await Task.Delay(OverlayTimeouts.MessageRead + TimeSpan.FromSeconds(5));

        string? idleFailureDetails = null;
        await WaitForAsync(
            async () =>
            {
                var alphaConnections = await alphaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");
                var betaConnections = await betaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");

                var alphaStillConnected = alphaConnections?.Exists(peer =>
                    string.Equals(peer.Username, "mesh-beta", StringComparison.OrdinalIgnoreCase)) == true;
                var betaStillConnected = betaConnections?.Exists(peer =>
                    string.Equals(peer.Username, "mesh-alpha", StringComparison.OrdinalIgnoreCase)) == true;

                idleFailureDetails = await BuildFailureDetailsAsync(alphaClient, betaClient, alphaConnections, betaConnections);
                return alphaStillConnected && betaStillConnected;
            },
            TimeSpan.FromSeconds(5),
            () => "overlay mesh neighbors disconnected after one message-read timeout\n" + idleFailureDetails);
    }

    [Fact]
    public async Task TwoFullInstances_CanSearchAndDownloadOverOverlayMesh()
    {
        using var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        await using var alpha = new SlskdnFullInstanceRunner(
            loggerFactory.CreateLogger<SlskdnFullInstanceRunner>(),
            $"mesh-alpha-{Guid.NewGuid():N}"[..19]);
        await using var beta = new SlskdnFullInstanceRunner(
            loggerFactory.CreateLogger<SlskdnFullInstanceRunner>(),
            $"mesh-beta-{Guid.NewGuid():N}"[..18]);

        var probeId = Guid.NewGuid().ToString("N")[..12];
        var probeFilename = $"meshprobe{probeId}.flac";
        var probeBytes = Enumerable.Range(0, 8192).Select(i => (byte)(i % 251)).ToArray();
        probeBytes[0] = 0x66;
        probeBytes[1] = 0x4C;
        probeBytes[2] = 0x61;
        probeBytes[3] = 0x43;
        var betaSharePath = Path.Combine(beta.SharesDirectory, probeFilename);
        await File.WriteAllBytesAsync(betaSharePath, probeBytes);

        await alpha.StartAsync(
            disableAuthentication: true,
            soulseekUsername: "mesh-alpha",
            soulseekPassword: "mesh-alpha-pass");
        await beta.StartAsync(
            disableAuthentication: true,
            soulseekUsername: "mesh-beta",
            soulseekPassword: "mesh-beta-pass");

        Assert.True(beta.OverlayPort.HasValue);

        using var alphaClient = new HttpClient { BaseAddress = new Uri(alpha.ApiUrl) };
        using var betaClient = new HttpClient { BaseAddress = new Uri(beta.ApiUrl) };
        alphaClient.DefaultRequestHeaders.TryAddWithoutValidation("X-API-Key", "integration-test");
        betaClient.DefaultRequestHeaders.TryAddWithoutValidation("X-API-Key", "integration-test");

        var scanResponse = await betaClient.PutAsync("/api/v0/shares", content: null);
        scanResponse.EnsureSuccessStatusCode();

        var contentId = $"content:test:{probeId}";
        await WaitForAsync(
            () => TrySeedContentItemAsync(beta, probeFilename, contentId),
            TimeSpan.FromSeconds(20),
            () => "beta share repository did not index the probe file");

        await WaitForOverlayConnectAsync(
            alphaClient,
            beta.OverlayAddress,
            beta.OverlayPort.Value,
            TimeSpan.FromSeconds(20));

        await WaitForAsync(
            async () =>
            {
                var alphaConnections = await alphaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");
                return alphaConnections?.Exists(peer =>
                    string.Equals(peer.Username, "mesh-beta", StringComparison.OrdinalIgnoreCase)) == true;
            },
            TimeSpan.FromSeconds(20),
            () => "alpha did not keep an outbound overlay connection to beta");

        var searchResponse = await alphaClient.PostAsJsonAsync(
            "/api/v0/searches",
            new
            {
                searchText = Path.GetFileNameWithoutExtension(probeFilename),
                filterResponses = false,
                searchTimeout = 5,
                providers = new[] { "pod" },
            });
        Assert.True(
            searchResponse.IsSuccessStatusCode,
            $"Search request failed: {(int)searchResponse.StatusCode} {await searchResponse.Content.ReadAsStringAsync()}");

        using var searchJson = JsonDocument.Parse(await searchResponse.Content.ReadAsStringAsync());
        var searchId = searchJson.RootElement.GetProperty("id").GetGuid();

        var itemId = await WaitForMeshSearchResultAsync(alphaClient, searchId, probeFilename, contentId);
        var downloadResponse = await alphaClient.PostAsync($"/api/v0/searches/{searchId}/items/{itemId}/download", content: null);
        Assert.True(
            downloadResponse.IsSuccessStatusCode,
            $"Download request failed: {(int)downloadResponse.StatusCode} {await downloadResponse.Content.ReadAsStringAsync()}");

        using var downloadJson = JsonDocument.Parse(await downloadResponse.Content.ReadAsStringAsync());
        Assert.True(downloadJson.RootElement.GetProperty("success").GetBoolean());
        Assert.Equal(contentId, downloadJson.RootElement.GetProperty("content_id").GetString());
        Assert.Equal("pod", downloadJson.RootElement.GetProperty("source").GetString());

        var localPath = downloadJson.RootElement.GetProperty("path").GetString();
        Assert.False(string.IsNullOrWhiteSpace(localPath));
        Assert.True(File.Exists(localPath), $"Downloaded file not found: {localPath}");
        Assert.Equal(probeBytes, await File.ReadAllBytesAsync(localPath!));
    }

    [Fact]
    public async Task OptionalLiveAccounts_CanSearchAndDownloadHostedProbeOverOverlayMesh()
    {
        if (!ShouldRunLiveMeshAccountSmoke())
        {
            return;
        }

        if (!TryLoadLocalMeshAccounts(out var accounts))
        {
            return;
        }

        using var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
        var testLogger = loggerFactory.CreateLogger<TwoNodeMeshFullInstanceTests>();
        await using var alpha = new SlskdnFullInstanceRunner(
            loggerFactory.CreateLogger<SlskdnFullInstanceRunner>(),
            $"mesh-live-alpha-{Guid.NewGuid():N}"[..24]);
        await using var beta = new SlskdnFullInstanceRunner(
            loggerFactory.CreateLogger<SlskdnFullInstanceRunner>(),
            $"mesh-live-beta-{Guid.NewGuid():N}"[..23]);

        var probeId = Guid.NewGuid().ToString("N")[..12];
        var probeFilename = $"mesh-live-probe-{probeId}.flac";
        var probeBytes = Enumerable.Range(0, 8192).Select(i => (byte)((i * 17) % 251)).ToArray();
        var betaSharePath = Path.Combine(beta.SharesDirectory, probeFilename);
        await File.WriteAllBytesAsync(betaSharePath, probeBytes);

        await alpha.StartAsync(
            disableAuthentication: true,
            noConnect: false,
            soulseekUsername: accounts.AlphaUsername,
            soulseekPassword: accounts.AlphaPassword);
        await beta.StartAsync(
            disableAuthentication: true,
            noConnect: false,
            soulseekUsername: accounts.BetaUsername,
            soulseekPassword: accounts.BetaPassword);

        using var alphaClient = new HttpClient { BaseAddress = new Uri(alpha.ApiUrl), Timeout = TimeSpan.FromSeconds(45) };
        using var betaClient = new HttpClient { BaseAddress = new Uri(beta.ApiUrl), Timeout = TimeSpan.FromSeconds(45) };
        alphaClient.DefaultRequestHeaders.TryAddWithoutValidation("X-API-Key", "integration-test");
        betaClient.DefaultRequestHeaders.TryAddWithoutValidation("X-API-Key", "integration-test");

        testLogger.LogInformation("[LIVE-MESH] Waiting for Soulseek login");
        await WaitForSoulseekLoggedInAsync(alphaClient, "alpha");
        await WaitForSoulseekLoggedInAsync(betaClient, "beta");
        testLogger.LogInformation("[LIVE-MESH] Both Soulseek sessions are logged in");

        testLogger.LogInformation("[LIVE-MESH] Scanning beta shares");
        var scanResponse = await betaClient.PutAsync("/api/v0/shares", content: null);
        Assert.True(
            scanResponse.IsSuccessStatusCode,
            $"Share scan request failed: {(int)scanResponse.StatusCode} {await scanResponse.Content.ReadAsStringAsync()}");

        var contentId = $"content:live-test:{probeId}";
        testLogger.LogInformation("[LIVE-MESH] Seeding content item {ContentId}", contentId);
        await WaitForAsync(
            () => TrySeedContentItemAsync(beta, probeFilename, contentId),
            TimeSpan.FromSeconds(20),
            () => "beta live-account share repository did not index the probe file");

        testLogger.LogInformation("[LIVE-MESH] Connecting alpha overlay to beta at {Address}:{Port}", beta.OverlayAddress, beta.OverlayPort!.Value);
        await WaitForOverlayConnectAsync(
            alphaClient,
            beta.OverlayAddress,
            beta.OverlayPort!.Value,
            TimeSpan.FromSeconds(20));

        testLogger.LogInformation("[LIVE-MESH] Waiting for alpha overlay neighbor");
        await WaitForAsync(
            async () =>
            {
                var alphaConnections = await alphaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");
                return alphaConnections?.Exists(peer =>
                    string.Equals(peer.Username, accounts.BetaUsername, StringComparison.OrdinalIgnoreCase)) == true;
            },
            TimeSpan.FromSeconds(20),
            () => "alpha did not keep an outbound overlay connection to beta using live accounts");

        testLogger.LogInformation("[LIVE-MESH] Searching for {ProbeFilename}", probeFilename);
        var searchResponse = await alphaClient.PostAsJsonAsync(
            "/api/v0/searches",
            new
            {
                searchText = Path.GetFileNameWithoutExtension(probeFilename),
                filterResponses = false,
                searchTimeout = 5,
                providers = new[] { "pod" },
            });
        Assert.True(
            searchResponse.IsSuccessStatusCode,
            $"Search request failed: {(int)searchResponse.StatusCode} {await searchResponse.Content.ReadAsStringAsync()}");

        using var searchJson = JsonDocument.Parse(await searchResponse.Content.ReadAsStringAsync());
        var searchId = searchJson.RootElement.GetProperty("id").GetGuid();

        testLogger.LogInformation("[LIVE-MESH] Waiting for mesh search result");
        var itemId = await WaitForMeshSearchResultAsync(alphaClient, searchId, probeFilename, contentId, accounts.BetaUsername);
        testLogger.LogInformation("[LIVE-MESH] Downloading search item {ItemId}", itemId);
        var downloadResponse = await alphaClient.PostAsync($"/api/v0/searches/{searchId}/items/{itemId}/download", content: null);
        Assert.True(
            downloadResponse.IsSuccessStatusCode,
            $"Download request failed: {(int)downloadResponse.StatusCode} {await downloadResponse.Content.ReadAsStringAsync()}");

        using var downloadJson = JsonDocument.Parse(await downloadResponse.Content.ReadAsStringAsync());
        Assert.True(downloadJson.RootElement.GetProperty("success").GetBoolean());
        Assert.Equal(contentId, downloadJson.RootElement.GetProperty("content_id").GetString());
        Assert.Equal("pod", downloadJson.RootElement.GetProperty("source").GetString());

        var localPath = downloadJson.RootElement.GetProperty("path").GetString();
        Assert.False(string.IsNullOrWhiteSpace(localPath));
        Assert.True(File.Exists(localPath), $"Downloaded file not found: {localPath}");
        Assert.Equal(probeBytes, await File.ReadAllBytesAsync(localPath!));
        testLogger.LogInformation("[LIVE-MESH] Download completed at {LocalPath}", localPath);
    }

    private static async Task WaitForAsync(Func<Task<bool>> predicate, TimeSpan timeout, Func<string> failureMessageFactory)
    {
        var deadline = DateTimeOffset.UtcNow + timeout;
        while (DateTimeOffset.UtcNow < deadline)
        {
            if (await predicate())
            {
                return;
            }

            var remaining = deadline - DateTimeOffset.UtcNow;
            if (remaining <= TimeSpan.Zero)
            {
                break;
            }

            await Task.Delay(remaining < TimeSpan.FromMilliseconds(250) ? remaining : TimeSpan.FromMilliseconds(250));
        }

        throw new TimeoutException(failureMessageFactory());
    }

    private static async Task<string> WaitForMeshSearchResultAsync(HttpClient client, Guid searchId, string expectedFilename, string expectedContentId)
    {
        return await WaitForMeshSearchResultAsync(client, searchId, expectedFilename, expectedContentId, "mesh-beta");
    }

    private static async Task<string> WaitForMeshSearchResultAsync(HttpClient client, Guid searchId, string expectedFilename, string expectedContentId, string expectedUsername)
    {
        string? failureDetails = null;

        await WaitForAsync(
            async () =>
            {
                using var response = await client.GetAsync($"/api/v0/searches/{searchId}?includeResponses=true");
                var body = await response.Content.ReadAsStringAsync();
                failureDetails = body;
                response.EnsureSuccessStatusCode();

                using var document = JsonDocument.Parse(body);
                if (!document.RootElement.TryGetProperty("responses", out var responses) ||
                    responses.ValueKind != JsonValueKind.Array)
                {
                    return false;
                }

                var responseIndex = 0;
                foreach (var searchResponse in responses.EnumerateArray())
                {
                    var username = searchResponse.TryGetProperty("username", out var usernameElement)
                        ? usernameElement.GetString()
                        : null;
                    var primarySource = searchResponse.TryGetProperty("primarySource", out var primarySourceElement)
                        ? primarySourceElement.GetString()
                        : null;

                    if (!string.Equals(username, expectedUsername, StringComparison.OrdinalIgnoreCase) ||
                        !string.Equals(primarySource, "pod", StringComparison.OrdinalIgnoreCase))
                    {
                        responseIndex++;
                        continue;
                    }

                    if (!searchResponse.TryGetProperty("files", out var files) ||
                        files.ValueKind != JsonValueKind.Array)
                    {
                        responseIndex++;
                        continue;
                    }

                    var fileIndex = 0;
                    foreach (var file in files.EnumerateArray())
                    {
                        var filename = file.TryGetProperty("filename", out var filenameElement)
                            ? filenameElement.GetString()
                            : null;
                        var contentId = file.TryGetProperty("contentId", out var contentIdElement)
                            ? contentIdElement.GetString()
                            : null;

                        if (filename?.EndsWith(expectedFilename, StringComparison.OrdinalIgnoreCase) == true &&
                            string.Equals(contentId, expectedContentId, StringComparison.Ordinal))
                        {
                            failureDetails = $"{responseIndex}:{fileIndex}";
                            return true;
                        }

                        fileIndex++;
                    }

                    responseIndex++;
                }

                return false;
            },
            TimeSpan.FromSeconds(20),
            () => "mesh search result did not include beta's content-routed probe file\n" + failureDetails);

        return failureDetails!;
    }

    private static async Task<OverlayConnectResultResponse> WaitForOverlayConnectAsync(
        HttpClient client,
        string overlayAddress,
        int overlayPort,
        TimeSpan timeout)
    {
        var deadline = DateTimeOffset.UtcNow + timeout;
        string? failureDetails = null;

        while (DateTimeOffset.UtcNow < deadline)
        {
            using var response = await client.PostAsJsonAsync(
                "/api/v0/overlay/connect",
                new ConnectOverlayPeerRequest
                {
                    Address = overlayAddress,
                    Port = overlayPort,
                });

            var body = await response.Content.ReadAsStringAsync();
            failureDetails = $"{(int)response.StatusCode} {body}";

            if (response.IsSuccessStatusCode)
            {
                var result = JsonSerializer.Deserialize<OverlayConnectResultResponse>(
                    body,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                if (result is not null && result.Connected)
                {
                    return result;
                }
            }

            await Task.Delay(TimeSpan.FromMilliseconds(500));
        }

        Assert.Fail($"Overlay connect request did not succeed within {timeout.TotalSeconds:n0}s: {failureDetails}");
        throw new InvalidOperationException("Unreachable after Assert.Fail");
    }

    private static async Task WaitForSoulseekLoggedInAsync(HttpClient client, string nodeName)
    {
        string? failureDetails = null;
        var deadline = DateTimeOffset.UtcNow + TimeSpan.FromSeconds(90);
        while (DateTimeOffset.UtcNow < deadline)
        {
            using var response = await client.GetAsync("/api/v0/application");
            var body = await response.Content.ReadAsStringAsync();
            failureDetails = body;

            if (response.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
            {
                await Task.Delay(TimeSpan.FromSeconds(2));
                continue;
            }

            response.EnsureSuccessStatusCode();

            using var document = JsonDocument.Parse(body);
            if (document.RootElement
                .GetProperty("server")
                .GetProperty("isLoggedIn")
                .GetBoolean())
            {
                return;
            }

            await Task.Delay(TimeSpan.FromSeconds(2));
        }

        Assert.Fail($"{nodeName} did not log in to Soulseek with the configured live test account\n" + failureDetails);
    }

    private static bool TryLoadLocalMeshAccounts(out LocalMeshAccounts accounts)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var envPath in GetLocalMeshAccountEnvPaths())
        {
            if (!File.Exists(envPath))
            {
                continue;
            }

            ReadEnvFile(values, envPath);
        }

        var pool = LoadLocalMeshAccountPool(values);
        if (pool.Count < 2)
        {
            accounts = new LocalMeshAccounts(string.Empty, string.Empty, string.Empty, string.Empty);
            return false;
        }

        accounts = new LocalMeshAccounts(
            pool[0].Username,
            pool[0].Password,
            pool[1].Username,
            pool[1].Password);
        return true;
    }

    private static bool ShouldRunLiveMeshAccountSmoke()
    {
        var value = Environment.GetEnvironmentVariable("SLSKDN_RUN_LIVE_MESH_ACCOUNT_TESTS");
        return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase);
    }

    private static string ReadCredential(Dictionary<string, string> values, string key)
    {
        var envValue = Environment.GetEnvironmentVariable(key);
        if (!string.IsNullOrWhiteSpace(envValue))
        {
            return envValue;
        }

        return values.TryGetValue(key, out var fileValue) ? fileValue : string.Empty;
    }

    private static IEnumerable<string> GetLocalMeshAccountEnvPaths()
    {
        yield return Path.Combine(AppContext.BaseDirectory, "local-mesh-accounts.env");
        yield return Path.Combine(AppContext.BaseDirectory, "local-mesh-account-pool.env");

        var repositoryTestDirectory = Path.Combine(FindRepositoryRoot(), "tests", "slskd.Tests.Integration");
        yield return Path.Combine(repositoryTestDirectory, "local-mesh-accounts.env");
        yield return Path.Combine(repositoryTestDirectory, "local-mesh-account-pool.env");
    }

    private static void ReadEnvFile(Dictionary<string, string> values, string envPath)
    {
        foreach (var line in File.ReadAllLines(envPath))
        {
            var trimmed = line.Trim();
            if (trimmed.Length == 0 || trimmed.StartsWith("#", StringComparison.Ordinal))
            {
                continue;
            }

            var separatorIndex = trimmed.IndexOf('=');
            if (separatorIndex <= 0)
            {
                continue;
            }

            values[trimmed[..separatorIndex].Trim()] = trimmed[(separatorIndex + 1)..].Trim();
        }
    }

    private static List<LocalMeshAccount> LoadLocalMeshAccountPool(Dictionary<string, string> values)
    {
        var accounts = new List<LocalMeshAccount>();
        foreach (var suffix in new[] { "A", "B", "C", "D", "E", "F" })
        {
            AddAccountIfComplete(values, accounts, suffix);
        }

        for (var index = 1; index <= 16; index++)
        {
            AddAccountIfComplete(values, accounts, index.ToString());
        }

        return accounts
            .GroupBy(account => account.Username, StringComparer.OrdinalIgnoreCase)
            .Select(group => group.First())
            .Take(16)
            .ToList();
    }

    private static void AddAccountIfComplete(Dictionary<string, string> values, List<LocalMeshAccount> accounts, string suffix)
    {
        var username = ReadCredential(values, $"SLSKDN_MESH_ACCOUNT_{suffix}_USERNAME");
        var password = ReadCredential(values, $"SLSKDN_MESH_ACCOUNT_{suffix}_PASSWORD");
        if (!string.IsNullOrWhiteSpace(username) && !string.IsNullOrWhiteSpace(password))
        {
            accounts.Add(new LocalMeshAccount(username, password));
        }
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (directory != null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "slskd.sln")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        return Directory.GetCurrentDirectory();
    }

    private sealed record LocalMeshAccounts(
        string AlphaUsername,
        string AlphaPassword,
        string BetaUsername,
        string BetaPassword);

    private sealed record LocalMeshAccount(string Username, string Password);

    private static Task<bool> TrySeedContentItemAsync(SlskdnFullInstanceRunner runner, string filename, string contentId)
    {
        var databasePath = Path.Combine(runner.DataDirectory, "shares.local.db");
        if (!File.Exists(databasePath))
        {
            return Task.FromResult(false);
        }

        // The API can become ready before the background share scanner creates its SQLite schema.
        // Treat that startup window as not-yet-indexed so the caller's bounded wait can retry.
        using (var readinessConnection = new SqliteConnection(
            $"Data Source={databasePath};Mode=ReadWrite;Cache=shared"))
        {
            readinessConnection.Open();
            using var readinessCommand = readinessConnection.CreateCommand();
            readinessCommand.CommandText = "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'files';";
            if (readinessCommand.ExecuteScalar() is null)
            {
                return Task.FromResult(false);
            }
        }

        using var repository = new SqliteShareRepository($"Data Source={databasePath};Cache=shared");
        var file = repository.ListFiles(includeFullPath: true).FirstOrDefault(f =>
            f.Filename.EndsWith(filename, StringComparison.OrdinalIgnoreCase));
        if (file == null)
        {
            return Task.FromResult(false);
        }

        repository.UpsertContentItem(
            contentId,
            "test",
            "probe",
            file.Filename,
            isAdvertisable: true,
            moderationReason: null,
            checkedAt: DateTimeOffset.UtcNow.ToUnixTimeSeconds());

        return Task.FromResult(true);
    }

    private static async Task<string> BuildFailureDetailsAsync(
        HttpClient alphaClient,
        HttpClient betaClient,
        List<MeshPeerInfoResponse>? alphaConnections = null,
        List<MeshPeerInfoResponse>? betaConnections = null,
        PeerStatistics? alphaPeerStats = null,
        PeerStatistics? betaPeerStats = null)
    {
        alphaConnections ??= await alphaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");
        betaConnections ??= await betaClient.GetFromJsonAsync<List<MeshPeerInfoResponse>>("/api/v0/overlay/connections");
        alphaPeerStats ??= await alphaClient.GetFromJsonAsync<PeerStatistics>("/api/v0/security/peers/stats");
        betaPeerStats ??= await betaClient.GetFromJsonAsync<PeerStatistics>("/api/v0/security/peers/stats");
        var alphaOverlayStats = await alphaClient.GetFromJsonAsync<OverlayStatsResponse>("/api/v0/overlay/stats");
        var betaOverlayStats = await betaClient.GetFromJsonAsync<OverlayStatsResponse>("/api/v0/overlay/stats");
        var alphaDhtStatus = await alphaClient.GetFromJsonAsync<DhtStatusResponse>("/api/v0/dht/status");
        var betaDhtStatus = await betaClient.GetFromJsonAsync<DhtStatusResponse>("/api/v0/dht/status");

        return JsonSerializer.Serialize(new
        {
            alpha = new { connections = alphaConnections, peerStats = alphaPeerStats, overlay = alphaOverlayStats, dht = alphaDhtStatus },
            beta = new { connections = betaConnections, peerStats = betaPeerStats, overlay = betaOverlayStats, dht = betaDhtStatus },
        }, new JsonSerializerOptions { WriteIndented = true });
    }
}
