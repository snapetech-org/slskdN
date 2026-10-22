// <copyright file="ProtocolCountHardeningTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
// </copyright>

namespace Soulseek.Tests.Unit.Messaging.Messages
{
    using Soulseek.Messaging;
    using Soulseek.Messaging.Messages;
    using Xunit;

    public class ProtocolCountHardeningTests
    {
        [Fact(DisplayName = "Search response rejects impossible file count")]
        public void Search_Response_Rejects_Impossible_File_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.SearchResponse)
                .WriteString("user")
                .WriteInteger(1)
                .WriteInteger(10)
                .Compress()
                .Build();

            Assert.Throws<MessageReadException>(() => SearchResponseFactory.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Search response accepts negative file size from the wire")]
        public void Search_Response_Accepts_Negative_File_Size()
        {
            // Some Soulseek clients emit -1 (or other negatives) for unknown file sizes; accept
            // the value so the entire response isn't dropped over a single malformed entry.
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.SearchResponse)
                .WriteString("user")
                .WriteInteger(1)
                .WriteInteger(1)
                .WriteByte(0x2)
                .WriteString("file")
                .WriteLong(long.MinValue)
                .WriteString("ext")
                .WriteInteger(0)
                .WriteByte(0)
                .WriteInteger(0)
                .WriteLong(0)
                .WriteBytes(new byte[4])
                .Compress()
                .Build();

            var response = SearchResponseFactory.FromByteArray(bytes);

            Assert.Contains(response.Files, file => file.Size == long.MinValue);
        }

        [Fact(DisplayName = "Search response accepts legacy sign-extended unsigned file size")]
        public void Search_Response_Accepts_Legacy_Sign_Extended_Unsigned_File_Size()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.SearchResponse)
                .WriteString("user")
                .WriteInteger(1)
                .WriteInteger(1)
                .WriteByte(0x2)
                .WriteString("file")
                .WriteLong(-1)
                .WriteString("ext")
                .WriteInteger(0)
                .WriteByte(0)
                .WriteInteger(0)
                .WriteLong(0)
                .WriteBytes(new byte[4])
                .Compress()
                .Build();

            var response = SearchResponseFactory.FromByteArray(bytes);

            Assert.Contains(response.Files, file => file.Size == uint.MaxValue);
        }

        [Fact(DisplayName = "Join room rejects mismatched parallel counts")]
        public void Join_Room_Rejects_Mismatched_Parallel_Counts()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.JoinRoom)
                .WriteString("room")
                .WriteInteger(1)
                .WriteString("alice")
                .WriteInteger(0)
                .Build();

            Assert.Throws<MessageException>(() => JoinRoomResponse.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Browse response rejects negative nested directory file count")]
        public void Browse_Response_Rejects_Negative_Nested_Directory_File_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.BrowseResponse)
                .WriteInteger(1)
                .WriteString("dir")
                .WriteInteger(-1)
                .Compress()
                .Build();

            Assert.Throws<MessageException>(() => BrowseResponseFactory.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Browse response rejects impossible nested file attribute count")]
        public void Browse_Response_Rejects_Impossible_Nested_File_Attribute_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.BrowseResponse)
                .WriteInteger(1)
                .WriteString("dir")
                .WriteInteger(1)
                .WriteByte(0)
                .WriteString("file.mp3")
                .WriteLong(123)
                .WriteString("mp3")
                .WriteInteger(1)
                .Compress()
                .Build();

            Assert.Throws<MessageReadException>(() => BrowseResponseFactory.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Message reader rejects negative string length")]
        public void Message_Reader_Rejects_Negative_String_Length()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.BrowseResponse)
                .WriteInteger(-1)
                .Build();
            var reader = new MessageReader<MessageCode.Peer>(bytes);

            Assert.Throws<MessageReadException>(() => reader.ReadString());
        }

        [Fact(DisplayName = "Message reader rejects negative byte count")]
        public void Message_Reader_Rejects_Negative_Byte_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Peer.BrowseResponse)
                .Build();
            var reader = new MessageReader<MessageCode.Peer>(bytes);

            Assert.Throws<MessageReadException>(() => reader.ReadBytes(-1));
        }

        [Fact(DisplayName = "NetInfo rejects negative parent count")]
        public void NetInfo_Rejects_Negative_Parent_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.NetInfo)
                .WriteInteger(-1)
                .Build();

            Assert.Throws<MessageException>(() => NetInfoNotification.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Room list rejects impossible room name count")]
        public void Room_List_Rejects_Impossible_Room_Name_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.RoomList)
                .WriteInteger(3)
                .WriteString("room")
                .Build();

            Assert.Throws<MessageReadException>(() => RoomListResponseFactory.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Room list rejects negative room user count")]
        public void Room_List_Rejects_Negative_Room_User_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.RoomList)
                .WriteInteger(1)
                .WriteString("room")
                .WriteInteger(1)
                .WriteInteger(-1)
                .WriteInteger(0)
                .WriteInteger(0)
                .WriteInteger(0)
                .Build();

            Assert.Throws<MessageException>(() => RoomListResponseFactory.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Private room owned list rejects negative user count")]
        public void Private_Room_Owned_List_Rejects_Negative_User_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.PrivateRoomOwned)
                .WriteString("room")
                .WriteInteger(-1)
                .Build();

            Assert.Throws<MessageException>(() => PrivateRoomOwnedListNotification.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Privileged user list rejects negative count")]
        public void Privileged_User_List_Rejects_Negative_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.PrivilegedUsers)
                .WriteInteger(-1)
                .Build();

            Assert.Throws<MessageException>(() => PrivilegedUserListNotification.FromByteArray(bytes));
        }

        [Fact(DisplayName = "Excluded search phrase list rejects negative count")]
        public void Excluded_Search_Phrase_List_Rejects_Negative_Count()
        {
            var bytes = new MessageBuilder()
                .WriteCode(MessageCode.Server.ExcludedSearchPhrases)
                .WriteInteger(-1)
                .Build();

            Assert.Throws<MessageException>(() => ExcludedSearchPhrasesNotification.FromByteArray(bytes));
        }
    }
}
