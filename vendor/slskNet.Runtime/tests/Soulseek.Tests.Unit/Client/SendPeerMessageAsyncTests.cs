// <copyright file="SendPeerMessageAsyncTests.cs" company="slskdN Team">
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

namespace Soulseek.Tests.Unit.Client
{
    using System;
    using System.Linq;
    using System.Net;
    using System.Threading;
    using System.Threading.Tasks;
    using AutoFixture.Xunit2;
    using Moq;
    using Soulseek;
    using Soulseek.Messaging.Messages;
    using Soulseek.Network;
    using Xunit;

    public class SendPeerMessageAsyncTests
    {
        [Trait("Category", "SendPeerMessageAsync")]
        [Fact(DisplayName = "SendPeerMessageAsync throws InvalidOperationException when not connected")]
        public async Task SendPeerMessageAsync_Throws_InvalidOperationException_When_Not_Connected()
        {
            using (var s = new SoulseekClient(minorVersion: 9999))
            {
                var ex = await Record.ExceptionAsync(() => s.SendPeerMessageAsync("foo", 4096, new byte[] { 1, 2, 3 }));

                Assert.NotNull(ex);
                Assert.IsType<InvalidOperationException>(ex);
            }
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Theory(DisplayName = "SendPeerMessageAsync throws ArgumentException given bad input")]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("  ")]
        public async Task SendPeerMessageAsync_Throws_ArgumentException_Given_Bad_Input(string username)
        {
            using (var s = new SoulseekClient(minorVersion: 9999))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                var ex = await Record.ExceptionAsync(() => s.SendPeerMessageAsync(username, 4096, new byte[] { 1, 2, 3 }));

                Assert.NotNull(ex);
                Assert.IsType<ArgumentException>(ex);
            }
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Fact(DisplayName = "SendPeerMessageAsync throws ArgumentOutOfRangeException for negative message code")]
        public async Task SendPeerMessageAsync_Throws_ArgumentOutOfRangeException_For_Negative_Message_Code()
        {
            using (var s = new SoulseekClient(minorVersion: 9999))
            {
                var ex = await Record.ExceptionAsync(() => s.SendPeerMessageAsync("foo", -1, Array.Empty<byte>()));

                Assert.NotNull(ex);
                Assert.IsType<ArgumentOutOfRangeException>(ex);
            }
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Theory(DisplayName = "SendPeerMessageAsync sends expected code and payload"), AutoData]
        public async Task SendPeerMessageAsync_Sends_Expected_Code_And_Payload(string username, byte[] payload, IPEndPoint endpoint, int messageCode)
        {
            if (messageCode < 0)
            {
                messageCode *= -1;
            }

            messageCode = messageCode % 65000;
            if (messageCode < 1)
            {
                messageCode = 4096;
            }

            if (payload == null)
            {
                payload = new byte[] { 1, 2, 3 };
            }

            var waiter = new Mock<IWaiter>();
            waiter.Setup(m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new UserAddressResponse(username, endpoint.Address, endpoint.Port)));

            var serverConn = new Mock<IMessageConnection>();
            serverConn.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);

            byte[] sentMessage = null;
            var peerConn = new Mock<IMessageConnection>();
            peerConn.Setup(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
                .Callback<byte[], CancellationToken>((message, token) => sentMessage = message)
                .Returns(Task.CompletedTask);

            var connManager = new Mock<IPeerConnectionManager>();
            connManager.Setup(m => m.GetOrAddMessageConnectionAsync(username, endpoint, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(peerConn.Object));

            using (var s = new SoulseekClient(minorVersion: 9999, waiter: waiter.Object, serverConnection: serverConn.Object, peerConnectionManager: connManager.Object))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                await s.SendPeerMessageAsync(username, messageCode, payload);
            }

            var outgoing = sentMessage;
            Assert.NotNull(outgoing);
            Assert.Equal(messageCode, BitConverter.ToInt32(outgoing, 4));
            Assert.Equal(payload, outgoing.Skip(8).ToArray());

            connManager.Verify(m => m.GetOrAddMessageConnectionAsync(username, endpoint, It.IsAny<CancellationToken>()), Times.Once);
            peerConn.Verify(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()), Times.Once);
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Fact(DisplayName = "SendPeerMessageAsync throws SoulseekClientException when write fails")]
        public async Task SendPeerMessageAsync_Throws_SoulseekClientException_When_Write_Fails()
        {
            var username = "foo";
            var endpoint = new IPEndPoint(IPAddress.Loopback, 1234);

            var waiter = new Mock<IWaiter>();
            waiter.Setup(m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new UserAddressResponse(username, endpoint.Address, endpoint.Port)));

            var serverConn = new Mock<IMessageConnection>();
            serverConn.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);

            var peerConn = new Mock<IMessageConnection>();
            peerConn.Setup(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
                .Throws(new ConnectionWriteException());

            var connManager = new Mock<IPeerConnectionManager>();
            connManager.Setup(m => m.GetOrAddMessageConnectionAsync(username, endpoint, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(peerConn.Object));

            using (var s = new SoulseekClient(minorVersion: 9999, waiter: waiter.Object, serverConnection: serverConn.Object, peerConnectionManager: connManager.Object))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                var ex = await Record.ExceptionAsync(() => s.SendPeerMessageAsync(username, 4096, new byte[] { 1, 2, 3 }));

                Assert.NotNull(ex);
                Assert.IsType<SoulseekClientException>(ex);
                Assert.IsType<ConnectionWriteException>(ex.InnerException);
            }
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Fact(DisplayName = "SendPeerMessageAsync uses given cancellation token")]
        public async Task SendPeerMessageAsync_Uses_Given_CancellationToken()
        {
            var cancellationToken = new CancellationToken(false);
            var username = "foo";
            var endpoint = new IPEndPoint(IPAddress.Loopback, 1234);

            var waiter = new Mock<IWaiter>();
            waiter.Setup(m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new UserAddressResponse(username, endpoint.Address, endpoint.Port)));

            var serverConn = new Mock<IMessageConnection>();
            serverConn.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);

            var peerConn = new Mock<IMessageConnection>();
            CancellationToken writeToken = default;
            peerConn.Setup(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
                .Callback<byte[], CancellationToken>((message, token) => writeToken = token)
                .Returns(Task.CompletedTask);

            var connManager = new Mock<IPeerConnectionManager>();
            connManager.Setup(m => m.GetOrAddMessageConnectionAsync(username, endpoint, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(peerConn.Object));

            using (var s = new SoulseekClient(minorVersion: 9999, waiter: waiter.Object, serverConnection: serverConn.Object, peerConnectionManager: connManager.Object))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                await s.SendPeerMessageAsync(username, 4096, new byte[] { 1, 2, 3 }, cancellationToken);
            }

            waiter.Verify(
                m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()),
                Times.Once);
            connManager.Verify(m => m.GetOrAddMessageConnectionAsync(username, endpoint, cancellationToken), Times.Once);
            Assert.Equal(cancellationToken, writeToken);
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Fact(DisplayName = "RegisterPeerMessageHandler registers and unregisters")]
        public void RegisterPeerMessageHandler_Registers_And_Unregisters()
        {
            using (var s = new SoulseekClient(minorVersion: 9999))
            {
                var code = 4096;

                s.RegisterPeerMessageHandler(code, (username, endpoint, payload) => Task.CompletedTask);

                Assert.True(s.UnregisterPeerMessageHandler(code));
                Assert.False(s.UnregisterPeerMessageHandler(code));
            }
        }

        [Trait("Category", "SendPeerMessageAsync")]
        [Fact(DisplayName = "RegisterPeerMessageHandler throws for null handler")]
        public void RegisterPeerMessageHandler_Throws_When_Handler_Is_Null()
        {
            using (var s = new SoulseekClient(minorVersion: 9999))
            {
                var ex = Record.Exception(() => s.RegisterPeerMessageHandler(4096, null));

                Assert.NotNull(ex);
                Assert.IsType<ArgumentNullException>(ex);
            }
        }
    }
}
