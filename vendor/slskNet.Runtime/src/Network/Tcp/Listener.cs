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
//     SPDX-License-Identifier: GPL-3.0-only
//
//     Modified by slskdN Team.
//     Modified: Added obfuscated listener identity.
//     Modified: Added per-connection obfuscation sniffing for shared single-port listeners.
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
    internal sealed class Listener : IListener
    {
        private const int InitialAcceptRetryDelayMilliseconds = 100;
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
        /// <param name="obfuscated">A value indicating whether accepted peer-message handshakes use type-1 obfuscation.</param>
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
        public bool Listening => listening;

        /// <summary>
        ///     Gets a value indicating whether accepted init frames are type-1 obfuscated.
        /// </summary>
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

        private ITcpListener TcpListener { get; set; }

        /// <summary>
        ///     Starts the listener.
        /// </summary>
        public void Start()
        {
            TcpListener.Start();
            var cancellation = new CancellationTokenSource();
            listenCancellation = cancellation;
            listening = true;
            Task.Run(() => ListenContinuouslyAsync(cancellation.Token)).Forget();
        }

        /// <summary>
        ///     Stops the listener.
        /// </summary>
        public void Stop()
        {
            listening = false;
            var cancellation = listenCancellation;
            listenCancellation = null;
            cancellation?.Cancel();

            try
            {
                TcpListener.Stop();
            }
            finally
            {
                cancellation?.Dispose();
            }
        }

        private async Task ListenContinuouslyAsync(CancellationToken cancellationToken)
        {
            var retryDelayMilliseconds = InitialAcceptRetryDelayMilliseconds;

            while (Listening && !cancellationToken.IsCancellationRequested)
            {
                TcpClient client;
                try
                {
                    client = await TcpListener.AcceptTcpClientAsync().ConfigureAwait(false);
                }
                catch (SocketException ex) when (Listening && !cancellationToken.IsCancellationRequested)
                {
                    diagnosticFactory?.Warning("A TCP listener accept failed; retrying with bounded backoff.", ex);

                    try
                    {
                        await Task.Delay(retryDelayMilliseconds, cancellationToken).ConfigureAwait(false);
                    }
                    catch (OperationCanceledException) when (!Listening || cancellationToken.IsCancellationRequested)
                    {
                        break;
                    }

                    retryDelayMilliseconds = Math.Min(retryDelayMilliseconds * 2, MaximumAcceptRetryDelayMilliseconds);
                    continue;
                }
                catch (InvalidOperationException) when (!Listening)
                {
                    break;
                }
                catch (ObjectDisposedException) when (!Listening)
                {
                    break;
                }
                catch (SocketException) when (!Listening)
                {
                    break;
                }
                catch (OperationCanceledException) when (!Listening)
                {
                    break;
                }

                retryDelayMilliseconds = InitialAcceptRetryDelayMilliseconds;

                Task.Run(() =>
                {
                    var endPoint = (IPEndPoint)client.Client.RemoteEndPoint;
                    var eventArgs = new Connection(endPoint, ConnectionOptions, new TcpClientAdapter(client), Obfuscated);

                    Accepted?.Invoke(this, eventArgs);
                }, CancellationToken.None).Forget();
            }
        }
    }
}
