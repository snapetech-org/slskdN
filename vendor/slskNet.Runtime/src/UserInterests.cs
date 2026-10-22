// <copyright file="UserInterests.cs" company="JP Dillingham; slskdN Team">
// Copyright (c) JP Dillingham.
// Copyright (c) slskdN Team.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, version 3.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see https://www.gnu.org/licenses/.
//
// This program is distributed with Additional Terms pursuant to Section 7
// of the GPLv3.  See the LICENSE file in the root directory of this
// project for the complete terms and conditions.
//
// SPDX-FileCopyrightText: JP Dillingham
// SPDX-FileCopyrightText: slskdN Team
// SPDX-License-Identifier: GPL-3.0-only
// </copyright>

namespace Soulseek
{
    using System;
    using System.Collections.Generic;
    using System.Linq;

    /// <summary>
    ///     A user's liked and hated interests.
    /// </summary>
    public class UserInterests
    {
        /// <summary>
        ///     Initializes a user's interests.
        /// </summary>
        /// <param name="username">The username.</param>
        /// <param name="likes">The liked interests.</param>
        /// <param name="hates">The hated interests.</param>
        public UserInterests(string username, IEnumerable<string> likes, IEnumerable<string> hates)
        {
            var liked = likes?.ToList() ?? new List<string>();
            var hated = hates?.ToList() ?? new List<string>();

            if (liked.Any(interest => interest == null))
            {
                throw new ArgumentException("The liked interest list must not contain null entries", nameof(likes));
            }

            if (hated.Any(interest => interest == null))
            {
                throw new ArgumentException("The hated interest list must not contain null entries", nameof(hates));
            }

            Username = username;
            Likes = liked.AsReadOnly();
            Hates = hated.AsReadOnly();
        }

        /// <summary>
        ///     Gets the user's liked interests.
        /// </summary>
        public IReadOnlyCollection<string> Likes { get; }

        /// <summary>
        ///     Gets the user's hated interests.
        /// </summary>
        public IReadOnlyCollection<string> Hates { get; }

        /// <summary>
        ///     Gets the user's liked interests (fork API alias).
        /// </summary>
        public IReadOnlyCollection<string> Liked => Likes;

        /// <summary>
        ///     Gets the user's hated interests (fork API alias).
        /// </summary>
        public IReadOnlyCollection<string> Hated => Hates;

        /// <summary>
        ///     Gets the username.
        /// </summary>
        public string Username { get; }
    }
}
