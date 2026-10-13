// <copyright file="SlskdnFullInstanceRunner.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Integration.Harness;

using System.Collections.Concurrent;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

/// <summary>
/// Full slskdn instance runner for tests that require TCP listeners (e.g., Bridge proxy server).
/// Starts an actual slskdn process instead of using TestServer.
/// </summary>
public class SlskdnFullInstanceRunner : IAsyncDisposable
{
    private static readonly TimeSpan ApiStartupTimeout = TimeSpan.FromSeconds(60);
    private static readonly TimeSpan ApiStartupProbeDelay = TimeSpan.FromMilliseconds(500);
    private static readonly object TcpPortReservationLock = new();
    private static readonly HashSet<int> ReservedTcpPorts = new();
    private const int CapturedLogLineLimit = 200;
    private readonly ILogger<SlskdnFullInstanceRunner> logger;
    private readonly string testId;
    private readonly string appDir;
    private readonly string stdoutLogPath;
    private readonly string stderrLogPath;
    private readonly ConcurrentQueue<string> stdoutLines = new();
    private readonly ConcurrentQueue<string> stderrLines = new();
    private readonly List<int> reservedTcpPorts = new();
    private Process? slskdnProcess;
    private int apiPort;
    private int? bridgePort;
    private int? overlayPort;
    private int? dhtPort;
    private int? udpOverlayPort;
    private int? dataOverlayPort;
    private int? soulseekListenPort;
    private string apiHost = "127.0.0.1";
    private string? vpnNamespaceName;
    private string? vpnNamespaceHostIp;
    private bool isRunning;

    public SlskdnFullInstanceRunner(ILogger<SlskdnFullInstanceRunner> logger, string testId)
    {
        this.logger = logger;
        this.testId = testId;
        this.appDir = Path.Combine(Path.GetTempPath(), "slskdn-test", testId);
        stdoutLogPath = Path.Combine(appDir, "slskd.stdout.log");
        stderrLogPath = Path.Combine(appDir, "slskd.stderr.log");

        Directory.CreateDirectory(appDir);
        Directory.CreateDirectory(Path.Combine(appDir, "config"));
        Directory.CreateDirectory(Path.Combine(appDir, "downloads"));
        Directory.CreateDirectory(Path.Combine(appDir, "incomplete"));
        Directory.CreateDirectory(Path.Combine(appDir, "shares"));
    }

    public string AppDirectory => appDir;
    public string DataDirectory => Path.Combine(appDir, "data");
    public string DownloadsDirectory => Path.Combine(appDir, "downloads");
    public string IncompleteDirectory => Path.Combine(appDir, "incomplete");
    public string SharesDirectory => Path.Combine(appDir, "shares");
    public int ApiPort => apiPort;
    public int? BridgePort => bridgePort;
    public int? OverlayPort => overlayPort;
    public int? DhtPort => dhtPort;
    public int? SoulseekListenPort => soulseekListenPort;
    public bool IsRunning => isRunning;
    public string ApiUrl => $"http://{apiHost}:{apiPort}";
    public string OverlayAddress => apiHost;

