// <copyright file="ListenerTests.cs" company="JP Dillingham">
//     Copyright (c) JP Dillingham. All rights reserved.
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

namespace Soulseek.Tests.Unit.Network.Tcp
{
    using System;
    using System.Net;
    using System.Net.Sockets;
    using System.Threading;
    using System.Threading.Tasks;
    using Moq;
    using Soulseek.Diagnostics;
    using Soulseek.Network.Tcp;
    using Xunit;

    public class ListenerTests
    {
        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Instantiates properly")]
        public void Instantiates_Properly()
        {
            var options = new ConnectionOptions();
            var port = 0;

            var l = new Listener(IPAddress.Loopback, port, options);

            Assert.Equal(IPAddress.Loopback, l.IPAddress);
            Assert.Equal(port, l.Port);
            Assert.Equal(options, l.ConnectionOptions);

            Assert.False(l.Listening);
            Assert.False(l.Obfuscated);
            Assert.False(l.ObfuscationSniffingEnabled);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Instantiates with obfuscation sniffing enabled")]
        public void Instantiates_With_Obfuscation_Sniffing_Enabled()
        {
            var options = new ConnectionOptions();
            var port = 0;

            var l = new Listener(IPAddress.Loopback, port, options, obfuscationSniffingEnabled: true);

            Assert.True(l.ObfuscationSniffingEnabled);
            Assert.False(l.Obfuscated);
        }

        [Trait("Category", "Start")]
        [Fact(DisplayName = "Start starts listening")]
        public void Start_Starts_Listening()
        {
            var options = new ConnectionOptions();
            var port = 0;

            var l = new Listener(IPAddress.Loopback, port, options);

            var first = l.Listening;

            try
            {
                l.Start();

                Assert.False(first);
                Assert.True(l.Listening);
            }
            finally
            {
                l.Stop();
            }
        }

        [Trait("Category", "Stop")]
        [Fact(DisplayName = "Stop stops listening")]
        public void Stop_Stops_Listening()
        {
            var options = new ConnectionOptions();
            var port = 0;

            var l = new Listener(IPAddress.Loopback, port, options);

            l.Start();

            var first = l.Listening;

            l.Stop();

            Assert.True(first);
            Assert.False(l.Listening);
        }

        [Trait("Category", "Accept")]
        [Fact(DisplayName = "Transient accept failure retries and accepts the next connection")]
        public async Task Start_RetriesTransientAcceptFailure()
        {
            var socketListener = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0);
            socketListener.Start();

            var remoteClient = new TcpClient();
            TcpClient acceptedClient = null;
            Listener listener = null;
            IConnection acceptedConnection = null;

            try
            {
                var endpoint = (IPEndPoint)socketListener.LocalEndpoint;
                var connectTask = remoteClient.ConnectAsync(endpoint.Address, endpoint.Port);
                acceptedClient = await socketListener.AcceptTcpClientAsync();
                await connectTask;

                var pendingAccept = new TaskCompletionSource<TcpClient>(TaskCreationOptions.RunContinuationsAsynchronously);
                var retrying = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
                var accepted = new TaskCompletionSource<IConnection>(TaskCreationOptions.RunContinuationsAsynchronously);
                var warning = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
                var acceptCount = 0;

                var tcpListener = new Mock<ITcpListener>();
                tcpListener.Setup(m => m.AcceptTcpClientAsync()).Returns(() =>
                {
                    var current = Interlocked.Increment(ref acceptCount);

                    if (current == 1)
                    {
                        return Task.FromException<TcpClient>(new SocketException((int)SocketError.Interrupted));
                    }

                    if (current == 2)
                    {
                        return Task.FromResult(acceptedClient);
                    }

                    retrying.TrySetResult(true);
                    return pendingAccept.Task;
                });
                tcpListener.Setup(m => m.Stop()).Callback(() => pendingAccept.TrySetException(new SocketException((int)SocketError.OperationAborted)));

                var diagnosticFactory = new Mock<IDiagnosticFactory>();
                diagnosticFactory
                    .Setup(m => m.Warning(It.IsAny<string>(), It.IsAny<Exception>()))
                    .Callback<string, Exception>((message, _) => warning.TrySetResult(message));

                listener = new Listener(
                    IPAddress.Loopback,
                    0,
                    new ConnectionOptions(),
                    tcpListener.Object,
                    diagnosticFactory: diagnosticFactory.Object);
                listener.Accepted += (_, connection) => accepted.TrySetResult(connection);
                listener.Start();

                acceptedConnection = await accepted.Task.WaitAsync(TimeSpan.FromSeconds(5));
                var warningMessage = await warning.Task.WaitAsync(TimeSpan.FromSeconds(5));
                await retrying.Task.WaitAsync(TimeSpan.FromSeconds(5));

                Assert.True(listener.Listening);
                Assert.Equal("A TCP listener accept failed; retrying with bounded backoff.", warningMessage);
                Assert.Equal(3, Volatile.Read(ref acceptCount));
                Assert.NotNull(acceptedConnection.IPEndPoint);
                diagnosticFactory.Verify(m => m.Warning(It.IsAny<string>(), It.IsAny<Exception>()), Times.Once);
            }
            finally
            {
                listener?.Stop();
                acceptedConnection?.Dispose();
                acceptedClient?.Dispose();
                remoteClient.Dispose();
                socketListener.Stop();
            }
        }
    }
}
