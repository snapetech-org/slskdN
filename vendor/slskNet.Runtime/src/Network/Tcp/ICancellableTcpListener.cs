// <copyright file="ICancellableTcpListener.cs" company="JP Dillingham">
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

namespace Soulseek.Network.Tcp
{
    using System.Net.Sockets;
    using System.Threading;
    using System.Threading.Tasks;

    /// <summary>
    ///     An injected TCP listener that can cancel a pending accept without closing its shared socket or queue.
    /// </summary>
    internal interface ICancellableTcpListener : ITcpListener
    {
        /// <summary>
        ///     Accepts a pending connection request and cancels the wait when <paramref name="cancellationToken"/> is canceled.
        /// </summary>
        /// <param name="cancellationToken">The token that cancels the pending accept.</param>
        /// <returns>The operation context, including the new connection client.</returns>
        Task<TcpClient> AcceptTcpClientAsync(CancellationToken cancellationToken);
    }
}
