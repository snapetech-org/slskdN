// <copyright file="ConnectToPeerResponseTests.cs" company="JP Dillingham">
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

    public class ConnectToPeerResponseTests
    {
        [Trait("Category", "Instantiation")]
        [Theory(DisplayName = "Instantiates with the given data"), AutoData]
        public void Instantiates_With_The_Given_Data(string username, string type, IPEndPoint endpoint, int token, bool isPrivileged)
        {
            ConnectToPeerResponse response = null;

            var ex = Record.Exception(() => response = new ConnectToPeerResponse(username, type, endpoint, token, isPrivileged));

            Assert.Null(ex);

            Assert.Equal(username, response.Username);
            Assert.Equal(type, response.Type);
            Assert.Equal(endpoint.Address, response.IPEndPoint.Address);
            Assert.Equal(endpoint.Port, response.IPEndPoint.Port);
            Assert.Equal(token, response.Token);
            Assert.Equal(isPrivileged, response.IsPrivileged);
        }

        [Trait("Category", "Instantiation")]
        [Theory(DisplayName = "Snapshots endpoint"), AutoData]
        public void Snapshots_Endpoint(string username, string type, IPEndPoint endpoint, int token, bool isPrivileged)
        {
            var port = endpoint.Port;
            var response = new ConnectToPeerResponse(username, type, endpoint, token, isPrivileged);

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
            var response = new ConnectToPeerResponse("user", "P", address, 1234, 1, false, obfuscationType: 1, obfuscatedPort: 4321);

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

            var ex = Record.Exception(() => ConnectToPeerResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Fact(DisplayName = "Parse throws MessageReadException on missing data")]
        public void Parse_Throws_MessageReadException_On_Missing_Data()
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.ConnectToPeer)
                .WriteString("foo")
                .WriteString("F")
                .Build();

            var ex = Record.Exception(() => ConnectToPeerResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageReadException>(ex);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse returns expected data"), AutoData]
        public void Parse_Returns_Expected_Data(string username, string type, IPEndPoint endpoint, int token, bool isPrivileged)
        {
            var ipBytes = endpoint.Address.GetAddressBytes();
            Array.Reverse(ipBytes);

            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.ConnectToPeer)
                .WriteString(username)
                .WriteString(type)
                .WriteBytes(ipBytes)
                .WriteInteger(endpoint.Port)
                .WriteInteger(token)
                .WriteByte((byte)(isPrivileged ? 1 : 0))
                .Build();

            var response = ConnectToPeerResponse.FromByteArray(msg);

            Assert.Equal(username, response.Username);
            Assert.Equal(type, response.Type);
            Assert.Equal(endpoint.Address, response.IPAddress);
            Assert.Equal(endpoint.Port, response.Port);
            Assert.Equal(token, response.Token);
            Assert.Equal(isPrivileged, response.IsPrivileged);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse throws MessageException on invalid port")]
        [InlineData(-1)]
        [InlineData(65536)]
        public void Parse_Throws_MessageException_On_Invalid_Port(int port)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.ConnectToPeer)
                .WriteString("user")
                .WriteString("P")
                .WriteBytes(new byte[] { 1, 0, 0, 127 })
                .WriteInteger(port)
                .WriteInteger(1)
                .WriteByte(0)
                .Build();

            var ex = Record.Exception(() => ConnectToPeerResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse returns obfuscated metadata"), AutoData]
        public void Parse_Returns_Obfuscated_Metadata(string username, IPEndPoint endpoint, int token, bool isPrivileged)
        {
            var ipBytes = endpoint.Address.GetAddressBytes();
            Array.Reverse(ipBytes);

            var obfuscatedPort = endpoint.Port == IPEndPoint.MinPort ? 1 : endpoint.Port;

            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.ConnectToPeer)
                .WriteString(username)
                .WriteString("P")
                .WriteBytes(ipBytes)
                .WriteInteger(endpoint.Port)
                .WriteInteger(token)
                .WriteByte((byte)(isPrivileged ? 1 : 0))
                .WriteInteger(1)
                .WriteInteger(obfuscatedPort)
                .Build();

            var response = ConnectToPeerResponse.FromByteArray(msg);

            Assert.Equal(1, response.ObfuscationType);
            Assert.Equal(obfuscatedPort, response.ObfuscatedPort);
            Assert.True(response.HasObfuscatedEndpoint);
            Assert.Equal(obfuscatedPort, response.ObfuscatedIPEndPoint.Port);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "Parse throws MessageException on invalid obfuscated port")]
        [InlineData(-1)]
        [InlineData(0)]
        [InlineData(65536)]
        public void Parse_Throws_MessageException_On_Invalid_Obfuscated_Port(int obfuscatedPort)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.ConnectToPeer)
                .WriteString("user")
                .WriteString("P")
                .WriteBytes(new byte[] { 1, 0, 0, 127 })
                .WriteInteger(1)
                .WriteInteger(1)
                .WriteByte(0)
                .WriteInteger(1)
                .WriteInteger(obfuscatedPort)
                .Build();

            var ex = Record.Exception(() => ConnectToPeerResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }
    }
}
