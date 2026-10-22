// <copyright file="FedTcpListener.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.SoulseekRuntime;

using System.Net.Sockets;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using Soulseek.Network.Tcp;

/// <summary>
/// An <see cref="ITcpListener"/> that never binds a socket of its own. A
/// <see cref="slskd.DhtRendezvous.SharedMeshTcpListener"/> feeds it already-accepted TCP
/// connections that it has classified as Soulseek peer traffic, letting the vendored Soulseek
/// client's listener share one public TCP port with other application-level protocols instead of
/// owning an exclusive socket.
/// </summary>
/// <remarks>
/// This instance is long-lived (a singleton) and outlives any individual vendored
/// <c>Soulseek.Network.Tcp.Listener</c> that wraps it -- the vendored client constructs a new
/// <c>Listener</c> around the same <see cref="FedTcpListener"/> instance on every connect and
/// reconfigure, so <see cref="Start"/> and <see cref="Stop"/> (called once per that lifecycle) are
/// no-ops here: completing the underlying channel on every reconnect would break subsequent feeds.
/// Only <see cref="Complete"/>, called by the owning <see cref="slskd.DhtRendezvous.SharedMeshTcpListener"/>
/// on final shutdown, actually closes it.
/// </remarks>
internal sealed class FedTcpListener : ICancellableTcpListener
{
    private readonly Channel<TcpClient> _channel = Channel.CreateUnbounded<TcpClient>(new UnboundedChannelOptions
    {
        SingleReader = true,
        SingleWriter = false,
    });

    /// <summary>
    /// Hands an already-accepted, already-classified connection to the fed listener's accept queue.
    /// </summary>
    public void Feed(TcpClient client) => _channel.Writer.TryWrite(client);

    /// <summary>
    /// Permanently closes the feed. Only the owning demux calls this, on shutdown.
    /// </summary>
    public void Complete() => _channel.Writer.TryComplete();

    public Task<TcpClient> AcceptTcpClientAsync() => _channel.Reader.ReadAsync().AsTask();

    public Task<TcpClient> AcceptTcpClientAsync(CancellationToken cancellationToken)
        => _channel.Reader.ReadAsync(cancellationToken).AsTask();

    public bool Pending() => _channel.Reader.TryPeek(out _);

    public void Start()
    {
        // No-op: the real socket is owned externally by SharedMeshTcpListener.
    }

    public void Stop()
    {
        // No-op: see remarks on the type. The vendored Listener wrapping this instance calls
        // Stop() on every reconnect/reconfigure; completing the channel here would strand feeds
        // arriving before the next Listener is constructed around this same instance.
    }
}
