// <copyright file="ObfuscatedTransferConnection.cs" company="slskdN Team">
//     Copyright (c) slskdN Team.
//
//     This file is part of slskNet.Runtime, a modified version of Soulseek.NET.
//     Modified: Added Soulseek type-1 rotated obfuscation for transfer streams.
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

namespace Soulseek.Network.Tcp
{
    using System;
    using System.Buffers.Binary;
    using System.Collections.Generic;
    using System.IO;
    using System.Net;
    using System.Threading;
    using System.Threading.Tasks;

    /// <summary>
    ///     Provides a raw transfer connection whose bytes are carried in Soulseek type-1 obfuscated frames.
    /// </summary>
    internal sealed class ObfuscatedTransferConnection : IConnection
    {
        private const int FrameLengthBytes = 4;

        private readonly Connection innerConnection;
        private readonly Queue<byte> decodedBuffer = new Queue<byte>();

        public ObfuscatedTransferConnection(IPEndPoint ipEndPoint, ConnectionOptions options = null, ITcpClient tcpClient = null)
        {
            innerConnection = new Connection(ipEndPoint, options ?? new ConnectionOptions(), tcpClient, obfuscated: true);
        }

        public event EventHandler Connected
        {
            add => innerConnection.Connected += value;
            remove => innerConnection.Connected -= value;
        }

        public event EventHandler<ConnectionDataEventArgs> DataRead
        {
            add => innerConnection.DataRead += value;
            remove => innerConnection.DataRead -= value;
        }

        public event EventHandler<ConnectionDataEventArgs> DataWritten
        {
            add => innerConnection.DataWritten += value;
            remove => innerConnection.DataWritten -= value;
        }

        public event EventHandler<ConnectionDisconnectedEventArgs> Disconnected
        {
            add => innerConnection.Disconnected += value;
            remove => innerConnection.Disconnected -= value;
        }

        public event EventHandler<ConnectionStateChangedEventArgs> StateChanged
        {
            add => innerConnection.StateChanged += value;
            remove => innerConnection.StateChanged -= value;
        }

        public Guid Id => innerConnection.Id;

        public TimeSpan InactiveTime => innerConnection.InactiveTime;

        public IPEndPoint IPEndPoint => innerConnection.IPEndPoint;

        public ConnectionKey Key => innerConnection.Key;

        public ConnectionOptions Options => innerConnection.Options;

        public bool Obfuscated => true;

        public ConnectionState State => innerConnection.State;

        public ConnectionTypes Type
        {
            get => innerConnection.Type;
            set => innerConnection.Type = value;
        }

        public int WriteQueueDepth => innerConnection.WriteQueueDepth;

        public void MarkObfuscated()
        {
        }

        public Task ConnectAsync(CancellationToken cancellationToken = default)
            => innerConnection.ConnectAsync(cancellationToken);

        public void Disconnect(string message = null, Exception exception = null)
            => innerConnection.Disconnect(message, exception);

        public void Dispose()
            => innerConnection.Dispose();

        public ITcpClient HandoffTcpClient()
            => innerConnection.HandoffTcpClient();

        public async Task<byte[]> ReadAsync(long length, CancellationToken cancellationToken = default)
        {
            if (length < 0)
            {
                throw new ArgumentException("The requested length must be greater than or equal to zero", nameof(length));
            }

            if (length > int.MaxValue)
            {
                throw new ArgumentOutOfRangeException(nameof(length), $"The requested length must be less than or equal to {int.MaxValue}");
            }

            if (length > Connection.MaximumBufferedReadLength)
            {
                throw new ArgumentOutOfRangeException(nameof(length), $"Buffered reads are limited to {Connection.MaximumBufferedReadLength} bytes; use the stream overload for larger transfers");
            }

            var output = new byte[checked((int)length)];
            var offset = 0;

            while (offset < output.Length)
            {
                if (decodedBuffer.Count == 0)
                {
                    await ReadNextFrameAsync(cancellationToken).ConfigureAwait(false);
                }

                while (decodedBuffer.Count > 0 && offset < output.Length)
                {
                    output[offset++] = decodedBuffer.Dequeue();
                }
            }

            return output;
        }

        public async Task ReadAsync(long length, Stream outputStream, Func<int, CancellationToken, Task<int>> governor, Action<int, int, int> reporter = null, CancellationToken cancellationToken = default)
        {
            if (length < 0)
            {
                throw new ArgumentException("The requested length must be greater than or equal to zero", nameof(length));
            }

            if (outputStream == null)
            {
                throw new ArgumentNullException(nameof(outputStream), "The specified output stream is null");
            }

            if (!outputStream.CanWrite)
            {
                throw new InvalidOperationException("The specified output stream is not writeable");
            }

            governor ??= (s, t) => Task.FromResult(int.MaxValue);
            var token = cancellationToken;
            long totalBytesRead = 0;

            while (totalBytesRead < length)
            {
                if (decodedBuffer.Count == 0)
                {
                    await ReadNextFrameAsync(token).ConfigureAwait(false);
                }

                var bytesRemaining = length - totalBytesRead;
                var bytesAvailable = Math.Min(decodedBuffer.Count, (int)Math.Min(bytesRemaining, int.MaxValue));
                var bytesGranted = Math.Min(bytesAvailable, await governor(bytesAvailable, token).ConfigureAwait(false));

                if (bytesGranted <= 0)
                {
                    throw new ConnectionReadException($"Read governor granted {bytesGranted} bytes; obfuscated transfer reads require forward progress");
                }

                var buffer = new byte[bytesGranted];

                for (var i = 0; i < bytesGranted; i++)
                {
                    buffer[i] = decodedBuffer.Dequeue();
                }

                await outputStream.WriteAsync(buffer, 0, buffer.Length, token).ConfigureAwait(false);
                totalBytesRead += buffer.Length;
                reporter?.Invoke(bytesAvailable, bytesGranted, buffer.Length);
            }

            await outputStream.FlushAsync(token).ConfigureAwait(false);
        }

