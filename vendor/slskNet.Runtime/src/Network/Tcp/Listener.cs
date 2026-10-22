// <copyright file="Listener.cs" company="JP Dillingham">
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
//     SPDX-FileCopyrightText: slskdN Team
//     SPDX-License-Identifier: GPL-3.0-only
//
//     Modified by slskdN Team to support obfuscated listeners, IP snapshots, and per-connection
//     obfuscation sniffing for shared single-port listeners.
// </copyright>

namespace Soulseek.Network.Tcp
{
    using System;
    using System.Net;
    using System.Net.Sockets;
    using System.Threading;
    using System.Threading.Tasks;
    using Soulseek.Diagnostics;

    /// <summary>
    ///     Listens for client connections for TCP network services.
    /// </summary>
    /// <remarks>
    ///     Excluded from code coverage due to the inability to test the accepted code block; You can't instantiate TcpClient with
    ///     an ip and port without it connecting immediately, so the test either must create a new connection to *something*, or a
    ///     bunch of hoops need to be jumped through to handle TcpClients coming from the listener not connected/without an
    ///     endpoint, both of which will and SHOULD throw exceptions and die.
    /// </remarks>
    internal sealed class Listener : IListener
    {
        private const int InitialAcceptRetryDelayMilliseconds = 1000;
        private const int MaximumAcceptRetryDelayMilliseconds = 5000;

        private readonly IPAddress ipAddress;
        private readonly IDiagnosticFactory diagnosticFactory;
        private volatile bool listening;
        private CancellationTokenSource listenCancellation;

        /// <summary>
        ///     Initializes a new instance of the <see cref="Listener"/> class.
        /// </summary>
        /// <param name="ipAddress">The IP address to which to bind the listener.</param>
        /// <param name="port">The port of the listener.</param>
        /// <param name="connectionOptions">The optional options to use when creating <see cref="IConnection"/> instances.</param>
        /// <param name="tcpListener">The optional TcpClient instance to use.</param>
        /// <param name="obfuscated">Whether accepted peer init frames use type-1 obfuscation.</param>
        /// <param name="obfuscationSniffingEnabled">
        ///     A value indicating whether plain-vs-obfuscated status should be determined per accepted connection by
        ///     inspecting the first bytes read from the socket, rather than assuming the static <paramref name="obfuscated"/>
        ///     value. Used when plain and obfuscated peer connections share this listener's single bound port.
        /// </param>
        /// <param name="diagnosticFactory">The optional diagnostic factory used to report listener recovery.</param>
        public Listener(
            IPAddress ipAddress,
            int port,
            ConnectionOptions connectionOptions,
            ITcpListener tcpListener = null,
            bool obfuscated = false,
            bool obfuscationSniffingEnabled = false,
            IDiagnosticFactory diagnosticFactory = null)
        {
            var address = ipAddress.Snapshot();
            this.ipAddress = address;
            Port = port;
            ConnectionOptions = connectionOptions ?? new ConnectionOptions();
            TcpListener = tcpListener ?? new TcpListenerAdapter(new TcpListener(address, port));
            Obfuscated = obfuscated;
            ObfuscationSniffingEnabled = obfuscationSniffingEnabled;
            this.diagnosticFactory = diagnosticFactory;
        }

        /// <summary>
        ///     Occurs when a new connection is accepted.
        /// </summary>
        public event EventHandler<IConnection> Accepted;

        /// <summary>
        ///     Occurs when the listener encounters an exception while accepting a connection.
        /// </summary>
        public event EventHandler<Exception> Error;

        /// <summary>
        ///     Gets the options used when creating new <see cref="IConnection"/> instances.
        /// </summary>
        public ConnectionOptions ConnectionOptions { get; }

        /// <summary>
        ///     Gets the port of the listener.
        /// </summary>
        public IPAddress IPAddress => ipAddress.Snapshot();

        /// <summary>
        ///     Gets a value indicating whether the listener is listening for connections.
        /// </summary>
        public bool Listening
        {
            get => listening;
            private set => listening = value;
        }

        /// <summary>Gets whether accepted connections use type-1 obfuscation.</summary>
        public bool Obfuscated { get; }

        /// <summary>
        ///     Gets a value indicating whether this listener determines, per accepted connection, whether the init frame is
        ///     type-1 obfuscated by inspecting the first bytes read from the socket.
        /// </summary>
        public bool ObfuscationSniffingEnabled { get; }

