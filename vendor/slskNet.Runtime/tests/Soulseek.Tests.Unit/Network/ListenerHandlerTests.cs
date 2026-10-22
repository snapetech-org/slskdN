// <copyright file="ListenerHandlerTests.cs" company="JP Dillingham">
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

namespace Soulseek.Tests.Unit.Network
{
    using System;
    using System.Buffers.Binary;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Net;
    using System.Reflection;
    using System.Runtime.CompilerServices;
    using System.Threading;
    using System.Threading.Tasks;
    using AutoFixture.Xunit2;
    using Moq;
    using Soulseek.Diagnostics;
    using Soulseek.Messaging.Messages;
    using Soulseek.Network;
    using Soulseek.Network.Tcp;
    using Xunit;

    public class ListenerHandlerTests
    {
        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Instantiation throws given null SoulseekClient")]
        public void Instantiation_Throws_Given_Null_SoulseekClient()
        {
            var ex = Record.Exception(() => new ListenerHandler(null));

            Assert.NotNull(ex);
            Assert.IsType<ArgumentNullException>(ex);
            Assert.Equal("soulseekClient", ((ArgumentNullException)ex).ParamName);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Ensures Diagnostic given null")]
        public void Ensures_Diagnostic_Given_Null()
        {
            using (var client = new SoulseekClient(minorVersion: 9999, options: null))
            {
                ListenerHandler l = default;

                var ex = Record.Exception(() => l = new ListenerHandler(client));

                Assert.Null(ex);
                Assert.NotNull(l.GetProperty<IDiagnosticFactory>("Diagnostic"));
            }
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Raises DiagnosticGenerated on diagnostic"), AutoData]
        public void Raises_DiagnosticGenerated_On_Diagnostic(string message)
        {
            using (var client = new SoulseekClient(minorVersion: 9999, options: null))
            {
                DiagnosticEventArgs args = default;

                ListenerHandler l = new ListenerHandler(client);
                l.DiagnosticGenerated += (sender, e) => args = e;

                var diagnostic = l.GetProperty<IDiagnosticFactory>("Diagnostic");
                diagnostic.Info(message);

                Assert.Equal(message, args.Message);
            }
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Does not throw raising DiagnosticGenerated if no handlers bound"), AutoData]
        public void Does_Not_Throw_Raising_DiagnosticGenerated_If_No_Handlers_Bound(string message)
        {
            using (var client = new SoulseekClient(minorVersion: 9999, options: null))
            {
                ListenerHandler l = new ListenerHandler(client);

                var diagnostic = l.GetProperty<IDiagnosticFactory>("Diagnostic");

                var ex = Record.Exception(() => diagnostic.Info(message));

                Assert.Null(ex);
            }
        }

        [Trait("Category", "Diagnostic")]
        [Fact(DisplayName = "Dispatches connection handling without an async-void boundary")]
        public void Dispatches_Connection_Handling_Without_An_Async_Void_Boundary()
        {
            var method = typeof(ListenerHandler).GetMethod(nameof(ListenerHandler.HandleConnection), BindingFlags.Public | BindingFlags.Instance);

            Assert.NotNull(method);
            Assert.Equal(typeof(void), method.ReturnType);
            Assert.Empty(method.GetCustomAttributes(typeof(AsyncStateMachineAttribute), inherit: false));
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on connection"), AutoData]
        public void Creates_Diagnostic_On_Connection(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            handler.HandleConnection(null, mocks.Connection.Object);

            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Accepted incoming connection", StringComparison.InvariantCultureIgnoreCase))), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on error"), AutoData]
        public void Creates_Diagnostic_On_Error(IPEndPoint endpoint, string message)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Diagnostic.Setup(m => m.Warning(It.IsAny<string>(), It.IsAny<Exception>()));

            var exception = new Exception(message);

            handler.HandleError(null, exception);

            mocks.Diagnostic.Verify(
                m => m.Warning(
                    It.Is<string>(s => s.Contains("Failed to establish an incoming connection", StringComparison.InvariantCultureIgnoreCase) && s.Contains(message, StringComparison.InvariantCultureIgnoreCase)),
                    exception),
                Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on unknown connection"), AutoData]
        public void Creates_Diagnostic_On_Unknown_Connection(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(5)));

            mocks.Connection.Setup(m => m.ReadAsync(1, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(1)));

            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            handler.HandleConnection(null, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("failed to initialize", compare) && s.Contains("Unrecognized initialization message", compare))), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic if connection read throws"), AutoData]
        public void Creates_Diagnostic_If_Connection_Read_Throws(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Throws(new Exception());

            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            handler.HandleConnection(null, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("failed to initialize", compare))), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Handles obfuscated mark failures inside diagnostic boundary"), AutoData]
        public async Task Handles_Obfuscated_Mark_Failures_Inside_Diagnostic_Boundary(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.Connection.Setup(m => m.MarkObfuscated()).Throws(new InvalidOperationException("mark failed"));
            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            await handler.HandleConnectionAsync(mocks.Listener.Object, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("failed to initialize", compare) && s.Contains("mark failed", compare))), Times.Once);
            mocks.Connection.Verify(m => m.Disconnect(It.Is<string>(s => s.Contains("mark failed", StringComparison.InvariantCultureIgnoreCase)), null), Times.Once);
            mocks.Connection.Verify(m => m.Dispose(), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Swallows cleanup failures after initialization failure"), AutoData]
        public async Task Swallows_Cleanup_Failures_After_Initialization_Failure(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Throws(new InvalidOperationException("read failed"));
            mocks.Connection.Setup(m => m.Disconnect(It.IsAny<string>(), null))
                .Throws(new InvalidOperationException("disconnect failed"));
            mocks.Connection.Setup(m => m.Dispose())
                .Throws(new InvalidOperationException("dispose failed"));
            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            var ex = await Record.ExceptionAsync(() => handler.HandleConnectionAsync(null, mocks.Connection.Object));

            Assert.Null(ex);
            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("failed to initialize", compare) && s.Contains("read failed", compare))), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Fact(DisplayName = "Null connection stays inside diagnostic boundary")]
        public async Task Null_Connection_Stays_Inside_Diagnostic_Boundary()
        {
            using (var client = new SoulseekClient(minorVersion: 9999, options: null))
            {
                var diagnostic = new Mock<IDiagnosticFactory>();
                diagnostic.Setup(m => m.Debug(It.IsAny<string>()));
                var handler = new ListenerHandler(client, diagnostic.Object);

                var ex = await Record.ExceptionAsync(() => handler.HandleConnectionAsync(null, null));

                Assert.Null(ex);
                diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("failed to initialize", StringComparison.InvariantCultureIgnoreCase) && s.Contains("connection", StringComparison.InvariantCultureIgnoreCase))), Times.Once);
            }
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on PeerInit"), AutoData]
        public void Creates_Diagnostic_On_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            var message = new PeerInit(username, Constants.ConnectionType.Peer, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            handler.HandleConnection(null, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("PeerInit for connection type", compare))), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on unknown PierceFirewall"), AutoData]
        public async Task Creates_Diagnostic_On_PierceFirewall(IPEndPoint endpoint, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Throws(new Exception());

            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            await handler.HandleConnectionAsync(null, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Unknown PierceFirewall", compare))), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Adds provisional peer connection on unknown PierceFirewall"), AutoData]
        public async Task Adds_Provisional_Peer_Connection_On_Unknown_PierceFirewall(IPEndPoint endpoint, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            await handler.HandleConnectionAsync(null, mocks.Connection.Object);

            var expectedUsername = $"pierce-{token}-{endpoint.Address}:{endpoint.Port}";
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(expectedUsername, mocks.Connection.Object), Times.Once);
            mocks.Connection.Verify(m => m.Disconnect(It.IsAny<string>(), It.IsAny<Exception>()), Times.Never);
            mocks.Connection.Verify(m => m.Dispose(), Times.Never);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Adds provisional obfuscated peer connection on unknown obfuscated PierceFirewall"), AutoData]
        public async Task Adds_Provisional_Obfuscated_Peer_Connection_On_Unknown_Obfuscated_PierceFirewall(IPEndPoint endpoint, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token).ToByteArray();
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 8).ToArray()));
            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));

            await handler.HandleConnectionAsync(mocks.Listener.Object, mocks.Connection.Object);

            var expectedUsername = $"pierce-{token}-{endpoint.Address}:{endpoint.Port}";
            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateObfuscatedMessageConnectionAsync(expectedUsername, mocks.Connection.Object), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(expectedUsername, mocks.Connection.Object), Times.Never);
            mocks.Connection.Verify(m => m.Disconnect(It.IsAny<string>(), It.IsAny<Exception>()), Times.Never);
            mocks.Connection.Verify(m => m.Dispose(), Times.Never);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on peer PierceFirewall"), AutoData]
        public void Creates_Diagnostic_On_Peer_PierceFirewall(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));
            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            var dict = new ConcurrentDictionary<int, string>();
            dict.TryAdd(token, username);

            mocks.PeerConnectionManager.Setup(m => m.PendingSolicitations)
                .Returns(dict);

            handler.HandleConnection(null, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Peer PierceFirewall", compare))), Times.Once);
        }

        [Trait("Category", "Diagnostic")]
        [Theory(DisplayName = "Creates diagnostic on distributed PierceFirewall"), AutoData]
        public void Creates_Diagnostic_On_Distributed_PierceFirewall(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));
            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            var dict = new ConcurrentDictionary<int, string>();
            dict.TryAdd(token, username);

            mocks.DistributedConnectionManager.Setup(m => m.PendingSolicitations)
                .Returns(dict);

            handler.HandleConnection(null, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Distributed PierceFirewall", compare))), Times.Once);
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Adds peer connection on peer PeerInit"), AutoData]
        public void Adds_Peer_Connection_On_Peer_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Peer, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            handler.HandleConnection(null, mocks.Connection.Object);

            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(username, It.IsAny<IConnection>()));
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Adds transfer connection on transfer PeerInit"), AutoData]
        public void Adds_Transfer_Connection_On_Transfer_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Transfer, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            handler.HandleConnection(null, mocks.Connection.Object);

            mocks.PeerConnectionManager.Verify(m => m.GetTransferConnectionAsync(username, token, It.IsAny<IConnection>()));
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Completes DirectTransfer wait on transfer PeerInit"), AutoData]
        public void Completes_DirectTransfer_Wait_On_Transfer_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Transfer, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            var newTransfer = new Mock<IConnection>();

            mocks.PeerConnectionManager.Setup(m => m.GetTransferConnectionAsync(username, token, It.IsAny<IConnection>()))
                .Returns(Task.FromResult((newTransfer.Object, token)));

            // make it appear as though the wait exists, so the transfer is expected
            mocks.Waiter.Setup(m => m.HasWait(It.IsAny<WaitKey>())).Returns(true);

            handler.HandleConnection(null, mocks.Connection.Object);

            var key = new WaitKey(Constants.WaitKey.DirectTransfer, username, token);
            mocks.Waiter.Verify(m => m.Complete(key, newTransfer.Object), Times.Once);
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Disconnects DirectTransfer on missing wait"), AutoData]
        public void Disconnects_DirectTransfer_On_Missing_Wait(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Transfer, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            var newTransfer = new Mock<IConnection>();

            mocks.PeerConnectionManager.Setup(m => m.GetTransferConnectionAsync(username, token, It.IsAny<IConnection>()))
                .Returns(Task.FromResult((newTransfer.Object, token)));

            // make it appear as though the wait does not exist, so the transfer is unexpected
            mocks.Waiter.Setup(m => m.HasWait(It.IsAny<WaitKey>())).Returns(false);

            handler.HandleConnection(null, mocks.Connection.Object);

            var key = new WaitKey(Constants.WaitKey.DirectTransfer, username, token);
            mocks.Waiter.Verify(m => m.Complete(key, newTransfer.Object), Times.Never);

            newTransfer.Verify(m => m.Disconnect("Transfer connection rejected: unknown token", null), Times.Once);
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Adds distributed connection on distributed PeerInit"), AutoData]
        public void Adds_Distributed_Connection_On_Distributed_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Distributed, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            handler.HandleConnection(null, mocks.Connection.Object);

            mocks.DistributedConnectionManager.Verify(m => m.AddOrUpdateChildConnectionAsync(username, It.IsAny<IConnection>()));
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Adds obfuscated distributed connection on distributed PeerInit"), AutoData]
        public void Adds_Obfuscated_Distributed_Connection_On_Distributed_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Distributed, token).ToByteArray();
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 8).ToArray()));
            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));

            handler.HandleConnection(mocks.Listener.Object, mocks.Connection.Object);

            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Once);
            mocks.DistributedConnectionManager.Verify(m => m.AddOrUpdateChildConnectionAsync(username, mocks.Connection.Object), Times.Once);
        }

        [Trait("Category", "PeerInit")]
        [Theory(DisplayName = "Accepts obfuscated transfer PeerInit"), AutoData]
        public void Accepts_Obfuscated_Transfer_PeerInit(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Transfer, token).ToByteArray();
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 8).ToArray()));
            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));

            handler.HandleConnection(mocks.Listener.Object, mocks.Connection.Object);

            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.GetTransferConnectionAsync(username, token, It.IsAny<IConnection>()), Times.Once);
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Obfuscated transfer PeerInit accepted", StringComparison.InvariantCultureIgnoreCase))), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Completes solicited peer connection on peer PierceFirewall"), AutoData]
        public void Completes_Solicited_Peer_Connection_On_Peer_PierceFirewall(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));
            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            var dict = new ConcurrentDictionary<int, string>();
            dict.TryAdd(token, username);

            mocks.PeerConnectionManager.Setup(m => m.PendingSolicitations)
                .Returns(dict);

            handler.HandleConnection(null, mocks.Connection.Object);

            var expectedKey = new WaitKey(Constants.WaitKey.SolicitedPeerConnection, username, token);
            mocks.Waiter.Verify(m => m.Complete(expectedKey, mocks.Connection.Object), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Completes solicited obfuscated peer connection on peer PierceFirewall"), AutoData]
        public void Completes_Solicited_Obfuscated_Peer_Connection_On_Peer_PierceFirewall(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token).ToByteArray();
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 8).ToArray()));
            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));

            var dict = new ConcurrentDictionary<int, string>();
            dict.TryAdd(token, username);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.PeerConnectionManager.Setup(m => m.PendingSolicitations)
                .Returns(dict);

            handler.HandleConnection(mocks.Listener.Object, mocks.Connection.Object);

            var expectedKey = new WaitKey(Constants.WaitKey.SolicitedPeerConnection, username, token);
            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Once);
            mocks.Waiter.Verify(m => m.Complete(expectedKey, mocks.Connection.Object), Times.Once);
        }

        [Trait("Category", "Message")]
        [Theory(DisplayName = "Rejects oversized obfuscated init before allocation"), AutoData]
        public void Rejects_Oversized_Obfuscated_Init_Before_Allocation(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var lengthBytes = new byte[4];
            BinaryPrimitives.WriteInt32LittleEndian(lengthBytes, RotatedObfuscation.MaxInitMessageLength + 1);
            var firstBlock = RotatedObfuscation.Encode(lengthBytes, 0x1020_3040);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(firstBlock));
            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            handler.HandleConnection(mocks.Listener.Object, mocks.Connection.Object);

            mocks.Connection.Verify(m => m.ReadAsync(RotatedObfuscation.MaxInitMessageLength + 1, It.IsAny<CancellationToken>()), Times.Never);
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Invalid obfuscated initialization message length", StringComparison.InvariantCultureIgnoreCase))), Times.Once);
        }

        [Trait("Category", "Message")]
        [Theory(DisplayName = "Rejects oversized plain init without faulting the listener task"), AutoData]
        public async Task Rejects_Oversized_Plain_Init_Without_Faulting_The_Listener_Task(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var invalidLength = RotatedObfuscation.MaxInitMessageLength + 1;
            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(invalidLength)));
            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            var exception = await Record.ExceptionAsync(() => handler.HandleConnectionAsync(null, mocks.Connection.Object));

            Assert.Null(exception);
            mocks.Connection.Verify(m => m.ReadAsync(invalidLength, It.IsAny<CancellationToken>()), Times.Never);
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("Invalid initialization message length", StringComparison.InvariantCultureIgnoreCase))), Times.Once);
            mocks.Connection.Verify(m => m.Disconnect(It.Is<string>(s => s.Contains("Invalid initialization message length", StringComparison.InvariantCultureIgnoreCase)), null), Times.Once);
        }

        [Trait("Category", "SharedObfuscationSniffing")]
        [Theory(DisplayName = "Shared listener classifies plain PeerInit connection as plain"), AutoData]
        public async Task Shared_Listener_Classifies_Plain_PeerInit_Connection_As_Plain(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Peer, token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Listener.Setup(m => m.ObfuscationSniffingEnabled).Returns(true);

            // the plain length prefix (well within the [4, MaxInitMessageLength] bound) is read once as the
            // "sniffed" first four bytes and is not re-read from the socket.
            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));

            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            await handler.HandleConnectionAsync(mocks.Listener.Object, mocks.Connection.Object);

            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Never);
            mocks.Connection.Verify(m => m.ReadAsync(8, It.IsAny<CancellationToken>()), Times.Never);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(username, mocks.Connection.Object), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateObfuscatedMessageConnectionAsync(username, mocks.Connection.Object), Times.Never);
        }

        [Trait("Category", "SharedObfuscationSniffing")]
        [Theory(DisplayName = "Shared listener classifies obfuscated PeerInit connection as obfuscated"), AutoData]
        public async Task Shared_Listener_Classifies_Obfuscated_PeerInit_Connection_As_Obfuscated(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PeerInit(username, Constants.ConnectionType.Peer, token).ToByteArray();

            // the key (0x1020_3040), read raw as the first four bytes of the obfuscated header, decodes to a
            // candidate length far outside the plain [4, MaxInitMessageLength] bound, so sniffing correctly falls
            // through to the obfuscated interpretation.
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Listener.Setup(m => m.ObfuscationSniffingEnabled).Returns(true);

            mocks.Connection.SetupSequence(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 4).ToArray()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(4, 4).ToArray()));

            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));

            await handler.HandleConnectionAsync(mocks.Listener.Object, mocks.Connection.Object);

            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateObfuscatedMessageConnectionAsync(username, mocks.Connection.Object), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(username, mocks.Connection.Object), Times.Never);
        }

        [Trait("Category", "SharedObfuscationSniffing")]
        [Theory(DisplayName = "Shared listener disconnects when sniffed obfuscated frame fails validation"), AutoData]
        public async Task Shared_Listener_Disconnects_When_Sniffed_Obfuscated_Frame_Fails_Validation(IPEndPoint endpoint)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var lengthBytes = new byte[4];
            BinaryPrimitives.WriteInt32LittleEndian(lengthBytes, RotatedObfuscation.MaxInitMessageLength + 1);
            var obfuscatedHeader = RotatedObfuscation.Encode(lengthBytes, 0x1020_3040);

            mocks.Listener.Setup(m => m.ObfuscationSniffingEnabled).Returns(true);

            mocks.Connection.SetupSequence(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedHeader.AsSpan().Slice(0, 4).ToArray()))
                .Returns(Task.FromResult(obfuscatedHeader.AsSpan().Slice(4, 4).ToArray()));

            mocks.Diagnostic.Setup(m => m.Debug(It.IsAny<string>()));

            await handler.HandleConnectionAsync(mocks.Listener.Object, mocks.Connection.Object);

            var compare = StringComparison.InvariantCultureIgnoreCase;
            mocks.Diagnostic.Verify(m => m.Debug(It.Is<string>(s => s.Contains("failed to initialize", compare) && s.Contains("Invalid obfuscated initialization message length", compare))), Times.Once);
            mocks.Connection.Verify(m => m.Disconnect(It.Is<string>(s => s.Contains("Invalid obfuscated initialization message length", StringComparison.InvariantCultureIgnoreCase)), null), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Completes solicited distributed connection on distributed PierceFirewall"), AutoData]
        public void Completes_Solicited_Distributed_Connection_On_Distributed_PierceFirewall(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));
            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            var dict = new ConcurrentDictionary<int, string>();
            dict.TryAdd(token, username);

            mocks.DistributedConnectionManager.Setup(m => m.PendingSolicitations)
                .Returns(dict);

            handler.HandleConnection(null, mocks.Connection.Object);

            var expectedKey = new WaitKey(Constants.WaitKey.SolicitedDistributedConnection, username, token);
            mocks.Waiter.Verify(m => m.Complete(expectedKey, mocks.Connection.Object), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Completes solicited obfuscated distributed connection on distributed PierceFirewall"), AutoData]
        public void Completes_Solicited_Obfuscated_Distributed_Connection_On_Distributed_PierceFirewall(IPEndPoint endpoint, string username, int token)
        {
            var (handler, mocks) = GetFixture(endpoint);

            var message = new PierceFirewall(token).ToByteArray();
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 8).ToArray()));
            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));

            var dict = new ConcurrentDictionary<int, string>();
            dict.TryAdd(token, username);

            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);
            mocks.DistributedConnectionManager.Setup(m => m.PendingSolicitations)
                .Returns(dict);

            handler.HandleConnection(mocks.Listener.Object, mocks.Connection.Object);

            var expectedKey = new WaitKey(Constants.WaitKey.SolicitedDistributedConnection, username, token);
            mocks.Connection.Verify(m => m.MarkObfuscated(), Times.Once);
            mocks.Waiter.Verify(m => m.Complete(expectedKey, mocks.Connection.Object), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Adds connection on SearchResponse PierceFirewall"), AutoData]
        public void Adds_Connection_On_SearchResponse_PierceFirewall(IPEndPoint endpoint, string username, int token, string query)
        {
            (string Username, int Token, string Query, SearchResponse SearchResponse) response = (username, token, query, null);

            var cache = new Mock<ISearchResponseCache>();
            cache.Setup(m => m.TryGet(token, out response)).Returns(true);

            var (handler, mocks) = GetFixture(endpoint, new SoulseekClientOptions(searchResponseCache: cache.Object));

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));
            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            handler.HandleConnection(null, mocks.Connection.Object);

            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(username, mocks.Connection.Object), Times.Once);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Adds obfuscated connection on obfuscated SearchResponse PierceFirewall"), AutoData]
        public void Adds_Obfuscated_Connection_On_Obfuscated_SearchResponse_PierceFirewall(IPEndPoint endpoint, string username, int token, string query)
        {
            (string Username, int Token, string Query, SearchResponse SearchResponse) response = (username, token, query, null);

            var cache = new Mock<ISearchResponseCache>();
            cache.Setup(m => m.TryGet(token, out response)).Returns(true);

            var (handler, mocks) = GetFixture(endpoint, new SoulseekClientOptions(searchResponseCache: cache.Object));

            var message = new PierceFirewall(token).ToByteArray();
            var obfuscatedMessage = RotatedObfuscation.Encode(message, 0x1020_3040);

            mocks.Connection.Setup(m => m.ReadAsync(8, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(0, 8).ToArray()));
            mocks.Connection.Setup(m => m.ReadAsync(message.Length - 4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(obfuscatedMessage.AsSpan().Slice(8).ToArray()));
            mocks.Listener.Setup(m => m.Obfuscated).Returns(true);

            handler.HandleConnection(mocks.Listener.Object, mocks.Connection.Object);

            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateObfuscatedMessageConnectionAsync(username, mocks.Connection.Object), Times.Once);
            mocks.PeerConnectionManager.Verify(m => m.AddOrUpdateMessageConnectionAsync(username, mocks.Connection.Object), Times.Never);
        }

        [Trait("Category", "PierceFirewall")]
        [Theory(DisplayName = "Responds to search on SearchResponse PierceFirewall"), AutoData]
        public void Responds_To_Search_On_SearchResponse_PierceFirewall(IPEndPoint endpoint, string username, int token, string query)
        {
            (string Username, int Token, string Query, SearchResponse SearchResponse) response = (username, token, query, null);

            var cache = new Mock<ISearchResponseCache>();
            cache.Setup(m => m.TryGet(token, out response)).Returns(true);

            var (handler, mocks) = GetFixture(endpoint, new SoulseekClientOptions(searchResponseCache: cache.Object));

            var message = new PierceFirewall(token);
            var messageBytes = message.ToByteArray().AsSpan().Slice(4).ToArray();

            mocks.Connection.Setup(m => m.ReadAsync(4, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(BitConverter.GetBytes(messageBytes.Length)));
            mocks.Connection.Setup(m => m.ReadAsync(messageBytes.Length, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(messageBytes));

            handler.HandleConnection(null, mocks.Connection.Object);

            mocks.SearchResponder.Verify(m => m.TryRespondAsync(token), Times.Once);
        }

        private static (ListenerHandler Handler, Mocks Mocks) GetFixture(IPEndPoint endpoint, SoulseekClientOptions clientOptions = null)
        {
            var mocks = new Mocks(clientOptions);

            mocks.Connection.Setup(m => m.IPEndPoint).Returns(endpoint);

            var handler = new ListenerHandler(
                mocks.Client.Object,
                mocks.Diagnostic.Object);

            return (handler, mocks);
        }

        private class Mocks
        {
            public Mocks(SoulseekClientOptions clientOptions = null)
            {
                Client = new Mock<SoulseekClient>(9999, clientOptions)
                {
                    CallBase = true,
                };

                Listener.Setup(m => m.Port).Returns(clientOptions?.ListenPort ?? new SoulseekClientOptions().ListenPort);
                PeerConnectionManager.Setup(m => m.PendingSolicitations)
                    .Returns(new Dictionary<int, string>());
                DistributedConnectionManager.Setup(m => m.PendingSolicitations)
                    .Returns(new Dictionary<int, string>());

                Client.Setup(m => m.PeerConnectionManager).Returns(PeerConnectionManager.Object);
                Client.Setup(m => m.DistributedConnectionManager).Returns(DistributedConnectionManager.Object);
                Client.Setup(m => m.State).Returns(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
                Client.Setup(m => m.Options).Returns(clientOptions ?? new SoulseekClientOptions());
                Client.Setup(m => m.Listener).Returns(Listener.Object);
                Client.Setup(m => m.Waiter).Returns(Waiter.Object);
                Client.Setup(m => m.SearchResponder).Returns(SearchResponder.Object);
            }

            public Mock<SoulseekClient> Client { get; }
            public Mock<IPeerConnectionManager> PeerConnectionManager { get; } = new Mock<IPeerConnectionManager>();
            public Mock<IDistributedConnectionManager> DistributedConnectionManager { get; } = new Mock<IDistributedConnectionManager>();
            public Mock<IDiagnosticFactory> Diagnostic { get; } = new Mock<IDiagnosticFactory>();
            public Mock<IConnection> Connection { get; } = new Mock<IConnection>();
            public Mock<IListener> Listener { get; } = new Mock<IListener>();
            public Mock<IWaiter> Waiter { get; } = new Mock<IWaiter>();
            public Mock<ISearchResponder> SearchResponder { get; } = new Mock<ISearchResponder>();
        }
    }
}