    /// <summary>
    /// Start full slskdn instance.
    /// </summary>
    public async Task StartAsync(
        bool enableBridge = false,
        int? bridgePortOverride = null,
        bool disableAuthentication = false,
        int? overlayPortOverride = null,
        int? dhtPortOverride = null,
        bool noConnect = true,
        string? soulseekUsername = null,
        string? soulseekPassword = null,
        IReadOnlyDictionary<string, int>? soulseekEndpointOverrides = null,
        CancellationToken ct = default)
    {
        logger.LogInformation("[TEST-SLSKDN-FULL] Starting full instance {TestId}", testId);

        // Allocate ephemeral ports
        apiPort = AllocateEphemeralPort();
        // DHT mesh TCP and Soulseek peer traffic share the Soulseek listen port. Keep the
        // externally visible OverlayPort property aligned with that single socket so readiness
        // probes and peer-connection tests target the port the application actually binds.
        soulseekListenPort = overlayPortOverride ?? AllocateEphemeralPort();
        overlayPort = soulseekListenPort;
        dhtPort = dhtPortOverride ?? AllocateEphemeralPortUdp();
        udpOverlayPort = AllocateEphemeralPortUdp();
        dataOverlayPort = AllocateEphemeralPort();
        if (enableBridge)
        {
            bridgePort = bridgePortOverride ?? AllocateEphemeralPort();

            if (string.IsNullOrEmpty(DiscoverSoulfindBinary()))
            {
                throw new InvalidOperationException(
                    "Soulfind binary not found. Install soulfind or set SOULFIND_PATH before running bridge integration tests.");
            }
        }

        // Write configuration file
        var configPath = Path.Combine(appDir, "config", "slskd.yml");
        var configYaml = BuildConfigYaml(enableBridge, disableAuthentication, noConnect, soulseekUsername, soulseekPassword);
        await File.WriteAllTextAsync(configPath, configYaml, ct);

        // Find slskdn binary
        var binaryPath = DiscoverSlskdnBinary();
        if (string.IsNullOrEmpty(binaryPath))
        {
            throw new InvalidOperationException(
                "slskdn binary not found. Build the project first: dotnet build -c Release");
        }

        // Start process
        var startInfo = BuildStartInfo(binaryPath, configPath);

        if (enableBridge)
        {
            startInfo.Environment["SLSKDN_ENABLE_BRIDGE_PROXY"] = "1";
        }

        startInfo.Environment["APP_DIR"] = appDir;
        if (soulseekEndpointOverrides is { Count: > 0 })
        {
            startInfo.Environment["SLSKDN_TEST_USER_ENDPOINT_OVERRIDES"] = string.Join(
                ';',
                soulseekEndpointOverrides.Select(overrideEntry => $"{overrideEntry.Key}=127.0.0.1:{overrideEntry.Value}"));
        }

        slskdnProcess = Process.Start(startInfo);
        if (slskdnProcess == null)
        {
            throw new InvalidOperationException($"Failed to start slskdn process: {binaryPath}");
        }

        slskdnProcess.OutputDataReceived += (_, args) => CaptureProcessLogLine(stdoutLines, stdoutLogPath, args.Data);
        slskdnProcess.ErrorDataReceived += (_, args) => CaptureProcessLogLine(stderrLines, stderrLogPath, args.Data);
        slskdnProcess.BeginOutputReadLine();
        slskdnProcess.BeginErrorReadLine();

        // Wait for API to be ready
        await WaitForApiReadyAsync(ct);
        await ConfigureVpnWrapperTestRouteAsync(ct);

        if (overlayPort.HasValue)
        {
            await WaitForTcpPortReadyAsync(overlayPort.Value, "overlay", ct);
        }

        // If bridge is enabled, wait for bridge port to be listening
        if (enableBridge && bridgePort.HasValue)
        {
            await WaitForTcpPortReadyAsync(bridgePort.Value, "bridge", ct);
        }

        isRunning = true;
        logger.LogInformation("[TEST-SLSKDN-FULL] Instance {TestId} ready on API port {ApiPort}", testId, apiPort);
        if (enableBridge && bridgePort.HasValue)
        {
            logger.LogInformation("[TEST-SLSKDN-FULL] Bridge ready on port {BridgePort}", bridgePort.Value);
        }
    }

    /// <summary>
    /// Stop slskdn instance.
    /// </summary>
    public async Task StopAsync()
    {
        try
        {
            if (slskdnProcess != null && !slskdnProcess.HasExited)
            {
                logger.LogInformation("[TEST-SLSKDN-FULL] Stopping instance {TestId}", testId);

                try
                {
                    slskdnProcess.CancelOutputRead();
                    slskdnProcess.CancelErrorRead();
                    slskdnProcess.Kill(entireProcessTree: true);
                    await slskdnProcess.WaitForExitAsync();
                }
                catch (Exception ex)
                {
                    logger.LogWarning(ex, "[TEST-SLSKDN-FULL] Error stopping process");
                }
                finally
                {
                    await CleanupVpnNamespaceAsync(CancellationToken.None);
                }
            }

            if (slskdnProcess == null || slskdnProcess.HasExited)
            {
                slskdnProcess?.Dispose();
                slskdnProcess = null;
                ReleaseReservedTcpPorts();
            }
        }
        finally
        {
            isRunning = false;
        }
    }

