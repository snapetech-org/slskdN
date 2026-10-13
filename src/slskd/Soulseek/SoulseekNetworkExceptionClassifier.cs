// <copyright file="SoulseekNetworkExceptionClassifier.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.SoulseekExceptions;

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Sockets;

public static class SoulseekNetworkExceptionClassifier
{
    public static bool IsExpected(Exception exception)
    {
        var flattened = FlattenExceptions(exception).ToList();

        return flattened.Count > 0 && flattened.All(IsExpectedCore);
    }

    private static IEnumerable<Exception> FlattenExceptions(Exception exception)
    {
        if (exception is AggregateException aggregateException)
        {
            foreach (var innerException in aggregateException.Flatten().InnerExceptions)
            {
                foreach (var flattenedInnerException in FlattenExceptions(innerException))
                {
                    yield return flattenedInnerException;
                }
            }

            yield break;
        }

        yield return exception;

        if (exception.InnerException is not null)
        {
            foreach (var innerException in FlattenExceptions(exception.InnerException))
            {
                yield return innerException;
            }
        }
    }

    private static bool IsExpectedCore(Exception exception)
    {
        var typeName = exception.GetType().FullName ?? exception.GetType().Name;
        var details = exception.ToString();
        var isSoulseekMessageConnectionClosed =
            exception is InvalidOperationException &&
            details.Contains("The underlying Tcp connection is closed", StringComparison.Ordinal) &&
            details.Contains("Soulseek.Network.MessageConnection.ReadContinuouslyAsync", StringComparison.Ordinal);
        var isSoulseekTimerResetReadRace =
            exception is NullReferenceException &&
            details.Contains("Soulseek.Extensions.Reset(", StringComparison.Ordinal) &&
            details.Contains("Soulseek.Network.MessageConnection.ReadContinuouslyAsync", StringComparison.Ordinal);
        var isSoulseekTimerResetWriteRace =
            exception is NullReferenceException &&
            details.Contains("Soulseek.Extensions.Reset(", StringComparison.Ordinal) &&
            details.Contains("Soulseek.Network.Tcp.Connection.WriteInternalAsync", StringComparison.Ordinal);
        var isSoulseekTcpDoubleDisconnectRace =
            exception is InvalidOperationException &&
            details.Contains("An attempt was made to transition a task to a final state", StringComparison.Ordinal) &&
            details.Contains("Soulseek.Network.Tcp.Connection.Disconnect", StringComparison.Ordinal);
        var isSoulseekDisconnectingReadLoopRace =
            exception is InvalidOperationException &&
            details.Contains("Invalid attempt to send to a disconnected or transitioning connection", StringComparison.Ordinal) &&
            details.Contains("Soulseek.Network.MessageConnection.ReadContinuouslyAsync", StringComparison.Ordinal);
        var isSoulseekListenerSocketDisposed =
            exception is ObjectDisposedException listenerDisposedException &&
            string.Equals(listenerDisposedException.ObjectName, "System.Net.Sockets.Socket", StringComparison.Ordinal) &&
            details.Contains("Soulseek.Network.Tcp.Listener.ListenContinuouslyAsync", StringComparison.Ordinal);
        var isExpectedSocketFailure =
            exception is SocketException socketException &&
            socketException.SocketErrorCode is SocketError.ConnectionRefused or
                SocketError.ConnectionReset or
                SocketError.HostUnreachable or
                SocketError.NetworkUnreachable or
                SocketError.TimedOut;

        var isNetworkFailure =
            exception is TimeoutException ||
            exception is OperationCanceledException ||
            exception is IOException ||
            exception is UnauthorizedAccessException ||
            (exception is ObjectDisposedException objectDisposedException && string.Equals(objectDisposedException.ObjectName, "Connection", StringComparison.Ordinal)) ||
            (exception is ObjectDisposedException messageConnectionDisposedException && string.Equals(messageConnectionDisposedException.ObjectName, "MessageConnection", StringComparison.Ordinal)) ||
            exception is System.Net.Sockets.SocketException ||
            isSoulseekMessageConnectionClosed ||
            isSoulseekTimerResetReadRace ||
            isSoulseekTimerResetWriteRace ||
            isSoulseekTcpDoubleDisconnectRace ||
            isSoulseekDisconnectingReadLoopRace ||
            isSoulseekListenerSocketDisposed ||
            typeName.Contains("Soulseek.SoulseekClientException", StringComparison.Ordinal) ||
            typeName.Contains("Soulseek.MessageReadException", StringComparison.Ordinal) ||
            typeName.Contains("Soulseek.ConnectionReadException", StringComparison.Ordinal) ||
            typeName.Contains("Soulseek.ConnectionException", StringComparison.Ordinal) ||
            typeName.Contains("Soulseek.TransferException", StringComparison.Ordinal) ||
            typeName.Contains("Soulseek.TransferRejectedException", StringComparison.Ordinal) ||
            typeName.Contains("Soulseek.TransferReportedFailedException", StringComparison.Ordinal);

        if (!isNetworkFailure)
        {
            return false;
        }

        // UnauthorizedAccessException from file creation during transfers
        var isUnauthorizedAccessFileFailure =
            exception is UnauthorizedAccessException &&
            (details.Contains("Access to the path", StringComparison.Ordinal) ||
             details.Contains("Failed to create file", StringComparison.Ordinal));

        if (isUnauthorizedAccessFileFailure)
        {
            return true;
        }

        // IOException wrapping a file creation failure (e.g. UnauthorizedAccessException)
        var isFileCreationIoFailure =
            exception is IOException &&
            !(exception is UnauthorizedAccessException) &&
            (details.Contains("Failed to create file", StringComparison.Ordinal) ||
             details.Contains("Access to the path", StringComparison.Ordinal));

        if (isFileCreationIoFailure)
        {
            return true;
        }

        return isExpectedSocketFailure ||
            details.Contains("Soulseek.Network.PeerConnectionManager", StringComparison.Ordinal) ||
            details.Contains("Soulseek.Network.DistributedConnectionManager", StringComparison.Ordinal) ||
            details.Contains("Soulseek.Network.Tcp.Connection", StringComparison.Ordinal) ||
            details.Contains("Soulseek.Network.Tcp.Listener", StringComparison.Ordinal) ||
            details.Contains("Failed to connect", StringComparison.Ordinal) ||
            details.Contains("Connection refused", StringComparison.Ordinal) ||
            details.Contains("Connection reset by peer", StringComparison.Ordinal) ||
            details.Contains("Remote connection closed", StringComparison.Ordinal) ||
            details.Contains("The connection was closed unexpectedly", StringComparison.Ordinal) ||
            details.Contains("The underlying Tcp connection is closed", StringComparison.Ordinal) ||
            details.Contains("Download reported as failed by remote client", StringComparison.Ordinal) ||
            details.Contains("Enqueue failed due to internal error", StringComparison.Ordinal) ||
            details.Contains("File not shared", StringComparison.Ordinal) ||
            details.Contains("File read error", StringComparison.Ordinal) ||
            details.Contains("Overwhelmed with requests", StringComparison.Ordinal) ||
            details.Contains("Too many megabytes", StringComparison.Ordinal) ||
            details.Contains("Too many files", StringComparison.Ordinal) ||
            details.Contains("Transfer failed: Transfer complete", StringComparison.Ordinal) ||
            details.Contains("Transfer failed: Transfer error", StringComparison.Ordinal) ||
            details.Contains("No route to host", StringComparison.Ordinal) ||
            details.Contains("Operation timed out", StringComparison.Ordinal) ||
            details.Contains("Connection timed out", StringComparison.Ordinal) ||
            details.Contains("The wait timed out", StringComparison.Ordinal) ||
            details.Contains("Inactivity timeout", StringComparison.Ordinal) ||
            details.Contains("Failed to read", StringComparison.Ordinal) ||
            details.Contains("Unable to read data from the transport connection", StringComparison.Ordinal) ||
            details.Contains("Operation canceled", StringComparison.Ordinal) ||
            details.Contains("Operation cancelled", StringComparison.Ordinal) ||
            details.Contains("Unknown PierceFirewall attempt", StringComparison.Ordinal) ||
            details.Contains("Cannot access a disposed object.", StringComparison.Ordinal);
    }
}