        /// <summary>
        ///     Gets the port of the listener.
        /// </summary>
        public int Port { get; }

        private object SyncRoot { get; } = new object();
        private ITcpListener TcpListener { get; set; }
        private long MaxConsecutiveErrors { get; } = 20;
        private long ConsecutiveErrors { get; set; }

        /// <summary>
        ///     Starts the listener.
        /// </summary>
        /// <param name="backlog">The maximum number of pending connections the OS will queue for this listener.</param>
        public void Start(int backlog = (int)SocketOptionName.MaxConnections)
        {
            lock (SyncRoot)
            {
                if (Listening)
                {
                    return;
                }

                var cancellation = new CancellationTokenSource();
                try
                {
                    TcpListener.Start(backlog);
                    listenCancellation = cancellation;
                    Listening = true;
                    Task.Run(() => ListenContinuouslyAsync()).Forget();
                }
                catch
                {
                    Listening = false;
                    cancellation.Cancel();
                    cancellation.Dispose();
                    TcpListener.Stop();
                    throw;
                }
            }
        }

        /// <summary>
        ///     Stops the listener.
        /// </summary>
        public void Stop()
        {
            lock (SyncRoot)
            {
                if (!Listening)
                {
                    return;
                }

                Listening = false;
                var cancellation = listenCancellation;
                listenCancellation = null;
                cancellation?.Cancel();

                try
                {
                    TcpListener.Stop(); // unblocks AcceptTcpClientAsync()
                }
                finally
                {
                    cancellation?.Dispose();
                }
            }
        }

        private async Task ListenContinuouslyAsync()
        {
            var cancellationToken = listenCancellation?.Token ?? CancellationToken.None;
            var retryDelayMilliseconds = InitialAcceptRetryDelayMilliseconds;

            while (Listening && !cancellationToken.IsCancellationRequested)
            {
                TcpClient client = null;
                Connection connection = null;

                try
                {
                    client = await AcceptTcpClientAsync(cancellationToken).ConfigureAwait(false);

                    if (cancellationToken.IsCancellationRequested)
                    {
                        client?.TryDispose();
                        return;
                    }

                    var endPoint = (IPEndPoint)client.Client.RemoteEndPoint;
                    connection = new Connection(endPoint, ConnectionOptions, new TcpClientAdapter(client), Obfuscated);

                    if (connection.State != ConnectionState.Connected)
                    {
                        throw new ConnectionException($"The remote client disconnected before the connection could be accepted");
                    }

                    ConsecutiveErrors = 0;
                    retryDelayMilliseconds = InitialAcceptRetryDelayMilliseconds;

                    _ = Task
                        .Run(() => Accepted?.Invoke(this, connection))
                        .ContinueWith(task => _ = task.Exception, TaskContinuationOptions.OnlyOnFaulted | TaskContinuationOptions.RunContinuationsAsynchronously);
                }
                catch (OperationCanceledException) when (!Listening || cancellationToken.IsCancellationRequested)
                {
                    client?.TryDispose();
                    connection?.TryDispose();
                    return;
                }
                catch (Exception ex)
                {
                    client?.TryDispose();
                    connection?.TryDispose();

                    if (!Listening || cancellationToken.IsCancellationRequested)
                    {
                        return;
                    }

                    ConsecutiveErrors++;

                    try
                    {
                        Error?.Invoke(this, ex);
                    }
                    catch
                    {
                        // A listener error handler must not terminate the accept loop.
                    }

                    diagnosticFactory?.Warning("A TCP listener accept failed; retrying with bounded backoff.", ex);

                    if (ConsecutiveErrors >= MaxConsecutiveErrors)
                    {
                        try
                        {
                            await Task.Delay(retryDelayMilliseconds, cancellationToken).ConfigureAwait(false);
                        }
                        catch (OperationCanceledException) when (!Listening || cancellationToken.IsCancellationRequested)
                        {
                            return;
                        }

                        retryDelayMilliseconds = Math.Min(retryDelayMilliseconds * 2, MaximumAcceptRetryDelayMilliseconds);
                    }
                }
            }
        }

        private Task<TcpClient> AcceptTcpClientAsync(CancellationToken cancellationToken)
        {
            return TcpListener is ICancellableTcpListener cancellableListener
                ? cancellableListener.AcceptTcpClientAsync(cancellationToken)
                : TcpListener.AcceptTcpClientAsync();
        }
    }
}
