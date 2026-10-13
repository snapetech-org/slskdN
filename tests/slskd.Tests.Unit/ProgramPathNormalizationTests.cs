// <copyright file="ProgramPathNormalizationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit;

using System;
using System.IO;
using Directory = System.IO.Directory;
using File = System.IO.File;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.ExceptionServices;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.Features;
using Moq;
using slskd.Bootstrap;
using slskd.Configuration;
using slskd.Core.Security;
using slskd.Mesh.Overlay;
using slskd.SoulseekExceptions;
using slskd.SoulseekRuntime;
using Soulseek;
using Xunit;

[Collection("ProgramAppDirectory")]
public class ProgramPathNormalizationTests
{
    [Fact]
    public void ResolveAppRelativePath_UsesAppDirectory_ForRelativePaths()
    {
        var originalAppDirectory = Program.AppDirectory;

        try
        {
            SetAppDirectory(Path.Combine(Path.GetTempPath(), $"slskdn-appdir-{Guid.NewGuid():N}"));

            var resolved = AppPathResolver.ResolveAppRelativePath("mesh-overlay.key", "mesh-overlay.key", Program.AppDirectory, Program.DefaultAppDirectory);

            Assert.Equal(Path.Combine(Program.AppDirectory, "mesh-overlay.key"), resolved);
        }
        finally
        {
            SetAppDirectory(originalAppDirectory);
        }
    }

    [Fact]
    public void ResolveAppRelativePath_KeepsAbsolutePaths()
    {
        var absolutePath = Path.Combine(Path.GetTempPath(), $"slskdn-absolute-{Guid.NewGuid():N}", "mesh-overlay.key");

        var resolved = AppPathResolver.ResolveAppRelativePath(absolutePath, "mesh-overlay.key", Program.AppDirectory, Program.DefaultAppDirectory);

        Assert.Equal(absolutePath, resolved);
    }

    [Fact]
    public void ResolveAppRelativePath_UsesFallback_ForBlankValues()
    {
        var originalAppDirectory = Program.AppDirectory;

        try
        {
            SetAppDirectory(Path.Combine(Path.GetTempPath(), $"slskdn-appdir-{Guid.NewGuid():N}"));

            var resolved = AppPathResolver.ResolveAppRelativePath(string.Empty, "data", Program.AppDirectory, Program.DefaultAppDirectory);

            Assert.Equal(Path.Combine(Program.AppDirectory, "data"), resolved);
        }
        finally
        {
            SetAppDirectory(originalAppDirectory);
        }
    }

    [Fact]
    public void ResolveOptionalAppRelativePath_UsesAppDirectory_ForRelativePaths()
    {
        var originalAppDirectory = Program.AppDirectory;

        try
        {
            SetAppDirectory(Path.Combine(Path.GetTempPath(), $"slskdn-appdir-{Guid.NewGuid():N}"));

            var resolved = AppPathResolver.ResolveOptionalAppRelativePath("quarantine", Program.AppDirectory, Program.DefaultAppDirectory);

            Assert.Equal(Path.Combine(Program.AppDirectory, "quarantine"), resolved);
        }
        finally
        {
            SetAppDirectory(originalAppDirectory);
        }
    }

    [Fact]
    public void ResolveOptionalAppRelativePath_LeavesBlankValuesBlank()
    {
        var resolved = AppPathResolver.ResolveOptionalAppRelativePath(string.Empty, Program.AppDirectory, Program.DefaultAppDirectory);

        Assert.Equal(string.Empty, resolved);
    }

    [Fact]
    public void GetWriteBaseDirectory_UsesDefaultAppDirectory_WhenAppDirectoryIsBlank()
    {
        var originalAppDirectory = Program.AppDirectory;

        try
        {
            SetAppDirectory(string.Empty);

            var baseDirectory = AppPathResolver.GetWriteBaseDirectory(Program.AppDirectory, Program.DefaultAppDirectory);

            Assert.Equal(Program.DefaultAppDirectory, baseDirectory);
        }
        finally
        {
            SetAppDirectory(originalAppDirectory);
        }
    }