    public async ValueTask DisposeAsync()
    {
        await StopAsync();

        // Cleanup
        try
        {
            if (Directory.Exists(appDir) && !ShouldKeepArtifacts())
            {
                Directory.Delete(appDir, recursive: true);
            }
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "[TEST-SLSKDN-FULL] Failed to clean up directory: {Dir}", appDir);
        }
    }

    private string BuildConfigYaml(
        bool enableBridge,
        bool disableAuthentication,
        bool noConnect,
        string? soulseekUsername,
        string? soulseekPassword)
    {
        var sb = new StringBuilder();
        sb.AppendLine("web:");
        sb.AppendLine($"  port: {apiPort}");
        sb.AppendLine($"  address: {(IsVpnWrapperConfigured() ? "0.0.0.0" : "127.0.0.1")}");
        sb.AppendLine("  content_path: .");
        sb.AppendLine("  https:");
        sb.AppendLine("    disabled: true");
        sb.AppendLine("    force: false");
        sb.AppendLine("  authentication:");
        sb.AppendLine($"    disabled: {disableAuthentication.ToString().ToLowerInvariant()}");
        sb.AppendLine("    username: admin");
        sb.AppendLine("    password: admin");
        if (disableAuthentication && IsVpnWrapperConfigured())
        {
            sb.AppendLine("    passthrough:");
            sb.AppendLine("      allowed_cidrs: 10.224.0.0/11");
            sb.AppendLine("  allow_remote_no_auth: true");
        }

        sb.AppendLine("directories:");
        sb.AppendLine($"  downloads: {Path.Combine(appDir, "downloads")}");
        sb.AppendLine($"  incomplete: {Path.Combine(appDir, "incomplete")}");
        sb.AppendLine("shares:");
        sb.AppendLine("  directories:");
        sb.AppendLine($"    - {Path.Combine(appDir, "shares")}");
        sb.AppendLine("  cache:");
        sb.AppendLine("    storage_mode: disk");
        sb.AppendLine("feature:");
        sb.AppendLine("  Dht: true");
        sb.AppendLine("  Mesh: true");
        sb.AppendLine("  MultiSourceDownloads: true");
        sb.AppendLine("  Pods: true");
        sb.AppendLine("  VirtualSoulfind: true");
        sb.AppendLine("  identityFriends: true");
        sb.AppendLine("  collectionsSharing: true");
        sb.AppendLine("  scenePodBridge: true");
        sb.AppendLine("soulseek:");
        sb.AppendLine($"  address: {GetSoulseekAddressForConfig()}");
        sb.AppendLine("  port: 2271");
        sb.AppendLine($"  username: {YamlEscape(soulseekUsername ?? testId)}");
        sb.AppendLine($"  password: {YamlEscape(soulseekPassword ?? "test-password")}");
        sb.AppendLine("  listen_ip_address: 0.0.0.0");
        sb.AppendLine($"  listen_port: {soulseekListenPort ?? 50300}");
        sb.AppendLine("dht:");
        sb.AppendLine("  enabled: true");
        sb.AppendLine($"  overlay_port: {overlayPort ?? 50305}");
        sb.AppendLine($"  dht_port: {dhtPort ?? 50305}");
        sb.AppendLine("  lan_only: true");
        sb.AppendLine("  bootstrap_routers: []");
        sb.AppendLine("  announce_interval_seconds: 900");
        sb.AppendLine("  discovery_interval_seconds: 600");
        sb.AppendLine("  min_neighbors: 1");
        sb.AppendLine("mesh:");
        sb.AppendLine("  enable_dht: true");
        sb.AppendLine("  enable_overlay: true");
        sb.AppendLine("overlay:");
        sb.AppendLine("  enable: false");
        sb.AppendLine($"  listen_port: {udpOverlayPort ?? 50400}");
        sb.AppendLine("overlayData:");
        sb.AppendLine("  enable: false");
        sb.AppendLine($"  listen_port: {dataOverlayPort ?? 50401}");

        if (enableBridge && bridgePort.HasValue)
        {
            sb.AppendLine("virtualSoulfind:");
            sb.AppendLine("  bridge:");
            sb.AppendLine("    enabled: true");
            sb.AppendLine($"    port: {bridgePort.Value}");
            sb.AppendLine("    requireAuth: false");
        }

        sb.AppendLine("flags:");
        sb.AppendLine($"  no_connect: {noConnect.ToString().ToLowerInvariant()}");
        sb.AppendLine("headless: true");

        return sb.ToString();
    }

    private string? DiscoverSlskdnBinary()
    {
        // Check environment variable
        var envPath = Environment.GetEnvironmentVariable("SLSKDN_BINARY_PATH");
        if (!string.IsNullOrEmpty(envPath) && File.Exists(envPath))
        {
            return envPath;
        }

        // Check common build output locations
        var solutionRoot = FindSolutionRoot();
        if (solutionRoot != null)
        {
            var appHostName = OperatingSystem.IsWindows() ? "slskd.exe" : "slskd";
            var candidates = new[]
            {
                Path.Combine(solutionRoot, "src", "slskd", "bin", "Debug", "net10.0", appHostName),
                Path.Combine(solutionRoot, "src", "slskd", "bin", "Release", "net10.0", appHostName),
                Path.Combine(solutionRoot, "publish", appHostName)
            };

            foreach (var candidate in candidates)
            {
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
        }

        return null;
    }

    private ProcessStartInfo BuildStartInfo(string binaryPath, string configPath)
    {
        var startInfo = new ProcessStartInfo
        {
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            WorkingDirectory = appDir
        };

        var vpnLease = VpnNamespaceLeaseAllocator.Allocate();
        if (vpnLease != null)
        {
            apiHost = vpnLease.NamespaceIp;
            vpnNamespaceName = vpnLease.NamespaceName;
            vpnNamespaceHostIp = vpnLease.NamespaceHostIp;

            startInfo.FileName = vpnLease.Wrapper;
            startInfo.ArgumentList.Add(vpnLease.NamespaceName);
            startInfo.ArgumentList.Add(vpnLease.Config);
            startInfo.ArgumentList.Add(GetVpnEntrypointPath());
            startInfo.ArgumentList.Add(binaryPath);
            startInfo.ArgumentList.Add("--config");
            startInfo.ArgumentList.Add(configPath);
            startInfo.ArgumentList.Add("--app-dir");
            startInfo.ArgumentList.Add(appDir);

            startInfo.Environment["SLSKR_NETNS_HOST_IP"] = vpnLease.NamespaceHostIp;
            startInfo.Environment["SLSKR_NETNS_IP"] = vpnLease.NamespaceIp;
            startInfo.Environment["SLSKR_NETNS_SUBNET"] = vpnLease.NamespaceSubnet;
            startInfo.Environment["SLSKDN_VPN_TEST_FORWARD_PORT"] = (soulseekListenPort ?? 50300).ToString();
            startInfo.Environment["SLSKDN_VPN_TEST_FORWARD_NAMESPACE"] = vpnLease.NamespaceName;
            startInfo.Environment["SLSKDN_VPN_TEST_FORWARD_STATE_FILE"] = Path.Combine(appDir, "vpn-port-forward.env");

            logger.LogInformation(
                "[TEST-SLSKDN-FULL] Routing instance {TestId} through VPN namespace {Namespace} using config {Config}",
                testId,
                vpnLease.NamespaceName,
                Path.GetFileName(vpnLease.Config));

            return startInfo;
        }

        startInfo.FileName = binaryPath;
        startInfo.ArgumentList.Add("--config");
        startInfo.ArgumentList.Add(configPath);
        startInfo.ArgumentList.Add("--app-dir");
        startInfo.ArgumentList.Add(appDir);
        return startInfo;
    }

    private static bool IsVpnWrapperConfigured()
    {
        return VpnNamespaceLeaseAllocator.IsConfigured();
    }

    private static string GetVpnEntrypointPath()
    {
        return Path.Combine(AppContext.BaseDirectory, "Harness", "run-with-vpn-port-forward.sh");
    }

    private static string GetSoulseekAddressForConfig()
    {
        var configuredAddress = Environment.GetEnvironmentVariable("SLSKDN_TEST_SOULSEEK_ADDRESS") ?? "vps.slsknet.org";
        if (!IsVpnWrapperConfigured() || IPAddress.TryParse(configuredAddress, out _))
        {
            return configuredAddress;
        }

        var address = Dns.GetHostAddresses(configuredAddress)
            .FirstOrDefault(candidate => candidate.AddressFamily == AddressFamily.InterNetwork);

        return address?.ToString() ?? configuredAddress;
    }

    private async Task ConfigureVpnWrapperTestRouteAsync(CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(vpnNamespaceName) || string.IsNullOrWhiteSpace(vpnNamespaceHostIp))
        {
            return;
        }

        var testCidr = Environment.GetEnvironmentVariable("SLSKDN_FULL_INSTANCE_VPN_TEST_CIDR") ?? "10.224.0.0/11";
        var nsVeth = $"v-{vpnNamespaceName}n";
        var startInfo = new ProcessStartInfo
        {
            FileName = "sudo",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };

        startInfo.ArgumentList.Add("ip");
        startInfo.ArgumentList.Add("netns");
        startInfo.ArgumentList.Add("exec");
        startInfo.ArgumentList.Add(vpnNamespaceName);
        startInfo.ArgumentList.Add("ip");
        startInfo.ArgumentList.Add("route");
        startInfo.ArgumentList.Add("replace");
        startInfo.ArgumentList.Add(testCidr);
        startInfo.ArgumentList.Add("via");
        startInfo.ArgumentList.Add(vpnNamespaceHostIp);
        startInfo.ArgumentList.Add("dev");
        startInfo.ArgumentList.Add(nsVeth);

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start VPN test route command");
        await process.WaitForExitAsync(ct);
        if (process.ExitCode != 0)
        {
            var stderr = await process.StandardError.ReadToEndAsync(ct);
            throw new InvalidOperationException($"Failed to configure VPN test route in namespace {vpnNamespaceName}: {stderr}");
        }
    }

    private async Task CleanupVpnNamespaceAsync(CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(vpnNamespaceName))
        {
            return;
        }

        var namespacePids = await RunBestEffortWithOutputAsync("sudo", ["ip", "netns", "pids", vpnNamespaceName], ct);
        foreach (var pid in namespacePids.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            await RunBestEffortAsync("sudo", ["kill", pid], ct);
        }

        await RunBestEffortAsync("sudo", ["ip", "netns", "delete", vpnNamespaceName], ct);
    }

    private static async Task RunBestEffortAsync(string fileName, string[] arguments, CancellationToken ct)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };

        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo);
        if (process != null)
        {
            await process.WaitForExitAsync(ct);
        }
    }

    private static async Task<string> RunBestEffortWithOutputAsync(string fileName, string[] arguments, CancellationToken ct)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };

        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo);
        if (process == null)
        {
            return string.Empty;
        }

        var output = await process.StandardOutput.ReadToEndAsync(ct);
        await process.WaitForExitAsync(ct);
        return output;
    }

    private string? DiscoverSoulfindBinary()
    {
        var locations = new[]
        {
            "/usr/local/bin/soulfind",
            "/usr/bin/soulfind",
            "./soulfind",
            "../soulfind/soulfind",
            Environment.GetEnvironmentVariable("SOULFIND_PATH")
        };

        foreach (var location in locations.Where(l => !string.IsNullOrWhiteSpace(l)))
        {
            if (File.Exists(location))
            {
                return location;
            }
        }

        try
        {
            var whichCommand = OperatingSystem.IsWindows() ? "where" : "which";
            var psi = new ProcessStartInfo
            {
                FileName = whichCommand,
                Arguments = "soulfind",
                RedirectStandardOutput = true,
                UseShellExecute = false
            };

            using var process = Process.Start(psi);
            var output = process?.StandardOutput.ReadToEnd()?.Trim();

            if (!string.IsNullOrEmpty(output) && File.Exists(output))
            {
                return output;
            }
        }
        catch
        {
        }

        return null;
    }

    private string? FindSolutionRoot()
    {
        var current = Directory.GetCurrentDirectory();
        var dir = new DirectoryInfo(current);

        while (dir != null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "slskd.sln")) ||
                File.Exists(Path.Combine(dir.FullName, "src", "slskd", "slskd.csproj")))
            {
                return dir.FullName;
            }
            dir = dir.Parent;
        }

        return null;
    }

    private async Task WaitForApiReadyAsync(CancellationToken ct)
    {
        var maxAttempts = (int)Math.Ceiling(ApiStartupTimeout.TotalMilliseconds / ApiStartupProbeDelay.TotalMilliseconds);
        var attempt = 0;

        while (attempt < maxAttempts && !ct.IsCancellationRequested)
        {
            if (slskdnProcess?.HasExited == true)
            {
                throw BuildProcessExitException();
            }

            try
            {
                using var client = new HttpClient();
                client.Timeout = TimeSpan.FromSeconds(2);
                var response = await client.GetAsync($"{ApiUrl}/api/v0/session/enabled", ct);
                if (response.IsSuccessStatusCode)
                {
                    logger.LogInformation("[TEST-SLSKDN-FULL] API ready after {Attempts} attempts", attempt + 1);
                    return;
                }
            }
            catch
            {
                // Not ready yet
            }

            await Task.Delay(ApiStartupProbeDelay, ct);
            attempt++;
        }

        throw new TimeoutException(
            $"slskdn instance did not become ready after {ApiStartupTimeout.TotalMilliseconds}ms" +
            $"{Environment.NewLine}STDOUT:{Environment.NewLine}{FormatCapturedLogs(stdoutLines)}" +
            $"{Environment.NewLine}STDERR:{Environment.NewLine}{FormatCapturedLogs(stderrLines)}");
    }

    private InvalidOperationException BuildProcessExitException()
    {
        if (slskdnProcess == null)
        {
            return new InvalidOperationException("slskdn process exited before startup completed");
        }

        return new InvalidOperationException(
            $"slskdn process exited before startup completed (exit code {slskdnProcess.ExitCode})" +
            $"{Environment.NewLine}STDOUT:{Environment.NewLine}{FormatCapturedLogs(stdoutLines)}" +
            $"{Environment.NewLine}STDERR:{Environment.NewLine}{FormatCapturedLogs(stderrLines)}");
    }

    private async Task WaitForTcpPortReadyAsync(int port, string serviceName, CancellationToken ct)
    {
        const int maxAttempts = 60;
        var attempt = 0;

        while (attempt < maxAttempts && !ct.IsCancellationRequested)
        {
            try
            {
                using var client = new TcpClient();
                await client.ConnectAsync(IPAddress.Parse(apiHost), port);
                client.Close();
                logger.LogInformation("[TEST-SLSKDN-FULL] {ServiceName} ready after {Attempts} attempts", serviceName, attempt + 1);
                return;
            }
            catch
            {
                // Not ready yet
            }

            await Task.Delay(500, ct);
            attempt++;
        }

        throw new TimeoutException($"{serviceName} did not become ready on port {port} after {maxAttempts * 500}ms");
    }

    private int AllocateEphemeralPort()
    {
        const int firstDynamicPort = 49152;
        const int lastDynamicPortExclusive = 65536;

        lock (TcpPortReservationLock)
        {
            for (var attempt = 0; attempt < lastDynamicPortExclusive - firstDynamicPort; attempt++)
            {
                var port = Random.Shared.Next(firstDynamicPort, lastDynamicPortExclusive);
                if (ReservedTcpPorts.Contains(port))
                {
                    continue;
                }

                try
                {
                    using var listener = new TcpListener(IPAddress.Loopback, port);
                    listener.Start();
                    ReservedTcpPorts.Add(port);
                    reservedTcpPorts.Add(port);
                    return port;
                }
                catch (SocketException)
                {
                    // Another local service already owns this candidate port.
                }
            }
        }

        throw new InvalidOperationException("Unable to reserve a unique TCP port for the full-instance test runner.");
    }

    private void ReleaseReservedTcpPorts()
    {
        lock (TcpPortReservationLock)
        {
            foreach (var port in reservedTcpPorts)
            {
                ReservedTcpPorts.Remove(port);
            }

            reservedTcpPorts.Clear();
        }
    }

    private int AllocateEphemeralPortUdp()
    {
        using var socket = new UdpClient(new IPEndPoint(IPAddress.Loopback, 0));
        return ((IPEndPoint)socket.Client.LocalEndPoint!).Port;
    }

    private static string YamlEscape(string value)
    {
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }

    private static bool ShouldKeepArtifacts()
    {
        var value = Environment.GetEnvironmentVariable("SLSKDN_TEST_KEEP_ARTIFACTS");
        return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase);
    }

    private static void CaptureProcessLogLine(ConcurrentQueue<string> lines, string logPath, string? line)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return;
        }

        File.AppendAllText(logPath, line + Environment.NewLine);
        lines.Enqueue(line);
        while (lines.Count > CapturedLogLineLimit && lines.TryDequeue(out _))
        {
        }
    }

    private static string FormatCapturedLogs(ConcurrentQueue<string> lines)
    {
        var snapshot = lines.ToArray();
        return snapshot.Length == 0
            ? "<no output captured>"
            : string.Join(Environment.NewLine, snapshot.TakeLast(CapturedLogLineLimit));
    }
}
