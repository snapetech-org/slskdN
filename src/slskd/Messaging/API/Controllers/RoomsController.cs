// <copyright file="RoomsController.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="RoomsController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Messaging.API
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Http;
    using Microsoft.AspNetCore.Mvc;
    using Soulseek;
    using slskd.Core.Security;

    /// <summary>
    ///     Rooms.
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class RoomsController : ControllerBase
    {
        private static readonly object RoomDirectorySyncRoot = new();
        private static IReadOnlyList<RoomInfoResponse> lastKnownRoomDirectory = Array.Empty<RoomInfoResponse>();

        public RoomsController(
            ISoulseekClient soulseekClient,
            IRoomService roomService,
            IStateMonitor<State> applicationStateMonitor,
            IOptionsSnapshot<Options> optionsSnapshot,
            IRoomTracker tracker)
        {
            Client = soulseekClient;
            ApplicationStateMonitor = applicationStateMonitor;
            OptionsSnapshot = optionsSnapshot;
            Tracker = tracker;
            RoomService = roomService;
        }

        private IRoomService RoomService { get; }
        private ISoulseekClient Client { get; }
        private IStateMonitor<State> ApplicationStateMonitor { get; }
        private IRoomTracker Tracker { get; }
        private IOptionsSnapshot<Options> OptionsSnapshot { get; }

        /// <summary>
        ///     Gets all rooms.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("joined")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Dictionary<string, Dictionary<string, Room>>), 200)]
        public IActionResult GetAll()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            return Ok(Tracker.Rooms.Keys);
        }

        /// <summary>
        ///     Gets the latest incoming message timestamp for each joined room.
        /// </summary>
        /// <returns>A map of room names to Unix timestamps in milliseconds.</returns>
        [HttpGet("activity")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Dictionary<string, long>), 200)]
        public IActionResult GetActivity()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var username = ApplicationStateMonitor.CurrentValue.User.Username;
            var activity = new Dictionary<string, long>(StringComparer.Ordinal);

            foreach (var (roomName, room) in Tracker.Rooms)
            {
                lock (room)
                {
                    for (var index = room.Messages.Count - 1; index >= 0; index--)
                    {
                        var message = room.Messages[index];
                        if (string.Equals(message.Username, username, StringComparison.Ordinal))
                        {
                            continue;
                        }

                        var timestamp = new DateTimeOffset(message.Timestamp).ToUnixTimeMilliseconds();
                        if (timestamp > 0)
                        {
                            activity[roomName] = timestamp;
                        }

                        break;
                    }
                }
            }

            return Ok(activity);
        }

        /// <summary>
        ///     Gets the specified room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">The specified roomName could not be found.</response>
        [HttpGet("joined/{roomName}")]
        [HttpGet("by-name")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Room), 200)]
        [ProducesResponseType(404)]
        public IActionResult GetByRoomName(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            if (Tracker.TryGet(roomName, out var room) && room is not null)
            {
                return Ok(MapRoomToRoomResponse(room));
            }

            return NotFound();
        }

        /// <summary>
        ///     Sends a message to the specified room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="message"></param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="201">The request completed successfully.</response>
        /// <response code="404">The specified roomName could not be found.</response>
        [HttpPost("joined/{roomName}/messages")]
        [HttpPost("by-name/messages")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(201)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> SendMessage(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromBody] string message,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            message = NormalizeRequiredValue(message);

            if (string.IsNullOrWhiteSpace(message))
            {
                return BadRequest("message is required");
            }

            if (Tracker.TryGet(roomName, out var _))
            {
                await Client.SendRoomMessageAsync(roomName, message);
                return StatusCode(StatusCodes.Status201Created);
            }

            return NotFound();
        }

        /// <summary>
        ///     Sets a ticker for the specified room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="message"></param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="201">The request completed successfully.</response>
        /// <response code="404">The specified roomName could not be found.</response>
        [HttpPost("joined/{roomName}/ticker")]
        [HttpPost("by-name/ticker")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(201)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> SetTicker(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromBody] string message,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            message = NormalizeRequiredValue(message);

            if (string.IsNullOrWhiteSpace(message))
            {
                return BadRequest("message is required");
            }

            if (Tracker.TryGet(roomName, out var _))
            {
                await Client.SetRoomTickerAsync(roomName, message);
                return StatusCode(StatusCodes.Status201Created);
            }

            return NotFound();
        }

        /// <summary>
        ///     Adds a member to a private room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="username"></param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="201">The request completed successfully.</response>
        /// <response code="404">The specified roomName could not be found.</response>
        [HttpPost("joined/{roomName}/members")]
        [HttpPost("by-name/members")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(201)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> AddRoomMember(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromBody] string username,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            username = NormalizeRequiredValue(username);

            if (string.IsNullOrWhiteSpace(username))
            {
                return BadRequest("username is required");
            }

            if (Tracker.TryGet(roomName, out var _))
            {
                await Client.AddPrivateRoomMemberAsync(roomName, username);
                return StatusCode(StatusCodes.Status201Created);
            }

            return NotFound();
        }

        /// <summary>
        ///     Gets the current list of users for the specified room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">The specified roomName could not be found.</response>
        [HttpGet("joined/{roomName}/users")]
        [HttpGet("by-name/users")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(IList<UserData>), 200)]
        [ProducesResponseType(404)]
        public IActionResult GetUsersByRoomName(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            if (Tracker.TryGet(roomName, out var room) && room is not null)
            {
                List<UserDataResponse> response;
                lock (room)
                {
                    response = room.Users
                        .Select(user => UserDataResponse.FromUserData(user, self: user.Username == ApplicationStateMonitor.CurrentValue.User.Username))
                        .ToList();
                }

                return Ok(response);
            }

            return NotFound();
        }

        /// <summary>
        ///     Gets the current list of messages for the specified room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="since">Optional Unix timestamp in milliseconds; only newer messages are returned.</param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">The specified roomName could not be found.</response>
        [HttpGet("joined/{roomName}/messages")]
        [HttpGet("by-name/messages")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(IList<RoomMessageResponse>), 200)]
        [ProducesResponseType(404)]
        public IActionResult GetMessagesByRoomName(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromQuery] long? since = null,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            DateTime? messagesSince = null;
            if (since.HasValue)
            {
                if (since.Value < 0)
                {
                    return BadRequest("since must be a non-negative Unix timestamp in milliseconds");
                }

                try
                {
                    messagesSince = DateTimeOffset.FromUnixTimeMilliseconds(since.Value).UtcDateTime;
                }
                catch (ArgumentOutOfRangeException)
                {
                    return BadRequest("since is outside the supported Unix timestamp range");
                }
            }

            if (Tracker.TryGet(roomName, out var room) && room is not null)
            {
                List<RoomMessageResponse> response;
                lock (room)
                {
                    response = room.Messages
                        .Where(message => !messagesSince.HasValue || message.Timestamp > messagesSince.Value)
                        .Select(message => RoomMessageResponse.FromRoomMessage(message, self: message.Username == ApplicationStateMonitor.CurrentValue.User.Username))
                        .ToList();
                }

                return Ok(response);
            }

            return NotFound();
        }

        /// <summary>
        ///     Gets a list of rooms from the server.
        /// </summary>
        /// <returns></returns>
        [HttpGet("available")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(List<RoomInfo>), 200)]
        public async Task<IActionResult> GetRooms()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (!Client.State.HasFlag(SoulseekClientStates.LoggedIn))
            {
                return Ok(Array.Empty<RoomInfoResponse>());
            }

            RoomList list;

            try
            {
                list = await Client.GetRoomListAsync();
            }
            catch (TimeoutException)
            {
                return Ok(GetLastKnownRoomDirectory());
            }
            catch (InvalidOperationException)
            {
                return Ok(GetLastKnownRoomDirectory());
            }

            var response = MapRoomList(list);
            SetLastKnownRoomDirectory(response);

            return Ok(response);
        }

        /// <summary>
        ///     Joins a room.
        /// </summary>
        /// <param name="roomName"></param>
        /// <returns></returns>
        /// <response code="201">The request completed successfully.</response>
        /// <response code="304">The room has already been joined.</response>
        [HttpPost("joined")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(Room), 201)]
        [ProducesResponseType(304)]
        public async Task<IActionResult> JoinRoom([FromBody] string roomName)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            roomName = NormalizeRequiredValue(roomName);
            if (string.IsNullOrWhiteSpace(roomName))
            {
                return BadRequest("roomName is required");
            }

            if (Tracker.Rooms.ContainsKey(roomName))
            {
                return Ok();
            }

            if (!Client.State.HasFlag(SoulseekClientStates.LoggedIn))
            {
                return StatusCode(StatusCodes.Status503ServiceUnavailable, "Soulseek is reconnecting; try again shortly.");
            }

            try
            {
                var roomData = await RoomService.JoinAsync(roomName);
                var room = Room.FromRoomData(roomData);

                return StatusCode(StatusCodes.Status201Created, MapRoomToRoomResponse(room));
            }
            catch (Exception ex)
            {
                if (ex.InnerException is RoomJoinForbiddenException)
                {
                    return StatusCode(StatusCodes.Status403Forbidden, $"The server rejected your request to join {roomName}");
                }

                if (ex is InvalidOperationException)
                {
                    return StatusCode(StatusCodes.Status503ServiceUnavailable, "Soulseek is reconnecting; try again shortly.");
                }

                if (ex is NoResponseException)
                {
                    var room = new Room { Name = roomName };
                    Tracker.TryAdd(roomName, room);
                    return StatusCode(StatusCodes.Status202Accepted, MapRoomToRoomResponse(room));
                }

                throw;
            }
        }

        /// <summary>
        ///     Leaves a room.
        /// </summary>
        /// <param name="routeRoomName">Room name supplied by the existing route, when used.</param>
        /// <param name="queryRoomName">Room name supplied by the query-addressed route, when used.</param>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="404">The room has not been joined.</response>
        [HttpDelete("joined/{roomName}")]
        [HttpDelete("by-name")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> LeaveRoom(
            [FromRoute(Name = "roomName")] string? routeRoomName,
            [FromQuery(Name = "roomName")] string? queryRoomName = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (ResolveRoomName(routeRoomName, queryRoomName, out var roomName) is { } error)
            {
                return error;
            }

            if (!Tracker.Rooms.ContainsKey(roomName))
            {
                return StatusCode(StatusCodes.Status404NotFound);
            }

            await RoomService.LeaveAsync(roomName);
            Tracker.TryRemove(roomName);

            return StatusCode(StatusCodes.Status204NoContent);
        }

        private RoomResponse MapRoomToRoomResponse(Room room)
        {
            bool IsSelf(string username)
            {
                return username == ApplicationStateMonitor.CurrentValue.User.Username;
            }

            lock (room)
            {
                var response = RoomResponse.FromRoom(room);
                response.Users = room.Users
                    .Select(user => UserDataResponse.FromUserData(user, self: IsSelf(user.Username)))
                    .ToList();
                response.Messages = room.Messages
                    .Select(message => RoomMessageResponse.FromRoomMessage(message, self: IsSelf(message.Username)))
                    .ToList();

                return response;
            }
        }

        private static string NormalizeRequiredValue(string? value)
        {
            return value?.Trim() ?? string.Empty;
        }

        private IActionResult? ResolveRoomName(string? routeRoomName, string? queryRoomName, out string roomName)
        {
            var normalizedRouteName = NormalizeRequiredValue(routeRoomName);
            var normalizedQueryName = NormalizeRequiredValue(queryRoomName);

            if (routeRoomName is not null &&
                queryRoomName is not null &&
                !string.Equals(normalizedRouteName, normalizedQueryName, StringComparison.Ordinal))
            {
                roomName = string.Empty;
                return BadRequest("roomName cannot have conflicting route and query values");
            }

            roomName = routeRoomName is null ? normalizedQueryName : normalizedRouteName;
            return string.IsNullOrWhiteSpace(roomName) ? BadRequest("roomName is required") : null;
        }

        private static List<RoomInfoResponse> MapRoomList(RoomList list)
        {
            var response = new List<RoomInfoResponse>();

            response.AddRange(list.Public.Select(r => RoomInfoResponse.FromRoomInfo(r)));
            response.AddRange(list.Private.Select(r => RoomInfoResponse.FromRoomInfo(r, isPrivate: true)));
            response.AddRange(list.Owned.Select(r => RoomInfoResponse.FromRoomInfo(r, isPrivate: true, isOwned: true)));

            foreach (var room in response)
            {
                room.IsModerated = list.ModeratedRoomNames.Contains(room.Name);
            }

            return response;
        }

        private static IReadOnlyList<RoomInfoResponse> GetLastKnownRoomDirectory()
        {
            lock (RoomDirectorySyncRoot)
            {
                return lastKnownRoomDirectory.ToArray();
            }
        }

        private static void SetLastKnownRoomDirectory(IReadOnlyList<RoomInfoResponse> rooms)
        {
            lock (RoomDirectorySyncRoot)
            {
                lastKnownRoomDirectory = rooms.ToArray();
            }
        }
    }
}
