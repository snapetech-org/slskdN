// <copyright file="UserInfoResponseFactory.cs" company="JP Dillingham">
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
    using Soulseek.Messaging;
    using Soulseek.Messaging.Messages;

    /// <summary>
    ///     The response to a user info request.
    /// </summary>
    internal static class UserInfoResponseFactory
    {
        private const int MinimumTrailingFieldBytesAfterPicture = 9;

        /// <summary>
        ///     Creates a new instance of <see cref="UserInfo"/> from the specified <paramref name="bytes"/>.
        /// </summary>
        /// <param name="bytes">The byte array from which to parse.</param>
        /// <returns>The parsed instance.</returns>
        public static UserInfo FromByteArray(byte[] bytes)
        {
            var reader = new MessageReader<MessageCode.Peer>(bytes);
            var code = reader.ReadCode();

            if (code != MessageCode.Peer.InfoResponse)
            {
                throw new MessageException($"Message Code mismatch creating {nameof(UserInfo)} (expected: {(int)MessageCode.Peer.InfoResponse}, received: {(int)code})");
            }

            var description = reader.ReadString();
            var hasPictureByte = reader.ReadByte();
            ProtocolValueValidator.ValidateBooleanFlag(hasPictureByte, "user info picture flag");

            var hasPicture = hasPictureByte == 1;
            byte[] picture = null;

            if (hasPicture)
            {
                var pictureLen = reader.ReadInteger();

                if (pictureLen < 0)
                {
                    throw new MessageException($"Invalid picture length: {pictureLen}");
                }

                var maximumPictureLength = reader.Remaining - MinimumTrailingFieldBytesAfterPicture;

                if (pictureLen > maximumPictureLength)
                {
                    throw new MessageException($"Invalid picture length: {pictureLen} exceeds the maximum possible length of {maximumPictureLength} for the remaining payload");
                }

                picture = reader.ReadBytes(pictureLen);
            }

            var uploadSlots = reader.ReadInteger();
            var queueLength = reader.ReadInteger();
            var hasFreeUploadSlotByte = reader.ReadByte();
            ProtocolValueValidator.ValidateBooleanFlag(hasFreeUploadSlotByte, "user info free upload slot flag");

            var hasFreeUploadSlot = hasFreeUploadSlotByte == 1;

            ProtocolValueValidator.ValidateNonNegative(uploadSlots, "upload slot count");
            ProtocolValueValidator.ValidateNonNegative(queueLength, "queue length");

            if (SoulseekClient.ReportUnreadMessageData && reader.HasMoreData)
            {
                Diagnostics.GlobalDiagnostic.Warning($"Message reader for {nameof(MessageCode.Peer.InfoResponse)} finalized with {reader.Remaining} unread bytes");
            }

            return new UserInfo(description, uploadSlots, queueLength, hasFreeUploadSlot, picture);
        }

        /// <summary>
        ///     Constructs a <see cref="byte"/> array from this message.
        /// </summary>
        /// <param name="userInfo">The instance from which to construct the byte array.</param>
        /// <returns>The constructed byte array.</returns>
        public static byte[] ToByteArray(this UserInfo userInfo)
        {
            var builder = new MessageBuilder()
                .WriteCode(MessageCode.Peer.InfoResponse)
                .WriteString(userInfo.Description)
                .WriteByte((byte)(userInfo.HasPicture ? 1 : 0));

            if (userInfo.HasPicture)
            {
                builder
                    .WriteInteger(userInfo.Picture.Length)
                    .WriteBytes(userInfo.Picture);
            }

            builder
                .WriteInteger(userInfo.UploadSlots)
                .WriteInteger(userInfo.QueueLength)
                .WriteByte((byte)(userInfo.HasFreeUploadSlot ? 1 : 0));

            return builder.Build();
        }
    }
}
