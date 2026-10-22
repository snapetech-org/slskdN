// <copyright file="MeshRendezvousInterestTests.cs" company="slskdN Team">
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
    using System.Collections.Generic;
    using System.Linq;
    using System.Text;
    using System.Threading;
    using System.Threading.Tasks;
    using Moq;
    using Soulseek;
    using Soulseek.Messaging;
    using Soulseek.Messaging.Messages;
    using Soulseek.Network;
    using Xunit;

    public class MeshRendezvousInterestTests
    {
        [Trait("Category", "MeshRendezvousInterest")]
        [Fact(DisplayName = "MeshRendezvousInterestTag has expected protocol value")]
        public void MeshRendezvousInterestTag_Has_Expected_Protocol_Value()
        {
            Assert.Equal("slskdn-mesh-v1", SoulseekClient.MeshRendezvousInterestTag);
        }

        [Trait("Category", "MeshRendezvousInterest")]
        [Fact(DisplayName = "AddMeshRendezvousInterestAsync adds mesh rendezvous tag as interest")]
        public async Task AddMeshRendezvousInterestAsync_Adds_Mesh_Rendezvous_Tag()
        {
            var serverConn = new Mock<IMessageConnection>();
            IOutgoingMessage interestMessage = null;
            serverConn.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Callback<IOutgoingMessage, CancellationToken>( (m, _) => interestMessage = m)
                .Returns(Task.CompletedTask);

            using (var s = new SoulseekClient(
                minorVersion: 9999,
                serverConnection: serverConn.Object))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                await s.AddMeshRendezvousInterestAsync();
            }

            Assert.NotNull(interestMessage);
            var sentMessage = interestMessage.ToByteArray();
            var sentCode = BitConverter.ToInt32(sentMessage, 4);
            Assert.Equal((int)MessageCode.Server.InterestAdd, sentCode);

            Assert.Equal(SoulseekClient.MeshRendezvousInterestTag, ReadStringFromMessage(sentMessage, 8));
        }

        [Trait("Category", "MeshRendezvousInterest")]
        [Fact(DisplayName = "RemoveMeshRendezvousInterestAsync removes mesh rendezvous tag from interest")]
        public async Task RemoveMeshRendezvousInterestAsync_Removes_Mesh_Rendezvous_Tag()
        {
            var serverConn = new Mock<IMessageConnection>();
            IOutgoingMessage interestMessage = null;
            serverConn.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Callback<IOutgoingMessage, CancellationToken>( (m, _) => interestMessage = m)
                .Returns(Task.CompletedTask);

            using (var s = new SoulseekClient(
                minorVersion: 9999,
                serverConnection: serverConn.Object))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                await s.RemoveMeshRendezvousInterestAsync();
            }

            Assert.NotNull(interestMessage);
            var sentMessage = interestMessage.ToByteArray();
            var sentCode = BitConverter.ToInt32(sentMessage, 4);
            Assert.Equal((int)MessageCode.Server.InterestRemove, sentCode);

            Assert.Equal(SoulseekClient.MeshRendezvousInterestTag, ReadStringFromMessage(sentMessage, 8));
        }

        [Trait("Category", "MeshRendezvousInterest")]
        [Fact(DisplayName = "GetMeshRendezvousUsersAsync gets similar users")]
        public async Task GetMeshRendezvousUsersAsync_Uses_GetSimilarUsers()
        {
            var expectedUsers = new[]
            {
                new SimilarUser("alice", 1),
                new SimilarUser("bob", 3),
            };

            var waiter = new Mock<IWaiter>();
            waiter.Setup(m => m.Wait<PersonalSimilarUsersResponse>(It.IsAny<WaitKey>(), null, It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult(new PersonalSimilarUsersResponse(expectedUsers.Select(user => (user.Username, user.Rating)))));

            var serverConn = new Mock<IMessageConnection>();
            IOutgoingMessage similarUsersMessage = null;
            serverConn.Setup(m => m.WriteAsync(It.IsAny<IOutgoingMessage>(), It.IsAny<CancellationToken>()))
                .Callback<IOutgoingMessage, CancellationToken>( (m, _) => similarUsersMessage = m)
                .Returns(Task.CompletedTask);

            using (var s = new SoulseekClient(
                minorVersion: 9999,
                waiter: waiter.Object,
                serverConnection: serverConn.Object))
            {
                s.SetProperty("State", SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn);

                var actual = await s.GetMeshRendezvousUsersAsync();

                Assert.Equal(
                    expectedUsers.Select(user => (user.Username, user.Rating)),
                    actual.Select(user => (user.Username, user.Rating)));
            }

            Assert.NotNull(similarUsersMessage);
            var sentMessage = similarUsersMessage.ToByteArray();
            var sentCode = BitConverter.ToInt32(sentMessage, 4);
            Assert.Equal((int)MessageCode.Server.GetSimilarUsers, sentCode);
        }

        private static string ReadStringFromMessage(byte[] message, int stringOffset)
        {
            var stringLength = BitConverter.ToInt32(message, stringOffset);
            return Encoding.UTF8.GetString(message, stringOffset + 4, stringLength);
        }
    }
}
