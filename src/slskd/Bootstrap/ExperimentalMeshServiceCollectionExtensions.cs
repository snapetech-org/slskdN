// <copyright file="ExperimentalMeshServiceCollectionExtensions.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Bootstrap;

using System;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Serilog;
using slskd.Common.Security;
using slskd.Configuration;
using slskd.DhtRendezvous;
using slskd.Mesh;
using slskd.Mesh.Gossip;
using slskd.Mesh.Governance;
using slskd.Mesh.Realm;
using slskd.Mesh.Realm.Bridge;
using slskd.SocialFederation;
using slskd.Streaming;

public static class ExperimentalMeshServiceCollectionExtensions
{
    public static IServiceCollection AddSlskdExperimentalMeshServices(
        this IServiceCollection services,
        IConfiguration configuration,
        slskd.Options optionsAtStartup)
    {
        // Typed options (Phase 11) - bind under slskd: namespace to match YAML provider
        var slskdSection = configuration.GetSection(Program.AppName);
        var meshOptionsAtStartup = slskdSection.GetSection("Mesh").Get<Mesh.MeshOptions>() ?? new Mesh.MeshOptions();
        services.AddOptions<Core.SwarmOptions>().Bind(slskdSection.GetSection("Swarm"));
        services.AddOptions<Core.SecurityOptions>().Bind(slskdSection.GetSection("Security"));
        services.AddOptions<Common.Security.AdversarialOptions>().Bind(slskdSection.GetSection("Security:Adversarial"));
        services.AddOptions<PodCore.PodMessageSignerOptions>().Bind(slskdSection.GetSection("PodCore:Security"));
        services.AddOptions<PodCore.PodJoinOptions>().Bind(slskdSection.GetSection("PodCore:Join"));

        // Transport policy manager for per-peer/per-pod transport policies
        services.AddSingleton<Mesh.Transport.TransportPolicyManager>();

        // Anonymity transport selector with policy-aware selection
        services.AddSingleton<Common.Security.IAnonymityTransportSelector>(sp =>
        {
            var options = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<Common.Security.AdversarialOptions>>();
            var policyManager = sp.GetRequiredService<Mesh.Transport.TransportPolicyManager>();
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Common.Security.AnonymityTransportSelector>>();
            var loggerFactory = sp.GetRequiredService<ILoggerFactory>();
            var overlayDataPlane = sp.GetService<Mesh.Overlay.IOverlayDataPlane>();
            return new Common.Security.AnonymityTransportSelector(options.Value, policyManager, logger, loggerFactory, overlayDataPlane);
        });

        // Privacy layer for traffic analysis protection
        services.AddSingleton<Mesh.Privacy.IPrivacyLayer>(sp =>
        {
            var options = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<Common.Security.AdversarialOptions>>();
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.Privacy.PrivacyLayer>>();
            var loggerFactory = sp.GetRequiredService<ILoggerFactory>();
            return new Mesh.Privacy.PrivacyLayer(logger, loggerFactory, options.Value.Privacy);
        });

        services.AddOptions<Core.BrainzOptions>().Bind(configuration.GetSection($"{Program.AppName}:Brainz"));
        services.AddOptions<Mesh.MeshOptions>().Bind(configuration.GetSection($"{Program.AppName}:Mesh")); // transport prefs
        services.AddOptions<Mesh.MeshSyncSecurityOptions>().Bind(configuration.GetSection($"{Program.AppName}:Mesh:SyncSecurity"));
        services.AddOptions<Mesh.MeshTransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Mesh:Transport"));
        services.AddOptions<Mesh.TorTransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Mesh:Transport:Tor"));
        services.AddOptions<Mesh.I2PTransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Mesh:Transport:I2P"));
        services.AddOptions<Common.Security.WebSocketTransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Security:Adversarial:Transport:WebSocket"));
        services.AddOptions<Common.Security.HttpTunnelTransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Security:Adversarial:Transport:HttpTunnel"));
        services.AddOptions<Common.Security.Obfs4TransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Security:Adversarial:Transport:Obfs4"));
        services.AddOptions<Common.Security.MeekTransportOptions>().Bind(configuration.GetSection($"{Program.AppName}:Security:Adversarial:Transport:Meek"));

        // Register options as singletons for direct injection (temporary workaround)
        services.AddSingleton(sp => sp.GetRequiredService<IOptions<Mesh.TorTransportOptions>>().Value);
        services.AddSingleton(sp => sp.GetRequiredService<IOptions<Mesh.I2PTransportOptions>>().Value);
        services.AddSingleton(sp => sp.GetRequiredService<IOptions<Common.Security.WebSocketTransportOptions>>().Value);
        services.AddSingleton(sp => sp.GetRequiredService<IOptions<Common.Security.HttpTunnelTransportOptions>>().Value);
        services.AddSingleton(sp => sp.GetRequiredService<IOptions<Common.Security.Obfs4TransportOptions>>().Value);
        services.AddSingleton(sp => sp.GetRequiredService<IOptions<Common.Security.MeekTransportOptions>>().Value);
        services.AddOptions<MediaCore.MediaCoreOptions>().Bind(configuration.GetSection($"{Program.AppName}:MediaCore"));
        services.AddOptions<Mesh.Overlay.OverlayOptions>().Bind(configuration.GetSection($"{Program.AppName}:Overlay"));
        services.AddOptions<Mesh.Overlay.DataOverlayOptions>().Bind(configuration.GetSection($"{Program.AppName}:OverlayData"));
        services.PostConfigure<Mesh.MeshOptions>(options =>
        {
            options.DataDirectory = AppPathResolver.ResolveAppRelativePath(options.DataDirectory, "data", Program.AppDirectory, Program.DefaultAppDirectory);
        });
        services.PostConfigure<Mesh.Overlay.OverlayOptions>(options =>
        {
            options.KeyPath = AppPathResolver.ResolveAppRelativePath(options.KeyPath, "mesh-overlay.key", Program.AppDirectory, Program.DefaultAppDirectory);
        });
        services.AddOptions<Mesh.ServiceFabric.MeshGatewayOptions>()
            .Bind(configuration.GetSection($"{Program.AppName}:MeshGateway"))
            .Validate(options => options.Validate().IsValid, "MeshGateway configuration is invalid.")
            .ValidateOnStart();

        // Realm services (T-REALM-01, T-REALM-02, T-REALM-04)
        Log.Debug("[DI] Configuring Realm services...");
        services.Configure<Mesh.Realm.RealmConfig>(configuration.GetSection($"{Program.AppName}:Realm"));
        services.Configure<Mesh.Realm.MultiRealmConfig>(configuration.GetSection($"{Program.AppName}:MultiRealm"));
        services.AddRealmServices(optionsAtStartup.Feature.Mesh);

        // Social federation services (required by bridges)
        Log.Debug("[DI] Configuring Social Federation services...");
        services.AddSocialFederation(configuration);
        services.AddBridgeServices();

        // Governance and Gossip services (T-REALM-03)
        Log.Debug("[DI] Configuring Governance and Gossip services...");
        services.AddGovernanceServices();
        services.AddGossipServices();

        // MeshCore (Phase 8 implementation)
        Log.Debug("[DI] Configuring MeshCore services...");
        services.Configure<Mesh.MeshOptions>(configuration.GetSection($"{Program.AppName}:Mesh"));
        services.AddSingleton<Mesh.INatDetector, Mesh.StunNatDetector>();
        services.AddSingleton<Mesh.Nat.IUdpHolePuncher, Mesh.Nat.UdpHolePuncher>();
        services.AddSingleton<Mesh.Nat.IRelayClient, Mesh.Nat.RelayClient>();
        services.AddSingleton<Mesh.Nat.INatTraversalService, Mesh.Nat.NatTraversalService>();

        // DHT: use in-memory Kademlia-style implementation for now
        services.AddSingleton<VirtualSoulfind.ShadowIndex.IDhtClient>(sp =>
        {
            Log.Debug("[DI] Constructing InMemoryDhtClient...");
            Log.Debug("[DI] Resolving ILogger<InMemoryDhtClient>...");
            var logger = sp.GetRequiredService<ILogger<Mesh.Dht.InMemoryDhtClient>>();
            Log.Debug("[DI] Resolving IOptions<MeshOptions> for InMemoryDhtClient...");
            var options = sp.GetRequiredService<IOptions<Mesh.MeshOptions>>();
            Log.Debug("[DI] Resolving MeshStatsCollector for InMemoryDhtClient (optional)...");
            var statsCollector = sp.GetRequiredService<Mesh.MeshStatsCollector>();
            Log.Debug("[DI] All InMemoryDhtClient dependencies resolved, creating instance...");
            var service = new Mesh.Dht.InMemoryDhtClient(logger, options, statsCollector);
            Log.Debug("[DI] InMemoryDhtClient constructed");
            return service;
        });
        services.AddSingleton<Mesh.Dht.IMeshDhtClient>(sp =>
        {
            Log.Debug("[DI] Constructing MeshDhtClient...");
            Log.Debug("[DI] Resolving ILogger<MeshDhtClient>...");
            var logger = sp.GetRequiredService<ILogger<Mesh.Dht.MeshDhtClient>>();
            Log.Debug("[DI] Resolving IDhtClient for MeshDhtClient...");
            var dhtClient = sp.GetRequiredService<VirtualSoulfind.ShadowIndex.IDhtClient>();
            Log.Debug("[DI] All MeshDhtClient dependencies resolved, creating instance (DhtService will be resolved lazily to break circular dependency)...");
            var service = new Mesh.Dht.MeshDhtClient(logger, dhtClient, sp, sp.GetService<IOptions<Mesh.MeshOptions>>());
            Log.Debug("[DI] MeshDhtClient constructed");
            return service;
        });
        services.AddSingleton<Mesh.Dht.IPeerDescriptorPublisher>(sp =>
        {
            Log.Debug("[DI] Constructing PeerDescriptorPublisher...");
            var service = new Mesh.Dht.PeerDescriptorPublisher(
                sp.GetRequiredService<ILogger<Mesh.Dht.PeerDescriptorPublisher>>(),
                sp.GetRequiredService<Mesh.Dht.IMeshDhtClient>(),
                sp.GetRequiredService<IOptions<Mesh.MeshOptions>>(),
                sp.GetRequiredService<Mesh.INatDetector>(),
                sp.GetRequiredService<IOptions<Mesh.MeshTransportOptions>>(),
                sp.GetRequiredService<IOptions<Mesh.Overlay.OverlayOptions>>(),
                sp.GetRequiredService<Mesh.Transport.DescriptorSigningService>(),
                sp.GetService<Mesh.Overlay.IKeyStore>());
            Log.Debug("[DI] PeerDescriptorPublisher constructed");
            return service;
        });
        services.AddSingleton<Mesh.IMeshDirectory, Mesh.Dht.ContentDirectory>();
        services.AddSingleton<Mesh.IMeshAdvanced>(sp => new Mesh.MeshAdvanced(
            sp.GetRequiredService<ILogger<Mesh.MeshAdvanced>>(),
            sp.GetRequiredService<Mesh.IMeshDirectory>(),
            sp.GetRequiredService<Mesh.MeshStatsCollector>(),
            sp.GetRequiredService<Mesh.Dht.IMeshDhtClient>(),
            sp.GetRequiredService<Mesh.Nat.INatTraversalService>()));
        services.AddSingleton<Mesh.MeshStatsCollector>(sp =>
        {
            Log.Debug("[DI] Constructing MeshStatsCollector...");
            var service = new Mesh.MeshStatsCollector(
                sp.GetRequiredService<ILogger<Mesh.MeshStatsCollector>>(),
                sp);
            Log.Debug("[DI] MeshStatsCollector constructed");
            return service;
        });
        services.AddSingleton<Mesh.IMeshStatsCollector>(sp => sp.GetRequiredService<Mesh.MeshStatsCollector>());
        if (optionsAtStartup.Feature.Mesh && meshOptionsAtStartup.EnableDht)
        {
            services.AddHostedService(p =>
            {
                Log.Debug("[DI] Resolving MeshBootstrapService hosted service...");
                var service = ActivatorUtilities.CreateInstance<Mesh.Bootstrap.MeshBootstrapService>(p);
                Log.Debug("[DI] MeshBootstrapService hosted service resolved");
                return service;
            });
            services.AddHostedService(p =>
            {
                Log.Debug("[DI] Resolving PeerDescriptorRefreshService hosted service...");
                var service = ActivatorUtilities.CreateInstance<Mesh.Dht.PeerDescriptorRefreshService>(p);
                Log.Debug("[DI] PeerDescriptorRefreshService hosted service resolved");
                return service;
            });
        }

        services.AddSingleton<Mesh.Dht.IContentPeerPublisher>(sp =>
        {
            Log.Debug("[DI] Constructing ContentPeerPublisher...");
            Log.Debug("[DI] Resolving ILogger<ContentPeerPublisher>...");
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.Dht.ContentPeerPublisher>>();
            Log.Debug("[DI] Resolving IMeshDhtClient for ContentPeerPublisher...");
            var dht = sp.GetRequiredService<Mesh.Dht.IMeshDhtClient>();
            Log.Debug("[DI] Resolving IOptions<MeshOptions> for ContentPeerPublisher...");
            var options = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<Mesh.MeshOptions>>();
            Log.Debug("[DI] All ContentPeerPublisher dependencies resolved, creating instance...");
            var service = new Mesh.Dht.ContentPeerPublisher(logger, dht, options);
            Log.Debug("[DI] ContentPeerPublisher constructed");
            return service;
        });
        services.AddSingleton<Mesh.Dht.IContentPeerHintService>(sp =>
        {
            Log.Debug("[DI] Constructing ContentPeerHintService...");
            var service = new Mesh.Dht.ContentPeerHintService(
                sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.Dht.ContentPeerHintService>>(),
                sp.GetRequiredService<Mesh.Dht.IContentPeerPublisher>());
            Log.Debug("[DI] ContentPeerHintService constructed");
            return service;
        });
        if (optionsAtStartup.Feature.Mesh &&
            optionsAtStartup.Feature.MeshPublishAvailability &&
            meshOptionsAtStartup.EnableDht)
        {
            services.AddHostedService(sp => (Mesh.Dht.ContentPeerHintService)sp.GetRequiredService<Mesh.Dht.IContentPeerHintService>());
        }

        services.AddSingleton<Mesh.Health.IMeshHealthService, Mesh.Health.MeshHealthService>();

        // Service Fabric (client + directory + validation)
        services.AddSingleton<Mesh.ServiceFabric.IMeshPeerPublicKeyResolver, Mesh.ServiceFabric.MeshPeerPublicKeyResolver>();
        services.AddSingleton<Mesh.ServiceFabric.IMeshServiceDescriptorValidator, Mesh.ServiceFabric.MeshServiceDescriptorValidator>();
        services.AddSingleton<Mesh.ServiceFabric.IMeshServiceDirectory, Mesh.ServiceFabric.DhtMeshServiceDirectory>();
        services.AddSingleton<Mesh.ServiceFabric.IMeshServiceClient, Mesh.ServiceFabric.MeshServiceClient>();
        services.AddOptions<Mesh.ServiceFabric.MeshServiceFabricOptions>().Bind(configuration.GetSection($"{Program.AppName}:MeshServiceFabric"));
        services.AddSingleton<Mesh.ServiceFabric.MeshServiceRouter>();

        // MeshContentFetcher requires IMeshServiceClient, so register after it
        services.AddSingleton<IMeshContentFetcher, MeshContentFetcher>();

        // Kademlia routing table using overlay key material for node ID
        services.AddSingleton<Mesh.Dht.KademliaRoutingTable>(sp =>
        {
            var keyStore = sp.GetRequiredService<Mesh.Overlay.IKeyStore>();
            var pubKey = keyStore.Current.PublicKey;

            // Bind the 160-bit Kademlia node ID to the same SHA-256 identity digest as PeerId.
            var selfId = System.Security.Cryptography.SHA256.HashData(pubKey).AsSpan(0, 20).ToArray();

            return new Mesh.Dht.KademliaRoutingTable(selfId);
        });

        // DHT services for Kademlia operations
        services.AddSingleton<Mesh.Dht.KademliaRpcClient>(sp =>
        {
            Log.Debug("[DI] Constructing KademliaRpcClient...");
            Log.Debug("[DI] Resolving ILogger<KademliaRpcClient>...");
            var logger = sp.GetRequiredService<ILogger<Mesh.Dht.KademliaRpcClient>>();
            Log.Debug("[DI] Resolving IMeshServiceClient for KademliaRpcClient...");
            var meshClient = sp.GetRequiredService<Mesh.ServiceFabric.IMeshServiceClient>();
            Log.Debug("[DI] Resolving KademliaRoutingTable for KademliaRpcClient...");
            var routingTable = sp.GetRequiredService<Mesh.Dht.KademliaRoutingTable>();
            Log.Debug("[DI] Resolving IDhtClient for KademliaRpcClient...");
            var dhtClient = sp.GetRequiredService<VirtualSoulfind.ShadowIndex.IDhtClient>();
            Log.Debug("[DI] All KademliaRpcClient dependencies resolved, creating instance...");
            var service = new Mesh.Dht.KademliaRpcClient(logger, meshClient, routingTable, dhtClient, sp.GetService<DhtRendezvous.MeshNeighborRegistry>());
            Log.Debug("[DI] KademliaRpcClient constructed");
            return service;
        });
        services.AddSingleton<Mesh.ServiceFabric.Services.DhtMeshService>();
        services.AddSingleton<Mesh.ServiceFabric.Services.PodsMeshService>();
        services.AddSingleton<Mesh.ServiceFabric.Services.VirtualSoulfindMeshService>();
        services.AddSingleton<Mesh.ServiceFabric.Services.MeshIntrospectionService>();
        services.AddSingleton<Mesh.Dht.DhtService>(sp =>
        {
            Log.Debug("[DI] Constructing DhtService...");
            Log.Debug("[DI] Resolving ILogger<DhtService>...");
            var logger = sp.GetRequiredService<ILogger<Mesh.Dht.DhtService>>();
            Log.Debug("[DI] Resolving KademliaRoutingTable for DhtService...");
            var routingTable = sp.GetRequiredService<Mesh.Dht.KademliaRoutingTable>();
            Log.Debug("[DI] Resolving IDhtClient for DhtService...");
            var dhtClient = sp.GetRequiredService<VirtualSoulfind.ShadowIndex.IDhtClient>();
            Log.Debug("[DI] Resolving KademliaRpcClient for DhtService...");
            var rpcClient = sp.GetRequiredService<Mesh.Dht.KademliaRpcClient>();
            Log.Debug("[DI] Resolving IMeshMessageSigner for DhtService...");
            var messageSigner = sp.GetRequiredService<Mesh.IMeshMessageSigner>();
            Log.Debug("[DI] All DhtService dependencies resolved, creating instance...");
            var service = new Mesh.Dht.DhtService(logger, routingTable, dhtClient, rpcClient, messageSigner);
            Log.Debug("[DI] DhtService constructed");
            return service;
        });

        // Hole punching services for NAT traversal
        services.AddSingleton<Mesh.ServiceFabric.Services.HolePunchMeshService>();
        services.AddSingleton<Mesh.ServiceFabric.Services.MeshContentMeshService>();
        services.AddSingleton<Mesh.ServiceFabric.Services.ListedRadioMeshService>();
        services.AddSingleton<Mesh.Nat.IHolePunchCoordinator, Mesh.Nat.HolePunchCoordinator>();

        // Private gateway service for VPN functionality (Phase 14)
        services.AddSingleton<DnsSecurityService>();
        services.AddSingleton<LocalPortForwarder>();
        services.AddSingleton<Mesh.ServiceFabric.Services.PrivateGatewayMeshService>();

        // Onion routing services (Phase 12)
        services.AddSingleton<Mesh.IMeshPeerManager, Mesh.MeshPeerManager>();
        services.AddSingleton<Mesh.IMeshTransportService>(sp =>
        {
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.MeshTransportService>>();
            var meshOptions = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<Mesh.MeshOptions>>();
            var anonymitySelector = sp.GetService<Common.Security.IAnonymityTransportSelector>();
            var adversarialOptions = sp.GetService<Microsoft.Extensions.Options.IOptions<Common.Security.AdversarialOptions>>();
            return new Mesh.MeshTransportService(logger, meshOptions, anonymitySelector, adversarialOptions);
        });

        services.AddSingleton<Mesh.MeshCircuitBuilder>(sp =>
        {
            var meshOptions = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<Mesh.MeshOptions>>();
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.MeshCircuitBuilder>>();
            var peerManager = sp.GetRequiredService<Mesh.IMeshPeerManager>();
            var transportSelector = sp.GetRequiredService<Common.Security.IAnonymityTransportSelector>();
            return new Mesh.MeshCircuitBuilder(meshOptions.Value, logger, peerManager, transportSelector);
        });
        services.AddSingleton<Mesh.IMeshCircuitBuilder>(sp => sp.GetRequiredService<Mesh.MeshCircuitBuilder>());
        if (optionsAtStartup.Feature.Mesh && meshOptionsAtStartup.EnableOverlay)
        {
            services.AddHostedService(p =>
            {
                Log.Debug("[DI] Constructing CircuitMaintenanceService hosted service...");
                var service = ActivatorUtilities.CreateInstance<Mesh.CircuitMaintenanceService>(p);
                Log.Debug("[DI] CircuitMaintenanceService constructed");
                return service;
            });
        }

        // Transport dialers (Tor/I2P integration Phase 2)
        var meshTransportoptionsAtStartup =
            configuration.GetSection($"{Program.AppName}:Mesh:Transport").Get<Mesh.MeshTransportOptions>() ??
            new Mesh.MeshTransportOptions();

        if (Mesh.QuicRuntime.IsAvailable())
        {
            services.AddSingleton<Mesh.Transport.ITransportDialer, Mesh.Transport.DirectQuicDialer>();
        }
        else if (meshTransportoptionsAtStartup.EnableDirect)
        {
            Log.Warning("[DI] Direct mesh transport is enabled but QUIC runtime support is unavailable; direct clearnet mesh circuits will be disabled until QUIC support is installed or a non-QUIC direct transport is configured");
        }

        services.AddSingleton<Mesh.Transport.ITransportDialer>(sp =>
        {
            var options = sp.GetRequiredService<IOptions<Mesh.TorTransportOptions>>();
            var logger = sp.GetRequiredService<ILogger<Mesh.Transport.TorSocksDialer>>();
            return new Mesh.Transport.TorSocksDialer(options.Value, logger);
        });
        services.AddSingleton<Mesh.Transport.ITransportDialer>(sp =>
        {
            var options = sp.GetRequiredService<IOptions<Mesh.I2PTransportOptions>>();
            var logger = sp.GetRequiredService<ILogger<Mesh.Transport.I2pSocksDialer>>();
            return new Mesh.Transport.I2pSocksDialer(options.Value, logger);
        });

        // Transport downgrade protection
        services.AddSingleton<Mesh.Transport.TransportDowngradeProtector>();

        // Certificate pin management for peer identity verification
        services.AddSingleton<Mesh.Transport.CertificatePinManager>();

        // Rate limiting for DoS protection
        services.AddSingleton<Mesh.Transport.RateLimiter>();
        services.AddSingleton<Mesh.Transport.ConnectionThrottler>();
        services.AddSingleton<Mesh.Dht.DhtRateLimiter>();

        // DNS leak prevention verification
        services.AddSingleton<Mesh.Transport.DnsLeakPreventionVerifier>();

        // Transport selector for endpoint negotiation
        services.AddSingleton<Mesh.Transport.TransportSelector>(sp =>
        {
            var options = sp.GetRequiredService<IOptions<Mesh.MeshTransportOptions>>();
            var dialers = sp.GetServices<Mesh.Transport.ITransportDialer>();
            var policyManager = sp.GetRequiredService<Mesh.Transport.TransportPolicyManager>();
            var downgradeProtector = sp.GetRequiredService<Mesh.Transport.TransportDowngradeProtector>();
            var connectionThrottler = sp.GetRequiredService<Mesh.Transport.ConnectionThrottler>();
            var logger = sp.GetRequiredService<ILogger<Mesh.Transport.TransportSelector>>();
            return new Mesh.Transport.TransportSelector(
                options.Value,
                dialers,
                policyManager,
                downgradeProtector,
                connectionThrottler,
                logger);
        });

        // Descriptor signing service for cryptographic integrity
        services.AddSingleton<Mesh.Transport.DescriptorSigningService>();

        // Ed25519 signing implementation
        services.AddSingleton<Mesh.Transport.Ed25519Signer>();

        // Control envelope validator for replay protection and peer-bound verification
        services.AddSingleton<Mesh.Overlay.ControlEnvelopeValidator>();

        // KeyStore for Ed25519 signing (used by ControlSigner and MeshMessageSigner)
        services.AddSingleton<Mesh.Overlay.IKeyStore, Mesh.Overlay.FileKeyStore>();
        services.AddSingleton<Mesh.Overlay.IControlSigner, Mesh.Overlay.ControlSigner>();
        services.AddSingleton<Mesh.Overlay.IControlDispatcher>(sp =>
        {
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.Overlay.ControlDispatcher>>();
            var validator = sp.GetRequiredService<Mesh.Overlay.ControlEnvelopeValidator>();
            var privacyLayer = sp.GetService<Mesh.Privacy.IPrivacyLayer>();
            return new Mesh.Overlay.ControlDispatcher(logger, validator, privacyLayer);
        });

        // Mesh message signing for mesh sync security
        services.AddSingleton<Mesh.IMeshMessageSigner, Mesh.MeshMessageSigner>();
        services.AddSingleton(sp =>
        {
            var keyStore = sp.GetRequiredService<Mesh.Overlay.IKeyStore>();
            return keyStore.Current;
        });
        var overlayoptionsAtStartup = configuration.GetSection($"{Program.AppName}:Overlay").Get<Mesh.Overlay.OverlayOptions>() ?? new Mesh.Overlay.OverlayOptions();
        var dataOverlayoptionsAtStartup = configuration.GetSection($"{Program.AppName}:OverlayData").Get<Mesh.Overlay.DataOverlayOptions>() ?? new Mesh.Overlay.DataOverlayOptions();
        var dhtoptionsAtStartup = optionsAtStartup.DhtRendezvous;
        var quicPlatformSupported = OperatingSystem.IsLinux() || OperatingSystem.IsMacOS() || OperatingSystem.IsWindows();
        var quicRuntimeAvailable = quicPlatformSupported && Mesh.QuicRuntime.IsAvailable();
        var quicOverlayRequested = optionsAtStartup.Feature.Mesh && meshOptionsAtStartup.EnableOverlay && overlayoptionsAtStartup.Enable && overlayoptionsAtStartup.EnableQuic;
        var quicDataRequested = optionsAtStartup.Feature.Mesh && meshOptionsAtStartup.EnableOverlay && dataOverlayoptionsAtStartup.Enable;
        var sharedMeshUdpRequested = DhtRendezvousService.ShouldUseSharedMeshUdpListener(dhtoptionsAtStartup, overlayoptionsAtStartup);

        if (optionsAtStartup.Feature.Mesh &&
            meshOptionsAtStartup.EnableOverlay &&
            Mesh.Overlay.QuicOverlayFactory.ShouldRunStandaloneUdpOverlayServer(overlayoptionsAtStartup.Enable, sharedMeshUdpRequested))
        {
            services.AddHostedService(p =>
            {
                Log.Debug("[DI] Constructing UdpOverlayServer hosted service...");
                var service = ActivatorUtilities.CreateInstance<Mesh.Overlay.UdpOverlayServer>(p);
                Log.Debug("[DI] UdpOverlayServer constructed");
                return service;
            });
        }
        else
        {
            Log.Debug("[DI] Standalone UDP overlay server skipped because the shared mesh UDP listener owns the configured overlay port");
        }

        if (quicOverlayRequested && quicRuntimeAvailable)
        {
#pragma warning disable CA1416 // Runtime platform guards apply in this branch
            services.AddHostedService(p =>
            {
                Log.Debug("[DI] Constructing QuicOverlayServer hosted service...");
                var service = Mesh.Overlay.QuicOverlayFactory.CreateOverlayServer(p);
                Log.Debug("[DI] QuicOverlayServer constructed");
                return service;
            });
#pragma warning restore CA1416
        }
        else if (quicOverlayRequested)
        {
            Log.Warning("[DI] QUIC overlay requested but runtime/platform support is unavailable; skipping QuicOverlayServer hosted service");
        }
        else
        {
            Log.Debug("[DI] QUIC overlay disabled by configuration; skipping QuicOverlayServer hosted service");
        }

        if (quicOverlayRequested && quicRuntimeAvailable)
        {
#pragma warning disable CA1416 // Runtime platform guards apply in this branch.
            services.AddSingleton<Mesh.Overlay.IOverlayClient>(sp =>
            {
                return Mesh.Overlay.QuicOverlayFactory.CreateOverlayClient(sp);
            });
#pragma warning restore CA1416
        }
        else
        {
            services.AddSingleton<Mesh.Overlay.IOverlayClient>(sp =>
            {
                var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<Mesh.Overlay.UdpOverlayClient>>();
                var options = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<Mesh.Overlay.OverlayOptions>>();
                var privacyLayer = sp.GetService<Mesh.Privacy.IPrivacyLayer>();
                return new Mesh.Overlay.UdpOverlayClient(logger, options, privacyLayer);
            });
        }

        if (quicDataRequested && quicRuntimeAvailable)
        {
#pragma warning disable CA1416 // Runtime platform guards apply in this branch.
            services.AddSingleton<Mesh.Overlay.IOverlayDataPlane>(sp => Mesh.Overlay.QuicOverlayFactory.CreateDataClient(sp));
#pragma warning restore CA1416
        }

        if (quicDataRequested && quicRuntimeAvailable)
        {
            services.AddHostedService(p =>
            {
                Log.Debug("[DI] Constructing QuicDataServer hosted service...");
                var service = ActivatorUtilities.CreateInstance<Mesh.Overlay.QuicDataServer>(p);
                Log.Debug("[DI] QuicDataServer constructed");
                return service;
            });
        }
        else if (quicDataRequested)
        {
            Log.Warning("[DI] QUIC data overlay requested but runtime/platform support is unavailable; skipping QuicDataServer hosted service");
        }
        else
        {
            Log.Debug("[DI] QUIC data overlay disabled by configuration; skipping QuicDataServer hosted service");
        }

        return services;
    }
}
