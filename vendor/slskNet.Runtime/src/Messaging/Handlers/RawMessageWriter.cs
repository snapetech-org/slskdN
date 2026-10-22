// <copyright file="RawMessageWriter.cs" company="slskdN Team">
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
//     SPDX-FileCopyrightText: slskdN Team
//     SPDX-License-Identifier: GPL-3.0-only
// </copyright>

namespace Soulseek.Messaging.Handlers
{
    using System;
    using System.IO;
    using System.Security.Cryptography;
    using System.Threading;
    using System.Threading.Tasks;
    using Soulseek.Network;

    /// <summary>
    ///     Writes pre-serialized peer messages while preserving peer-message transport framing.
    /// </summary>
    internal static class RawMessageWriter
    {
        public static async Task WriteAsync(IMessageConnection connection, long length, Stream stream, CancellationToken? cancellationToken = null)
        {
            if (connection == null)
            {
                throw new ArgumentNullException(nameof(connection));
            }

            var token = cancellationToken ?? CancellationToken.None;

            if (!connection.Obfuscated)
            {
                await connection.WriteAsync(length, stream, cancellationToken: token).ConfigureAwait(false);
                return;
            }

            if (length > long.MaxValue - sizeof(uint))
            {
                throw new ArgumentOutOfRangeException(nameof(length), "The raw message is too large to obfuscate");
            }

            var obfuscatedStream = new RotatedObfuscationEncodingStream(stream);
            try
            {
                await connection.WriteAsync(length + sizeof(uint), obfuscatedStream, cancellationToken: token).ConfigureAwait(false);
            }
            finally
            {
                obfuscatedStream.Dispose();
            }
        }

        private sealed class RotatedObfuscationEncodingStream : Stream
        {
            private readonly byte[] keyBytes = new byte[sizeof(uint)];
            private readonly Stream innerStream;
            private int keyPrefixPosition;
            private uint key;
            private long payloadPosition;

            public RotatedObfuscationEncodingStream(Stream innerStream)
            {
                this.innerStream = innerStream ?? throw new ArgumentNullException(nameof(innerStream));

                using (var rng = RandomNumberGenerator.Create())
                {
                    rng.GetBytes(keyBytes);
                }

                key = BitConverter.ToUInt32(keyBytes, 0);
            }

            public override bool CanRead => innerStream.CanRead;
            public override bool CanSeek => false;
            public override bool CanWrite => false;
            public override long Length => innerStream.Length + keyBytes.Length;

            public override long Position
            {
                get => payloadPosition + keyPrefixPosition;
                set => throw new NotSupportedException();
            }

            public override void Flush()
                => throw new NotSupportedException();

            public override int Read(byte[] buffer, int offset, int count)
            {
                ValidateReadArguments(buffer, offset, count);

                if (count == 0)
                {
                    return 0;
                }

                var written = WriteKeyPrefix(buffer, offset, count);
                if (written == count)
                {
                    return written;
                }

                var bytesRead = innerStream.Read(buffer, offset + written, count - written);
                Obfuscate(buffer, offset + written, bytesRead);
                return written + bytesRead;
            }

            public override async Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken)
            {
                ValidateReadArguments(buffer, offset, count);

                if (count == 0)
                {
                    return 0;
                }

                var written = WriteKeyPrefix(buffer, offset, count);
                if (written == count)
                {
                    return written;
                }

                var bytesRead = await innerStream.ReadAsync(buffer, offset + written, count - written, cancellationToken).ConfigureAwait(false);
                Obfuscate(buffer, offset + written, bytesRead);
                return written + bytesRead;
            }

#if NETSTANDARD2_1_OR_GREATER || NET8_0_OR_GREATER
            public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
            {
                if (buffer.Length == 0)
                {
                    return 0;
                }

                var temp = new byte[buffer.Length];
                var bytesRead = await ReadAsync(temp, 0, temp.Length, cancellationToken).ConfigureAwait(false);
                new ReadOnlyMemory<byte>(temp, 0, bytesRead).CopyTo(buffer);
                return bytesRead;
            }
#endif

            public override long Seek(long offset, SeekOrigin origin)
                => throw new NotSupportedException();

            public override void SetLength(long value)
                => throw new NotSupportedException();

            public override void Write(byte[] buffer, int offset, int count)
                => throw new NotSupportedException();

            private static uint RotateLeft(uint value, int count)
                => (value << count) | (value >> (32 - count));

            private static void ValidateReadArguments(byte[] buffer, int offset, int count)
            {
                if (buffer == null)
                {
                    throw new ArgumentNullException(nameof(buffer));
                }

                if (offset < 0 || count < 0 || offset + count > buffer.Length)
                {
                    throw new ArgumentOutOfRangeException(nameof(count));
                }
            }

            private int WriteKeyPrefix(byte[] buffer, int offset, int count)
            {
                var written = 0;

                while (keyPrefixPosition < keyBytes.Length && written < count)
                {
                    buffer[offset + written] = keyBytes[keyPrefixPosition];
                    keyPrefixPosition++;
                    written++;
                }

                return written;
            }

            private void Obfuscate(byte[] buffer, int offset, int count)
            {
                for (var index = 0; index < count; index++)
                {
                    if (payloadPosition % sizeof(uint) == 0)
                    {
                        key = RotateLeft(key, 1);
                        keyBytes[0] = (byte)key;
                        keyBytes[1] = (byte)(key >> 8);
                        keyBytes[2] = (byte)(key >> 16);
                        keyBytes[3] = (byte)(key >> 24);
                    }

                    buffer[offset + index] ^= keyBytes[(int)(payloadPosition % sizeof(uint))];
                    payloadPosition++;
                }
            }
        }
    }
}
