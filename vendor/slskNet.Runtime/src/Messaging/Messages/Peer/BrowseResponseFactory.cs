// <copyright file="BrowseResponseFactory.cs" company="JP Dillingham">
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
    using System.Collections.Generic;
    using System.IO;
    using System.Text;
    using Soulseek.Diagnostics;
    using Soulseek.Messaging.Compression;

    /// <summary>
    ///     Factory for browse response messages. This class helps keep message abstractions from leaking into the public API via
    ///     <see cref="BrowseResponse"/>, which is a public class.
    /// </summary>
    internal static class BrowseResponseFactory
    {
        /// <summary>
        ///     Creates a new instance of <see cref="BrowseResponse"/> from the specified <paramref name="bytes"/>.
        /// </summary>
        /// <param name="bytes">The byte array from which to parse.</param>
        /// <returns>The parsed instance.</returns>
        public static BrowseResponse FromByteArray(byte[] bytes)
        {
            var reader = new MessageReader<MessageCode.Peer>(bytes);
            var code = reader.ReadCode();

            if (code != MessageCode.Peer.BrowseResponse)
            {
                throw new MessageException($"Message Code mismatch creating {nameof(BrowseResponse)} (expected: {(int)MessageCode.Peer.BrowseResponse}, received: {(int)code}");
            }

            reader.Decompress();

            var directoryCount = ProtocolCountReader.ReadCount(reader, "directory", minimumBytesPerItem: 4);
            var directoryList = new List<Soulseek.Directory>();
            var lockedDirectoryList = new List<Soulseek.Directory>();

            for (int i = 0; i < directoryCount; i++)
            {
                directoryList.Add(reader.ReadDirectory());
            }

            if (reader.HasMoreData)
            {
                _ = reader.ReadInteger();

                if (reader.HasMoreData)
                {
                    var lockedDirectoryCount = ProtocolCountReader.ReadCount(reader, "locked directory", minimumBytesPerItem: 4);

                    for (int i = 0; i < lockedDirectoryCount; i++)
                    {
                        lockedDirectoryList.Add(reader.ReadDirectory());
                    }
                }
            }

            return new BrowseResponse(directoryList, lockedDirectoryList);
        }

        /// <summary>
        ///     Constructs a <see cref="byte"/> array from this message.
        /// </summary>
        /// <param name="browseResponse">The instance from which to construct the byte array.</param>
        /// <returns>The constructed byte array.</returns>
        public static byte[] ToByteArray(this BrowseResponse browseResponse)
        {
            var builder = new MessageBuilder()
                .WriteCode(MessageCode.Peer.BrowseResponse)
                .WriteInteger(browseResponse.DirectoryCount);

            foreach (var directory in browseResponse.Directories)
            {
                builder.WriteDirectory(directory);
            }

            builder.WriteInteger(0);
            builder.WriteInteger(browseResponse.LockedDirectoryCount);

            foreach (var directory in browseResponse.LockedDirectories)
            {
                builder.WriteDirectory(directory);
            }

            builder.Compress();
            return builder.Build();
        }

        public static void WriteToStream(BrowseResponse browseResponse, Stream stream)
        {
            if (browseResponse == null)
            {
                throw new ArgumentNullException(nameof(browseResponse));
            }

            WriteToStream(
                browseResponse.DirectoryCount,
                browseResponse.Directories,
                browseResponse.LockedDirectoryCount,
                browseResponse.LockedDirectories,
                stream);
        }

        /// <summary>
        ///     Writes a browse message from streaming directory sequences without first creating a collection-backed response.
        /// </summary>
        /// <param name="directoryCount">The number of unlocked directories.</param>
        /// <param name="directories">The unlocked directories in wire order.</param>
        /// <param name="lockedDirectoryCount">The number of locked directories.</param>
        /// <param name="lockedDirectories">The locked directories in wire order.</param>
        /// <param name="stream">The seekable stream to which the message is written.</param>
        public static void WriteToStream(
            int directoryCount,
            IEnumerable<Soulseek.Directory> directories,
            int lockedDirectoryCount,
            IEnumerable<Soulseek.Directory> lockedDirectories,
            Stream stream)
        {
            if (directoryCount < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(directoryCount));
            }

            if (directories == null)
            {
                throw new ArgumentNullException(nameof(directories));
            }

            if (lockedDirectoryCount < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(lockedDirectoryCount));
            }

            if (lockedDirectories == null)
            {
                throw new ArgumentNullException(nameof(lockedDirectories));
            }

            if (stream == null)
            {
                throw new ArgumentNullException(nameof(stream));
            }

            if (!stream.CanWrite)
            {
                throw new InvalidOperationException("The specified stream is not writable");
            }

            if (!stream.CanSeek)
            {
                throw new InvalidOperationException("The specified stream must be seekable");
            }

            var start = stream.Position;
            WriteInteger(stream, 0);
            WriteInteger(stream, (int)MessageCode.Peer.BrowseResponse);