        public Task<string> WaitForDisconnect(CancellationToken cancellationToken = default)
            => innerConnection.WaitForDisconnect(cancellationToken);

        public Task WriteAsync(byte[] bytes, CancellationToken cancellationToken = default)
        {
            if (bytes == null || bytes.Length == 0)
            {
                throw new ArgumentException("Invalid attempt to send empty data", nameof(bytes));
            }

            return innerConnection.WriteAsync(EncodeFrame(bytes), cancellationToken);
        }

        public async Task WriteAsync(long length, Stream inputStream, Func<int, CancellationToken, Task<int>> governor = null, Action<int, int, int> reporter = null, CancellationToken cancellationToken = default)
        {
            if (length <= 0)
            {
                throw new ArgumentException("The requested length must be greater than or equal to zero", nameof(length));
            }

            if (inputStream == null)
            {
                throw new ArgumentNullException(nameof(inputStream), "The specified output stream is null");
            }

            if (!inputStream.CanRead)
            {
                throw new InvalidOperationException("The specified input stream is not readable");
            }

            governor ??= (s, t) => Task.FromResult(int.MaxValue);
            var token = cancellationToken;
            var maxPayloadLength = Math.Min(Options.WriteBufferSize, RotatedObfuscation.MaxMessageLength - FrameLengthBytes);
            var buffer = new byte[maxPayloadLength];
            long totalBytesWritten = 0;

            while (totalBytesWritten < length)
            {
                var bytesRemaining = length - totalBytesWritten;
                var bytesToRead = Math.Min(buffer.Length, (int)Math.Min(bytesRemaining, int.MaxValue));
                var bytesGranted = Math.Min(bytesToRead, await governor(bytesToRead, token).ConfigureAwait(false));

                if (bytesGranted <= 0)
                {
                    throw new ConnectionWriteException($"Write governor granted {bytesGranted} bytes; obfuscated transfer writes require forward progress");
                }

                var bytesRead = await inputStream.ReadAsync(buffer, 0, bytesGranted, token).ConfigureAwait(false);

                if (bytesRead == 0)
                {
                    throw new ConnectionWriteException("Input stream closed before the requested transfer length was written");
                }

                var payload = new byte[bytesRead];
                Buffer.BlockCopy(buffer, 0, payload, 0, bytesRead);
                await innerConnection.WriteAsync(EncodeFrame(payload), token).ConfigureAwait(false);

                totalBytesWritten += bytesRead;
                reporter?.Invoke(bytesToRead, bytesGranted, bytesRead);
            }
        }

        private static byte[] EncodeFrame(byte[] payload)
        {
            if (payload.Length > RotatedObfuscation.MaxMessageLength - FrameLengthBytes)
            {
                throw new ConnectionWriteException($"Obfuscated transfer frame payload exceeds {RotatedObfuscation.MaxMessageLength - FrameLengthBytes} bytes");
            }

            var frame = new byte[FrameLengthBytes + payload.Length];
            BinaryPrimitives.WriteInt32LittleEndian(frame, payload.Length);
            Buffer.BlockCopy(payload, 0, frame, FrameLengthBytes, payload.Length);
            return RotatedObfuscation.Encode(frame);
        }

        private async Task ReadNextFrameAsync(CancellationToken cancellationToken)
        {
            var firstBlock = await innerConnection.ReadAsync(8, cancellationToken).ConfigureAwait(false);
            var decodedFirstBlock = RotatedObfuscation.Decode(firstBlock);
            var length = BinaryPrimitives.ReadInt32LittleEndian(decodedFirstBlock);

            if (length <= 0 || length > RotatedObfuscation.MaxMessageLength - FrameLengthBytes)
            {
                throw new ConnectionReadException($"Invalid obfuscated transfer frame length: {length}");
            }

            var encoded = new byte[8 + length];
            Buffer.BlockCopy(firstBlock, 0, encoded, 0, firstBlock.Length);

            if (length > 0)
            {
                var remaining = await innerConnection.ReadAsync(length, cancellationToken).ConfigureAwait(false);
                Buffer.BlockCopy(remaining, 0, encoded, 8, remaining.Length);
            }

            var decoded = RotatedObfuscation.Decode(encoded);
            for (var i = FrameLengthBytes; i < decoded.Length; i++)
            {
                decodedBuffer.Enqueue(decoded[i]);
            }
        }
    }
}
