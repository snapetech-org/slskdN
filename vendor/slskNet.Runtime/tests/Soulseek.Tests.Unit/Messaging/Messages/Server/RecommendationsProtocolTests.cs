// <copyright file="RecommendationsProtocolTests.cs" company="slskdN Team">
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
    using System.Collections.Generic;
    using System.Linq;
    using AutoFixture.Xunit2;
    using Soulseek.Messaging;
    using Soulseek.Messaging.Messages;
    using Xunit;

    public class RecommendationsProtocolTests
    {
        [Trait("Category", "ToByteArray")]
        [Theory(DisplayName = "InterestCommand constructs the correct message"), AutoData]
        public void InterestCommand_Constructs_The_Correct_Message(string item)
        {
            var msg = new InterestCommand(MessageCode.Server.InterestAdd, item).ToByteArray();
            var reader = new MessageReader<MessageCode.Server>(msg);

            Assert.Equal(MessageCode.Server.InterestAdd, reader.ReadCode());
            Assert.Equal(item, reader.ReadString());
        }

        [Trait("Category", "ToByteArray")]
        [Fact(DisplayName = "RecommendationsRequest constructs the correct messages")]
        public void RecommendationsRequest_Constructs_The_Correct_Messages()
        {
            Assert.Equal(MessageCode.Server.GetRecommendations, new MessageReader<MessageCode.Server>(new RecommendationsRequest().ToByteArray()).ReadCode());
            Assert.Equal(MessageCode.Server.GetGlobalRecommendations, new MessageReader<MessageCode.Server>(new RecommendationsRequest(global: true).ToByteArray()).ReadCode());
        }

        [Trait("Category", "ToByteArray")]
        [Theory(DisplayName = "ItemRecommendationsRequest throws given invalid code"), AutoData]
        public void ItemRecommendationsRequest_Throws_Given_Invalid_Code(string item)
        {
            var ex = Record.Exception(() => new ItemRecommendationsRequest(MessageCode.Server.JoinRoom, item));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "RecommendationsResponse parses recommendations and unrecommendations"), AutoData]
        public void RecommendationsResponse_Parses_Recommendations_And_Unrecommendations(string recommendation, string unrecommendation, int recommendationScore, int unrecommendationScore)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetRecommendations)
                .WriteInteger(1)
                .WriteString(recommendation)
                .WriteInteger(recommendationScore)
                .WriteInteger(1)
                .WriteString(unrecommendation)
                .WriteInteger(unrecommendationScore)
                .Build();

            var response = RecommendationsResponse.FromByteArray(msg);

            Assert.Equal(recommendation, response.Recommendations.Single().Item);
            Assert.Equal(recommendationScore, response.Recommendations.Single().Score);
            Assert.Equal(unrecommendation, response.Unrecommendations.Single().Item);
            Assert.Equal(unrecommendationScore, response.Unrecommendations.Single().Score);
        }

        [Trait("Category", "Parse")]
        [Fact(DisplayName = "RecommendationsResponse throws given negative count")]
        public void RecommendationsResponse_Throws_Given_Negative_Count()
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetRecommendations)
                .WriteInteger(-1)
                .Build();

            var ex = Record.Exception(() => RecommendationsResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsType<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Fact(DisplayName = "RecommendationsResponse throws given impossible count")]
        public void RecommendationsResponse_Throws_Given_Impossible_Count()
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetRecommendations)
                .WriteInteger(1)
                .Build();

            var ex = Record.Exception(() => RecommendationsResponse.FromByteArray(msg));

            Assert.NotNull(ex);
            Assert.IsAssignableFrom<MessageException>(ex);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "UserInterestsResponse parses liked and hated interests"), AutoData]
        public void UserInterestsResponse_Parses_Liked_And_Hated_Interests(string username, string liked, string hated)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetUserInterests)
                .WriteString(username)
                .WriteInteger(1)
                .WriteString(liked)
                .WriteInteger(1)
                .WriteString(hated)
                .Build();

            var response = UserInterestsResponse.FromByteArray(msg);

            Assert.Equal(username, response.Username);
            Assert.Equal(liked, response.Liked.Single());
            Assert.Equal(hated, response.Hated.Single());
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "SimilarUsersResponse parses users"), AutoData]
        public void SimilarUsersResponse_Parses_Users(string username, int rating)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetSimilarUsers)
                .WriteInteger(1)
                .WriteString(username)
                .WriteInteger(rating)
                .Build();

            var response = SimilarUsersResponse.FromByteArray(msg).Single();

            Assert.Equal(username, response.Username);
            Assert.Equal(rating, response.Rating);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "ItemRecommendationsResponse parses recommendations"), AutoData]
        public void ItemRecommendationsResponse_Parses_Recommendations(string item, string recommendation, int score)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetItemRecommendations)
                .WriteString(item)
                .WriteInteger(1)
                .WriteString(recommendation)
                .WriteInteger(score)
                .Build();

            var response = ItemRecommendationsResponse.FromByteArray(msg);

            Assert.Equal(item, response.Item);
            Assert.Equal(recommendation, response.Recommendations.Single().Item);
            Assert.Equal(score, response.Recommendations.Single().Score);
        }

        [Trait("Category", "Parse")]
        [Theory(DisplayName = "ItemSimilarUsersResponse parses users"), AutoData]
        public void ItemSimilarUsersResponse_Parses_Users(string item, string username)
        {
            var msg = new MessageBuilder()
                .WriteCode(MessageCode.Server.GetItemSimilarUsers)
                .WriteString(item)
                .WriteInteger(1)
                .WriteString(username)
                .Build();

            var response = ItemSimilarUsersResponse.FromByteArray(msg);

            Assert.Equal(item, response.Item);
            Assert.Equal(username, response.Usernames.Single());
        }

        [Trait("Category", "ToByteArray")]
        [Theory(DisplayName = "MessageUsersCommand constructs the correct message"), AutoData]
        public void MessageUsersCommand_Constructs_The_Correct_Message(string username, string otherUsername, string message)
        {
            var msg = new MessageUsersCommand(new[] { username, otherUsername }, message).ToByteArray();
            var reader = new MessageReader<MessageCode.Server>(msg);

            Assert.Equal(MessageCode.Server.MessageUsers, reader.ReadCode());
            Assert.Equal(2, reader.ReadInteger());
            Assert.Equal(username, reader.ReadString());
            Assert.Equal(otherUsername, reader.ReadString());
            Assert.Equal(message, reader.ReadString());
        }

        [Trait("Category", "ToByteArray")]
        [Fact(DisplayName = "MessageUsersCommand snapshots usernames")]
        public void MessageUsersCommand_Snapshots_Usernames()
        {
            var usernames = new List<string> { "alice", "bob" };
            var command = new MessageUsersCommand(usernames, "hello");

            usernames[0] = "carol";

            Assert.Equal(new[] { "alice", "bob" }, command.Usernames);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "MessageUsersCommand rejects null inputs")]
        public void MessageUsersCommand_Rejects_Null_Inputs()
        {
            Assert.Throws<ArgumentNullException>(() => new MessageUsersCommand(null, "hello"));
            Assert.Throws<ArgumentNullException>(() => new MessageUsersCommand(new[] { "alice" }, null));
            Assert.Throws<ArgumentException>(() => new MessageUsersCommand(new[] { "alice", null }, "hello"));
        }
    }
}
