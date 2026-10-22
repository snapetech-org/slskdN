// <copyright file="MeshRendezvousPeerMessageRoundTripTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
// </copyright>

namespace Soulseek.Tests.Unit.Client
{
    using System;
    using System.Linq;
    using System.Net;
    using System.Text;
    using System.Threading;
    using System.Threading.Tasks;
    using AutoFixture.Xunit2;
    using Moq;
    using Soulseek;
    using Soulseek.Diagnostics;
    using Soulseek.Messaging;
    using Soulseek.Messaging.Handlers;
    using Soulseek.Messaging.Messages;
    using Soulseek.Network;
    using Xunit;

    public class MeshRendezvousPeerMessageRoundTripTests
    {
        [Trait("Category", "MeshRendezvous")]
        [Theory, AutoData]
        public async Task SendPeerMessageAsync_round_trips_between_two_clients(string username, string targetUsername, byte[] payload)
        {
            if (payload == null || payload.Length == 0)
            {
                payload = Encoding.UTF8.GetBytes("mesh-ping");
            }

            var messageCode = 4096;
            var peerEndpoint = new IPEndPoint(IPAddress.Loopback, 5000);
            var senderToReceiverConnection = new Mock<IMessageConnection>();

            senderToReceiverConnection.SetupGet(m => m.Username)
                .Returns(username);

            senderToReceiverConnection.SetupGet(m => m.IPEndPoint)
                .Returns(peerEndpoint);

            byte[] rawMessage = null;
            senderToReceiverConnection.Setup(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
                .Callback<byte[], CancellationToken>((message, _) => rawMessage = message)
                .Returns(Task.CompletedTask);

            var waiter = new Mock<IWaiter>();
            waiter.Setup(m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new UserAddressResponse(targetUsername, peerEndpoint.Address, peerEndpoint.Port)));

            var serverConnA = new Mock<IMessageConnection>();
            var peerConnManagerA = new Mock<IPeerConnectionManager>();
            peerConnManagerA.Setup(m => m.GetOrAddMessageConnectionAsync(targetUsername, peerEndpoint, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(senderToReceiverConnection.Object));

            using (var sender = new SoulseekClient(
                minorVersion: 9999,
                waiter: waiter.Object,
                serverConnection: serverConnA.Object,
                peerConnectionManager: peerConnManagerA.Object))
            using (var receiver = new SoulseekClient(minorVersion: 9999))
            {
                sender.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
                receiver.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                byte[] receivedPayload = null;
                var receivedCompletion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

                receiver.RegisterPeerMessageHandler(messageCode, (fromUsername, endpoint, messagePayload) =>
                {
                    receivedPayload = messagePayload.ToArray();
                    receivedCompletion.TrySetResult(true);
                    return Task.CompletedTask;
                });

                await sender.SendPeerMessageAsync(targetUsername, messageCode, payload);

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(senderToReceiverConnection.Object, rawMessage);

                var result = await Task.WhenAny(receivedCompletion.Task, Task.Delay(TimeSpan.FromMilliseconds(200)));
                Assert.Same(receivedCompletion.Task, result);
                Assert.NotNull(rawMessage);
                Assert.NotNull(receivedPayload);
                Assert.Equal(payload, receivedPayload);
            }
        }

        [Trait("Category", "MeshRendezvous")]
        [Theory, AutoData]
        public void Signed_PeerCapability_Message_Updates_Registry(string username)
        {
            var endpoint = new IPEndPoint(IPAddress.Loopback, 5000);

            using (var signer = new Ed25519PeerDescriptorSigner())
            using (var receiver = new SoulseekClient(minorVersion: 9999))
            {
                var keys = signer.GenerateKeyPair();
                var descriptor = signer.Sign(
                    new PeerCapabilityDescriptor(features: new[] { "mesh" }),
                    keys.PrivateKey,
                    keys.PublicKey);

                var connection = GetCapabilityConnection(username, endpoint);
                var message = GetCapabilityMessage(new PeerCapabilityEnvelope(PeerCapabilityMessageType.Hello, descriptor, nonce: "n1"));

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(connection.Object, message);

                Assert.True(receiver.PeerCapabilities.TryGet(username, out var record));
                Assert.Equal(descriptor.PeerId, record.Descriptor.PeerId);
            }
        }

        [Trait("Category", "MeshRendezvous")]
        [Theory, AutoData]
        public async Task PeerCapability_Registry_Updated_Handler_Exception_Does_Not_Prevent_Acknowledgement(string username)
        {
            var endpoint = new IPEndPoint(IPAddress.Loopback, 5000);
            var diagnostic = new Mock<IDiagnosticFactory>();
            var waiter = new Mock<IWaiter>();
            var serverConnection = new Mock<IMessageConnection>();
            var acknowledgementConnection = new Mock<IMessageConnection>();
            var peerConnectionManager = new Mock<IPeerConnectionManager>();
            var acknowledgementSent = new TaskCompletionSource<byte[]>(TaskCreationOptions.RunContinuationsAsynchronously);

            waiter.Setup(m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new UserAddressResponse(username, endpoint.Address, endpoint.Port)));
            serverConnection.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);
            acknowledgementConnection.Setup(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
                .Callback<byte[], CancellationToken>((message, _) => acknowledgementSent.TrySetResult(message))
                .Returns(Task.CompletedTask);
            peerConnectionManager.Setup(m => m.GetOrAddMessageConnectionAsync(username, endpoint, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(acknowledgementConnection.Object));

            using (var signer = new Ed25519PeerDescriptorSigner())
            using (var receiver = new SoulseekClient(
                minorVersion: 9999,
                waiter: waiter.Object,
                serverConnection: serverConnection.Object,
                peerConnectionManager: peerConnectionManager.Object,
                diagnosticFactory: diagnostic.Object))
            {
                receiver.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
                receiver.SetPeerCapabilityDescriptor(new PeerCapabilityDescriptor(features: new[] { "local" }));
                receiver.PeerCapabilities.Updated += (_, __) => throw new InvalidOperationException("subscriber failed");

                var keys = signer.GenerateKeyPair();
                var descriptor = signer.Sign(
                    new PeerCapabilityDescriptor(features: new[] { "mesh" }),
                    keys.PrivateKey,
                    keys.PublicKey);
                var connection = GetCapabilityConnection(username, endpoint);
                var message = GetCapabilityMessage(new PeerCapabilityEnvelope(PeerCapabilityMessageType.Hello, descriptor, nonce: "n1"));

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(connection.Object, message);

                var completed = await Task.WhenAny(acknowledgementSent.Task, Task.Delay(TimeSpan.FromMilliseconds(500)));

                Assert.Same(acknowledgementSent.Task, completed);
                Assert.True(receiver.PeerCapabilities.TryGet(username, out _));
                Assert.Equal(PeerCapabilityEnvelope.MessageCode, BitConverter.ToInt32(await acknowledgementSent.Task, 4));
                diagnostic.Verify(m => m.Warning(It.Is<string>(s => s.ContainsInsensitive("Unhandled exception in Updated event handler")), It.IsAny<InvalidOperationException>()), Times.Once);
            }
        }

        [Trait("Category", "MeshRendezvous")]
        [Theory, AutoData]
        public async Task PeerCapability_Received_Handler_Exception_Does_Not_Prevent_Acknowledgement(string username)
        {
            var endpoint = new IPEndPoint(IPAddress.Loopback, 5000);
            var diagnostic = new Mock<IDiagnosticFactory>();
            var waiter = new Mock<IWaiter>();
            var serverConnection = new Mock<IMessageConnection>();
            var acknowledgementConnection = new Mock<IMessageConnection>();
            var peerConnectionManager = new Mock<IPeerConnectionManager>();
            var acknowledgementSent = new TaskCompletionSource<byte[]>(TaskCreationOptions.RunContinuationsAsynchronously);

            waiter.Setup(m => m.Wait<UserAddressResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new UserAddressResponse(username, endpoint.Address, endpoint.Port)));
            serverConnection.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);
            acknowledgementConnection.Setup(m => m.WriteAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
                .Callback<byte[], CancellationToken>((message, _) => acknowledgementSent.TrySetResult(message))
                .Returns(Task.CompletedTask);
            peerConnectionManager.Setup(m => m.GetOrAddMessageConnectionAsync(username, endpoint, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(acknowledgementConnection.Object));

            using (var signer = new Ed25519PeerDescriptorSigner())
            using (var receiver = new SoulseekClient(
                minorVersion: 9999,
                waiter: waiter.Object,
                serverConnection: serverConnection.Object,
                peerConnectionManager: peerConnectionManager.Object,
                diagnosticFactory: diagnostic.Object))
            {
                receiver.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);
                receiver.SetPeerCapabilityDescriptor(new PeerCapabilityDescriptor(features: new[] { "local" }));
                receiver.PeerCapabilityReceived += (_, __) => throw new InvalidOperationException("subscriber failed");

                var keys = signer.GenerateKeyPair();
                var descriptor = signer.Sign(
                    new PeerCapabilityDescriptor(features: new[] { "mesh" }),
                    keys.PrivateKey,
                    keys.PublicKey);
                var connection = GetCapabilityConnection(username, endpoint);
                var message = GetCapabilityMessage(new PeerCapabilityEnvelope(PeerCapabilityMessageType.Hello, descriptor, nonce: "n1"));

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(connection.Object, message);

                var completed = await Task.WhenAny(acknowledgementSent.Task, Task.Delay(TimeSpan.FromMilliseconds(500)));

                Assert.Same(acknowledgementSent.Task, completed);
                Assert.True(receiver.PeerCapabilities.TryGet(username, out _));
                Assert.Equal(PeerCapabilityEnvelope.MessageCode, BitConverter.ToInt32(await acknowledgementSent.Task, 4));
                diagnostic.Verify(m => m.Warning(It.Is<string>(s => s.ContainsInsensitive("Unhandled exception in PeerCapabilityReceived event handler")), It.IsAny<InvalidOperationException>()), Times.Once);
            }
        }

