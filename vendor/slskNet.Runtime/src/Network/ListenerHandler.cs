// <copyright file="ListenerHandler.cs" company="JP Dillingham">
//     Copyright (c) JP Dillingham.
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
//     SPDX-License-Identifier: GPL-3.0-only
//
//     Modified by slskdN Team.
//     Modified: Added type-1 obfuscated peer-message init handling.
//     Modified: Added per-connection obfuscation sniffing for shared single-port listeners.
// </copyright>

namespace Soulseek.Network
{
    using System;
    using System.Buffers.Binary;
    using System.Linq;
    using Soulseek.Diagnostics;
    using Soulseek.Messaging.Messages;
    using Soulseek.Network.Tcp;

    /// <summary>
    ///     Handles incoming connections established by the <see cref="IListener"/>.
    /// </summary>
    internal sealed class ListenerHandler : IListenerHandler
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="ListenerHandler"/> class.
        /// </summary>
        /// <param name="soulseekClient">The ISoulseekClient instance to use.</param>
        /// <param name="diagnosticFactory">The IDiagnosticFactory instance to use.</param>
        public ListenerHandler(
            SoulseekClient soulseekClient,
            IDiagnosticFactory diagnosticFactory = null)
        {
            SoulseekClient = soulseekClient ?? throw new ArgumentNullException(nameof(soulseekClient));
            Diagnostic = diagnosticFactory ??
                new DiagnosticFactory(SoulseekClient.Options.MinimumDiagnosticLevel, (e) => DiagnosticGenerated?.Invoke(this, e));
        }

        /// <summary>
        ///     Occurs when an internal diagnostic message is generated.
        /// </summary>
        public event EventHandler<DiagnosticEventArgs> DiagnosticGenerated;

        private IDiagnosticFactory Diagnostic { get; }
        private SoulseekClient SoulseekClient { get; }

        /// <summary>
        ///     Handle <see cref="IListener.Accepted"/> events.
        /// </summary>
        /// <param name="sender">The originating <see cref="IListener"/> instance.</param>
        /// <param name="connection">The accepted connection.</param>
        // EventHandler cannot await this asynchronous path; explicitly observe the task so a
        // malformed peer frame cannot surface later as an unobserved task exception.
        public void HandleConnection(object sender, IConnection connection)
            => HandleConnectionAsync(sender, connection).Forget();

        public void HandleError(object sender, Exception exception)
        {
            Diagnostic.Warning($"Failed to establish an incoming connection: {exception.Message}", exception);
        }