    [Fact]
    public void CreateInitialSoulseekClientOptions_UsesConfiguredListenerAndDistributedNetworkSettings()
    {
        var optionsAtStartup = new OptionsAtStartup
        {
            Soulseek = new Options.SoulseekOptions
            {
                ListenIpAddress = "127.0.0.1",
                ListenPort = 50444,
                DistributedNetwork = new Options.SoulseekOptions.DistributedNetworkOptions
                {
                    ChildLimit = 7,
                    Disabled = false,
                    DisableChildren = false,
                },
            },
        };

        var options = SoulseekClientOptionsFactory.CreateInitial(optionsAtStartup);

        Assert.True(options.EnableListener);
        Assert.Equal("127.0.0.1", options.ListenIPAddress.ToString());
        Assert.Equal(50444, options.ListenPort);
        Assert.True(options.EnableDistributedNetwork);
        Assert.True(options.AcceptDistributedChildren);
        Assert.Equal(7, options.DistributedChildLimit);
        Assert.True(options.PeerObfuscationOptions.Enabled);

        // Obfuscation.ListenPort defaults to 0, meaning obfuscated peer connections share the
        // regular listen port (50444) via per-connection sniffing rather than binding a second,
        // dedicated port.
        Assert.Equal(0, options.PeerObfuscationOptions.ListenPort);
    }

    [Fact]
    public void CreateWebHtmlRewriteRules_AddsRootBase_ForRootUrlBase()
    {
        var rules = WebHtmlRewriteRules.Create("/");

        var html = """
            <head>
            <script type="module" src="/assets/index.js"></script>
            """;

        foreach (var (pattern, replacement) in rules)
        {
            html = System.Text.RegularExpressions.Regex.Replace(html, pattern, replacement);
        }

        Assert.Contains("<head><base href=\"/\" />", html);
        Assert.Contains("src=\"/assets/index.js\"", html);
    }

    [Fact]
    public void CreateWebHtmlRewriteRules_PrefixesAssetAndManifestPaths_ForUrlBase()
    {
        var rules = WebHtmlRewriteRules.Create("/system");

        var html = """
            <head>
            <link rel="manifest" href="/manifest.json" />
            <link rel="apple-touch-icon" href="/logo192.png" />
            <script type="module" src="/assets/index.js"></script>
            """;

        foreach (var (pattern, replacement) in rules)
        {
            html = System.Text.RegularExpressions.Regex.Replace(html, pattern, replacement);
        }

        Assert.Contains("<head><base href=\"/system/\" />", html);
        Assert.Contains("href=\"/system/manifest.json\"", html);
        Assert.Contains("href=\"/system/logo192.png\"", html);
        Assert.Contains("src=\"/system/assets/index.js\"", html);
    }

    [Fact]
    public void GetConfigurationCompatibilityWarnings_ReportsLegacyConfigKeysAndRetryFloor()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"slskdn-config-warning-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);

