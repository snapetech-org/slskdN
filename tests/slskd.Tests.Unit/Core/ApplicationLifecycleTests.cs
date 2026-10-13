// <copyright file="ApplicationLifecycleTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Moq;
using Serilog;
using Serilog.Core;
using Serilog.Events;
using slskd.Configuration;
using slskd.Core.API;
using slskd.Events;
using slskd.Files;
using slskd.Integrations.Notifications;
using slskd.Integrations.VPN;
using slskd.Messaging;
using slskd.Relay;
using slskd.Search;
using slskd.Shares;
using slskd.Tests.Unit;
using slskd.Transfers;
using slskd.Transfers.API;
using slskd.Users;
using Soulseek;
using Xunit;

namespace slskd.Tests.Unit.Core;

[Collection(StaticEventCollection.Name)]
public class ApplicationLifecycleTests
{
    [Fact]
    public void DownloadDeniedEvent_EscapesPeerFieldsBeforeLogging()
    {
        var sink = new CapturingLogSink();
        var originalLogger = Log.Logger;
        using var logger = new LoggerConfiguration()
            .MinimumLevel.Verbose()
            .WriteTo.Sink(sink)
            .CreateLogger();
        Log.Logger = logger;

        Application? application = null;
        try
        {
            application = CreateApplication(
                new TestOptionsMonitor<Options>(new Options()),
                new ManagedState<State>(),
                new ManagedState<ShareState>(),
                new ManagedState<RelayState>(),
                out _,
                out var soulseekClient);

            soulseekClient.Raise(
                client => client.DownloadDenied += null,
                new DownloadDeniedEventArgs("peer\r\ninjected", "track\r\nname.flac", "denied\r\nwith reason"));

            var entry = Assert.Single(sink.Events, logEvent => logEvent.RenderMessage().StartsWith("Download of ", StringComparison.Ordinal));
            var rendered = entry.RenderMessage();

            Assert.Contains("track\\r\\nname.flac", rendered);
            Assert.Contains("peer\\r\\ninjected", rendered);
            Assert.Contains("denied\\r\\nwith reason", rendered);
            Assert.DoesNotContain("\r\n", rendered);
        }
        finally
        {
            application?.Dispose();
            Log.Logger = originalLogger;
        }
    }

