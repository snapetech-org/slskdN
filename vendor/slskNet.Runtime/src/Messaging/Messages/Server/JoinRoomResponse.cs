// <copyright file="JoinRoomResponse.cs" company="JP Dillingham">
//     Copyright (c) JP Dillingham.
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, version 3.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
//
//     This program is distributed with Additional Terms pursuant to Section 7
//     of the GPLv3.  See the LICENSE file in the root directory of this
//     project for the complete terms and conditions.
//
//     SPDX-FileCopyrightText: JP Dillingham
//     SPDX-FileCopyrightText: slskdN Team
//     SPDX-License-Identifier: GPL-3.0-only
// </copyright>

namespace Soulseek.Messaging.Messages
{
    using System.Collections.Generic;

    /// <summary>
    ///     The response to request to join a chat room.
    /// </summary>
    internal sealed class JoinRoomResponse : IIncomingMessage
    {
        /// <summary>
        ///     Creates a new instance of <see cref="RoomData"/> from the specified <paramref name="bytes"/>.
        /// </summary>
        /// <param name="bytes">The byte array from which to parse.</param>
        /// <returns>The created instance.</returns>
        internal static RoomData FromByteArray(byte[] bytes)
        {
            var reader = new MessageReader<MessageCode.Server>(bytes);
            var code = reader.ReadCode();

            if (code != MessageCode.Server.JoinRoom)
            {
                throw new MessageException($"Message Code mismatch creating {nameof(JoinRoomResponse)} (expected: {(int)MessageCode.Server.JoinRoom}, received: {(int)code}");
            }

            var roomName = reader.ReadString();

            var userCount = ProtocolCountReader.ReadCount(reader, "room user", minimumBytesPerItem: 4);
            var userNames = new List<string>();

            for (int i = 0; i < userCount; i++)
            {
                userNames.Add(reader.ReadString());
            }

            var statusCount = ProtocolCountReader.ReadCount(reader, "room user status", minimumBytesPerItem: 4);
            ProtocolCountReader.ValidateMatchingCount(userCount, statusCount, "room user status");
            var statuses = new List<UserPresence>();

            for (int i = 0; i < statusCount; i++)
            {
                statuses.Add(ProtocolValueValidator.ToDefinedEnum<UserPresence>(reader.ReadInteger(), "user presence"));
            }

            var dataCount = ProtocolCountReader.ReadCount(reader, "room user data", minimumBytesPerItem: 20);
            ProtocolCountReader.ValidateMatchingCount(userCount, dataCount, "room user data");
            var datums = new List<(int AverageSpeed, long DownloadCount, int FileCount, int DirectoryCount)>();

            for (int i = 0; i < dataCount; i++)
            {
                var averageSpeed = reader.ReadInteger();
                var downloadCount = reader.ReadLong();
                var fileCount = reader.ReadInteger();
                var directoryCount = reader.ReadInteger();

                ProtocolValueValidator.ValidateNonNegative(averageSpeed, "average speed");
                ProtocolValueValidator.ValidateNonNegative(downloadCount, "upload count");
                ProtocolValueValidator.ValidateNonNegative(fileCount, "file count");
                ProtocolValueValidator.ValidateNonNegative(directoryCount, "directory count");

                datums.Add((averageSpeed, downloadCount, fileCount, directoryCount));
            }

            var slotsFreeCount = ProtocolCountReader.ReadCount(reader, "room user slot", minimumBytesPerItem: 4);
            ProtocolCountReader.ValidateMatchingCount(userCount, slotsFreeCount, "room user slot");
            var slots = new List<int>();

            for (int i = 0; i < slotsFreeCount; i++)
            {
                var slotCount = reader.ReadInteger();
                ProtocolValueValidator.ValidateNonNegative(slotCount, "free slot count");
                slots.Add(slotCount);
            }

            var countryCount = ProtocolCountReader.ReadCount(reader, "room user country", minimumBytesPerItem: 4);
            ProtocolCountReader.ValidateMatchingCount(userCount, countryCount, "room user country");
            var countries = new List<string>();

            for (int i = 0; i < countryCount; i++)
            {
                countries.Add(reader.ReadString());
            }

            var users = new List<UserData>();

            for (int i = 0; i < userCount; i++)
            {
                var name = userNames[i];
                var status = statuses[i];
                var (averageSpeed, downloadCount, fileCount, directoryCount) = datums[i];
                var slot = slots[i];
                var country = countries[i];

                users.Add(new UserData(name, status, averageSpeed, downloadCount, fileCount, directoryCount, country, slot));
            }

            string owner = null;
            int? operatorCount = null;
            List<string> operatorList = null;

            if (reader.HasMoreData)
            {
                owner = reader.ReadString();
                operatorCount = ProtocolCountReader.ReadCount(reader, "room operator", minimumBytesPerItem: 4);
                operatorList = new List<string>();

                for (int i = 0; i < operatorCount; i++)
                {
                    operatorList.Add(reader.ReadString());
                }
            }

            if (SoulseekClient.ReportUnreadMessageData && reader.HasMoreData)
            {
                Diagnostics.GlobalDiagnostic.Warning($"Message reader for {nameof(MessageCode.Server.JoinRoom)} finalized with {reader.Remaining} unread bytes");
            }

            return new RoomData(roomName, users, owner != null, owner, operatorList);
        }
    }
}