        internal async System.Threading.Tasks.Task HandleConnectionAsync(object sender, IConnection connection)
        {
            try
            {
                if (connection == null)
                {
                    throw new ArgumentNullException(nameof(connection));
                }

                var listener = sender as IListener;
                var listenerPort = listener?.Port ?? SoulseekClient.Listener?.Port ?? 0;
                var listenerAddress = listener?.IPAddress ?? SoulseekClient.Listener?.IPAddress;
                var sniffObfuscation = listener?.ObfuscationSniffingEnabled == true;
                var obfuscated = !sniffObfuscation && listener?.Obfuscated == true;
                if (obfuscated)
                {
                    connection.MarkObfuscated();
                }

                Diagnostic.Debug($"Accepted incoming connection from {connection.IPEndPoint.Address} on {listenerAddress}:{listenerPort} (id: {connection.Id})");

                byte[] message;

                if (sniffObfuscation)
                {
                    // this listener's single bound port is shared by plain and type-1 obfuscated connections. peek at the
                    // frame by reading the first four bytes once (IConnection.ReadAsync only supports forward reads, so these
                    // bytes cannot be "put back") and testing whether they form a plausible plain init frame length. if so,
                    // treat the connection as plain and reuse those bytes as the length prefix; otherwise, treat them as the
                    // first four bytes of the eight-byte obfuscated header and read the remaining four to complete it.
                    var firstFour = await connection.ReadAsync(4).ConfigureAwait(false);
                    var candidateLength = BitConverter.ToInt32(firstFour, 0);

                    if (MessageFrameValidator.IsValidInitMessageLength(candidateLength))
                    {
                        obfuscated = false;

                        var bodyBytes = await connection.ReadAsync(candidateLength).ConfigureAwait(false);
                        message = firstFour.Concat(bodyBytes).ToArray();
                    }
                    else
                    {
                        obfuscated = true;
                        connection.MarkObfuscated();

                        var remainingHeaderBytes = await connection.ReadAsync(4).ConfigureAwait(false);
                        var firstBlock = firstFour.Concat(remainingHeaderBytes).ToArray();
                        var decodedFirstBlock = RotatedObfuscation.Decode(firstBlock);
                        var length = BinaryPrimitives.ReadInt32LittleEndian(decodedFirstBlock);
                        if (!MessageFrameValidator.IsValidInitMessageLength(length))
                        {
                            RejectConnection(connection, CreateInvalidInitMessageException(length, "obfuscated initialization message"));
                            return;
                        }

                        var obfuscatedMessage = new byte[8 + length];
                        Buffer.BlockCopy(firstBlock, 0, obfuscatedMessage, 0, firstBlock.Length);

                        if (length > 0)
                        {
                            var remainingBytes = await connection.ReadAsync(length).ConfigureAwait(false);
                            Buffer.BlockCopy(remainingBytes, 0, obfuscatedMessage, 8, remainingBytes.Length);
                        }

                        message = RotatedObfuscation.Decode(obfuscatedMessage);
                    }
                }
                else if (obfuscated)
                {
                    var firstBlock = await connection.ReadAsync(8).ConfigureAwait(false);
                    var decodedFirstBlock = RotatedObfuscation.Decode(firstBlock);
                    var length = BinaryPrimitives.ReadInt32LittleEndian(decodedFirstBlock);
                    if (!MessageFrameValidator.IsValidInitMessageLength(length))
                    {
                        RejectConnection(connection, CreateInvalidInitMessageException(length, "obfuscated initialization message"));
                        return;
                    }

                    var obfuscatedMessage = new byte[8 + length];
                    Buffer.BlockCopy(firstBlock, 0, obfuscatedMessage, 0, firstBlock.Length);

                    if (length > 0)
                    {
                        var remainingBytes = await connection.ReadAsync(length).ConfigureAwait(false);
                        Buffer.BlockCopy(remainingBytes, 0, obfuscatedMessage, 8, remainingBytes.Length);
                    }

                    message = RotatedObfuscation.Decode(obfuscatedMessage);
                }
                else
                {
                    var lengthBytes = await connection.ReadAsync(4).ConfigureAwait(false);
                    var length = BitConverter.ToInt32(lengthBytes, 0);
                    if (!MessageFrameValidator.IsValidInitMessageLength(length))
                    {
                        RejectConnection(connection, CreateInvalidInitMessageException(length, "initialization message"));
                        return;
                    }

                    var bodyBytes = await connection.ReadAsync(length).ConfigureAwait(false);
                    message = lengthBytes.Concat(bodyBytes).ToArray();
                }

                if (PeerInit.TryFromByteArray(message, out var peerInit))
                {
                    // this connection is the result of an unsolicited connection from the remote peer, either to request info or
                    // browse, or to send a file.
                    Diagnostic.Debug($"PeerInit for connection type {peerInit.ConnectionType} received from {peerInit.Username} ({connection.IPEndPoint.Address}:{listenerPort}) (id: {connection.Id})");

                    if (peerInit.ConnectionType == Constants.ConnectionType.Peer)
                    {
                        if (obfuscated)
                        {
                            await SoulseekClient.PeerConnectionManager.AddOrUpdateObfuscatedMessageConnectionAsync(
                                peerInit.Username,
                                connection).ConfigureAwait(false);
                        }
                        else
                        {
                            await SoulseekClient.PeerConnectionManager.AddOrUpdateMessageConnectionAsync(
                                peerInit.Username,
                                connection).ConfigureAwait(false);
                        }
                    }
                    else if (peerInit.ConnectionType == Constants.ConnectionType.Transfer)
                    {
                        if (obfuscated)
                        {
                            Diagnostic.Debug($"Obfuscated transfer PeerInit accepted from {peerInit.Username} ({connection.IPEndPoint.Address}:{listenerPort}); handing off to transfer manager. (id: {connection.Id})");
                        }

                        // slightly misleading name; this hands the incoming connection off instead of establishing new
                        var (transferConnection, remoteToken) = await SoulseekClient.PeerConnectionManager.GetTransferConnectionAsync(
                            peerInit.Username,
                            peerInit.Token,
                            connection).ConfigureAwait(false);

                        var waitKey = new WaitKey(Constants.WaitKey.DirectTransfer, peerInit.Username, remoteToken);

                        // check to see if we are expecting this token, and if so complete the wait and start the upload
                        if (SoulseekClient.Waiter.HasWait(waitKey))
                        {
                            SoulseekClient.Waiter.Complete(new WaitKey(Constants.WaitKey.DirectTransfer, peerInit.Username, remoteToken), transferConnection);
                        }
                        else
                        {
                            // either a random client connected and tried to download something without being told it could,
                            // or a client tried to initiate a transfer as a last-ditch effort to "save" an upload
                            Diagnostic.Debug($"Unexpected transfer connection for token {peerInit.Token} from {peerInit.Username} ({connection.IPEndPoint.Address}:{listenerPort}) (id: {connection.Id})");
                            transferConnection.Disconnect("Transfer connection rejected: unknown token");
                        }
                    }
                    else if (peerInit.ConnectionType == Constants.ConnectionType.Distributed)
                    {
                        if (obfuscated)
                        {
                            Diagnostic.Debug($"Obfuscated distributed PeerInit accepted from {peerInit.Username} ({connection.IPEndPoint.Address}:{listenerPort}); handing off to distributed child manager. (id: {connection.Id})");
                        }

                        await SoulseekClient.DistributedConnectionManager.AddOrUpdateChildConnectionAsync(
                            peerInit.Username,
                            connection).ConfigureAwait(false);
                    }
                }
                else if (PierceFirewall.TryFromByteArray(message, out var pierceFirewall))
                {
                    // this connection is the result of a ConnectToPeer request sent to the user, and the incoming message will
                    // contain the token that was provided in the request. Ensure this token is among those expected, and use it
                    // to determine the username of the remote user.
                    if (SoulseekClient.PeerConnectionManager.PendingSolicitations.TryGetValue(pierceFirewall.Token, out var peerUsername))
                    {
                        Diagnostic.Debug($"Peer PierceFirewall with token {pierceFirewall.Token} received from {peerUsername} ({connection.IPEndPoint.Address}:{listenerPort}) (id: {connection.Id})");
                        SoulseekClient.Waiter.Complete(new WaitKey(Constants.WaitKey.SolicitedPeerConnection, peerUsername, pierceFirewall.Token), connection);
                    }
                    else if (SoulseekClient.DistributedConnectionManager.PendingSolicitations.TryGetValue(pierceFirewall.Token, out var distributedUsername))
                    {
                        if (obfuscated)
                        {
                            Diagnostic.Debug($"Obfuscated distributed PierceFirewall with token {pierceFirewall.Token} accepted from {distributedUsername} ({connection.IPEndPoint.Address}:{listenerPort}); completing solicited distributed wait. (id: {connection.Id})");
                        }

                        Diagnostic.Debug($"Distributed PierceFirewall with token {pierceFirewall.Token} received from {distributedUsername} ({connection.IPEndPoint.Address}:{listenerPort}) (id: {connection.Id})");
                        SoulseekClient.Waiter.Complete(new WaitKey(Constants.WaitKey.SolicitedDistributedConnection, distributedUsername, pierceFirewall.Token), connection);
                    }
                    else if (SoulseekClient.Options.SearchResponseCache != null && SoulseekClient.Options.SearchResponseCache.TryGet(pierceFirewall.Token, out var cachedSearchResponse))
                    {
                        // users may connect to retrieve search results long after we've given up waiting for them.  if this is the case, accept the connection,
                        // cache it with the manager for potential reuse, then try to send the pending response.
                        var (username, _, _, _) = cachedSearchResponse;

                        Diagnostic.Debug($"PierceFirewall matching pending search response received from {username} ({connection.IPEndPoint.Address}:{listenerPort}) (id: {connection.Id})");
                        if (obfuscated)
                        {
                            await SoulseekClient.PeerConnectionManager.AddOrUpdateObfuscatedMessageConnectionAsync(username, connection).ConfigureAwait(false);
                        }
                        else
                        {
                            await SoulseekClient.PeerConnectionManager.AddOrUpdateMessageConnectionAsync(username, connection).ConfigureAwait(false);
                        }

                        await SoulseekClient.SearchResponder.TryRespondAsync(pierceFirewall.Token).ConfigureAwait(false);
                    }
                    else
                    {
                        // Search responders behind a firewall can arrive with a bare PierceFirewall token before sending the
                        // peer SearchResponse message. There is no username in the init frame, but SearchResponse contains both
                        // username and search token, so keep the socket alive long enough for PeerMessageHandler to process it.
                        var provisionalUsername = $"pierce-{pierceFirewall.Token}-{connection.IPEndPoint.Address}:{connection.IPEndPoint.Port}";
                        Diagnostic.Debug($"Unknown PierceFirewall with token {pierceFirewall.Token} accepted as provisional peer message connection from {connection.IPEndPoint.Address}:{connection.IPEndPoint.Port} (id: {connection.Id})");

                        if (obfuscated)
                        {
                            await SoulseekClient.PeerConnectionManager.AddOrUpdateObfuscatedMessageConnectionAsync(provisionalUsername, connection).ConfigureAwait(false);
                        }
                        else
                        {
                            await SoulseekClient.PeerConnectionManager.AddOrUpdateMessageConnectionAsync(provisionalUsername, connection).ConfigureAwait(false);
                        }
                    }
                }
                else
                {
                    throw new ConnectionException($"Unrecognized initialization message: {BitConverter.ToString(message)} ({message.Length} bytes, id: {connection.Id})");
                }
            }
            catch (Exception ex)
            {
                RejectConnection(connection, ex);
            }
        }

        private void RejectConnection(IConnection connection, Exception exception)
        {
            Diagnostic.Debug($"Failed to initialize direct connection from {GetConnectionDescription(connection)}: {exception.Message}");
            DisconnectAndDispose(connection, exception);
        }

        private static void DisconnectAndDispose(IConnection connection, Exception exception)
        {
            if (connection == null)
            {
                return;
            }

            try
            {
                // Incoming listener connections are unsolicited and have no caller awaiting
                // WaitForDisconnect; preserve the reason without faulting that completion source.
                connection.Disconnect(message: exception?.Message);
            }
            catch (Exception)
            {
            }
            finally
            {
                try
                {
                    connection.Dispose();
                }
                catch (Exception)
                {
                }
            }
        }

        private static string GetConnectionDescription(IConnection connection)
        {
            if (connection == null)
            {
                return "<null>";
            }

            try
            {
                return $"{connection.IPEndPoint.Address}:{connection.IPEndPoint.Port}";
            }
            catch (Exception)
            {
                return "<unknown>";
            }
        }

        private static MessageReadException CreateInvalidInitMessageException(int length, string frameName)
            => new MessageReadException($"Invalid {frameName} length: {length}");
    }
}