#pragma warning disable CA2000 // ZOutputStream.Close closes the destination stream; end() releases compression state without closing it.
            var zStream = new ZOutputStream(stream, zlibConst.Z_DEFAULT_COMPRESSION);
#pragma warning restore CA2000

            try
            {
                WriteInteger(zStream, directoryCount);

                var writtenDirectories = 0;

                foreach (var directory in directories)
                {
                    if (writtenDirectories == directoryCount)
                    {
                        throw new MessageException("Browse response directory count does not match the streamed entries");
                    }

                    WriteDirectory(zStream, directory);
                    writtenDirectories++;
                }

                if (writtenDirectories != directoryCount)
                {
                    throw new MessageException("Browse response directory count does not match the streamed entries");
                }

                WriteInteger(zStream, 0);
                WriteInteger(zStream, lockedDirectoryCount);

                var writtenLockedDirectories = 0;

                foreach (var directory in lockedDirectories)
                {
                    if (writtenLockedDirectories == lockedDirectoryCount)
                    {
                        throw new MessageException("Browse response locked directory count does not match the streamed entries");
                    }

                    WriteDirectory(zStream, directory);
                    writtenLockedDirectories++;
                }

                if (writtenLockedDirectories != lockedDirectoryCount)
                {
                    throw new MessageException("Browse response locked directory count does not match the streamed entries");
                }

                zStream.finish();
            }
            finally
            {
                zStream.end();
            }

            var end = stream.Position;
            var length = end - start - sizeof(int);

            if (length > int.MaxValue)
            {
                throw new MessageException($"Browse response length exceeds the maximum message size: {length}");
            }

            stream.Position = start;
            WriteInteger(stream, (int)length);
            stream.Position = end;
        }

        private static void WriteDirectory(Stream stream, Soulseek.Directory directory)
        {
            directory = directory ?? throw new ArgumentNullException(nameof(directory));

            WriteString(stream, directory.Name);
            WriteInteger(stream, directory.FileCount);

            foreach (var file in directory.Files)
            {
                WriteFile(stream, file);
            }
        }

        private static void WriteFile(Stream stream, Soulseek.File file)
        {
            file = file ?? throw new ArgumentNullException(nameof(file));

            stream.WriteByte((byte)file.Code);
            WriteString(stream, file.Filename);
            WriteLong(stream, file.Size);
            WriteString(stream, file.Extension);
            WriteInteger(stream, file.AttributeCount);

            foreach (var attribute in file.Attributes)
            {
                WriteInteger(stream, (int)attribute.Type);
                WriteInteger(stream, attribute.Value);
            }
        }

        private static void WriteInteger(Stream stream, int value)
        {
            var bytes = BitConverter.GetBytes(value);
            stream.Write(bytes, 0, bytes.Length);
        }

        private static void WriteLong(Stream stream, long value)
        {
            var bytes = BitConverter.GetBytes(value);
            stream.Write(bytes, 0, bytes.Length);
        }

        private static void WriteString(Stream stream, string value)
        {
            if (value == null)
            {
                throw new ArgumentNullException(nameof(value), "Invalid attempt to write a null string to message");
            }

            byte[] bytes;

            try
            {
                bytes = Encoding.GetEncoding(CharacterEncoding.UTF8, EncoderFallback.ExceptionFallback, DecoderFallback.ExceptionFallback).GetBytes(value);
            }
            catch (Exception ex)
            {
                bytes = Encoding.GetEncoding(CharacterEncoding.UTF8).GetBytes(value);
                GlobalDiagnostic.Trace($"Failed to encode {CharacterEncoding.UTF8} string of {value.Length} characters; resorted to fallback encoding {CharacterEncoding.UTF8}", ex);
            }

            WriteInteger(stream, bytes.Length);
            stream.Write(bytes, 0, bytes.Length);
        }
    }
}
