// <copyright file="VPNServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Integrations.VPN;

using System;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Moq;
using slskd.Integrations.VPN;
using Soulseek;
using Xunit;

public class VPNServiceTests
{
    [Fact]
    public async Task PollingObserver_WhenPortForwardingIsReady_UpdatesPublicAdvertisementWithoutRebindingListener()
    {
        Program.ApplyConfigurationOverlay(new OptionsOverlay());

        var optionsAtStartup = new OptionsAtStartup
        {
            Integration = new OptionsAtStartup.IntegrationOptions
            {
                Vpn = new OptionsAtStartup.IntegrationOptions.VpnOptions
                {
                    Enabled = true,
                    PollingInterval = 100,
                },
            },
        };

        var options = new Options
        {
            Integration = new Options.IntegrationOptions
            {
                Vpn = new Options.IntegrationOptions.VpnOptions
                {
                    PortForwarding = true,
                    Gluetun = new Options.IntegrationOptions.VpnOptions.GluetunVpnOptions
                    {
                        Url = "http://127.0.0.1:8010",
                    },
                },
            },
            Soulseek = new Options.SoulseekOptions
            {
                ListenPort = 50300,
            },
        };

        var soulseek = new Mock<ISoulseekClient>();
        soulseek.SetupGet(client => client.Options)
            .Returns(new SoulseekClientOptions(listenPort: 50300));
        soulseek.Setup(client => client.ReconfigureOptionsAsync(
                It.IsAny<SoulseekClientOptionsPatch>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var service = new VPNService(
            optionsAtStartup,
            new TestOptionsMonitor<Options>(options),
            Mock.Of<IStateMutator<State>>(),
            soulseek.Object,
            Mock.Of<IHttpClientFactory>());

        SetVpnClient(service, Mock.Of<IVPNClient>(client =>
            client.GetStatusAsync() == Task.FromResult(new VPNStatus
            {
                IsConnected = true,
                PublicIPAddress = IPAddress.Parse("212.104.215.84"),
                ForwardedPort = 38325,
            })));

        await InvokeObserverAsync(service);

        Assert.True(service.IsReady);
        Assert.Equal(38325, service.Status.ForwardedPort);
        Assert.Null(Program.ConfigurationOverlay?.Soulseek?.ListenPort);
        Assert.Equal(50300, soulseek.Object.Options.ListenPort);
        soulseek.Verify(client => client.ReconfigureOptionsAsync(
            It.Is<SoulseekClientOptionsPatch>(patch => patch.AdvertisedListenPort == 38325),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task PollingObserver_WhenVpnClientIsMisconfigured_SwallowsTimerCallbackException()
    {
        var optionsAtStartup = new OptionsAtStartup
        {
            Integration = new OptionsAtStartup.IntegrationOptions
            {
                Vpn = new OptionsAtStartup.IntegrationOptions.VpnOptions
                {
                    Enabled = true,
                    PollingInterval = 100,
                },
            },
        };

        var service = new VPNService(
            optionsAtStartup,
            new TestOptionsMonitor<Options>(new Options()),
            Mock.Of<IStateMutator<State>>(),
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IHttpClientFactory>());

        await InvokeObserverAsync(service);

        Assert.False(service.IsReady);
        Assert.False(service.Status.IsConnected);
    }

    private static async Task InvokeObserverAsync(VPNService service)
    {
        var observerMethod = typeof(VPNService).GetMethod(
            "ObserveCheckConnectionAsync",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("VPNService.ObserveCheckConnectionAsync method was not found.");

        var task = (Task?)observerMethod.Invoke(service, null)
            ?? throw new InvalidOperationException("VPNService.ObserveCheckConnectionAsync did not return a task.");

        await task;
    }

    private static void SetVpnClient(VPNService service, IVPNClient client)
    {
        var clientProperty = typeof(VPNService).GetProperty(
            "Client",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("VPNService.Client property was not found.");

        clientProperty.SetValue(service, client);
    }
}
