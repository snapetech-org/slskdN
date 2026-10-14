// <copyright file="ApplicationControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Core.API;

using System;
using System.Linq;
using System.Reflection;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Moq;
using slskd;
using slskd.Core.API;
using Xunit;

public class ApplicationControllerTests
{

    [Fact]
    public void GetRestartArguments_DropsExecutablePath()
    {
        var args = ApplicationController.GetRestartArguments(new[] { "/usr/lib/slskd/slskd", "--config", "/etc/slskd/slskd.yml" }).ToList();

        Assert.Equal(new[] { "--config", "/etc/slskd/slskd.yml" }, args);
    }

    [Fact]
    public void State_ExposesRuntimeIdentityForTheRunningProcess()
    {
        var originalAppDirectory = Program.AppDirectory;
        var originalConfigurationFile = Program.ConfigurationFile;

        try
        {
            SetProgramValue(nameof(Program.AppDirectory), "/tmp/slskdn-app");
            SetProgramValue(nameof(Program.ConfigurationFile), "/tmp/slskdn-app/slskd.yml");

            var state = new State();

            Assert.Equal(Program.SemanticVersion, state.Version.Current);
            Assert.Equal(Program.ExecutablePath, state.Runtime.ExecutablePath);
            Assert.Equal(Program.BaseDirectory, state.Runtime.BaseDirectory);
            Assert.Equal("/tmp/slskdn-app", state.Runtime.AppDirectory);
            Assert.Equal("/tmp/slskdn-app/slskd.yml", state.Runtime.ConfigurationFile);
            Assert.Equal(Program.ProcessId, state.Runtime.ProcessId);
        }
        finally
        {
            SetProgramValue(nameof(Program.AppDirectory), originalAppDirectory);
            SetProgramValue(nameof(Program.ConfigurationFile), originalConfigurationFile);
        }
    }

    [Fact]
    public void GetBuild_ReturnsPublicVersionStateWithoutForcingWhenAlreadyChecked()
    {
        var application = new Mock<IApplication>();
        var controller = CreateController(
            application: application,
            state: new State
            {
                Version = new VersionState
                {
                    CheckedAt = DateTimeOffset.UtcNow,
                    IsUpdateAvailable = true,
                    Latest = "2026050500-slskdn.221",
                    LatestTag = "build-main-2026050500-slskdn.221",
                    LatestUrl = "https://github.com/snapetech-org/slskdN/releases/tag/build-main-2026050500-slskdn.221",
                },
            });

        var result = controller.GetBuild();

        var ok = Assert.IsType<OkObjectResult>(result);
        var version = Assert.IsType<VersionState>(ok.Value);
        Assert.Equal(Program.SemanticVersion, version.Current);
        Assert.Equal("2026050500-slskdn.221", version.Latest);
        Assert.True(version.IsUpdateAvailable);
        application.Verify(a => a.CheckVersionAsync(), Times.Never);
    }

    [Fact]
    public void GetBuild_DoesNotTriggerUpdateChecksForAnonymousRequests()
    {
        var application = new Mock<IApplication>();
        var controller = CreateController(application: application);

        controller.GetBuild(checkForUpdates: true);

        application.Verify(a => a.CheckVersionAsync(), Times.Never);
    }

    [Theory]
    [InlineData("build-main-2026050500-slskdn.221", "2026050500-slskdn.221")]
    [InlineData("v0.24.5-slskdn.186", "0.24.5-slskdn.186")]
    [InlineData("0.0.0-slskdn.manual.20260505010919.48e7e08771f8+abc", "0.0.0-slskdn.manual.20260505010919.48e7e08771f8")]
    public void NormalizeReleaseVersion_RemovesReleaseTagDecorations(string tag, string expected)
    {
        Assert.Equal(expected, GitHub.NormalizeReleaseVersion(tag));
    }

    [Theory]
    [InlineData("2026050400-slskdn.220", "2026050500-slskdn.221", true)]
    [InlineData("2026050500-slskdn.221", "2026050500-slskdn.221", false)]
    [InlineData("0.0.0-slskdn.manual.local", "2026050500-slskdn.221", true)]
    public void IsNewerVersionAvailable_HandlesSlskdnAndManualBuilds(string current, string latest, bool expected)
    {
        Assert.Equal(expected, GitHub.IsNewerVersionAvailable(current, latest));
    }

    [Fact]
    public void Loopback_WithNullBody_ReturnsBadRequest()
    {
        var controller = CreateController();

        var result = controller.Loopback(null!);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("Body is required", badRequest.Value);
    }


    private static void SetProgramValue(string propertyName, string value)
    {
        var property = typeof(Program).GetProperty(propertyName, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        Assert.NotNull(property);
        var setter = property!.GetSetMethod(nonPublic: true);
        Assert.NotNull(setter);
        setter!.Invoke(null, new object[] { value });
    }

    private static ApplicationController CreateController(
        Mock<IApplication>? application = null,
        State? state = null)
    {
        var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
        optionsMonitor.SetupGet(m => m.CurrentValue).Returns(new slskd.Options());

        var lifetime = new Mock<IHostApplicationLifetime>();
        var stateMonitor = new Mock<IStateMonitor<State>>();
        stateMonitor.SetupGet(m => m.CurrentValue).Returns(state ?? new State());

        return new ApplicationController(
            lifetime.Object,
            (application ?? new Mock<IApplication>()).Object,
            optionsMonitor.Object,
            stateMonitor.Object);
    }
}
