// <copyright file="UserAddressResponseTests.cs" company="JP Dillingham">
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

namespace Soulseek.Tests.Unit.Messaging.Messages
{
    using System;
    using System.Net;
    using AutoFixture.Xunit2;
    using Soulseek.Messaging;
    using Soulseek.Messaging.Messages;
    using Xunit;

    public class UserAddressResponseTests
    {
        [Trait("Category", "Instantiation")]
        [Theory(DisplayName = "Instantiates with the given data"), AutoData]
        public void Instantiates_With_The_Given_Data(string username, IPEndPoint endpoint)
        {
            UserAddressResponse response = null;

            var ex = Record.Exception(() => response = new UserAddressResponse(username, endpoint));

            Assert.Null(ex);

            Assert.Equal(username, response.Username);
            Assert.Equal(endpoint.Address, response.IPEndPoint.Address);
            Assert.Equal(endpoint.Port, response.IPEndPoint.Port);
        }

        [Trait("Category", "Instantiation")]
        [Theory(DisplayName = "Snapshots endpoint"), AutoData]
        public void Snapshots_Endpoint(string username, IPEndPoint endpoint)
        {
            var port = endpoint.Port;
            var response = new UserAddressResponse(username, endpoint);

            endpoint.Port = port == 1 ? 2 : 1;
            response.IPEndPoint.Port = port == 3 ? 4 : 3;

            Assert.Equal(port, response.IPEndPoint.Port);
            Assert.Equal(port, response.Port);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Snapshots IP address")]
        public void Snapshots_IPAddress()
        {
            var address = IPAddress.Parse("fe80::1");
            address.ScopeId = 10;
            var response = new UserAddressResponse("user", address, 1234, obfuscationType: 1, obfuscatedPort: 4321);

            address.ScopeId = 20;
            response.IPAddress.ScopeId = 30;
            response.IPEndPoint.Address.ScopeId = 40;
            response.ObfuscatedIPEndPoint.Address.ScopeId = 50;

            Assert.Equal(10, response.IPAddress.ScopeId);
            Assert.Equal(10, response.IPEndPoint.Address.ScopeId);
            Assert.Equal(10, response.ObfuscatedIPEndPoint.Address.ScopeId);
        }

        [Trait("Category", "Parse")]
        [Fact(DisplayName = "Parse throws MessageExcepton on code mismatch")]
        public void Parse_Throws_MessageException_On_Code_Mismatch()
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Peer.BrowseRequest)
                .Build();

            var ex = Record.Exception(() => UserAddressResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Fact(DisplayName = "Parse throws MessageReadException on missing data")]
        public void Parse_Throws_MessageReadException_On_Missing_Data()
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetPeerAddress)
                .WriteString("foo")
                .Build();

            var ex = Record.Exception(() => UserAddressResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageReadException>(ex);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse returns expected data"), AutoData]
        public void Parse_Returns_Expected_Data(string username, IPEndPoint endpoint)
        {
            var ipBytes = endpoint.Address.GetAddressBytes();
            Array.Reverse(ipBytes);

            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetPeerAddress)
                .WriteString(username)
                .WriteBytes(ipBytes)
                .WriteInteger(endpoint.Port)
                .Build();

            var response = UserAddressResponse.FromByteArray(msg);

            Assert.Equal(username, response.Username);
            Assert.Equal(endpoint.Address, response.IPAddress);
            Assert.Equal(endpoint.Port, response.Port);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse returns obfuscated metadata"), AutoData]
        public void Parse_Returns_Obfuscated_Metadata(string username, IPEndPoint endpoint)
        {
            var ipBytes = endpoint.Address.GetAddressBytes();
            Array.Reverse(ipBytes);

            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetPeerAddress)
                .WriteString(username)
                .WriteBytes(ipBytes)
                .WriteInteger(endpoint.Port)
                .WriteInteger(1)
                .WriteBytes(new byte[] { 0x34, 0x12 })
                .Build();

            var response = UserAddressResponse.FromByteArray(msg);

            Assert.Equal(1, response.ObfuscationType);
            Assert.Equal(0x1234, response.ObfuscatedPort);
            Assert.True(response.HasObfuscatedEndpoint);
            Assert.Equal(0x1234, response.ObfuscatedIPEndPoint.Port);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse throws MessageException on invalid port")]
        [InlineData(-1)]
        [InlineData(65536)]
        public void Parse_Throws_MessageException_On_Invalid_Port(int port)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetPeerAddress)
                .WriteString("user")
                .WriteBytes(new byte[] { 1, 0, 0, 127 })
                .WriteInteger(port)
                .Build();

            var ex = Record.Exception(() => UserAddressResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Fact(DisplayName = "Parse throws MessageException on invalid obfuscated port")]
        public void Parse_Throws_MessageException_On_Invalid_Obfuscated_Port()
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetPeerAddress)
                .WriteString("user")
                .WriteBytes(new byte[] { 1, 0, 0, 127 })
                .WriteInteger(1)
                .WriteInteger(1)
                .WriteBytes(new byte[] { 0, 0 })
                .Build();

            var ex = Record.Exception(() => UserAddressResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }
    }
}
