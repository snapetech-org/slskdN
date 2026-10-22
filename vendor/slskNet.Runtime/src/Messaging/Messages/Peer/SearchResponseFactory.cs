// <copyright file="SearchResponseFactory.cs" company="JP Dillingham">
//     Copyright (c) JP Dillingham.
//     Copyright (c) slskdN Team.
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
//     SPDX-FileCopyrightText: slskdN Team
//     SPDX-License-Identifier: GPL-3.0-only
// </copyright>

namespace Soulseek.Messaging.Messages
{
    using System;
    using System.Buffers.Binary;
    using System.Collections.Generic;
    using System.Linq;
    using Soulseek.Messaging.Compression;

    /// <summary>
    ///     Factory for search response messages. This class helps keep message abstractions from leaking into the public API via
    ///     <see cref="SearchResponse"/>, which is a public class.
    /// </summary>
    internal static class SearchResponseFactory
    {
        /// <summary>
        ///     Reads only the token from a compressed search response, without inflating its file list.
        /// </summary>
        /// <param name="bytes">The message bytes from which to read.</param>
        /// <returns>The search token.</returns>
        public static int ReadToken(byte[] bytes)
        {
            var reader = new MessageReader<MessageCode.Peer>(bytes);
            var code = reader.ReadCode();

            if (code != MessageCode.Peer.SearchResponse)
            {
                throw new MessageException($"Message Code mismatch creating {nameof(SearchResponse)} (expected: {(int)MessageCode.Peer.SearchResponse}, received: {(int)code}");
            }

            if (reader.Payload.Length == 0)
            {
                throw new MessageCompressionException("Unable to decompress an empty message");
            }

            try
            {
                using var compressedPayload = new System.IO.MemoryStream(bytes, 8, bytes.Length - 8, writable: false);
                using var decompressedPayload = new ZInputStream(compressedPayload);
                var integerBytes = new byte[sizeof(int)];
                var decompressedLength = 0;

                ReadExactly(decompressedPayload, integerBytes, sizeof(int), ref decompressedLength, "username length");
                var usernameLength = BinaryPrimitives.ReadInt32LittleEndian(integerBytes);

                if (usernameLength < 0)
                {
                    throw new MessageReadException($"Invalid string length: {usernameLength}");
                }

                if (usernameLength > MessageReader<MessageCode.Peer>.MaximumDecompressedPayloadLength - (sizeof(int) * 2))
                {
                    throw new MessageCompressionException($"Decompressed message payload exceeds the maximum allowed length of {MessageReader<MessageCode.Peer>.MaximumDecompressedPayloadLength} bytes");
                }

                var skipBuffer = new byte[8192];
                var remainingUsernameBytes = usernameLength;

                while (remainingUsernameBytes > 0)
                {
                    var bytesToSkip = Math.Min(remainingUsernameBytes, skipBuffer.Length);
                    ReadExactly(decompressedPayload, skipBuffer, bytesToSkip, ref decompressedLength, "username");
                    remainingUsernameBytes -= bytesToSkip;
                }

                ReadExactly(decompressedPayload, integerBytes, sizeof(int), ref decompressedLength, "search token");
                return BinaryPrimitives.ReadInt32LittleEndian(integerBytes);
            }
            catch (MessageException)
            {
                throw;
            }
            catch (Exception ex)
            {
                throw new MessageCompressionException("Failed to read the compressed search response prefix", ex);
            }
        }

        /// <summary>
        ///     Creates a new instance of <see cref="SearchResponse"/> from the specified <paramref name="bytes"/>.
        /// </summary>
        /// <param name="bytes">The byte array from which to parse.</param>
        /// <returns>The parsed instance.</returns>
        public static SearchResponse FromByteArray(byte[] bytes)
        {
            var reader = new MessageReader<MessageCode.Peer>(bytes);
            var code = reader.ReadCode();

            if (code != MessageCode.Peer.SearchResponse)
            {
                throw new MessageException($"Message Code mismatch creating {nameof(SearchResponse)} (expected: {(int)MessageCode.Peer.SearchResponse}, received: {(int)code}");
            }

            reader.Decompress();

            var username = reader.ReadString();
            var token = reader.ReadInteger();
            var fileCount = ProtocolCountReader.ReadCount(reader, "file", minimumBytesPerItem: 4);

            var fileList = reader.ReadFiles(fileCount);

            var freeUploadSlots = reader.ReadByte();
            var uploadSpeed = reader.ReadInteger();
            var queueLength = reader.ReadInteger();

            ProtocolValueValidator.ValidateNonNegative(uploadSpeed, "upload speed");
            ProtocolValueValidator.ValidateNonNegative(queueLength, "queue length");

            if (reader.HasMoreData)
            {
                // most clients send an unknown integer between queue length and the locked file count
                _ = reader.ReadInteger();
            }

            IEnumerable<File> lockedFileList = Enumerable.Empty<File>();

            if (reader.HasMoreData)
            {
                var count = ProtocolCountReader.ReadCount(reader, "locked file", minimumBytesPerItem: 4);
                lockedFileList = reader.ReadFiles(count);
            }

            if (SoulseekClient.ReportUnreadMessageData && reader.HasMoreData)
            {
                Diagnostics.GlobalDiagnostic.Warning($"Message reader for {nameof(MessageCode.Peer.SearchResponse)} finalized with {reader.Remaining} unread bytes");
            }

            return new SearchResponse(username, token, hasFreeUploadSlot: freeUploadSlots > 0, uploadSpeed, queueLength, fileList, lockedFileList);
        }

        private static void ReadExactly(ZInputStream reader, byte[] buffer, int count, ref int decompressedLength, string field)
        {
            var offset = 0;

            while (offset < count)
            {
                var read = reader.read(buffer, offset, count - offset);

                if (read < 0)
                {
                    throw new MessageReadException($"Failed to read search response {field}");
                }

                decompressedLength += read;

                if (decompressedLength > MessageReader<MessageCode.Peer>.MaximumDecompressedPayloadLength)
                {
                    throw new MessageCompressionException($"Decompressed message payload exceeds the maximum allowed length of {MessageReader<MessageCode.Peer>.MaximumDecompressedPayloadLength} bytes");
                }

                offset += read;
            }
        }

        /// <summary>
        ///     Constructs a <see cref="byte"/> array from this message.
        /// </summary>
        /// <param name="searchResponse">The instance from which to construct the byte array.</param>
        /// <returns>The constructed byte array.</returns>
        public static byte[] ToByteArray(this SearchResponse searchResponse)
        {
            var builder = new MessageBuilder()
                .WriteCode(MessageCode.Peer.SearchResponse)
                .WriteString(searchResponse.Username)
                .WriteInteger(searchResponse.Token)
                .WriteInteger(searchResponse.FileCount);

            foreach (var file in searchResponse.Files)
            {
                builder.WriteFile(file);
            }

            builder
                .WriteByte((byte)(searchResponse.HasFreeUploadSlot ? 1 : 0))
                .WriteInteger(searchResponse.UploadSpeed)
                .WriteInteger(searchResponse.QueueLength)
                .WriteInteger(0); // unknown value included for compatibility

            builder.WriteInteger(searchResponse.LockedFileCount);

            foreach (var file in searchResponse.LockedFiles)
            {
                builder.WriteFile(file);
            }

            builder.Compress();
            return builder.Build();
        }
    }
}