        [Trait("Category", "MeshRendezvous")]
        [Theory, AutoData]
        public void Unsigned_PeerCapability_Message_Does_Not_Update_Registry(string username)
        {
            var endpoint = new IPEndPoint(IPAddress.Loopback, 5000);

            using (var receiver = new SoulseekClient(minorVersion: 9999))
            {
                var descriptor = new PeerCapabilityDescriptor(peerId: "forged-peer", features: new[] { "mesh" });
                var connection = GetCapabilityConnection(username, endpoint);
                var message = GetCapabilityMessage(new PeerCapabilityEnvelope(PeerCapabilityMessageType.Hello, descriptor, nonce: "n1"));

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(connection.Object, message);

                Assert.False(receiver.PeerCapabilities.TryGet(username, out _));
            }
        }

        [Trait("Category", "MeshRendezvous")]
        [Theory, AutoData]
        public void Forged_PeerCapability_Message_Does_Not_Update_Registry(string username)
        {
            var endpoint = new IPEndPoint(IPAddress.Loopback, 5000);

            using (var signer = new Ed25519PeerDescriptorSigner())
            using (var receiver = new SoulseekClient(minorVersion: 9999))
            {
                var keys = signer.GenerateKeyPair();
                var signed = signer.Sign(
                    new PeerCapabilityDescriptor(features: new[] { "mesh" }),
                    keys.PrivateKey,
                    keys.PublicKey);
                var forged = new PeerCapabilityDescriptor(
                    signed.PeerId,
                    new[] { "mesh", "forged-feature" },
                    signed.OverlayPort,
                    signed.MaxPayloadLength,
                    signed.Signature);

                var connection = GetCapabilityConnection(username, endpoint);
                var message = GetCapabilityMessage(new PeerCapabilityEnvelope(PeerCapabilityMessageType.Hello, forged, nonce: "n1"));

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(connection.Object, message);

                Assert.False(receiver.PeerCapabilities.TryGet(username, out _));
            }
        }