    [Fact]
    public void WatchedUserStatus_UpdatesSharedApplicationState()
    {
        var applicationState = new ManagedState<State>();
        var trackedUsers = Array.Empty<User>();
        var watchedUsernames = Array.Empty<string>();
        var userService = new Mock<IUserService>();
        userService.SetupGet(service => service.Users).Returns(() => trackedUsers);
        userService.SetupGet(service => service.WatchedUsernames).Returns(() => watchedUsernames);

        Application? application = null;
        try
        {
            application = CreateApplication(
                new OptionsAtStartup(),
                new TestOptionsMonitor<Options>(new Options()),
                applicationState,
                new ManagedState<ShareState>(),
                new ManagedState<RelayState>(),
                out var hub,
                out var soulseekClient,
                out _,
                userServiceMock: userService);
            hub.Setup(client => client.SendCoreAsync(
                    It.IsAny<string>(),
                    It.IsAny<object?[]>(),
                    It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);

            trackedUsers = [new User { Username = "peer", Status = new Status { Presence = UserPresence.Online } }];
            watchedUsernames = ["peer"];
            soulseekClient.Raise(
                client => client.UserStatusChanged += null,
                null,
                new UserStatus("peer", UserPresence.Online, isPrivileged: false));

            var user = Assert.Single(applicationState.CurrentValue.Users);
            Assert.Equal("peer", user.Username);
            Assert.Equal(UserPresence.Online, user.Status.Presence);
        }
        finally
        {
            application?.Dispose();
        }
    }

    [Fact]
    public void WatchedUsersChanged_UpdatesSharedStateAfterRegistration()
    {
        var applicationState = new ManagedState<State>();
        var trackedUsers = Array.Empty<User>();
        var watchedUsernames = Array.Empty<string>();
        var userService = new Mock<IUserService>();
        userService.SetupGet(service => service.Users).Returns(() => trackedUsers);
        userService.SetupGet(service => service.WatchedUsernames).Returns(() => watchedUsernames);

        Application? application = null;
        try
        {
            application = CreateApplication(
                new OptionsAtStartup(),
                new TestOptionsMonitor<Options>(new Options()),
                applicationState,
                new ManagedState<ShareState>(),
                new ManagedState<RelayState>(),
                out var hub,
                out _,
                out _,
                userServiceMock: userService);
            hub.Setup(client => client.SendCoreAsync(
                    It.IsAny<string>(),
                    It.IsAny<object?[]>(),
                    It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);

            trackedUsers = [new User { Username = "peer", Status = new Status { Presence = UserPresence.Online } }];
            watchedUsernames = ["peer"];
            userService.Raise(service => service.WatchedUsersChanged += null, null, EventArgs.Empty);

            var user = Assert.Single(applicationState.CurrentValue.Users);
            Assert.Equal("peer", user.Username);
            Assert.Equal(UserPresence.Online, user.Status.Presence);
        }
        finally
        {
            application?.Dispose();
        }
    }

    [Fact]
    public async Task EnqueueDownload_RepeatedQueueLimitDenials_UsesSnapshotUntilUploadStateChanges()
    {
        var sink = new CapturingLogSink();
        var originalLogger = Log.Logger;
        using var logger = new LoggerConfiguration()
            .MinimumLevel.Verbose()
            .WriteTo.Sink(sink)
            .CreateLogger();
        Log.Logger = logger;

        var configuredOptions = new Options
        {
            Global = new Options.GlobalOptions
            {
                Limits = new Options.LimitsOptions
                {
                    Queued = new Options.LimitsOptions.Limits { Files = 1 },
                },
            },
        };
        var shareService = new Mock<IShareService>();
        shareService.Setup(service => service.ResolveFileAsync("track.flac"))
            .ReturnsAsync(("share", "track.flac", 100L));
        var userService = new Mock<IUserService>();
        userService.Setup(service => service.IsBlacklisted("peer", It.IsAny<IPAddress?>())).Returns(false);
        userService.Setup(service => service.GetOrFetchGroupAsync("peer", false)).ReturnsAsync(Application.DefaultGroup);
        var uploadService = new Mock<slskd.Transfers.Uploads.IUploadService>();
        uploadService.Setup(service => service.Summarize(
                It.IsAny<System.Linq.Expressions.Expression<Func<slskd.Transfers.Transfer, bool>>>()))
            .Returns((1, 100L));

        Application? application = null;
        Mock<IClientProxy>? hub = null;
        try
        {
            application = CreateApplication(
                new OptionsAtStartup(),
                new TestOptionsMonitor<Options>(configuredOptions),
                new ManagedState<State>(),
                new ManagedState<ShareState>(),
                new ManagedState<RelayState>(),
                out hub,
                out var soulseekClient,
                out _,
                shareServiceMock: shareService,
                userServiceMock: userService,
                uploadServiceMock: uploadService);
            hub.Setup(client => client.SendCoreAsync(
                    It.IsAny<string>(),
                    It.IsAny<object?[]>(),
                    It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);

            var enqueueMethod = typeof(Application).GetMethod(
                "EnqueueDownload",
                BindingFlags.Instance | BindingFlags.NonPublic)
                ?? throw new InvalidOperationException("EnqueueDownload method was not found.");
            Task AttemptEnqueue() => (Task)(enqueueMethod.Invoke(application, [
                "peer",
                new IPEndPoint(IPAddress.Loopback, 50_000),
                "track.flac",
            ]) ?? throw new InvalidOperationException("EnqueueDownload returned no task."));

            await Assert.ThrowsAsync<DownloadEnqueueException>(AttemptEnqueue);
            await Assert.ThrowsAsync<DownloadEnqueueException>(AttemptEnqueue);

            uploadService.Verify(service => service.Summarize(
                It.IsAny<System.Linq.Expressions.Expression<Func<slskd.Transfers.Transfer, bool>>>()), Times.Once);
            Assert.Single(sink.Events, logEvent =>
                logEvent.Level == LogEventLevel.Warning
                && logEvent.RenderMessage().Contains("[UPLOAD-DIAG] Rejected upload enqueue request", StringComparison.Ordinal));

            var transfer = new Soulseek.Transfer(
                TransferDirection.Upload,
                "peer",
                "track.flac",
                token: 1,
                state: TransferStates.Queued,
                size: 100,
                startOffset: 0);
            var stateArgs = (TransferStateChangedEventArgs)(typeof(TransferStateChangedEventArgs)
                .GetConstructor(
                    BindingFlags.Instance | BindingFlags.NonPublic,
                    binder: null,
                    types: [typeof(TransferStates), typeof(Soulseek.Transfer)],
                    modifiers: null)
                ?? throw new InvalidOperationException("Transfer state event constructor was not found."))
                .Invoke([TransferStates.Requested, transfer]);
            soulseekClient.Raise(client => client.TransferStateChanged += null, stateArgs);

            await Assert.ThrowsAsync<DownloadEnqueueException>(AttemptEnqueue);
            uploadService.Verify(service => service.Summarize(
                It.IsAny<System.Linq.Expressions.Expression<Func<slskd.Transfers.Transfer, bool>>>()), Times.Exactly(2));
            Assert.Equal(2, sink.Events.Count(logEvent =>
                logEvent.Level == LogEventLevel.Warning
                && logEvent.RenderMessage().Contains("[UPLOAD-DIAG] Rejected upload enqueue request", StringComparison.Ordinal)));
        }
        finally
        {
            application?.Dispose();
            Log.Logger = originalLogger;
        }
    }

    [Fact]
    public void ProgramLogEmitted_ObservesSignalRSendFailure()
    {
        var sink = new CapturingLogSink();
        var originalLogger = Log.Logger;
        using var logger = new LoggerConfiguration()
            .MinimumLevel.Verbose()
            .WriteTo.Sink(sink)
            .CreateLogger();
        Log.Logger = logger;

        var logClient = new Mock<IClientProxy>();
        logClient
            .Setup(client => client.SendCoreAsync(
                It.IsAny<string>(),
                It.IsAny<object?[]>(),
                It.IsAny<System.Threading.CancellationToken>()))
            .Returns(Task.FromException(new InvalidOperationException("send failed")));
        var logHubClients = new Mock<IHubClients>();
        logHubClients.SetupGet(clients => clients.All).Returns(logClient.Object);
        var logsHubContext = new Mock<IHubContext<LogsHub>>();
        logsHubContext.SetupGet(context => context.Clients).Returns(logHubClients.Object);

        Application? application = null;
        try
        {
            application = CreateApplication(
                new OptionsAtStartup(),
                new TestOptionsMonitor<Options>(new Options()),
                new ManagedState<State>(),
                new ManagedState<ShareState>(),
                new ManagedState<RelayState>(),
                out _,
                out _,
                out _,
                logsHubContext: logsHubContext);

            var raiseMethod = typeof(Program).GetMethod(
                "RaiseLogEmitted",
                BindingFlags.Static | BindingFlags.NonPublic)
                ?? throw new InvalidOperationException("Program.RaiseLogEmitted method was not found.");
            raiseMethod.Invoke(null, [new LogRecord
            {
                Context = "test",
                Message = "test",
                Timestamp = DateTime.UtcNow,
            }]);

            var failure = Assert.Single(
                sink.Events,
                logEvent => logEvent.RenderMessage().StartsWith("Failed to emit log record to connected clients:", StringComparison.Ordinal));
            Assert.Contains("send failed", failure.RenderMessage(), StringComparison.Ordinal);
            logClient.Verify(
                client => client.SendCoreAsync(
                    LogHubMethods.Log,
                    It.IsAny<object?[]>(),
                    It.IsAny<System.Threading.CancellationToken>()),
                Times.Once);
        }
        finally
        {
            application?.Dispose();
            Log.Logger = originalLogger;
        }
    }

    [Fact]
    public void OptionsMonitor_ObservesFailuresBeforeUpdateHandlerCatch()
    {
        var sink = new CapturingLogSink();
        var originalLogger = Log.Logger;
        using var logger = new LoggerConfiguration()
            .MinimumLevel.Verbose()
            .WriteTo.Sink(sink)
            .CreateLogger();
        Log.Logger = logger;

        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        Application? application = null;
        try
        {
            application = CreateApplication(
                optionsMonitor,
                new ManagedState<State>(),
                new ManagedState<ShareState>(),
                new ManagedState<RelayState>(),
                out _,
                out _);

            var optionsSyncRoot = (SemaphoreSlim)(typeof(Application)
                .GetProperty("OptionsSyncRoot", BindingFlags.Instance | BindingFlags.NonPublic)
                ?.GetValue(application)
                ?? throw new InvalidOperationException("Application.OptionsSyncRoot property was not found."));
            optionsSyncRoot.Dispose();

            var exception = Record.Exception(() => optionsMonitor.RaiseOnChange(new Options()));

            Assert.Null(exception);
            var failure = Assert.Single(
                sink.Events,
                logEvent => logEvent.RenderMessage().StartsWith("Unexpected failure escaped option update handler:", StringComparison.Ordinal));
            Assert.Contains("ObjectDisposedException", failure.RenderMessage(), StringComparison.Ordinal);
        }
        finally
        {
            application?.Dispose();
            Log.Logger = originalLogger;
        }
    }

    [Fact]
    public void CreateStartupSoulseekClientOptionsPatch_ConfiguresIncomingConnectionOptions()
    {
        var patch = Application.CreateStartupSoulseekClientOptionsPatch(
            new OptionsAtStartup(),
            static (_, _) => { },
            static (_, _) => Task.FromResult<UserInfo>(null!),
            static (_, _) => Task.FromResult<BrowseResponse>(null!),
            static (_, _, _, _) => Task.FromResult<IEnumerable<Soulseek.Directory>>(Array.Empty<Soulseek.Directory>()),
            static (_, _, _) => Task.CompletedTask,
            static (_, _, _) => Task.FromResult<SearchResponse?>(null),
            static (_, _, _) => Task.FromResult<int?>(null));

        Assert.NotNull(patch.PeerConnectionOptions);
        Assert.NotNull(patch.TransferConnectionOptions);
        Assert.NotNull(patch.IncomingConnectionOptions);
        Assert.NotNull(patch.PeerObfuscationOptions);
        Assert.Equal(patch.PeerConnectionOptions.ReadBufferSize, patch.IncomingConnectionOptions.ReadBufferSize);
        Assert.Equal(patch.PeerConnectionOptions.WriteBufferSize, patch.IncomingConnectionOptions.WriteBufferSize);
        Assert.Equal(patch.PeerConnectionOptions.InactivityTimeout, patch.IncomingConnectionOptions.InactivityTimeout);
        Assert.Equal(60_000, patch.PeerConnectionOptions.InactivityTimeout);
        Assert.Equal(60_000, patch.TransferConnectionOptions.InactivityTimeout);
    }

    [Fact]
    public void CreateStartupSoulseekClientOptionsPatch_UsesMtuCallbackForServerOnly()
    {
        var options = new OptionsAtStartup
        {
            Soulseek = new Options.SoulseekOptions
            {
                Connection = new Options.SoulseekOptions.ConnectionOptions { Mtu = 1500 },
            },
        };
        var serverMtuCalls = 0;
        var patch = Application.CreateStartupSoulseekClientOptionsPatch(
            options,
            static (_, _) => { },
            static (_, _) => Task.FromResult<UserInfo>(null!),
            static (_, _) => Task.FromResult<BrowseResponse>(null!),
            static (_, _, _, _) => Task.FromResult<IEnumerable<Soulseek.Directory>>(Array.Empty<Soulseek.Directory>()),
            static (_, _, _) => Task.CompletedTask,
            static (_, _, _) => Task.FromResult<SearchResponse?>(null),
            static (_, _, _) => Task.FromResult<int?>(null),
            configureServerSocketMtuOptions: (_, connectionOptions) =>
            {
                Assert.Equal(1500, connectionOptions.Mtu);
                serverMtuCalls++;
            });

        using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        patch.ServerConnectionOptions.ConfigureSocket(socket);
        patch.DistributedConnectionOptions.ConfigureSocket(socket);

        Assert.Equal(1, serverMtuCalls);
    }

    [Theory]
    [InlineData(AddressFamily.InterNetwork, 1460)]
    [InlineData(AddressFamily.InterNetworkV6, 1440)]
    public void CalculateMaximumTcpSegmentSize_AccountsForIpAndTcpHeaders(AddressFamily family, int expected)
    {
        Assert.Equal(expected, Application.CalculateMaximumTcpSegmentSize(1500, family));
    }

    [Theory]
    [InlineData(1279, false)]
    [InlineData(1500, true)]
    [InlineData(9000, true)]
    [InlineData(9001, false)]
    public void SoulseekConnectionMtu_ValidatesConfiguredRange(int mtu, bool expectedValid)
    {
        var options = new Options.SoulseekOptions.ConnectionOptions { Mtu = mtu };
        var results = new List<ValidationResult>();

        var valid = Validator.TryValidateObject(options, new ValidationContext(options), results, validateAllProperties: true);

        Assert.Equal(expectedValid, valid);
    }

    [Fact]
    public void CreateStartupSoulseekClientOptionsPatch_DoesNotReapplyListenerSettings()
    {
        var patch = Application.CreateStartupSoulseekClientOptionsPatch(
            new OptionsAtStartup(),
            static (_, _) => { },
            static (_, _) => Task.FromResult<UserInfo>(null!),
            static (_, _) => Task.FromResult<BrowseResponse>(null!),
            static (_, _, _, _) => Task.FromResult<IEnumerable<Soulseek.Directory>>(Array.Empty<Soulseek.Directory>()),
            static (_, _, _) => Task.CompletedTask,
            static (_, _, _) => Task.FromResult<SearchResponse?>(null),
            static (_, _, _) => Task.FromResult<int?>(null));

        Assert.Null(patch.EnableListener);
        Assert.Null(patch.ListenIPAddress);
        Assert.Null(patch.ListenPort);
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public void CompileSearchRequestFilters_PreservesConfiguredCaseMode(
        bool caseSensitive,
        bool expectedMatch)
    {
        var filters = Application.CompileSearchRequestFilters(["^secret$"], caseSensitive);

        Assert.Equal(expectedMatch, filters[0].IsMatch("SECRET"));
    }

    [Fact]
    public void FormatCompletedTransferProgress_ClampsNegativeAverageSpeed()
    {
        var formatted = Application.FormatCompletedTransferProgress(
            bytesTransferred: 0,
            size: 40_203_136,
            percentComplete: 0,
            averageSpeed: -18_400_000_000);

        Assert.Equal(" (0/40203136 = 0%) @ 0.0 bytes/s", formatted);
    }

    [Fact]
    public void SoulseekDownloadEvents_AccountProgressAndTerminalRemainder()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var applicationState = new ManagedState<State>();
        var shareState = new ManagedState<ShareState>();
        var relayState = new ManagedState<RelayState>();
        var trafficAccounting = new Mock<slskd.Transfers.MultiSource.Metrics.ITrafficAccountingService>();
        trafficAccounting
            .Setup(service => service.CommitSoulseekDownloadAsync(41, 175, 100, It.IsAny<System.Threading.CancellationToken>()))
            .Returns(Task.CompletedTask);

        var application = CreateApplication(
            new OptionsAtStartup(),
            optionsMonitor,
            applicationState,
            shareState,
            relayState,
            out _,
            out var soulseekClient,
            out _,
            trafficAccounting);

        var inProgress = new Soulseek.Transfer(
            Soulseek.TransferDirection.Download,
            "peer",
            "track.flac",
            token: 41,
            state: Soulseek.TransferStates.InProgress,
            size: 1_000,
            startOffset: 100,
            bytesTransferred: 150);
        var progressArgs = (Soulseek.TransferProgressUpdatedEventArgs)(typeof(Soulseek.TransferProgressUpdatedEventArgs)
            .GetConstructor(
                BindingFlags.Instance | BindingFlags.NonPublic,
                binder: null,
                types: [typeof(long), typeof(Soulseek.Transfer)],
                modifiers: null)
            ?? throw new InvalidOperationException("Transfer progress event constructor was not found."))
            .Invoke([100L, inProgress]);

        soulseekClient.Raise(client => client.TransferProgressUpdated += null, this, progressArgs);

        var completed = new Soulseek.Transfer(
            Soulseek.TransferDirection.Download,
            "peer",
            "track.flac",
            token: 41,
            state: Soulseek.TransferStates.Completed | Soulseek.TransferStates.Succeeded,
            size: 1_000,
            startOffset: 100,
            bytesTransferred: 175);
        var stateArgs = (Soulseek.TransferStateChangedEventArgs)(typeof(Soulseek.TransferStateChangedEventArgs)
            .GetConstructor(
                BindingFlags.Instance | BindingFlags.NonPublic,
                binder: null,
                types: [typeof(Soulseek.TransferStates), typeof(Soulseek.Transfer)],
                modifiers: null)
            ?? throw new InvalidOperationException("Transfer state event constructor was not found."))
            .Invoke([Soulseek.TransferStates.InProgress, completed]);

        soulseekClient.Raise(client => client.TransferStateChanged += null, this, stateArgs);

        trafficAccounting.Verify(service => service.RecordSoulseekDownloadProgress(41, 150, 100), Times.Once);
        trafficAccounting.Verify(service => service.CommitSoulseekDownloadAsync(41, 175, 100, It.IsAny<System.Threading.CancellationToken>()), Times.Once);
        application.Dispose();
    }

    [Fact]
    public void Dispose_DetachesManagedStateSubscriptions()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var applicationState = new ManagedState<State>();
        var shareState = new ManagedState<ShareState>();
        var relayState = new ManagedState<RelayState>();

        var application = CreateApplication(optionsMonitor, applicationState, shareState, relayState, out var applicationHub, out _);
        application.Dispose();

        shareState.SetValue(_ => new ShareState { Ready = true, Files = 7, Directories = 3 });
        relayState.SetValue(_ => new RelayState { Mode = RelayMode.Agent });
        applicationState.SetValue(state => state with { PendingReconnect = true });

        Assert.False(applicationState.CurrentValue.Shares.Ready);
        Assert.Equal(0, applicationState.CurrentValue.Shares.Files);
        Assert.Equal(0, applicationState.CurrentValue.Shares.Directories);
        Assert.NotEqual(RelayMode.Agent, applicationState.CurrentValue.Relay.Mode);
        applicationHub.Verify(
            hub => hub.SendCoreAsync(
                ApplicationHubMethods.State,
                It.IsAny<object?[]>(),
                default),
            Times.Never);
    }

    [Fact]
    public void Dispose_UnsubscribesOptionsMonitor()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var application = CreateApplication(
            optionsMonitor,
            new ManagedState<State>(),
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out _);

        Assert.Equal(2, optionsMonitor.ListenerCount);

        application.Dispose();

        Assert.Equal(1, optionsMonitor.ListenerCount);
    }

    [Fact]
    public void Dispose_UnsubscribesGlobalAndSoulseekEvents()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var programLogEmittedListenersBefore = GetStaticEventInvocationCount(typeof(Program), "LogEmitted");
        var clockEveryMinuteListenersBefore = GetStaticEventInvocationCount(typeof(Clock), "EveryMinute");
        var application = CreateApplication(
            optionsMonitor,
            new ManagedState<State>(),
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out var soulseekClient);

        Assert.Equal(programLogEmittedListenersBefore + 1, GetStaticEventInvocationCount(typeof(Program), "LogEmitted"));
        Assert.Equal(clockEveryMinuteListenersBefore + 1, GetStaticEventInvocationCount(typeof(Clock), "EveryMinute"));

        application.Dispose();

        Assert.Equal(programLogEmittedListenersBefore, GetStaticEventInvocationCount(typeof(Program), "LogEmitted"));
        Assert.Equal(clockEveryMinuteListenersBefore, GetStaticEventInvocationCount(typeof(Clock), "EveryMinute"));
        soulseekClient.VerifyRemove(x => x.DiagnosticGenerated -= It.IsAny<EventHandler<Soulseek.Diagnostics.DiagnosticEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.TransferStateChanged -= It.IsAny<EventHandler<TransferStateChangedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.TransferProgressUpdated -= It.IsAny<EventHandler<TransferProgressUpdatedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.BrowseProgressUpdated -= It.IsAny<EventHandler<BrowseProgressUpdatedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.UserStatusChanged -= It.IsAny<EventHandler<UserStatus>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.PrivateMessageReceived -= It.IsAny<EventHandler<PrivateMessageReceivedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.PrivateRoomMembershipAdded -= It.IsAny<EventHandler<string>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.PrivateRoomMembershipRemoved -= It.IsAny<EventHandler<string>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.PrivateRoomModerationAdded -= It.IsAny<EventHandler<string>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.PrivateRoomModerationRemoved -= It.IsAny<EventHandler<string>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.RoomMessageReceived -= It.IsAny<EventHandler<RoomMessageReceivedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.Disconnected -= It.IsAny<EventHandler<SoulseekClientDisconnectedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.Connected -= It.IsAny<EventHandler>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.LoggedIn -= It.IsAny<EventHandler>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.StateChanged -= It.IsAny<EventHandler<SoulseekClientStateChangedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.DownloadDenied -= It.IsAny<EventHandler<DownloadDeniedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.DownloadFailed -= It.IsAny<EventHandler<DownloadFailedEventArgs>>(), Times.Once);
        soulseekClient.VerifyRemove(x => x.ExcludedSearchPhrasesReceived -= It.IsAny<EventHandler<IReadOnlyCollection<string>>>(), Times.Once);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task OptionsChanged_WhenListenerReconfigurationSucceeds_DoesNotSetPendingReconnect(bool changeIpAddress)
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var applicationState = new ManagedState<State>();
        var reconfigured = new TaskCompletionSource<object?>();

        var application = CreateApplication(
            optionsMonitor,
            applicationState,
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out var soulseekClient);

        soulseekClient.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
        soulseekClient
            .Setup(client => client.ReconfigureOptionsAsync(
                It.IsAny<SoulseekClientOptionsPatch>(),
                It.IsAny<System.Threading.CancellationToken?>()))
            .Callback(() => reconfigured.TrySetResult(null))
            .ReturnsAsync(false);

        optionsMonitor.Set(new Options
        {
            Soulseek = new Options.SoulseekOptions
            {
                ListenIpAddress = changeIpAddress ? "0.0.0.1" : "0.0.0.0",
                ListenPort = changeIpAddress ? 50300 : 50301,
            },
        });

        await reconfigured.Task.WaitAsync(TimeSpan.FromSeconds(5));

        Assert.False(applicationState.CurrentValue.PendingReconnect);
        application.Dispose();
    }

