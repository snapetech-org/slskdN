// <copyright file="MeshRendezvousService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, version 3.
//
//     This program is distributed with Additional Terms pursuant to Section 7
//     of the GPLv3.  See the LICENSE file in the root directory of this
//     project for the complete terms and conditions.
//
//     SPDX-FileCopyrightText: slskdN Team
//     SPDX-License-Identifier: GPL-3.0-only
// </copyright>

namespace Soulseek
{
    using System;
    using System.Linq;
    using System.Threading;
    using System.Threading.Tasks;

    /// <summary>
    ///     Native Soulseek rendezvous helper for slskdN-aware peers.
    /// </summary>
    public sealed class MeshRendezvousService
    {
        private readonly ISoulseekClient client;
        private readonly MeshRendezvousOptions options;

        /// <summary>
        ///     Initializes a new instance of the <see cref="MeshRendezvousService"/> class.
        /// </summary>
        /// <param name="client">The Soulseek client.</param>
        /// <param name="options">The rendezvous options.</param>
        public MeshRendezvousService(ISoulseekClient client, MeshRendezvousOptions options = null)
        {
            this.client = client ?? throw new ArgumentNullException(nameof(client));
            this.options = options ?? new MeshRendezvousOptions();
        }

        /// <summary>
        ///     Registers the public rendezvous interest tag.
        /// </summary>
        /// <param name="cancellationToken">The token to monitor for cancellation requests.</param>
        /// <returns>The Task representing the asynchronous operation.</returns>
        public Task RegisterAsync(CancellationToken? cancellationToken = null)
        {
            return client.AddInterestAsync(options.InterestTag, cancellationToken);
        }

        /// <summary>
        ///     Removes the public rendezvous interest tag.
        /// </summary>
        /// <param name="cancellationToken">The token to monitor for cancellation requests.</param>
        /// <returns>The Task representing the asynchronous operation.</returns>
        public Task UnregisterAsync(CancellationToken? cancellationToken = null)
        {
            return client.RemoveInterestAsync(options.InterestTag, cancellationToken);
        }

        /// <summary>
        ///     Discovers similar users and optionally probes them for slskdN peer capability descriptors.
        /// </summary>
        /// <param name="cancellationToken">The token to monitor for cancellation requests.</param>
        /// <returns>The rendezvous result.</returns>
        public async Task<MeshRendezvousResult> DiscoverAsync(CancellationToken? cancellationToken = null)
        {
            var token = cancellationToken ?? CancellationToken.None;
            var users = await client.GetSimilarUsersAsync((CancellationToken?)token).ConfigureAwait(false);

            if (options.ProbePeerCapabilities && client.PeerCapabilityDescriptor != null)
            {
                foreach (var username in users.Select(u => u.Username).Where(u => !string.Equals(u, client.Username, StringComparison.OrdinalIgnoreCase)))
                {
                    token.ThrowIfCancellationRequested();

                    try
                    {
                        await client.SendPeerCapabilityAsync(username, cancellationToken: token).ConfigureAwait(false);
                    }
                    catch
                    {
                        // Discovery is opportunistic; callers can inspect the registry for peers that answered.
                    }
                }
            }

            return new MeshRendezvousResult(options.InterestTag, users, client.PeerCapabilities.Records);
        }
    }
}