        try
        {
            var path = Path.Combine(directory, "slskd.yml");
            File.WriteAllText(path, """
                global:
                  download:
                    retry:
                      max_delay: 1000
                integration:
                  webhooks: {}
                transfers:
                  limits:
                    queued:
                      files: 10
                groups:
                  default:
                    limits:
                      queued:
                        files: 5
                """);

            var warnings = ConfigurationCompatibilityWarnings.GetWarnings(
                path,
                new Options
                {
                    Global = new Options.GlobalOptions
                    {
                        Download = new Options.GlobalOptions.GlobalDownloadOptions
                        {
                            Retry = new Options.GlobalOptions.GlobalDownloadOptions.DownloadRetryOptions
                            {
                                MaxDelay = 1000,
                            },
                        },
                    },
                });

            Assert.Contains(warnings, warning => warning.Contains("'global'", StringComparison.Ordinal));
            Assert.Contains(warnings, warning => warning.Contains("'integration'", StringComparison.Ordinal));
            Assert.Contains(warnings, warning => warning.Contains("'groups'", StringComparison.Ordinal));
            Assert.Contains(warnings, warning => warning.Contains("'transfers.limits'", StringComparison.Ordinal));
            Assert.Contains(warnings, warning => warning.Contains("Group-level 'limits'", StringComparison.Ordinal));
            Assert.Contains(warnings, warning => warning.Contains("30000ms", StringComparison.Ordinal));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void IsBenignUnobservedTaskException_ReturnsFalse_ForConnectionRefusedSocketFailure()
    {
        var exception = new AggregateException(new SocketException((int)SocketError.ConnectionRefused));

        Assert.False(StartupExceptionClassifier.IsBenignUnobservedTaskException(exception));
    }

    [Fact]
    public void IsBenignUnobservedTaskException_ReturnsFalse_ForUnexpectedFailures()
    {
        var exception = new AggregateException(new InvalidOperationException("boom"));

        Assert.False(StartupExceptionClassifier.IsBenignUnobservedTaskException(exception));
    }

    [Fact]
    public void IsBenignUnobservedTaskException_ReturnsTrue_ForVpnDisconnect()
    {
        var exception = new AggregateException(new slskd.VPNClientException("VPN client disconnected"));

        Assert.True(StartupExceptionClassifier.IsBenignUnobservedTaskException(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForDisposedConnectionFailures()
    {
        var exception = new AggregateException(new ObjectDisposedException("Connection"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Theory]
    [InlineData("File not shared.")]
    [InlineData("Overwhelmed with requests; try again later.")]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForPeerTransferDenials(string message)
    {
        var exception = new AggregateException(new TransferRejectedException(message));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForPierceFirewallConnectionFailures()
    {
        var exception = new AggregateException(new IOException(
            "Unknown PierceFirewall attempt with token 46 from x.x.x.x:44490 (id: abcdef)"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForRemoteConnectionClosedFailures()
    {
        var exception = new AggregateException(new IOException("Remote connection closed"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekClientWrapperAroundRemoteClose()
    {
        var exception = new SoulseekClientException(
            "Failed to upload file to user alice: Failed to read transfer start offset: Remote connection closed",
            new ConnectionReadException("Failed to read 8 bytes: Remote connection closed"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForConnectionRefusedFailures()
    {
        var exception = new AggregateException(new IOException("Connection refused"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Theory]
    [InlineData(SocketError.ConnectionReset)]
    [InlineData(SocketError.ConnectionRefused)]
    [InlineData(SocketError.TimedOut)]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForExpectedSocketFailures(SocketError socketError)
    {
        var exception = new AggregateException(new SocketException((int)socketError));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsFalse_ForUnexpectedSocketFailures()
    {
        var exception = new AggregateException(new SocketException((int)SocketError.AccessDenied));

        Assert.False(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForRemoteTransferReportedFailedFailures()
    {
        var exception = new AggregateException(new TransferReportedFailedException("Download reported as failed by remote client"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForRemoteTransferRejectedEnqueueFailures()
    {
        var exception = new AggregateException(new TransferRejectedException("Enqueue failed due to internal error"));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Theory]
    [InlineData("Too many megabytes")]
    [InlineData("Too many files")]
    [InlineData("File read error.")]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForRemoteTransferRejectedPolicyFailures(string reason)
    {
        var exception = new AggregateException(new TransferRejectedException(reason));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Theory]
    [InlineData("Transfer failed: Transfer complete")]
    [InlineData("Transfer failed: Transfer error")]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForTransferTeardownFailures(string message)
    {
        var exception = new AggregateException(new ConnectionException(message));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekMessageConnectionClosedTeardown()
    {
        var inner = new InvalidOperationException("The underlying Tcp connection is closed");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at Soulseek.Network.MessageConnection.ReadContinuouslyAsync()");
        var exception = new AggregateException(inner);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekMessageConnectionDisposedTeardown()
    {
        var inner = new ObjectDisposedException("MessageConnection");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at Soulseek.Network.MessageConnection.ReadContinuouslyAsync()");
        var exception = new AggregateException(inner);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekTimerResetReadLoopRace()
    {
        var inner = new NullReferenceException("Object reference not set to an instance of an object.");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at Soulseek.Extensions.Reset(Timer timer)\n" +
            "   at Soulseek.Network.Tcp.Connection.ReadInternalAsync(Int64 length, Stream outputStream, Func`3 governor, Action`3 reporter, CancellationToken cancellationToken)\n" +
            "   at Soulseek.Network.MessageConnection.ReadContinuouslyAsync()");
        var exception = new AggregateException(inner);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekTimerResetWriteLoopRace()
    {
        var inner = new NullReferenceException("Object reference not set to an instance of an object.");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at Soulseek.Extensions.Reset(Timer timer)\n" +
            "   at Soulseek.Network.Tcp.Connection.WriteInternalAsync(Int64 length, Stream inputStream, Func`3 governor, Action`3 reporter, CancellationToken cancellationToken)");
        var exception = new AggregateException(inner);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekReadTimeoutChain()
    {
        var socketException = new SocketException((int)SocketError.TimedOut);
        ExceptionDispatchInfo.SetRemoteStackTrace(
            socketException,
            "   at System.Net.Sockets.Socket.AwaitableSocketAsyncEventArgs.ThrowException(SocketError error, CancellationToken cancellationToken)");

        var ioException = new IOException("Unable to read data from the transport connection: Connection timed out.", socketException);
        ExceptionDispatchInfo.SetRemoteStackTrace(
            ioException,
            "   at Soulseek.Network.Tcp.Connection.ReadInternalAsync(Int64 length, Stream outputStream, Func`3 governor, Action`3 reporter, CancellationToken cancellationToken)");

        var connectionException = new ConnectionReadException(
            "Failed to read 4 bytes from 92.157.108.121:57986: Unable to read data from the transport connection: Connection timed out.",
            ioException);
        ExceptionDispatchInfo.SetRemoteStackTrace(
            connectionException,
            "   at Soulseek.Network.Tcp.Connection.ReadInternalAsync(Int64 length, Stream outputStream, Func`3 governor, Action`3 reporter, CancellationToken cancellationToken)\n" +
            "   at Soulseek.Network.Tcp.Connection.ReadInternalAsync(Int64 length, CancellationToken cancellationToken)\n" +
            "   at Soulseek.Network.MessageConnection.ReadContinuouslyAsync()");

        var exception = new AggregateException(connectionException);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekTcpDoubleDisconnectRace()
    {
        var inner = new InvalidOperationException("An attempt was made to transition a task to a final state when it had already completed.");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at Soulseek.Network.Tcp.Connection.Disconnect(String message, Exception exception)\n" +
            "   at Soulseek.Network.Tcp.Connection.ReadInternalAsync(Int64 length, Stream outputStream, Func`3 governor, Action`3 reporter, CancellationToken cancellationToken)\n" +
            "   at Soulseek.Network.MessageConnection.ReadContinuouslyAsync()");
        var exception = new AggregateException(inner);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekDisconnectingReadLoopRace()
    {
        var inner = new InvalidOperationException("Invalid attempt to send to a disconnected or transitioning connection (current state: Disconnecting)");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at Soulseek.Network.Tcp.Connection.ReadAsync(Int64 length, Nullable`1 cancellationToken)\n" +
            "   at Soulseek.Network.MessageConnection.ReadContinuouslyAsync()");
        var exception = new AggregateException(new ConnectionException("One or more errors occurred.", new AggregateException(inner)));

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void IsExpectedSoulseekNetworkException_ReturnsTrue_ForSoulseekListenerSocketDisposedTeardown()
    {
        var inner = new ObjectDisposedException("System.Net.Sockets.Socket");
        ExceptionDispatchInfo.SetRemoteStackTrace(
            inner,
            "   at System.Net.Sockets.Socket.AcceptAsync(SocketAsyncEventArgs e, CancellationToken cancellationToken)\n" +
            "   at System.Net.Sockets.TcpListener.AcceptTcpClientAsync()\n" +
            "   at Soulseek.Network.Tcp.TcpListenerAdapter.AcceptTcpClientAsync()\n" +
            "   at Soulseek.Network.Tcp.Listener.ListenContinuouslyAsync()");
        var exception = new AggregateException(inner);

        Assert.True(SoulseekNetworkExceptionClassifier.IsExpected(exception));
    }

    [Fact]
    public void OverlayOptions_DefaultToEnabledQuicConfiguration()
    {
        var overlay = new slskd.Mesh.Overlay.OverlayOptions();
        var dataOverlay = new slskd.Mesh.Overlay.DataOverlayOptions();

        Assert.True(overlay.Enable);
        Assert.Equal(50300, overlay.ListenPort);
        Assert.True(overlay.EnableQuic);
        Assert.True(overlay.ShareQuicWithDhtPort);
        Assert.Equal(50300, overlay.QuicListenPort);
        Assert.Equal(55305, overlay.QuicBackendListenPort);
        Assert.False(dataOverlay.Enable);
        Assert.Equal(50300, dataOverlay.ListenPort);
        Assert.True(dataOverlay.ShareWithDhtPort);
        Assert.Equal(55401, dataOverlay.BackendListenPort);
    }

    [Theory]
    [InlineData(true, true, false)]
    [InlineData(true, false, true)]
    [InlineData(false, true, false)]
    [InlineData(false, false, false)]
    public void ShouldRunStandaloneUdpOverlayServer_UsesStandaloneSocketOnlyWhenSharedMeshUdpIsInactive(
        bool overlayEnabled,
        bool sharedMeshUdpRequested,
        bool expected)
    {
        Assert.Equal(expected, QuicOverlayFactory.ShouldRunStandaloneUdpOverlayServer(overlayEnabled, sharedMeshUdpRequested));
    }

    [Fact]
    public void IsStaleAntiforgeryTokenException_ReturnsTrue_ForKeyRingMismatch()
    {
        var exception = new AntiforgeryValidationException("The antiforgery token could not be decrypted.", new CryptographicException("The key {abc} was not found in the key ring."));

        Assert.True(AntiforgeryCookieRecovery.IsStaleTokenException(exception));
    }

    [Fact]
    public void StripKnownAntiforgeryCookiesFromRequest_RemovesXsrfCookies_AndResetsParsedRequestCookies()
    {
        var port = new OptionsAtStartup().Web.Port;
        var context = new DefaultHttpContext();
        context.Request.Headers.Cookie = $"session=keep; XSRF-COOKIE-{port}=stale-cookie; theme=dark; XSRF-TOKEN-{port}=stale-request; XSRF-TOKEN=legacy";

        _ = context.Request.Cookies;
        Assert.NotNull(context.Features.Get<IRequestCookiesFeature>());

        var stripped = AntiforgeryCookieRecovery.StripKnownCookiesFromRequest(context, port);

        Assert.True(stripped);
        Assert.Equal("session=keep; theme=dark", context.Request.Headers.Cookie.ToString());
        Assert.Equal("keep", context.Request.Cookies["session"]);
        Assert.Equal("dark", context.Request.Cookies["theme"]);
        Assert.False(context.Request.Cookies.ContainsKey($"XSRF-COOKIE-{port}"));
        Assert.False(context.Request.Cookies.ContainsKey($"XSRF-TOKEN-{port}"));
        Assert.False(context.Request.Cookies.ContainsKey("XSRF-TOKEN"));
    }

    [Fact]
    public void ClearKnownAntiforgeryCookies_UsesRequestSchemeForDeletion()
    {
        var port = new OptionsAtStartup().Web.Port;
        var httpsContext = new DefaultHttpContext();
        httpsContext.Request.Scheme = "https";

        AntiforgeryCookieRecovery.ClearKnownCookies(httpsContext, port);

        Assert.Equal(4, httpsContext.Response.Headers.SetCookie.Count);
        Assert.All(
            httpsContext.Response.Headers.SetCookie,
            value => Assert.Contains("; secure", value, StringComparison.OrdinalIgnoreCase));

        var httpContext = new DefaultHttpContext();
        httpContext.Request.Scheme = "http";

        AntiforgeryCookieRecovery.ClearKnownCookies(httpContext, port);

        Assert.Equal(4, httpContext.Response.Headers.SetCookie.Count);
        Assert.All(
            httpContext.Response.Headers.SetCookie,
            value => Assert.DoesNotContain("; secure", value, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void TryGetAndStoreAntiforgeryTokens_Retries_AfterClearingDirectCryptographicFailure()
    {
        var port = new OptionsAtStartup().Web.Port;
        var context = new DefaultHttpContext();
        context.Request.Scheme = "https";
        context.Request.Path = "/api/v0/session/enabled";
        context.Request.Headers.Cookie = $"XSRF-COOKIE-{port}=stale-cookie; XSRF-TOKEN-{port}=stale-request";

        var expectedTokens = new AntiforgeryTokenSet("fresh-request", "fresh-cookie", "X-CSRF-TOKEN", $"XSRF-COOKIE-{port}");
        var antiforgery = new Mock<IAntiforgery>();
        antiforgery
            .SetupSequence(mock => mock.GetAndStoreTokens(context))
            .Throws(new CryptographicException("The key {abc} was not found in the key ring."))
            .Returns(expectedTokens);

        var tokens = AntiforgeryCookieRecovery.TryGetAndStoreTokens(context, antiforgery.Object, port, _ => { });

        Assert.Same(expectedTokens, tokens);
        antiforgery.Verify(mock => mock.GetAndStoreTokens(context), Times.Exactly(2));
        Assert.Contains(context.Response.Headers["Set-Cookie"], value => value.Contains($"XSRF-COOKIE-{port}=;", StringComparison.Ordinal));
        Assert.Contains(context.Response.Headers["Set-Cookie"], value => value.Contains($"XSRF-TOKEN-{port}=;", StringComparison.Ordinal));
    }

    [Fact]
    public void TryGetAndStoreAntiforgeryTokens_Retries_AfterClearingStaleCookies()
    {
        var port = new OptionsAtStartup().Web.Port;
        var context = new DefaultHttpContext();
        context.Request.Scheme = "https";
        context.Request.Path = "/api/v0/session/enabled";
        context.Request.Headers.Cookie = $"XSRF-COOKIE-{port}=stale-cookie; XSRF-TOKEN-{port}=stale-request";

        var expectedTokens = new AntiforgeryTokenSet("fresh-request", "fresh-cookie", "X-CSRF-TOKEN", $"XSRF-COOKIE-{port}");
        var antiforgery = new Mock<IAntiforgery>();
        antiforgery
            .SetupSequence(mock => mock.GetAndStoreTokens(context))
            .Throws(new AntiforgeryValidationException("The antiforgery token could not be decrypted.", new CryptographicException("The key {abc} was not found in the key ring.")))
            .Returns(expectedTokens);

        var tokens = AntiforgeryCookieRecovery.TryGetAndStoreTokens(context, antiforgery.Object, port, _ => { });

        Assert.Same(expectedTokens, tokens);
        antiforgery.Verify(mock => mock.GetAndStoreTokens(context), Times.Exactly(2));
        Assert.Contains(context.Response.Headers["Set-Cookie"], value => value.Contains($"XSRF-COOKIE-{port}=;", StringComparison.Ordinal));
        Assert.Contains(context.Response.Headers["Set-Cookie"], value => value.Contains($"XSRF-TOKEN-{port}=;", StringComparison.Ordinal));
    }

    private static void SetAppDirectory(string value)
    {
        var property = typeof(Program).GetProperty(nameof(Program.AppDirectory), BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        Assert.NotNull(property);
        var setter = property!.GetSetMethod(nonPublic: true);
        Assert.NotNull(setter);
        setter!.Invoke(null, new object[] { value });
    }
}
