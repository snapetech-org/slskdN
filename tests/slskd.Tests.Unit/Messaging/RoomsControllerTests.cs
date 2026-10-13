// <copyright file="RoomsControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Messaging;

using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Messaging;
using slskd.Messaging.API;
using Soulseek;
using Xunit;

public class RoomsControllerTests
{
    [Fact]
    public async Task SendMessage_Trims_Room_And_Message_Before_Dispatch()
    {
        var client = new Mock<ISoulseekClient>();
        var tracker = CreateTracker();
        tracker
            .Setup(x => x.TryGet("room-1", out It.Ref<Room?>.IsAny))
            .Returns((string _, out Room? room) =>
            {
                room = null;
                return true;
            });
        var controller = CreateController(client: client.Object, tracker: tracker.Object);

        var result = await controller.SendMessage(" room-1 ", " hello ");

        Assert.IsType<StatusCodeResult>(result);
        client.Verify(x => x.SendRoomMessageAsync("room-1", "hello", null), Times.Once);
    }

    [Fact]
    public async Task JoinRoom_With_Blank_Name_Returns_BadRequest()
    {
        var controller = CreateController();

        var result = await controller.JoinRoom("   ");

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task JoinRoom_Trims_Room_Before_Dispatch()
    {
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(x => x.State).Returns(SoulseekClientStates.LoggedIn);
        var roomService = new Mock<IRoomService>();
        roomService
            .Setup(x => x.JoinAsync("ambient"))
            .ReturnsAsync(new RoomData("ambient", Array.Empty<UserData>(), isPrivate: false));
        var controller = CreateController(client: client.Object, roomService: roomService.Object);

        var result = await controller.JoinRoom(" ambient ");

        var created = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, created.StatusCode);
        roomService.Verify(x => x.JoinAsync("ambient"), Times.Once);
    }