    [Fact]
    public async Task OptionsChanged_WhenCorsChanges_SetsPendingRestart()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var applicationState = new ManagedState<State>();
        var restartPending = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);
        using var stateRegistration = applicationState.OnChange(change =>
        {
            if (change.Current.PendingRestart)
            {
                restartPending.TrySetResult(null);
            }
        });

        var application = CreateApplication(
            optionsMonitor,
            applicationState,
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out _);

        optionsMonitor.Set(new Options
        {
            Web = new Options.WebOptions
            {
                Cors = new Options.WebOptions.CorsOptions
                {
                    Enabled = true,
                    AllowedOrigins = ["https://example.invalid"],
                },
            },
        });

        await restartPending.Task.WaitAsync(TimeSpan.FromSeconds(5));

        Assert.True(applicationState.CurrentValue.PendingRestart);
        application.Dispose();
    }

    [Fact]
    public void CorsOptions_AllFieldsRequireRestart()
    {
        var properties = typeof(Options.WebOptions.CorsOptions).GetProperties(BindingFlags.Instance | BindingFlags.Public);

        Assert.All(properties, property => Assert.NotNull(property.GetCustomAttribute<RequiresRestartAttribute>()));
    }

    [Fact]
    public async Task PruneSearches_HonorsConfiguredCleanupInterval()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options
        {
            Filters = new Options.FiltersOptions
            {
                SearchRetention = new Options.FiltersOptions.SearchRetentionOptions
                {
                    CleanupIntervalSeconds = 3600,
                },
            },
        });
        var application = CreateApplication(
            optionsMonitor,
            new ManagedState<State>(),
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out _,
            out var searchService);
        searchService
            .Setup(service => service.CleanupAsync(30, 250))
            .ReturnsAsync(0);
        var startedAt = new DateTime(2026, 7, 15, 12, 0, 0, DateTimeKind.Utc);

        await application.PruneSearches(startedAt);
        await application.PruneSearches(startedAt.AddMinutes(59));
        await application.PruneSearches(startedAt.AddHours(1));

        searchService.Verify(service => service.CleanupAsync(30, 250), Times.Exactly(2));
        application.Dispose();
    }

    [Fact]
    public async Task PruneSearches_WhenCleanupFails_RetriesAtNextEvaluation()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var application = CreateApplication(
            optionsMonitor,
            new ManagedState<State>(),
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out _,
            out var searchService);
        searchService
            .SetupSequence(service => service.CleanupAsync(30, 250))
            .ThrowsAsync(new InvalidOperationException("cleanup failed"))
            .ReturnsAsync(0);
        var startedAt = new DateTime(2026, 7, 15, 12, 0, 0, DateTimeKind.Utc);

        await application.PruneSearches(startedAt);
        await application.PruneSearches(startedAt.AddMinutes(5));

        searchService.Verify(service => service.CleanupAsync(30, 250), Times.Exactly(2));
        application.Dispose();
    }

    [Fact]
    public async Task PruneSearches_WhenCleanupIsRunning_DoesNotOverlap()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var application = CreateApplication(
            optionsMonitor,
            new ManagedState<State>(),
            new ManagedState<ShareState>(),
            new ManagedState<RelayState>(),
            out _,
            out _,
            out var searchService);
        var cleanupCompletion = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
        searchService
            .Setup(service => service.CleanupAsync(30, 250))
            .Returns(cleanupCompletion.Task);
        var startedAt = new DateTime(2026, 7, 15, 12, 0, 0, DateTimeKind.Utc);

        var firstCleanup = application.PruneSearches(startedAt);
        await application.PruneSearches(startedAt.AddMinutes(5));

        searchService.Verify(service => service.CleanupAsync(30, 250), Times.Once);
        cleanupCompletion.SetResult(0);
        await firstCleanup;
        application.Dispose();
    }

    private static Application CreateApplication(
        OptionsAtStartup optionsAtStartup,
        TestOptionsMonitor<Options> optionsMonitor,
        ManagedState<State> applicationState,
        ManagedState<ShareState> shareState,
        ManagedState<RelayState> relayState,
        out Mock<IClientProxy> applicationHub,
        out Mock<ISoulseekClient> soulseekClient)
    {
        return CreateApplication(
            optionsAtStartup,
            optionsMonitor,
            applicationState,
            shareState,
            relayState,
            out applicationHub,
            out soulseekClient,
            out _);
    }

    private sealed class CapturingLogSink : ILogEventSink
    {
        private readonly ConcurrentBag<LogEvent> events = [];

        public IReadOnlyCollection<LogEvent> Events => events.ToArray();

        public void Emit(LogEvent logEvent) => events.Add(logEvent);
    }

    private static Application CreateApplication(
        OptionsAtStartup optionsAtStartup,
        TestOptionsMonitor<Options> optionsMonitor,
        ManagedState<State> applicationState,
        ManagedState<ShareState> shareState,
        ManagedState<RelayState> relayState,
        out Mock<IClientProxy> applicationHub,
        out Mock<ISoulseekClient> soulseekClient,
        out Mock<ISearchService> searchService,
        Mock<slskd.Transfers.MultiSource.Metrics.ITrafficAccountingService>? trafficAccounting = null,
        Mock<IHubContext<LogsHub>>? logsHubContext = null,
        Mock<IShareService>? shareServiceMock = null,
        Mock<IUserService>? userServiceMock = null,
        Mock<slskd.Transfers.Uploads.IUploadService>? uploadServiceMock = null)
    {
        applicationHub = new Mock<IClientProxy>();
        soulseekClient = new Mock<ISoulseekClient>();
        var vpnService = new VPNService(
            optionsAtStartup,
            optionsMonitor,
            Mock.Of<IStateMutator<State>>(),
            soulseekClient.Object,
            Mock.Of<IHttpClientFactory>());
        var connectionWatchdog = new ConnectionWatchdog(
            soulseekClient.Object,
            vpnService,
            optionsMonitor,
            optionsAtStartup,
            applicationState);
        var relayService = new Mock<IRelayService>();
        relayService.SetupGet(x => x.StateMonitor).Returns(relayState);
        relayService.SetupGet(x => x.Client).Returns(new NullRelayClient());

        var shareService = shareServiceMock ?? new Mock<IShareService>();
        shareService.SetupGet(x => x.StateMonitor).Returns(shareState);
        shareService.Setup(service => service.InitializeAsync(It.IsAny<bool>())).Returns(Task.CompletedTask);

        var uploadService = uploadServiceMock ?? new Mock<slskd.Transfers.Uploads.IUploadService>();
        uploadService
            .Setup(service => service.List(
                It.IsAny<System.Linq.Expressions.Expression<Func<slskd.Transfers.Transfer, bool>>>(),
                It.IsAny<bool>()))
            .Returns([]);

        var downloadService = new Mock<slskd.Transfers.Downloads.IDownloadService>();
        downloadService
            .Setup(service => service.List(
                It.IsAny<System.Linq.Expressions.Expression<Func<slskd.Transfers.Transfer, bool>>>(),
                It.IsAny<bool>()))
            .Returns([]);

        var transferService = new Mock<ITransferService>();
        transferService.SetupGet(service => service.Uploads).Returns(uploadService.Object);
        transferService.SetupGet(service => service.Downloads).Returns(downloadService.Object);

        searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.ListAsync(
                It.IsAny<System.Linq.Expressions.Expression<Func<slskd.Search.Search, bool>>>(),
                It.IsAny<int>(),
                It.IsAny<int>()))
            .ReturnsAsync([]);

        var hubClients = new Mock<IHubClients>();
        hubClients.SetupGet(x => x.All).Returns(applicationHub.Object);

        var transferHubClients = new Mock<IHubClients>();
        transferHubClients.SetupGet(x => x.All).Returns(applicationHub.Object);
        var transfersHub = new Mock<IHubContext<TransfersHub>>();
        transfersHub.SetupGet(x => x.Clients).Returns(transferHubClients.Object);

        var appHubContext = new Mock<IHubContext<ApplicationHub>>();
        appHubContext.SetupGet(x => x.Clients).Returns(hubClients.Object);
        var eventService = new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>());

        return new Application(
            optionsAtStartup,
            optionsMonitor,
            applicationState,
            soulseekClient.Object,
            new FileService(optionsMonitor),
            connectionWatchdog,
            transferService.Object,
            Mock.Of<IBrowseTracker>(),
            Mock.Of<IRoomService>(),
            userServiceMock?.Object ?? Mock.Of<IUserService>(),
            Mock.Of<IMessagingService>(),
            shareService.Object,
            searchService.Object,
            Mock.Of<INotificationService>(),
            relayService.Object,
            appHubContext.Object,
            logsHubContext?.Object ?? Mock.Of<IHubContext<LogsHub>>(),
            transfersHub.Object,
            new EventBus(eventService),
            eventService,
            Mock.Of<IServiceProvider>(),
            Mock.Of<IServiceScopeFactory>(),
            Mock.Of<slskd.NowPlaying.NowPlayingService>(),
            trafficAccounting?.Object ?? Mock.Of<slskd.Transfers.MultiSource.Metrics.ITrafficAccountingService>());
    }

    private static Application CreateApplication(
        TestOptionsMonitor<Options> optionsMonitor,
        ManagedState<State> applicationState,
        ManagedState<ShareState> shareState,
        ManagedState<RelayState> relayState,
        out Mock<IClientProxy> applicationHub,
        out Mock<ISoulseekClient> soulseekClient)
    {
        return CreateApplication(
            new OptionsAtStartup(),
            optionsMonitor,
            applicationState,
            shareState,
            relayState,
            out applicationHub,
            out soulseekClient);
    }

    private static Application CreateApplication(
        TestOptionsMonitor<Options> optionsMonitor,
        ManagedState<State> applicationState,
        ManagedState<ShareState> shareState,
        ManagedState<RelayState> relayState,
        out Mock<IClientProxy> applicationHub,
        out Mock<ISoulseekClient> soulseekClient,
        out Mock<ISearchService> searchService)
    {
        return CreateApplication(
            new OptionsAtStartup(),
            optionsMonitor,
            applicationState,
            shareState,
            relayState,
            out applicationHub,
            out soulseekClient,
            out searchService);
    }

    private static int GetStaticEventInvocationCount(Type type, string eventName)
    {
        var field = type.GetField(eventName, BindingFlags.Static | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException($"{type.FullName}.{eventName} backing field was not found.");

        return (field.GetValue(null) as MulticastDelegate)?.GetInvocationList().Length ?? 0;
    }
}
