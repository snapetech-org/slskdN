// <copyright file="UsersControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Users
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Threading;
    using Microsoft.AspNetCore.Mvc;
    using Moq;
    using slskd.Common.Security;
    using slskd.Users;
    using slskd.Users.API;
    using Soulseek;
    using Xunit;

    public class UsersControllerTests
    {
        [Fact]
        public void Group_Returns_User_Group()
        {
            // Arrange
            var userServiceMock = new Mock<IUserService>();
            userServiceMock.Setup(x => x.GetGroup("testuser")).Returns("privileged");

            var soulseekClientMock = new Mock<ISoulseekClient>();
            var browseTrackerMock = new Mock<IBrowseTracker>();
            var safetyLimiterMock = new Mock<ISoulseekSafetyLimiter>();
            var optionsSnapshotMock = new Mock<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>();

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: browseTrackerMock.Object,
                userService: userServiceMock.Object,
                safetyLimiter: safetyLimiterMock.Object,
                optionsSnapshot: optionsSnapshotMock.Object);

            // Act
            var result = controller.Group("testuser");

            // Assert
            Assert.IsType<OkObjectResult>(result);
            var okResult = result as OkObjectResult;
            Assert.Equal("privileged", okResult.Value);
        }

        [Fact]
        public void Group_Trims_User_Group_Username()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock.Setup(x => x.GetGroup("testuser")).Returns("privileged");

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = controller.Group(" testuser ");

            var okResult = Assert.IsType<OkObjectResult>(result);
            Assert.Equal("privileged", okResult.Value);
        }

        [Fact]
        public void Group_With_Blank_Username_Returns_BadRequest()
        {
            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = controller.Group("   ");

            Assert.IsType<BadRequestObjectResult>(result);
        }

        [Fact]
        public void Groups_ReturnsDistinctTrimmedCachedGroups()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock.Setup(service => service.GetGroup("alice")).Returns("privileged");
            userServiceMock.Setup(service => service.GetGroup("bob")).Returns("default");
            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = controller.Groups([" alice ", "ALICE", "bob", " "]);

            var groups = Assert.IsAssignableFrom<IReadOnlyDictionary<string, string>>(
                Assert.IsType<OkObjectResult>(result).Value);
            Assert.Equal(2, groups.Count);
            Assert.Equal("privileged", groups["alice"]);
            Assert.Equal("default", groups["bob"]);
            userServiceMock.Verify(service => service.GetGroup(It.IsAny<string>()), Times.Exactly(2));
        }

        [Fact]
        public void Groups_WithMoreThanMaximumDistinctUsers_ReturnsBadRequest()
        {
            var userServiceMock = new Mock<IUserService>();
            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = controller.Groups(
                Enumerable.Range(0, 101).Select(index => $"user-{index}").ToArray());

            Assert.IsType<BadRequestObjectResult>(result);
            userServiceMock.Verify(service => service.GetGroup(It.IsAny<string>()), Times.Never);
        }

        [Fact]
        public async Task Info_WhenUserOffline_DoesNotLeakExceptionMessage()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock.Setup(x => x.GetInfoAsync("testuser")).ThrowsAsync(new UserOfflineException("sensitive detail"));

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Info("testuser");

            var notFound = Assert.IsType<NotFoundObjectResult>(result);
            Assert.Equal("User is offline", notFound.Value);
        }

        [Fact]
        public async Task Info_WhenQuietUnavailableAndUserOffline_ReturnsNoContent()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock.Setup(x => x.GetInfoAsync("testuser")).ThrowsAsync(new UserOfflineException("sensitive detail"));

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Info("testuser", quietUnavailable: true);

            Assert.IsType<NoContentResult>(result);
        }

        [Fact]
        public async Task Info_WhenPeerConnectionFails_ReturnsServiceUnavailable()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock
                .Setup(x => x.GetInfoAsync("testuser"))
                .ThrowsAsync(new SoulseekClientException(
                    "Failed to retrieve information for user testuser",
                    new ConnectionException("Failed to establish a direct or indirect message connection")));

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Info("testuser");

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Unable to retrieve user info", unavailable.Value);
        }

        [Fact]
        public async Task Info_WhenQuietUnavailableAndPeerConnectionFails_ReturnsNoContent()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock
                .Setup(x => x.GetInfoAsync("testuser"))
                .ThrowsAsync(new SoulseekClientException(
                    "Failed to retrieve information for user testuser",
                    new ConnectionException("Failed to establish a direct or indirect message connection")));

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Info("testuser", quietUnavailable: true);

            Assert.IsType<NoContentResult>(result);
        }

        [Fact]
        public async Task Info_WhenPeerInfoTimesOut_ReturnsServiceUnavailable()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock
                .Setup(x => x.GetInfoAsync("testuser"))
                .ThrowsAsync(new TimeoutException("The wait timed out after 5000 milliseconds"));

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Info("testuser");

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Unable to retrieve user info", unavailable.Value);
        }

        [Fact]
        public async Task Info_WhenWrappedPeerInfoTimesOut_ReturnsServiceUnavailable()
        {
            var userServiceMock = new Mock<IUserService>();
            userServiceMock
                .Setup(x => x.GetInfoAsync("testuser"))
                .ThrowsAsync(new SoulseekClientException(
                    "Failed to retrieve information for user testuser",
                    new TimeoutException("The wait timed out after 5000 milliseconds")));

            var controller = new UsersController(
                soulseekClient: Mock.Of<ISoulseekClient>(),
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: userServiceMock.Object,
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Info("testuser");

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Unable to retrieve user info", unavailable.Value);
        }

        [Fact]
        public async Task Browse_WhenRequestIsCanceled_PropagatesCancellationToSoulseekClient()
        {
            using var cts = new CancellationTokenSource();
            await cts.CancelAsync();

            var soulseekClientMock = new Mock<ISoulseekClient>(MockBehavior.Strict);
            soulseekClientMock.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
            soulseekClientMock
                .Setup(client => client.BrowseAsync("testuser", It.IsAny<BrowseOptions>(), cts.Token))
                .ThrowsAsync(new OperationCanceledException(cts.Token));

            var safetyLimiterMock = new Mock<ISoulseekSafetyLimiter>();
            safetyLimiterMock
                .Setup(limiter => limiter.TryConsumeBrowse("user"))
                .Returns(true);

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: safetyLimiterMock.Object,
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            await Assert.ThrowsAsync<OperationCanceledException>(() => controller.Browse("testuser", cts.Token));
        }

        [Fact]
        public async Task Browse_WhenLimiterRejects_DoesNotBrowseNetwork()
        {
            var soulseekClientMock = new Mock<ISoulseekClient>(MockBehavior.Strict);
            soulseekClientMock.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
            var safetyLimiterMock = new Mock<ISoulseekSafetyLimiter>();
            safetyLimiterMock
                .Setup(limiter => limiter.TryConsumeBrowse("user"))
                .Returns(false);

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: safetyLimiterMock.Object,
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Browse("testuser", CancellationToken.None);

            var rejected = Assert.IsType<ObjectResult>(result);
            Assert.Equal(429, rejected.StatusCode);
            soulseekClientMock.VerifyGet(client => client.State, Times.Exactly(2));
            soulseekClientMock.VerifyNoOtherCalls();
        }

        [Fact]
        public async Task Browse_WhenSoulseekIsNotLoggedIn_ReturnsServiceUnavailable()
        {
            var soulseekClientMock = new Mock<ISoulseekClient>(MockBehavior.Strict);
            soulseekClientMock.SetupGet(client => client.State).Returns(SoulseekClientStates.Disconnected);

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Browse("testuser", CancellationToken.None);

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Soulseek server connection is not ready", unavailable.Value);
            soulseekClientMock.VerifyGet(client => client.State, Times.Once);
            soulseekClientMock.VerifyNoOtherCalls();
        }

        [Fact]
        public async Task Browse_WhenPeerConnectionFails_ReturnsServiceUnavailable()
        {
            var soulseekClientMock = new Mock<ISoulseekClient>();
            soulseekClientMock.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
            soulseekClientMock
                .Setup(client => client.BrowseAsync("testuser", It.IsAny<BrowseOptions>(), It.IsAny<CancellationToken>()))
                .ThrowsAsync(new SoulseekClientException(
                    "Failed to browse user testuser",
                    new ConnectionException("Failed to establish a direct or indirect message connection")));

            var safetyLimiterMock = new Mock<ISoulseekSafetyLimiter>();
            safetyLimiterMock
                .Setup(limiter => limiter.TryConsumeBrowse("user"))
                .Returns(true);

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: safetyLimiterMock.Object,
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Browse("testuser", CancellationToken.None);

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Unable to browse user; the remote peer is unavailable", unavailable.Value);
        }

        [Fact]
        public async Task Directory_WhenSoulseekIsNotLoggedIn_ReturnsServiceUnavailable()
        {
            var soulseekClientMock = new Mock<ISoulseekClient>();
            soulseekClientMock.SetupGet(x => x.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggingIn);

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Directory(
                "testuser",
                new DirectoryContentsRequest { Directory = "Music" });

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Soulseek server connection is not ready", unavailable.Value);
            soulseekClientMock.Verify(
                x => x.GetDirectoryContentsAsync(
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<int?>(),
                It.IsAny<CancellationToken>()),
                Times.Never);
        }

        [Fact]
        public async Task Directory_WhenPeerConnectionFails_ReturnsServiceUnavailable()
        {
            var soulseekClientMock = new Mock<ISoulseekClient>();
            soulseekClientMock.SetupGet(x => x.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
            soulseekClientMock
                .Setup(x => x.GetDirectoryContentsAsync(
                    "testuser",
                    "Music",
                    It.IsAny<int?>(),
                    It.IsAny<CancellationToken>()))
                .ThrowsAsync(new SoulseekClientException(
                    "Failed to retrieve directory contents",
                    new ConnectionException("Failed to establish a direct or indirect message connection")));

            var controller = new UsersController(
                soulseekClient: soulseekClientMock.Object,
                browseTracker: Mock.Of<IBrowseTracker>(),
                userService: Mock.Of<IUserService>(),
                safetyLimiter: Mock.Of<ISoulseekSafetyLimiter>(),
                optionsSnapshot: Mock.Of<Microsoft.Extensions.Options.IOptionsSnapshot<slskd.Options>>());

            var result = await controller.Directory(
                "testuser",
                new DirectoryContentsRequest { Directory = "Music" });

            var unavailable = Assert.IsType<ObjectResult>(result);
            Assert.Equal(503, unavailable.StatusCode);
            Assert.Equal("Unable to retrieve directory contents from user", unavailable.Value);
        }
    }
}
