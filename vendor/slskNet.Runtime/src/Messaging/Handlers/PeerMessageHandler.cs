// <copyright file="PeerMessageHandler.cs" company="JP Dillingham">
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

namespace Soulseek.Messaging.Handlers
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Linq;
    using System.Net;
    using System.Threading.Tasks;
    using Soulseek.Diagnostics;
    using Soulseek.Messaging.Messages;
    using Soulseek.Network;

    /// <summary>
    ///     Handles incoming messages from peer connections.
    /// </summary>
    internal sealed class PeerMessageHandler : IPeerMessageHandler
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="PeerMessageHandler"/> class.
        /// </summary>
        /// <param name="soulseekClient">The ISoulseekClient instance to use.</param>
        /// <param name="diagnosticFactory">The IDiagnosticFactory instance to use.</param>
        public PeerMessageHandler(
            SoulseekClient soulseekClient,
            IDiagnosticFactory diagnosticFactory = null)
        {
            SoulseekClient = soulseekClient ?? throw new ArgumentNullException(nameof(soulseekClient));
            Diagnostic = diagnosticFactory ??
                new DiagnosticFactory(SoulseekClient.Options.MinimumDiagnosticLevel, (e) => DiagnosticGenerated?.Invoke(this, e));
            CustomPeerMessageHandlers = new ConcurrentDictionary<int, Func<IMessageConnection, byte[], Task>>();
        }

        /// <summary>
        ///     Occurs when an internal diagnostic message is generated.
        /// </summary>
        public event EventHandler<DiagnosticEventArgs> DiagnosticGenerated;

        /// <summary>
        ///     Occurs when a user reports that a download has been denied.
        /// </summary>
        public event EventHandler<DownloadDeniedEventArgs> DownloadDenied;

        /// <summary>
        ///     Occurs when a user reports that a download has failed.
        /// </summary>
        public event EventHandler<DownloadFailedEventArgs> DownloadFailed;

        private IDiagnosticFactory Diagnostic { get; }
        private SoulseekClient SoulseekClient { get; }
        private ConcurrentDictionary<int, Func<IMessageConnection, byte[], Task>> CustomPeerMessageHandlers { get; }

        /// <summary>
        ///     Handles incoming messages.
        /// </summary>
        /// <param name="sender">The <see cref="IMessageConnection"/> instance from which the message originated.</param>
        /// <param name="args">The message event args.</param>
        public void HandleMessageRead(object sender, MessageEventArgs args)
        {
            HandleMessageRead(sender, args.Message);
        }

        /// <summary>
        ///     Handles incoming messages.
        /// </summary>
        /// <param name="sender">The <see cref="IMessageConnection"/> instance from which the message originated.</param>
        /// <param name="message">The message.</param>
        public async void HandleMessageRead(object sender, byte[] message)
        {
            var connection = (IMessageConnection)sender;
            var displayCode = "unknown";

            try
            {
                if (message.Length < 8)
                {
                    throw new MessageReadException("The peer message payload must include a 4-byte code and body length prefix");
                }

                var codeInt = BitConverter.ToInt32(message, 4);
                var isKnownCode = Enum.IsDefined(typeof(MessageCode.Peer), codeInt);
                var code = isKnownCode ? (MessageCode.Peer)codeInt : default;
                displayCode = isKnownCode ? code.ToString() : codeInt.ToString();

                Diagnostic.Debug($"Peer message received: {displayCode} from {connection.Username} ({connection.IPEndPoint}) (id: {connection.Id})");

                if (!isKnownCode && CustomPeerMessageHandlers.TryGetValue(codeInt, out var handler))
                {
                    var payload = message.Skip(8).ToArray();
                    await handler(connection, payload).ConfigureAwait(false);
                    return;
                }

                switch (code)
                {
                    case MessageCode.Peer.SearchResponse:
                        var token = SearchResponseFactory.ReadToken(message);

                        if (SoulseekClient.Searches.TryGetValue(token, out var search))
                        {
                            var searchResponse = SearchResponseFactory.FromByteArray(message);

                            if (SoulseekClient.Searches.TryGetValue(token, out var currentSearch) && ReferenceEquals(search, currentSearch))
                            {
                                SoulseekClient.RememberRemotePathEncodings(searchResponse.Username, searchResponse);
                                currentSearch.TryAddResponse(searchResponse);
                            }
                        }

                        break;

                    case MessageCode.Peer.BrowseResponse:
                        var browseWaitKey = new WaitKey(MessageCode.Peer.BrowseResponse, connection.Username);

                        try
                        {
                            var incomingBrowseResponse = BrowseResponseFactory.FromByteArray(message);
                            SoulseekClient.RememberRemotePathEncodings(connection.Username, incomingBrowseResponse);
                            SoulseekClient.Waiter.Complete(browseWaitKey, incomingBrowseResponse);
                        }
                        catch (Exception ex)
                        {
                            SoulseekClient.Waiter.Throw(browseWaitKey, new MessageReadException("The peer returned an invalid browse response", ex));
                            throw;
                        }

                        break;

                    case MessageCode.Peer.InfoRequest:
                        UserInfo outgoingInfo;

                        try
                        {
                            outgoingInfo = await SoulseekClient.Options
                                .UserInfoResolver(connection.Username, connection.IPEndPoint).ConfigureAwait(false);

                            if (outgoingInfo == null)
                            {
                                throw new InvalidOperationException("The user info resolver returned null");
                            }
                        }
                        catch (Exception ex)
                        {
                            outgoingInfo = await new SoulseekClientOptions()
                                .UserInfoResolver(connection.Username, connection.IPEndPoint).ConfigureAwait(false);

                            Diagnostic.Warning($"Failed to resolve user info response: {ex.Message}", ex);
                        }

                        await connection.WriteAsync(outgoingInfo.ToByteArray()).ConfigureAwait(false);
                        Diagnostic.Info($"User info sent to {connection.Username}");

                        break;

                    case MessageCode.Peer.SearchRequest:
                        var searchRequest = PeerSearchRequest.FromByteArray(message);

                        if (SoulseekClient.Options.SearchResponseResolver == default)
                        {
                            break;
                        }

                        try
                        {
                            var peerSearchResponse = await SoulseekClient.Options.SearchResponseResolver(connection.Username, searchRequest.Token, SearchQuery.FromText(searchRequest.Query)).ConfigureAwait(false);

                            if (peerSearchResponse is RawSearchResponse rawSearchResponse)
                            {
                                try
                                {
                                    await WriteRawSearchResponseAsync(connection, rawSearchResponse).ConfigureAwait(false);
                                }
                                finally
                                {
                                    DisposeRawSearchResponseStream(rawSearchResponse);
                                }
                            }
                            else if (peerSearchResponse != null && peerSearchResponse.FileCount + peerSearchResponse.LockedFileCount > 0)
                            {
                                await connection.WriteAsync(peerSearchResponse.ToByteArray()).ConfigureAwait(false);
                            }
                        }
                        catch (Exception ex)
                        {
                            Diagnostic.Warning($"Error resolving search response for query '{searchRequest.Query}' requested by {connection.Username} with token {searchRequest.Token}: {ex.Message}", ex);
                        }

                        break;

                    case MessageCode.Peer.BrowseRequest:
                        BrowseResponse browseResponse;

                        try
                        {
                            browseResponse = await SoulseekClient.Options.BrowseResponseResolver(connection.Username, connection.IPEndPoint).ConfigureAwait(false);
                        }
                        catch (Exception ex)
                        {
                            browseResponse = await new SoulseekClientOptions()
                                .BrowseResponseResolver(connection.Username, connection.IPEndPoint).ConfigureAwait(false);

                            Diagnostic.Warning($"Failed to resolve browse response: {ex.Message}", ex);
                        }

                        if (browseResponse is RawBrowseResponse rawBrowseResponse)
                        {
                            await WriteRawBrowseResponseAsync(connection, rawBrowseResponse).ConfigureAwait(false);
                        }
                        else if (browseResponse != null)
                        {
                            await connection.WriteAsync(browseResponse.ToByteArray()).ConfigureAwait(false);
                        }

                        if (browseResponse != null)
                        {
                            Diagnostic.Info($"Share contents sent to {connection.Username}");
                        }

                        break;

                    case MessageCode.Peer.FolderContentsRequest:
                        var folderContentsRequest = FolderContentsRequest.FromByteArray(message);
                        IEnumerable<Directory> outgoingFolderContents = null;

                        try
                        {
                            outgoingFolderContents = await SoulseekClient.Options.DirectoryContentsResolver(
                                connection.Username,
                                connection.IPEndPoint,
                                folderContentsRequest.Token,
                                folderContentsRequest.DirectoryName).ConfigureAwait(false);
                        }
                        catch (Exception ex)
                        {
                            Diagnostic.Warning($"Failed to resolve directory contents response: {ex.Message}", ex);
                        }

                        if (outgoingFolderContents != null)
                        {
                            try
                            {
                                var folderContentsResponseMessage = new FolderContentsResponse(folderContentsRequest.Token, folderContentsRequest.DirectoryName, outgoingFolderContents, folderContentsRequest.DirectoryNameEncoding);

                                await connection.WriteAsync(folderContentsResponseMessage).ConfigureAwait(false);
                                Diagnostic.Info($"Folder contents for {folderContentsRequest.DirectoryName} sent to {connection.Username}");
                            }
                            catch (Exception ex)
                            {
                                Diagnostic.Warning($"Failed to send directory contents response: {ex.Message}", ex);
                            }
                        }

                        break;

                    case MessageCode.Peer.FolderContentsResponse:
                        var folderContentsResponse = FolderContentsResponse.FromByteArray(message);
                        SoulseekClient.RememberRemotePathEncodings(connection.Username, folderContentsResponse.Directories);
                        SoulseekClient.Waiter.Complete(new WaitKey(MessageCode.Peer.FolderContentsResponse, connection.Username, folderContentsResponse.Token), folderContentsResponse.Directories);
                        break;

                    case MessageCode.Peer.InfoResponse:
                        var incomingInfo = UserInfoResponseFactory.FromByteArray(message);
                        SoulseekClient.Waiter.Complete(new WaitKey(MessageCode.Peer.InfoResponse, connection.Username), incomingInfo);
                        break;

                    case MessageCode.Peer.TransferResponse:
                        var transferResponse = TransferResponse.FromByteArray(message);
                        SoulseekClient.Waiter.Complete(new WaitKey(MessageCode.Peer.TransferResponse, connection.Username, transferResponse.Token), transferResponse);
                        break;

                    case MessageCode.Peer.QueueDownload:
                        var queueDownloadRequest = QueueDownloadRequest.FromByteArray(message);

                        var (queueRejected, queueRejectionMessage) =
                            await TryEnqueueDownloadAsync(connection.Username, connection.IPEndPoint, queueDownloadRequest.Filename).ConfigureAwait(false);

                        if (queueRejected)
                        {
                            await connection.WriteAsync(new UploadDenied(queueDownloadRequest.Filename, queueRejectionMessage)).ConfigureAwait(false);
                        }
                        else
                        {
                            await TrySendPlaceInQueueAsync(connection, queueDownloadRequest.Filename).ConfigureAwait(false);
                        }

                        break;

                    case MessageCode.Peer.TransferRequest:
                        var transferRequest = TransferRequest.FromByteArray(message);

                        if (transferRequest.Direction == TransferDirection.Upload)
                        {
                            if (!SoulseekClient.DownloadDictionary.IsEmpty && SoulseekClient.DownloadDictionary.Values.Any(d => d.Username == connection.Username && d.Filename == transferRequest.Filename))
                            {
                                SoulseekClient.Waiter.Complete(new WaitKey(MessageCode.Peer.TransferRequest, connection.Username, transferRequest.Filename), transferRequest);
                            }
                            else
                            {
                                // reject the transfer with an empty reason.  it was probably cancelled, but we can't be sure.
                                Diagnostic.Debug($"Rejecting unknown upload from {connection.Username} for {transferRequest.Filename} with token {transferRequest.Token}");
                                await connection.WriteAsync(new TransferResponse(transferRequest.Token, "Cancelled")).ConfigureAwait(false);
                            }
                        }
                        else
                        {
                            var (transferRejected, transferRejectionMessage) = await TryEnqueueDownloadAsync(connection.Username, connection.IPEndPoint, transferRequest.Filename).ConfigureAwait(false);

                            if (transferRejected)
                            {
                                await connection.WriteAsync(new TransferResponse(transferRequest.Token, transferRejectionMessage)).ConfigureAwait(false);
                                await connection.WriteAsync(new UploadDenied(transferRequest.Filename, transferRejectionMessage)).ConfigureAwait(false);
                            }
                            else
                            {
                                await connection.WriteAsync(new TransferResponse(transferRequest.Token, "Queued")).ConfigureAwait(false);
                                await TrySendPlaceInQueueAsync(connection, transferRequest.Filename).ConfigureAwait(false);
                            }
                        }

                        break;

                    case MessageCode.Peer.UploadDenied:
                        var uploadDeniedResponse = UploadDenied.FromByteArray(message);

                        Diagnostic.Debug($"Download of {uploadDeniedResponse.Filename} from {connection.Username} was denied: {uploadDeniedResponse.Message}");
                        SoulseekClient.Waiter.Throw(new WaitKey(MessageCode.Peer.TransferRequest, connection.Username, uploadDeniedResponse.Filename), new TransferRejectedException(uploadDeniedResponse.Message));

                        DownloadDenied?.Invoke(this, new DownloadDeniedEventArgs(connection.Username, uploadDeniedResponse.Filename, uploadDeniedResponse.Message));
                        break;

                    case MessageCode.Peer.PlaceInQueueResponse:
                        var placeInQueueResponse = PlaceInQueueResponse.FromByteArray(message);
                        SoulseekClient.Waiter.Complete(new WaitKey(MessageCode.Peer.PlaceInQueueResponse, connection.Username, placeInQueueResponse.Filename), placeInQueueResponse);
                        break;

                    case MessageCode.Peer.PlaceInQueueRequest:
                        var placeInQueueRequest = PlaceInQueueRequest.FromByteArray(message);
                        await TrySendPlaceInQueueAsync(connection, placeInQueueRequest.Filename).ConfigureAwait(false);

                        break;

                    case MessageCode.Peer.UploadFailed:
                        var uploadFailedResponse = UploadFailed.FromByteArray(message);

                        Diagnostic.Debug($"Download of {uploadFailedResponse.Filename} reported as failed by {connection.Username}");

                        SoulseekClient.Waiter.Throw(new WaitKey(MessageCode.Peer.TransferRequest, connection.Username, uploadFailedResponse.Filename), new TransferReportedFailedException("Download reported as failed by remote client"));

                        DownloadFailed?.Invoke(this, new DownloadFailedEventArgs(connection.Username, uploadFailedResponse.Filename));
                        break;

                    default:
                        Diagnostic.Debug($"Unhandled peer message: {displayCode} from {connection.Username} ({connection.IPEndPoint}); {message.Length} bytes");
                        break;
                }
            }
            catch (Exception ex)
            {
                Diagnostic.Warning($"Error handling peer message: {displayCode} from {connection.Username} ({connection.IPEndPoint}); {ex.Message}", ex);
            }
        }

        /// <summary>
        ///     Registers a handler for a custom peer message code.
        /// </summary>
        /// <param name="messageCode">The peer message code.</param>
        /// <param name="handler">The handler invoked when the custom peer message is received.</param>
        /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="messageCode"/> is less than zero.</exception>
        /// <exception cref="ArgumentNullException">Thrown when <paramref name="handler"/> is null.</exception>
        public void RegisterPeerMessageHandler(int messageCode, Func<string, IPEndPoint, byte[], Task> handler)
        {
            if (messageCode < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(messageCode), "The peer message code must be greater than or equal to zero.");
            }

            if (handler == null)
            {
                throw new ArgumentNullException(nameof(handler));
            }

            CustomPeerMessageHandlers.AddOrUpdate(
                messageCode,
                _ => (connection, data) => handler(connection.Username, connection.IPEndPoint, data),
                (_, __) => (connection, data) => handler(connection.Username, connection.IPEndPoint, data));
        }

        /// <summary>
        ///     Unregisters a handler for a custom peer message code.
        /// </summary>
        /// <param name="messageCode">The peer message code.</param>
        /// <returns>
        ///     A value indicating whether a handler was removed.
        /// </returns>
        /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="messageCode"/> is less than zero.</exception>
        public bool UnregisterPeerMessageHandler(int messageCode)
        {
            if (messageCode < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(messageCode), "The peer message code must be greater than or equal to zero.");
            }

            return CustomPeerMessageHandlers.TryRemove(messageCode, out _);
        }

        /// <summary>
        ///     Handles the receipt of incoming messages, prior to the body having been read and parsed.
        /// </summary>
        /// <param name="sender">The <see cref="IMessageConnection"/> instance from which the message originated.</param>
        /// <param name="args">The message receipt event args.</param>
        public void HandleMessageReceived(object sender, MessageReceivedEventArgs args)
        {
            var connection = (IMessageConnection)sender;
            var code = (MessageCode.Peer)BitConverter.ToInt32(args.Code, 0);

            try
            {
                switch (code)
                {
                    case MessageCode.Peer.BrowseResponse:
                        var key = new WaitKey(Constants.WaitKey.BrowseResponseConnection, connection.Username);
                        SoulseekClient.Waiter.Complete(key, (EventArgs: args, Connection: connection));
                        break;

                    default:
                        break;
                }
            }
            catch (Exception ex)
            {
                Diagnostic.Warning($"Error handling peer message: {code} from {connection.Username} ({connection.IPEndPoint}); {ex.Message}", ex);
            }
        }

        /// <summary>
        ///     Handles outgoing messages, post send.
        /// </summary>
        /// <param name="sender">The <see cref="IMessageConnection"/> instance to which the message was sent.</param>
        /// <param name="args">The message event args.</param>
        public void HandleMessageWritten(object sender, MessageEventArgs args)
        {
            var connection = (IMessageConnection)sender;
            var code = new MessageReader<MessageCode.Peer>(args.Message).ReadCode();
            Diagnostic.Debug($"Peer message sent: {code} ({connection.IPEndPoint}) (id: {connection.Id})");
        }

        private static void DisposeRawBrowseResponseStream(RawBrowseResponse rawBrowseResponse)
        {
            try
            {
                rawBrowseResponse.Stream?.Dispose();
            }
            catch
            {
                // noop
            }
        }

        private static void DisposeRawSearchResponseStream(RawSearchResponse rawSearchResponse)
        {
            try
            {
                rawSearchResponse.Stream?.Dispose();
            }
            catch
            {
                // noop
            }
        }

        private static async Task WriteRawBrowseResponseAsync(IMessageConnection connection, RawBrowseResponse rawBrowseResponse)
        {
            try
            {
                await RawMessageWriter.WriteAsync(connection, rawBrowseResponse.Length, rawBrowseResponse.Stream).ConfigureAwait(false);
            }
            finally
            {
                DisposeRawBrowseResponseStream(rawBrowseResponse);
            }
        }

        private static async Task WriteRawSearchResponseAsync(IMessageConnection connection, RawSearchResponse rawSearchResponse)
        {
            // Raw response streams are owned by the caller so disposal can be ordered with surrounding delivery handling.
            await RawMessageWriter.WriteAsync(connection, rawSearchResponse.Length, rawSearchResponse.Stream).ConfigureAwait(false);
        }

        private async Task<(bool Rejected, string RejectionMessage)> TryEnqueueDownloadAsync(string username, IPEndPoint ipEndPoint, string filename)
        {
            bool rejected = false;
            string rejectionMessage = string.Empty;

            try
            {
                await SoulseekClient.Options
                    .EnqueueDownload(username, ipEndPoint, filename).ConfigureAwait(false);
            }
            catch (DownloadEnqueueException ex)
            {
                // pass the exception message through to the remote user only if EnqueueDownloadException is thrown
                rejected = true;
                rejectionMessage = ex.Message;
            }
            catch (Exception ex)
            {
                Diagnostic.Warning($"Failed to invoke QueueDownload action: {ex.Message}", ex);

                // if any other exception is thrown, return a generic message. do this to avoid exposing potentially sensitive
                // information that may be contained in the Exception message (filesystem details, etc.)
                rejected = true;
                rejectionMessage = "Enqueue failed due to internal error";
            }

            return (rejected, rejectionMessage);
        }

        private async Task TrySendPlaceInQueueAsync(IMessageConnection connection, string filename)
        {
            int? placeInQueue = null;

            try
            {
                placeInQueue = await SoulseekClient.Options.PlaceInQueueResolver(connection.Username, connection.IPEndPoint, filename).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Diagnostic.Warning($"Failed to resolve place in queue for file {filename} from {connection.Username}: {ex.Message}", ex);
                return;
            }

            if (placeInQueue.HasValue)
            {
                try
                {
                    await connection.WriteAsync(new PlaceInQueueResponse(filename, placeInQueue.Value)).ConfigureAwait(false);
                }
                catch (Exception ex)
                {
                    Diagnostic.Warning($"Failed to send place in queue response for file {filename} from {connection.Username}: {ex.Message}", ex);
                }
            }
        }
    }
}