        [Trait("Category", "MeshRendezvous")]
        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        public void PeerCapability_Message_With_Empty_Username_Does_Not_Update_Registry(string username)
        {
            var endpoint = new IPEndPoint(IPAddress.Loopback, 5000);

            using (var signer = new Ed25519PeerDescriptorSigner())
            using (var receiver = new SoulseekClient(minorVersion: 9999))
            {
                var keys = signer.GenerateKeyPair();
                var descriptor = signer.Sign(
                    new PeerCapabilityDescriptor(features: new[] { "mesh" }),
                    keys.PrivateKey,
                    keys.PublicKey);
                var connection = GetCapabilityConnection(username, endpoint);
                var message = GetCapabilityMessage(new PeerCapabilityEnvelope(PeerCapabilityMessageType.Hello, descriptor, nonce: "n1"));

                var receiverHandler = receiver.GetProperty<IPeerMessageHandler>("PeerMessageHandler");
                receiverHandler.HandleMessageRead(connection.Object, message);

                Assert.Empty(receiver.PeerCapabilities.Records);
            }
        }

        private static Mock<IMessageConnection> GetCapabilityConnection(string username, IPEndPoint endpoint)
        {
            var connection = new Mock<IMessageConnection>();
            connection.SetupGet(m => m.Username).Returns(username);
            connection.SetupGet(m => m.IPEndPoint).Returns(endpoint);
            return connection;
        }

        private static byte[] GetCapabilityMessage(PeerCapabilityEnvelope envelope)
        {
            return new MessageBuilder()
                .WriteCode(PeerCapabilityEnvelope.MessageCode)
                .WriteBytes(envelope.ToByteArray())
                .Build();
        }
    }
}