    [Fact]
    public async Task JoinRoom_When_Reconnecting_Returns_ServiceUnavailable()
    {
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(x => x.State).Returns(SoulseekClientStates.Connecting);
        var roomService = new Mock<IRoomService>();
        var controller = CreateController(client: client.Object, roomService: roomService.Object);

        var result = await controller.JoinRoom("ambient");

        var unavailable = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, unavailable.StatusCode);
        roomService.Verify(x => x.JoinAsync(It.IsAny<string>()), Times.Never);
    }

    [Fact]
    public async Task JoinRoom_When_Server_Does_Not_Acknowledge_Adds_Degraded_Room()
    {
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(x => x.State).Returns(SoulseekClientStates.LoggedIn);
        var tracker = CreateTracker();
        var roomService = new Mock<IRoomService>();
        roomService
            .Setup(x => x.JoinAsync("slskd"))
            .ThrowsAsync(new NoResponseException("already joined"));
        var controller = CreateController(
            client: client.Object,
            roomService: roomService.Object,
            tracker: tracker.Object);

        var result = await controller.JoinRoom("slskd");

        var accepted = Assert.IsType<ObjectResult>(result);
        Assert.Equal(202, accepted.StatusCode);
        Assert.True(tracker.Object.Rooms.ContainsKey("slskd"));
    }

    [Fact]
    public void GetByRoomName_With_Blank_Name_Returns_BadRequest()
    {
        var controller = CreateController();

        var result = controller.GetByRoomName("   ");

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public void GetByRoomName_ReturnsMaterializedCollectionsWithStableMessageIds()
    {
        var tracker = CreateTracker();
        var message = new RoomMessage
        {
            Id = Guid.NewGuid(),
            Message = "hello",
            RoomName = "ambient",
            Timestamp = DateTime.UtcNow,
            Username = "friend",
        };
        tracker.Object.Rooms["ambient"] = new Room
        {
            Messages = new List<RoomMessage> { message },
        };
        var controller = CreateController(tracker: tracker.Object);

        var result = controller.GetByRoomName("ambient");

        var response = Assert.IsType<RoomResponse>(Assert.IsType<OkObjectResult>(result).Value);
        Assert.IsType<List<UserDataResponse>>(response.Users);
        var messages = Assert.IsType<List<RoomMessageResponse>>(response.Messages);
        Assert.Equal(message.Id, Assert.Single(messages).Id);
    }

    [Fact]
    public void GetActivity_ReturnsLatestIncomingTimestampPerRoom()
    {
        var tracker = CreateTracker();
        var firstIncoming = new DateTime(2026, 7, 15, 10, 0, 0, DateTimeKind.Utc);
        var latestIncoming = firstIncoming.AddMinutes(2);
        tracker.Object.Rooms["ambient"] = new Room
        {
            Messages = new List<RoomMessage>
            {
                new() { Username = "friend", Timestamp = firstIncoming },
                new() { Username = "self", Timestamp = firstIncoming.AddMinutes(1) },
                new() { Username = "friend", Timestamp = latestIncoming },
                new() { Username = "self", Timestamp = latestIncoming.AddMinutes(1) },
            },
        };
        tracker.Object.Rooms["solo"] = new Room
        {
            Messages = new List<RoomMessage>
            {
                new() { Username = "self", Timestamp = latestIncoming },
            },
        };
        var controller = CreateController(tracker: tracker.Object, username: "self");

        var result = controller.GetActivity();

        var ok = Assert.IsType<OkObjectResult>(result);
        var activity = Assert.IsType<Dictionary<string, long>>(ok.Value);
        var entry = Assert.Single(activity);
        Assert.Equal("ambient", entry.Key);
        Assert.Equal(
            new DateTimeOffset(latestIncoming).ToUnixTimeMilliseconds(),
            entry.Value);
    }

    [Fact]
    public void GetMessagesByRoomName_WithCursorReturnsOnlyNewerMaterializedMessages()
    {
        var tracker = CreateTracker();
        var firstTimestamp = new DateTime(2026, 7, 15, 10, 0, 0, 100, DateTimeKind.Utc);
        var secondTimestamp = firstTimestamp.AddMilliseconds(100);
        var first = new RoomMessage
        {
            Id = Guid.NewGuid(),
            Message = "first",
            RoomName = "ambient",
            Timestamp = firstTimestamp,
            Username = "friend",
        };
        var second = new RoomMessage
        {
            Id = Guid.NewGuid(),
            Message = "second",
            RoomName = "ambient",
            Timestamp = secondTimestamp,
            Username = "self",
        };
        tracker.Object.Rooms["ambient"] = new Room
        {
            Messages = new List<RoomMessage> { first, second },
        };
        var controller = CreateController(tracker: tracker.Object, username: "self");
        var cursor = new DateTimeOffset(firstTimestamp).ToUnixTimeMilliseconds();

        var result = controller.GetMessagesByRoomName("ambient", cursor);

        var response = Assert.IsType<List<RoomMessageResponse>>(
            Assert.IsType<OkObjectResult>(result).Value);
        var message = Assert.Single(response);
        Assert.Equal(second.Id, message.Id);
        Assert.Equal("second", message.Message);
        Assert.True(message.Self);
    }

    [Fact]
    public void GetMessagesByRoomName_ResolvesSlashNameFromQuery()
    {
        var roomName = "/mu/";
        var tracker = CreateTracker();
        tracker.Object.Rooms[roomName] = new Room();
        var controller = CreateController(tracker: tracker.Object);

        var result = controller.GetMessagesByRoomName(null, queryRoomName: roomName);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void GetMessagesByRoomName_RejectsConflictingRouteAndQueryNames()
    {
        var controller = CreateController();

        var result = controller.GetMessagesByRoomName("ambient", queryRoomName: "/mu/");

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Contains("conflicting", Assert.IsType<string>(badRequest.Value));
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(long.MaxValue)]
    public void GetMessagesByRoomName_WithInvalidCursorReturnsBadRequest(long cursor)
    {
        var controller = CreateController();

        var result = controller.GetMessagesByRoomName("ambient", cursor);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task GetRooms_When_Disconnected_Returns_Empty_List()
    {
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(x => x.State).Returns(SoulseekClientStates.Disconnected);
        var controller = CreateController(client: client.Object);

        var result = await controller.GetRooms();

        var ok = Assert.IsType<OkObjectResult>(result);
        var rooms = Assert.IsAssignableFrom<IEnumerable<RoomInfoResponse>>(ok.Value);
        Assert.Empty(rooms);
        client.Verify(x => x.GetRoomListAsync(null), Times.Never);
    }

    [Fact]
    public async Task GetRooms_When_Room_List_Times_Out_Returns_Empty_List()
    {
        ResetRoomDirectoryCache();
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(x => x.State).Returns(SoulseekClientStates.LoggedIn);
        client
            .Setup(x => x.GetRoomListAsync(null))
            .ThrowsAsync(new TimeoutException());
        var controller = CreateController(client: client.Object);

        var result = await controller.GetRooms();

        var ok = Assert.IsType<OkObjectResult>(result);
        var rooms = Assert.IsAssignableFrom<IEnumerable<RoomInfoResponse>>(ok.Value);
        Assert.Empty(rooms);
    }

    [Fact]
    public async Task GetRooms_When_Room_List_Times_Out_Returns_Last_Good_Directory()
    {
        ResetRoomDirectoryCache();
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(x => x.State).Returns(SoulseekClientStates.LoggedIn);
        client
            .SetupSequence(x => x.GetRoomListAsync(null))
            .ReturnsAsync(new RoomList(
                new[] { new RoomInfo("ambient", 12) },
                Array.Empty<RoomInfo>(),
                Array.Empty<RoomInfo>(),
                Array.Empty<string>()))
            .ThrowsAsync(new TimeoutException());
        var controller = CreateController(client: client.Object);

        await controller.GetRooms();

        var result = await controller.GetRooms();

        var ok = Assert.IsType<OkObjectResult>(result);
        var rooms = Assert.IsAssignableFrom<IEnumerable<RoomInfoResponse>>(ok.Value).ToArray();
        var room = Assert.Single(rooms);
        Assert.Equal("ambient", room.Name);
        Assert.Equal(12, room.UserCount);
    }

    private static RoomsController CreateController(
        ISoulseekClient? client = null,
        IRoomService? roomService = null,
        IRoomTracker? tracker = null,
        string username = "")
    {
        var stateMonitor = new Mock<IStateMonitor<State>>();
        stateMonitor.Setup(x => x.CurrentValue).Returns(new State
        {
            User = new UserState { Username = username },
        });

        var optionsSnapshot = new Mock<IOptionsSnapshot<slskd.Options>>();
        optionsSnapshot.Setup(x => x.Value).Returns(new slskd.Options());

        return new RoomsController(
            client ?? Mock.Of<ISoulseekClient>(),
            roomService ?? Mock.Of<IRoomService>(),
            stateMonitor.Object,
            optionsSnapshot.Object,
            tracker ?? CreateTracker().Object);
    }

    private static Mock<IRoomTracker> CreateTracker()
    {
        var tracker = new Mock<IRoomTracker>();
        var roomMap = new System.Collections.Concurrent.ConcurrentDictionary<string, Room>();
        tracker.SetupGet(x => x.Rooms).Returns(roomMap);
        tracker
            .Setup(x => x.TryAdd(It.IsAny<string>(), It.IsAny<Room>()))
            .Callback((string roomName, Room room) => roomMap.TryAdd(roomName, room));
        tracker
            .Setup(x => x.TryGet(It.IsAny<string>(), out It.Ref<Room?>.IsAny))
            .Returns((string roomName, out Room? room) =>
            {
                var found = roomMap.TryGetValue(roomName, out var value);
                room = value;
                return found;
            });

        return tracker;
    }

    private static void ResetRoomDirectoryCache()
    {
        var cache = typeof(RoomsController).GetField(
            "lastKnownRoomDirectory",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        cache?.SetValue(null, Array.Empty<RoomInfoResponse>());
    }
}
