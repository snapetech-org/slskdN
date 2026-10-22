// <copyright file="Recommendation.cs" company="JP Dillingham; slskdN Team">
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
    /// <summary>
    ///     A recommended or not recommended item from the server.
    /// </summary>
    public class Recommendation
    {
        /// <summary>
        ///     Initializes a recommendation.
        /// </summary>
        /// <param name="item">The recommended item or interest.</param>
        /// <param name="score">The recommendation count or score.</param>
        public Recommendation(string item, int score)
        {
            Item = item;
            Score = score;
        }

        /// <summary>
        ///     Gets the recommended item.
        /// </summary>
        public string Item { get; }

        /// <summary>
        ///     Gets the recommendation score.
        /// </summary>
        public int Score { get; }

        /// <summary>
        ///     Gets the recommended or not recommended interest.
        /// </summary>
        public string Interest => Item;

        /// <summary>
        ///     Gets the number of recommendations for the interest.
        /// </summary>
        public int Count => Score;
    }
}
