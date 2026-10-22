// <copyright file="UserInterestsRequest.cs" company="JP Dillingham; slskdN Team">
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
    /// <summary>
    ///     Requests a user's interests.
    /// </summary>
    internal sealed class UserInterestsRequest : IOutgoingMessage
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="UserInterestsRequest"/> class.
        /// </summary>
        /// <param name="username">The username.</param>
        public UserInterestsRequest(string username)
        {
            Username = ProtocolArgumentValidator.RequireNotNull(username, nameof(username), "username");
        }

        /// <summary>
        ///     Gets the username.
        /// </summary>
        public string Username { get; }

        /// <summary>
        ///     Constructs a <see cref="byte"/> array from this message.
        /// </summary>
        /// <returns>The constructed byte array.</returns>
        public byte[] ToByteArray()
        {
            return new MessageBuilder()
                .WriteCode(MessageCode.Server.GetUserInterests)
                .WriteString(Username)
                .Build();
        }
    }
}
