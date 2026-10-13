// <copyright file="Options.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="Options.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel;
    using System.ComponentModel.DataAnnotations;
    using System.Diagnostics;
    using System.IO;
    using System.Linq;
    using System.Net;
    using System.Text.Json.Serialization;
    using System.Text.RegularExpressions;
    using FluentFTP;
    using NetTools;
    using slskd.Authentication;
    using slskd.Common;
    using slskd.Common.Moderation;
    using slskd.Configuration;
    using slskd.DhtRendezvous;
    using slskd.Events;
    using slskd.Relay;
    using slskd.Shares;
    using slskd.Signals;
    using slskd.SocialFederation;
    using slskd.Validation;
    using Utility.CommandLine;
    using Utility.EnvironmentVariables;
    using YamlDotNet.Serialization;
    using SoulseekDiagnostics = Soulseek.Diagnostics;

    /// <summary>
    ///     Disambiguates options derived at startup from options that may update at run time.
    /// </summary>
    /// <remarks>
    ///     This class is added directly to dependency injection, but <see cref="Options"/> is not, so consumers must inject <see cref="OptionsAtStartup"/>
    ///     instead of <see cref="Options"/> to make it clear that these options will not change.  Options that may change should be accessed by injecting
    ///     <see cref="IOptionsMonitor{T}"/> or <see cref="IOptionsSnapshot{T}"/>, depending on the lifetime of the component.
    /// </remarks>
    public class OptionsAtStartup : Options
    {
    }

    /// <summary>
    ///     Soulseek type-1 peer/distributed/transfer obfuscation posture.
    /// </summary>
    public enum SoulseekObfuscationMode
    {
        /// <summary>
        ///     Advertise regular and obfuscated peer/distributed/transfer reachability when runtime support is available.
        /// </summary>
        Compatibility,

        /// <summary>
        ///     Prefer obfuscated peer/distributed/transfer connections when peers advertise compatible metadata.
        /// </summary>
        Prefer,

        /// <summary>
        ///     Reserved for obfuscated-only peer-message reachability; not currently supported by the runtime.
        /// </summary>
        Only,
    }

    /// <summary>
    ///     Application options.
    /// </summary>
    /// <remarks>
    ///     <para>
    ///         This class contains all application options, which may be sourced from (in order of precedence):
    ///         <list type="bullet">
    ///             <item>
    ///                 <term>Defaults</term>
    ///                 <description>Default values, statically defined in this class.</description>
    ///             </item>
    ///             <item>
    ///                 <term>Environment Variables</term>
    ///                 <description>Environment variables set at either the system or user scope.</description>
    ///             </item>
    ///             <item>
    ///                 <term>YAML Configuration File</term>
    ///                 <description>A YAML file containing a mapping of this class.</description>
    ///             </item>
    ///             <item>
    ///                 <term>Command Line</term>
    ///                 <description>Options provided via the command line when starting the application.</description>
    ///             </item>
    ///         </list>
    ///     </para>
    ///     <para>
    ///         Only the YAML configuration source can change at runtime and consumers of this class must be aware of this, either injecting
    ///         <see cref="IOptionsMonitor{T}"/> in components with a singleton lifetime, or <see cref="IOptionsSnapshot{T}"/> for transient or scoped lifetimes.
    ///     </para>
    ///     <para>
    ///         To obtain the Options specified at startup (discarding any updates that may have been applied since), inject <see cref="OptionsAtStartup"/>.
    ///     </para>
    ///     <para>
    ///         Options specified via the command line can not be overwritten by changes to the YAML file.  This is by design due to the immutable
    ///         nature of the command line string after the application is started.
    ///     </para>
    /// </remarks>
    public class Options : IValidatableObject
    {
        /// <summary>
        ///     Gets a value indicating whether to display the application version.
        /// </summary>
        [Argument('v', "version")]
        [Description("display version information")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public bool ShowVersion { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether to display a list of command line arguments.
        /// </summary>
        [Argument('h', "help")]
        [Description("display command line usage")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public bool ShowHelp { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether to display a list of configuration environment variables.
        /// </summary>
        [Argument('e', "envars")]
        [Description("display environment variables")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public bool ShowEnvironmentVariables { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether to generate an X509 certificate and password.
        /// </summary>
        [Argument('g', "generate-cert")]
        [Description("generate X509 certificate and password for HTTPS")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public bool GenerateCertificate { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether to generate a random secret.
        /// </summary>
        [Argument('k', "generate-secret")]
        [Description("generate random secret of the specified length")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public bool GenerateSecret { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether the application should run in debug mode.
        /// </summary>
        [Argument('d', "debug")]
        [EnvironmentVariable("DEBUG")]
        [Description("run in debug mode")]
        [RequiresRestart]
        public bool Debug { get; init; } = Debugger.IsAttached;

        /// <summary>
        ///     Gets a value indicating whether the application should run in headless (no web UI) mode.
        /// </summary>
        [Argument('H', "headless")]
        [EnvironmentVariable("HEADLESS")]
        [Description("run in headless (no web UI) mode")]
        [RequiresRestart]
        public bool Headless { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether remote configuration of options is allowed.
        /// </summary>
        [Argument(default, "remote-configuration")]
        [EnvironmentVariable("REMOTE_CONFIGURATION")]
        [Description("allow remote configuration")]
        public bool RemoteConfiguration { get; init; } = false;

        /// <summary>
        ///     Gets a value indicating whether remote file management is allowed.
        /// </summary>
        [Argument(default, "remote-file-management")]
        [EnvironmentVariable("REMOTE_FILE_MANAGEMENT")]
        [Description("allow remote file management")]
        public bool RemoteFileManagement { get; init; } = false;

        /// <summary>
        ///     Gets the unique name for this instance.
        /// </summary>
        [Argument('i', "instance-name")]
        [EnvironmentVariable("INSTANCE_NAME")]
        [Description("optional; a unique name for this instance")]
        [RequiresRestart]
        public string InstanceName { get; init; } = "default";

        /// <summary>
        ///     Gets optional flags.
        /// </summary>
        [Validate]
        public FlagsOptions Flags { get; init; } = new FlagsOptions();

        /// <summary>
        ///     Warm cache configuration for popular MBIDs (overlay-only prefetch/serve).
        /// </summary>
        [Validate]
        public WarmCacheOptions WarmCache { get; init; } = new WarmCacheOptions();

        /// <summary>
        ///     Gets the path where application data is saved.
        /// </summary>
        [Argument('a', "app-dir")]
        [EnvironmentVariable("APP_DIR")]
        [Description("path where application data is saved")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public string AppDirectory { get; init; } = Program.DefaultAppDirectory;

        /// <summary>
        ///     Gets the path where application data is saved.
        /// </summary>
        [Argument('c', "config")]
        [EnvironmentVariable("CONFIG")]
        [Description("path to configuration file")]
        [Obsolete("Used only for documentation; see Program for actual implementation")]
        [JsonIgnore]
        [YamlIgnore]
        public string ConfigurationFile { get; init; } = Program.DefaultConfigurationFile;

        /// <summary>
        ///     Gets relay options.
        /// </summary>
        [Validate]
        public RelayOptions Relay { get; init; } = new RelayOptions();

        /// <summary>
        ///     Gets permission options.
        /// </summary>
        [Validate]
        public PermissionsOptions Permissions { get; init; } = new PermissionsOptions();

        /// <summary>
        ///     Gets directory options.
        /// </summary>
        [Validate]
        [RequiresRestart]
        public DirectoriesOptions Directories { get; init; } = new DirectoriesOptions();

        /// <summary>
        ///     Gets share options.
        /// </summary>
        [Validate]
        public SharesOptions Shares { get; init; } = new SharesOptions();

        /// <summary>
        ///     Gets global options.
        /// </summary>
        [Validate]
        [YamlMember(Alias = "transfers")]
        public GlobalOptions Global { get; init; } = new GlobalOptions();

        /// <summary>
        ///     Gets the DhtRendezvous options.
        /// </summary>
        [YamlMember(Alias = "dht")]
        public DhtRendezvousOptions DhtRendezvous { get; init; } = new DhtRendezvousOptions();

        /// <summary>
        ///     Gets user groups.
        /// </summary>
        [Validate]
        public GroupsOptions Groups { get; init; } = new GroupsOptions();

        /// <summary>
        ///     Gets blacklist options.
        /// </summary>
        [Validate]
        public BlacklistOptions Blacklist { get; init; } = new BlacklistOptions();

        /// <summary>
        ///     Gets filter options.
        /// </summary>
        [Validate]
        public FiltersOptions Filters { get; init; } = new FiltersOptions();

        /// <summary>
        ///     Gets wishlist options.
        /// </summary>
        [Validate]
        public WishlistOptions Wishlist { get; init; } = new WishlistOptions();

        /// <summary>
        ///     Gets auto-replace options.
        /// </summary>
        [Validate]
        public AutoReplaceOptions AutoReplace { get; init; } = new AutoReplaceOptions();

        /// <summary>
        ///     Gets download destination options.
        /// </summary>
        [Validate]
        public DestinationsOptions Destinations { get; init; } = new DestinationsOptions();

        /// <summary>
        ///     Gets a list of rooms to automatically join upon connection.
        /// </summary>
        [Argument(default, "rooms")]
        [EnvironmentVariable("ROOMS")]
        [Description("a list of rooms to automatically join")]
        public string[] Rooms { get; init; } = Array.Empty<string>();

        /// <summary>
        ///     Gets options for the web UI.
        /// </summary>
        [Validate]
        public WebOptions Web { get; init; } = new WebOptions();

        /// <summary>
        ///     Gets retention options.
        /// </summary>
        [Validate]
        public RetentionOptions Retention { get; init; } = new RetentionOptions();

        /// <summary>
        ///     Gets throttling options.
        /// </summary>
        [Validate]
        [RequiresRestart]
        public ThrottlingOptions Throttling { get; init; } = new ThrottlingOptions();

        /// <summary>
        ///     Gets logger options.
        /// </summary>
        [Validate]
        [RequiresRestart]
        public LoggerOptions Logger { get; init; } = new LoggerOptions();

        /// <summary>
        ///     Gets diagnostics options (e.g. memory dump endpoint).
        /// </summary>
        [RequiresRestart]
        public DiagnosticsOptions Diagnostics { get; init; } = new DiagnosticsOptions();

        /// <summary>
        ///     Gets metrics options.
        /// </summary>
        [Validate]
        [RequiresRestart]
        public MetricsOptions Metrics { get; init; } = new MetricsOptions();

        /// <summary>
        ///     Gets telemetry options (OpenTelemetry tracing).
        /// </summary>
        [Validate]
        [RequiresRestart]
        public TelemetryOptions Telemetry { get; init; } = new TelemetryOptions();

        /// <summary>
        ///     Gets LAN discovery advertising options.
        /// </summary>
        [Validate]
        [RequiresRestart]
        public LanDiscoveryOptions LanDiscovery { get; init; } = new LanDiscoveryOptions();

        /// <summary>
        ///     Gets feature options.
        /// </summary>
        [Validate]
        [RequiresRestart]
        public FeatureOptions Feature { get; init; } = new FeatureOptions();

        /// <summary>
        ///     Gets Solid options (WebID, Solid-OIDC, Pod metadata).
        /// </summary>
        [Validate]
        public SolidOptions Solid { get; init; } = new SolidOptions();

        /// <summary>
        ///     Gets options for sharing (collections, share-grants, tokens).
        /// </summary>
        [Validate]
        public SharingOptions Sharing { get; init; } = new SharingOptions();

        /// <summary>
        ///     Gets options for SongID background processing.
        /// </summary>
        [Validate]
        public SongIdOptions SongId { get; init; } = new SongIdOptions();

        /// <summary>
        ///     Gets web player options.
        /// </summary>
        [Validate]
        public PlayerOptions Player { get; init; } = new PlayerOptions();

        /// <summary>
        ///     Gets options for the Soulseek client.
        /// </summary>
        [Validate]
        public SoulseekOptions Soulseek { get; init; } = new SoulseekOptions();

        /// <summary>
        ///     Gets options for rescue mode (underperformance detection and overlay backfill).
        /// </summary>
        [Validate]
        public RescueModeOptions RescueMode { get; init; } = new RescueModeOptions();

        /// <summary>
        ///     Gets options for external integrations.
        /// </summary>
        [Validate]
        [YamlMember(Alias = "integrations")]
        public IntegrationOptions Integration { get; init; } = new IntegrationOptions();

        /// <summary>
        ///     Gets options for moderation / control plane (T-MCP01).
        /// </summary>
        [Validate]
        public ModerationOptions Moderation { get; init; } = new ModerationOptions();

        /// <summary>
        ///     Gets options for social federation (T-FED01).
        /// </summary>
        [Validate]
        public SocialFederationOptions SocialFederation { get; init; } = new SocialFederationOptions();

        /// <summary>
        ///     Gets options for federation publishing (T-FED03).
        /// </summary>
        [Validate]
        public FederationPublishingOptions FederationPublishing { get; init; } = new FederationPublishingOptions();

        /// <summary>
        ///     Gets options for realm configuration (T-REALM-01).
        /// </summary>
        public Mesh.Realm.RealmConfig Realm { get; init; } = new Mesh.Realm.RealmConfig
        {
            Id = "default-realm",
            GovernanceRoots = new[] { "default-governance" },
            BootstrapNodes = Array.Empty<string>(),
            Policies = new Mesh.Realm.RealmPolicies(),
        };

        /// <summary>
        ///     Gets options for multi-realm configuration (T-REALM-02).
        /// </summary>
        public Mesh.Realm.MultiRealmConfig MultiRealm { get; init; } = new Mesh.Realm.MultiRealmConfig
        {
            Realms = new[]
            {
                new Mesh.Realm.RealmConfig
                {
                    Id = "default-realm",
                    GovernanceRoots = new[] { "default-governance" },
                    BootstrapNodes = Array.Empty<string>(),
                    Policies = new Mesh.Realm.RealmPolicies()
                },
            },
            Bridge = new Mesh.Realm.BridgeConfig(),
        };

        /// <summary>
        /// Gets or sets warm cache configuration.
        /// </summary>

        /// <summary>
        /// Gets or sets Virtual Soulfind configuration.
        /// </summary>
        public Core.VirtualSoulfindOptions? VirtualSoulfind { get; set; }

        /// <summary>
        ///     Gets or sets VirtualSoulfind v2 configuration.
        /// </summary>
        [Validate]
        public slskd.VirtualSoulfind.v2.Configuration.VirtualSoulfindOptions VirtualSoulfindV2 { get; init; } = new();

        /// <summary>
        ///     Gets or sets signal system configuration for multi-channel control signaling.
        /// </summary>
        [Validate]
        public Signals.SignalSystemOptions SignalSystem { get; init; } = new Signals.SignalSystemOptions();

        /// <summary>
        ///     Gets or sets security configuration options.
        /// </summary>
        [Validate]
        public Common.Security.SecurityOptions Security { get; init; } = new Common.Security.SecurityOptions();

        /// <summary>
        ///     Handles top-level validation that doesn't fit anywhere else.
        /// </summary>
        /// <param name="validationContext"></param>
        /// <returns></returns>
        public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
        {
            var results = new List<ValidationResult>();

            if (InstanceName == Program.LocalHostName && Relay.Mode.ToEnum<RelayMode>() == RelayMode.Agent)
            {
                results.Add(new ValidationResult($"Instance name must be something other than '{Program.LocalHostName}' when operating in Relay Agent mode"));
            }

            if (!Flags.NoConnect &&
                IPAddress.TryParse(Soulseek.ListenIpAddress, out var soulseekListenAddress) &&
                IPAddress.IsLoopback(soulseekListenAddress))
            {
                results.Add(new ValidationResult(
                    "Soulseek.ListenIpAddress must not be a loopback address when the client is connecting. Use 0.0.0.0 or a reachable LAN/VPN interface instead.",
                    [nameof(Soulseek), nameof(Flags)]));
            }

            if (DhtRendezvous.Enabled && (DhtRendezvous.DhtPort <= IPEndPoint.MinPort || DhtRendezvous.DhtPort > IPEndPoint.MaxPort))
            {
                results.Add(new ValidationResult(
                    "DHT rendezvous requires an explicit UDP port between 1 and 65535. Configure dht.dht_port to a stable forwarded or allow-listed port.",
                    [nameof(DhtRendezvous)]));
            }

            if (DhtRendezvous.Enabled && DhtRendezvous.AdvertisedOverlayPort is < 0 or > IPEndPoint.MaxPort)
            {
                results.Add(new ValidationResult(
                    "DHT rendezvous advertised overlay port must be 0 or between 1 and 65535. Configure dht.advertised_overlay_port to the VPN-assigned public TCP port, or leave it unset to use dht.overlay_port.",
                    [nameof(DhtRendezvous)]));
            }

            if (DhtRendezvous.Enabled && (DhtRendezvous.BootstrapRouters is null || DhtRendezvous.BootstrapRouters.Length == 0 || DhtRendezvous.BootstrapRouters.All(string.IsNullOrWhiteSpace)))
            {
                results.Add(new ValidationResult(
                    "DHT rendezvous requires at least one bootstrap router. Configure dht.bootstrap_routers with reachable BitTorrent DHT routers.",
                    [nameof(DhtRendezvous)]));
            }

            if (Soulseek.Obfuscation.Enabled &&
                Soulseek.Obfuscation.ListenPort > 0 &&
                Soulseek.Obfuscation.ListenPort == Soulseek.ListenPort)
            {
                results.Add(new ValidationResult(
                    "Soulseek obfuscation requires a dedicated listen port different from soulseek.listen_port.",
                    [nameof(Soulseek)]));
            }

            // Validate realm configuration (T-REALM-01, T-REALM-02)
            results.AddRange(Realm.Validate());
            results.AddRange(MultiRealm.Validate());
            results.AddRange(Soulseek.Obfuscation.Validate(new ValidationContext(Soulseek.Obfuscation)));

            return results;
        }

        /// <summary>
        ///     Optional flags.
        /// </summary>
        public class FlagsOptions
        {
            /// <summary>
            ///     Gets a value indicating whether the logo should be suppressed on startup.
            /// </summary>
            [Argument('n', "no-logo")]
            [EnvironmentVariable("NO_LOGO")]
            [Description("suppress logo on startup")]
            [RequiresRestart]
            public bool NoLogo { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should quit after initialization.
            /// </summary>
            [Argument('x', "no-start")]
            [EnvironmentVariable("NO_START")]
            [Description("quit the application after initialization")]
            [RequiresRestart]
            public bool NoStart { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should watch the configuration file for changes.
            /// </summary>
            [Argument(default, "no-config-watch")]
            [EnvironmentVariable("NO_CONFIG_WATCH")]
            [Description("do not watch the config file for changes")]
            [RequiresRestart]
            public bool NoConfigWatch { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should connect to the Soulseek network on startup.
            /// </summary>
            [Argument(default, "no-connect")]
            [EnvironmentVariable("NO_CONNECT")]
            [Description("do not connect to the Soulseek network on startup")]
            [RequiresRestart]
            public bool NoConnect { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should scan shared directories on startup.
            /// </summary>
            [Argument(default, "no-share-scan")]
            [EnvironmentVariable("NO_SHARE_SCAN")]
            [Description("do not scan shares on startup")]
            [RequiresRestart]
            public bool NoShareScan { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether shares should be forcibly re-scanned on startup.
            /// </summary>
            [Argument(default, "force-share-scan")]
            [EnvironmentVariable("FORCE_SHARE_SCAN")]
            [Description("force a share scan on startup")]
            [RequiresRestart]
            public bool ForceShareScan { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether to force database migrations to be applied on startup.
            /// </summary>
            [Argument(default, "force-migrations")]
            [EnvironmentVariable("FORCE_MIGRATIONS")]
            [Description("force database migrations to be applied on startup")]
            public bool ForceMigrations { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should check for a newer version on startup.
            /// </summary>
            [Argument(default, "no-version-check")]
            [EnvironmentVariable("NO_VERSION_CHECK")]
            [Description("do not check for newer version at startup")]
            [RequiresRestart]
            public bool NoVersionCheck { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether Entity Framework queries should be logged.
            /// </summary>
            [Argument(default, "log-sql")]
            [EnvironmentVariable("LOG_SQL")]
            [Description("log SQL queries generated by Entity Framework")]
            [RequiresRestart]
            public bool LogSQL { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether to log unobserved Exceptions.
            /// </summary>
            [Argument(default, "log-unobserved-exceptions")]
            [EnvironmentVariable("LOG_UNOBSERVED_EXCEPTIONS")]
            [Description("log unobserved exceptions (caution: verbose)")]
            [RequiresRestart]
            public bool LogUnobservedExceptions { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should run in experimental mode.
            /// </summary>
            [Argument(default, "experimental")]
            [EnvironmentVariable("EXPERIMENTAL")]
            [Description("run in experimental mode")]
            [RequiresRestart]
            public bool Experimental { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the application should run in volatile mode.
            /// </summary>
            [Argument(default, "volatile")]
            [EnvironmentVariable("VOLATILE")]
            [Description("use volatile data storage (all data will be lost at shutdown)")]
            [RequiresRestart]
            public bool Volatile { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether user-defined regular expressions are case sensitive.
            /// </summary>
            [Argument(default, "case-sensitive-regex")]
            [EnvironmentVariable("CASE_SENSITIVE_REGEX")]
            [Description("user-defined regular expressions are case sensitive")]
            [RequiresRestart]
            public bool CaseSensitiveRegEx { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether to use legacy TCP keepalive options, for Windows
            ///     versions prior to Windows 10, version 1709 (and associated Server SKUs).
            /// </summary>
            [Argument(default, "legacy-windows-tcp-keepalive")]
            [EnvironmentVariable("LEGACY_WINDOWS_TCP_KEEPALIVE")]
            [Description("use a legacy TCP keepalive strategy for older Windows versions")]
            public bool LegacyWindowsTcpKeepalive { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether to use the uploaded shares from Relay agents as the source of
            ///     truth for file existence and size, instead of querying the agent prior to enqueueing the file.
            /// </summary>
            [Argument(default, "optimistic-relay-file-info")]
            [EnvironmentVariable("OPTIMISTIC_RELAY_FILE_INFO")]
            [Description("use uploaded relay shares as source of truth for file existence and size")]
            public bool OptimisticRelayFileInfo { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether SQLite pooling should be disabled.
            /// </summary>
            [Argument(default, "no-sqlite-pooling")]
            [EnvironmentVariable("NO_SQLITE_POOLING")]
            [Description("disable SQLite pooling")]
            public bool NoSqlitePooling { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether audio hash-from-file (PCM extraction) is enabled.
            ///     Startup fails when true because this build does not provide PCM extraction support.
            ///     §11: Do not register incomplete features, or fail at startup, or 501 at runtime.
            /// </summary>
            [Description("unsupported audio hash from file option; startup fails when true")]
            [RequiresRestart]
            public bool HashFromAudioFileEnabled { get; init; } = false;

            /// <summary>
            ///     Run audio analyzer migration at startup (recompute quality/transcode for variants with stale analyzer_version).
            /// </summary>
            [Argument(default, "audio-reanalyze")]
            [EnvironmentVariable("AUDIO_REANALYZE")]
            [Description("run audio analyzer migration at startup (recompute quality/transcode for stale variants)")]
            public bool AudioReanalyze { get; init; } = false;

            /// <summary>
            ///     When used with --audio-reanalyze, recompute all variants (ignore analyzer_version). Otherwise only stale.
            /// </summary>
            [Argument(default, "audio-reanalyze-force")]
            [EnvironmentVariable("AUDIO_REANALYZE_FORCE")]
            [Description("with --audio-reanalyze: recompute all variants, not only stale")]
            public bool AudioReanalyzeForce { get; init; } = false;
        }

        /// <summary>
        ///     Relay options.
        /// </summary>
        public class RelayOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets a value indicating whether the relay is enabled.
            /// </summary>
            [Argument('r', "relay")]
            [EnvironmentVariable("RELAY")]
            [Description("enable relay")]
            [RequiresRestart]
            public bool Enabled { get; init; } = false;

            /// <summary>
            ///     Gets the relay mode.
            /// </summary>
            [Argument('m', "relay-mode")]
            [EnvironmentVariable("RELAY_MODE")]
            [Description("relay mode; controller, agent")]
            [RequiresRestart]
            [Enum(typeof(RelayMode))]
            public string Mode { get; init; } = RelayMode.Controller.ToString().ToLowerInvariant();

            /// <summary>
            ///     Gets the controller configuration.
            /// </summary>
            public RelayControllerConfigurationOptions Controller { get; init; } = new RelayControllerConfigurationOptions();

            /// <summary>
            ///     Gets the agent configuration.
            /// </summary>
            public Dictionary<string, RelayAgentConfigurationOptions> Agents { get; init; } = new();

            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                var mode = Mode.ToEnum<RelayMode>();
                var results = new List<ValidationResult>();
                var modeResults = new List<ValidationResult>();

                if (mode == RelayMode.Agent && !Validator.TryValidateObject(Controller, new ValidationContext(Controller), modeResults, validateAllProperties: true))
                {
                    results.Add(new CompositeValidationResult("Controller", modeResults));
                }
                else
                {
                    // determine whether any InstanceName is used more than once
                    var instanceNames = Agents.Values.Select(a => a.InstanceName);

                    if (instanceNames.Count() != instanceNames.Distinct().Count())
                    {
                        modeResults.Add(new ValidationResult("One or more Agent instance names are duplicated.  Ensure instance names are unique."));
                    }

                    foreach (var (name, agent) in Agents)
                    {
                        var res = new List<ValidationResult>();
                        if (!Validator.TryValidateObject(agent, new ValidationContext(agent), res, validateAllProperties: true))
                        {
                            modeResults.Add(new CompositeValidationResult(name, res));
                        }
                    }

                    if (modeResults.Any())
                    {
                        results.Add(new CompositeValidationResult("Agents", modeResults));
                    }
                }

                return results;
            }

            /// <summary>
            ///     Relay controller configuration options.
            /// </summary>
            public class RelayControllerConfigurationOptions
            {
                /// <summary>
                ///     Gets the controller address.
                /// </summary>
                [Argument(default, "controller-address")]
                [EnvironmentVariable("CONTROLLER_ADDRESS")]
                [Description("controller address url")]
                [Url]
                [NotNullOrWhiteSpace]
                public string Address { get; init; } = string.Empty;

                /// <summary>
                ///     Gets a value indicating whether controller certificate validation failures for
                ///     self-signed/untrusted-root chains should be tolerated. CA validation and other
                ///     chain failures remain blocked.
                /// </summary>
                [Argument(default, "controller-ignore-certificate-errors")]
                [EnvironmentVariable("CONTROLLER_IGNORE_CERTIFICATE_ERRORS")]
                [Description("allow self-signed/untrusted-root controller certificates")]
                public bool IgnoreCertificateErrors { get; init; } = false;

                /// <summary>
                ///     HARDENING-2026-04-20 H8-pin: comma-separated list of base64 SHA-256 SPKI pins
                ///     the controller's TLS certificate must match. When set, takes precedence over
                ///     <see cref="IgnoreCertificateErrors"/> — a certificate whose SPKI doesn't match
                ///     any configured pin is rejected, even in "ignore errors" mode. Leave empty to
                ///     preserve legacy CA-only validation.
                /// </summary>
                [Argument(default, "controller-pinned-spki")]
                [EnvironmentVariable("CONTROLLER_PINNED_SPKI")]
                [Description("optional; comma separated base64 SHA-256 SPKI pins required of the controller certificate")]
                public string PinnedSpki { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the controller API key.
                /// </summary>
                [Argument(default, "controller-api-key")]
                [EnvironmentVariable("CONTROLLER_API_KEY")]
                [Description("controller api key")]
                [StringLength(255, MinimumLength = 16)]
                [NotNullOrWhiteSpace]
                [Secret]
                public string ApiKey { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the controller secret.
                /// </summary>
                [Argument(default, "controller-secret")]
                [EnvironmentVariable("CONTROLLER_SECRET")]
                [Description("shared secret")]
                [StringLength(255, MinimumLength = 16)]
                [NotNullOrWhiteSpace]
                [Secret]
                public string Secret { get; init; } = string.Empty;

                /// <summary>
                ///     Gets a value indicating whether to receive completed downloads from the controller.
                /// </summary>
                [Argument(default, "controller-downloads")]
                [EnvironmentVariable("CONTROLLER_DOWNLOADS")]
                [Description("receive completed downloads from the controller")]
                public bool Downloads { get; init; } = false;
            }

            /// <summary>
            ///     Relay agent configuration options.
            /// </summary>
            public class RelayAgentConfigurationOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the agent instance name.
                /// </summary>
                [Description("the name for this agent")]
                [StringLength(255, MinimumLength = 1)]
                [NotNullOrWhiteSpace]
                [Secret]
                public string InstanceName { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the agent secret.
                /// </summary>
                [Description("shared secret for this agent")]
                [StringLength(255, MinimumLength = 16)]
                [NotNullOrWhiteSpace]
                [Secret]
                public string Secret { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the comma separated list of CIDRs that are authorized to connect as this agent.
                /// </summary>
                [Description("optional; comma separated list of CIDRs that are authorized to connect as this agent")]
                public string Cidr { get; init; } = "0.0.0.0/0,::/0";

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    foreach (var cidr in Cidr.Split(','))
                    {
                        try
                        {
                            if (cidr.StartsWith("::ffff", StringComparison.OrdinalIgnoreCase))
                            {
                                throw new Exception("IPv4 mapped IPv6 addresses are not allowed");
                            }

                            _ = IPAddressRange.Parse(cidr);
                        }
                        catch (Exception)
                        {
                            results.Add(new ValidationResult($"CIDR {cidr} is invalid"));
                        }
                    }

                    return results;
                }
            }
        }

        /// <summary>
        ///     Permission options.
        /// </summary>
        public class PermissionsOptions
        {
            /// <summary>
            ///     Gets file permission options.
            /// </summary>
            [Validate]
            public FileOptions File { get; init; } = new FileOptions();

            /// <summary>
            ///     File permission options.
            /// </summary>
            public class FileOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the permissions to apply to newly created files.
                /// </summary>
                /// <remarks>
                ///     Applicable to non-Windows operating systems, only.
                /// </remarks>
                [Argument(default, "file-permission-mode")]
                [EnvironmentVariable("FILE_PERMISSION_MODE")]
                [Description("the permissions to apply to newly created files (chmod syntax, non-Windows only)")]
                public string Mode { get; init; } = string.Empty;

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    if (!string.IsNullOrEmpty(Mode))
                    {
                        var regEx = new Regex("^[0-7]{3,4}$", RegexOptions.Compiled);

                        if (!regEx.IsMatch(Mode))
                        {
                            results.Add(new ValidationResult($"Field {nameof(Mode)} is invalid. Specify a three- or four-character string consisting of only 0-7 (chmod syntax, [0]000-[7]777, inclusive)"));
                        }
                    }

                    return results;
                }
            }
        }

        /// <summary>
        ///     Directory options.
        /// </summary>
        public class DirectoriesOptions
        {
            /// <summary>
            ///     Gets the path where incomplete downloads are saved.
            /// </summary>
            [Argument(default, "incomplete")]
            [EnvironmentVariable("INCOMPLETE_DIR")]
            [Description("path where incomplete downloads are saved")]
            [DirectoryExists(ensureWriteable: true)]
            [RequiresRestart]
            public string Incomplete { get; init; } = Program.DefaultIncompleteDirectory;

            /// <summary>
            ///     Gets the path where downloaded files are saved.
            /// </summary>
            [Argument('o', "downloads")]
            [EnvironmentVariable("DOWNLOADS_DIR")]
            [Description("path where downloaded files are saved")]
            [DirectoryExists(ensureWriteable: true)]
            [RequiresRestart]
            public string Downloads { get; init; } = Program.DefaultDownloadsDirectory;
        }

        /// <summary>
        ///     Share options.
        /// </summary>
        public class SharesOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets the list of paths to shared files.
            /// </summary>
            [Argument('s', "shared")]
            [EnvironmentVariable("SHARED_DIR")]
            [Description("paths to shared files")]
            public string[] Directories { get; init; } = Array.Empty<string>();

            /// <summary>
            ///     Gets the list of shared file filters.
            /// </summary>
            [Argument(default, "share-filter")]
            [EnvironmentVariable("SHARE_FILTER")]
            [Description("regular expressions to filter files from shares")]
            public string[] Filters { get; init; } = Array.Empty<string>();

            /// <summary>
            ///     Share caching options.
            /// </summary>
            [Validate]
            public ShareCacheOptions Cache { get; init; } = new ShareCacheOptions();

            /// <summary>
            ///     Gets a value indicating whether share scans should probe audio files for bitrate, length, sample rate, and bit depth.
            /// </summary>
            [Argument(default, "shares-probe-media-attributes")]
            [EnvironmentVariable("SHARES_PROBE_MEDIA_ATTRIBUTES")]
            [Description("probe shared audio files for media attributes during share scans")]
            public bool ProbeMediaAttributes { get; init; } = true;

            /// <summary>
            ///     Extended validation.
            /// </summary>
            /// <param name="validationContext"></param>
            /// <returns></returns>
            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                var results = new List<ValidationResult>();

                results.AddRange(ValidateShares());
                results.AddRange(ValidateFilters());

                return results;
            }

            private IEnumerable<ValidationResult> ValidateShares()
            {
                var results = new List<ValidationResult>();

                var directories = Directories ?? Enumerable.Empty<string>();

                bool IsBlankPath(string share) => Regex.IsMatch(share.LocalizePath(), @"^(!|-){0,1}(\[.*?\])$");
                directories?.Where(share => IsBlankPath(share)).ToList()
                    .ForEach(blank => results.Add(new ValidationResult($"Share {blank} does not specify a path")));

                bool IsRootMount(string share) => Regex.IsMatch(share.LocalizePath(), @"^(!|-){0,1}(\[.*?\])/$");
                directories?.Where(share => IsRootMount(share)).ToList()
                    .ForEach(blank => results.Add(new ValidationResult($"Share {blank} specifies a root mount, which is not supported.")));

                // starts with '/', 'X:', or '\\'
                bool IsAbsolutePath(string share) => Regex.IsMatch(share.LocalizePath(), @"^(!|-){0,1}(\[.*?\])?(\/|[a-zA-Z]:|\\\\).*$");
                directories?.Where(share => !IsAbsolutePath(share)).ToList()
                    .ForEach(relativePath => results.Add(new ValidationResult($"Share {relativePath} contains a relative path; only absolute paths are supported.")));

                (string Raw, string Alias, string Path) Digest(string share)
                {
                    var matches = Regex.Matches(share, @"^(!|-){0,1}\[(.*?)\](.*)$");

                    if (matches.Any())
                    {
                        return (share, matches[0].Groups[2].Value, matches[0].Groups[3].Value);
                    }

#pragma warning disable S3878 // Arrays should not be created for params parameters
                    return (share, share.Split(new[] { '/', '\\' }).Last(), share);
#pragma warning restore S3878 // Arrays should not be created for params parameters
                }

                var digestedShared = (directories ?? Enumerable.Empty<string>())
                    .Select(share => Digest(share.TrimEnd('/', '\\')))
                    .ToHashSet();

                // make sure all aliases are distinct
                digestedShared.GroupBy(share => share.Alias).Where(group => group.Count() > 1).ToList()
                    .ForEach(overlap => results.Add(new ValidationResult($"Shares {string.Join(", ", overlap.Select(s => $"'{s.Raw}'"))} collide. Specify an alias for one or both to disambiguate them.")));

                // make sure the same path hasn't been specified twice, under different aliases
                digestedShared.GroupBy(share => share.Path).Where(group => group.Count() > 1).ToList()
                    .ForEach(dupe => results.Add(new ValidationResult($"Shares {string.Join(", ", dupe.Select(s => $"'{s.Raw}'"))} alias the same path")));

                // make sure each share has an alias, or is alias-able, and that the alias is valid
                foreach (var share in digestedShared)
                {
                    if (string.IsNullOrWhiteSpace(share.Alias))
                    {
                        results.Add(new ValidationResult($"Share '{share.Raw}' is invalid; alias may not be null, empty or consist of only whitespace"));
                    }
                    else if (share.Alias.Contains('\\') || share.Alias.Contains('/'))
                    {
                        results.Add(new ValidationResult($"Share '{share.Raw}' is invalid; aliases may not contain path separators '/' or '\\'"));
                    }
                }

                return results;
            }

            private IEnumerable<ValidationResult> ValidateFilters()
            {
                var results = new List<ValidationResult>();

                foreach (var filter in Filters)
                {
                    if (!filter.IsValidRegex())
                    {
                        results.Add(new ValidationResult($"Share filter '{filter}' is not a valid regular expression"));
                    }
                }

                return results;
            }

            /// <summary>
            ///     Share caching options.
            /// </summary>
            public class ShareCacheOptions
            {
                private const int MaxConservativeWorkerDefault = 4;

                /// <summary>
                ///     Gets the type of storage to use for the share cache.
                /// </summary>
                [Argument(default, "share-cache-storage-mode")]
                [EnvironmentVariable("SHARE_CACHE_STORAGE_MODE")]
                [Description("the type of storage to use for the cache")]
                [Enum(typeof(StorageMode))]
                [RequiresRestart]
                public string StorageMode { get; init; } = slskd.Shares.StorageMode.Memory.ToString().ToLowerInvariant();

                /// <summary>
                ///     Gets the number of workers to use while scanning shares.
                /// </summary>
                [Argument(default, "share-cache-workers")]
                [EnvironmentVariable("SHARE_CACHE_WORKERS")]
                [Description("the number of workers to use while scanning shares")]
                [Range(1, 128)]
                [RequiresRestart]
                public int Workers { get; init; } = GetDefaultWorkers();

                /// <summary>
                ///     Gets the conservative default worker count for share scans.
                /// </summary>
                /// <param name="processorCount">Optional processor count override for testing.</param>
                /// <returns>The default worker count.</returns>
                public static int GetDefaultWorkers(int? processorCount = null)
                {
                    var count = processorCount ?? Environment.ProcessorCount;

                    if (count <= 2)
                    {
                        return 1;
                    }

                    return Math.Min(MaxConservativeWorkerDefault, Math.Max(2, count / 2));
                }

                /// <summary>
                ///     Gets the time to retain the cache (the interval on which to re-scan automatically), in minutes.
                /// </summary>
                [Argument(default, "share-cache-retention")]
                [EnvironmentVariable("SHARE_CACHE_RETENTION")]
                [Description("the time to retain the cache (re-scan interval), in minutes")]
                [Range(60, int.MaxValue)]
                public int? Retention { get; init; } = null;
            }
        }

        /// <summary>
        ///     Global options.
        /// </summary>
        public class GlobalOptions
        {
            /// <summary>
            ///     Gets global upload options.
            /// </summary>
            [Validate]
            public GlobalUploadOptions Upload { get; init; } = new GlobalUploadOptions();

            /// <summary>
            ///     Gets global limits.
            /// </summary>
            [Validate]
            public LimitsOptions Limits { get; init; } = new LimitsOptions();

            /// <summary>
            ///     Gets global download options.
            /// </summary>
            [Validate]
            public GlobalDownloadOptions Download { get; init; } = new GlobalDownloadOptions();

            /// <summary>
            ///     Global upload options.
            /// </summary>
            public class GlobalUploadOptions
            {
                /// <summary>
                ///     Gets the limit for the total number of upload slots.
                /// </summary>
                [Argument(default, "upload-slots")]
                [EnvironmentVariable("UPLOAD_SLOTS")]
                [Description("the total number of upload slots")]
                [RequiresRestart]
                [Range(1, int.MaxValue)]
                public int Slots { get; init; } = 10;

                /// <summary>
                ///     Gets the total upload speed limit, in kibibytes.
                /// </summary>
                [Argument(default, "upload-speed-limit")]
                [EnvironmentVariable("UPLOAD_SPEED_LIMIT")]
                [Description("the total upload speed limit")]
                [Range(1, int.MaxValue)]
                public int SpeedLimit { get; init; } = int.MaxValue;

                /// <summary>
                ///     Gets the scheduled upload speed limits.
                /// </summary>
                [Validate]
                public ScheduledSpeedLimitOptions ScheduledLimits { get; init; } = new();
            }

            /// <summary>
            ///     Gets global download options.
            /// </summary>
            public class GlobalDownloadOptions
            {
                /// <summary>
                ///     Gets the limit for the total number of download slots.
                /// </summary>
                [Argument(default, "download-slots")]
                [EnvironmentVariable("DOWNLOAD_SLOTS")]
                [Description("the total number of download slots")]
                [RequiresRestart]
                [Range(1, int.MaxValue)]
                public int Slots { get; init; } = int.MaxValue;

                /// <summary>
                ///     Gets the total download speed limit, in kibibytes.
                /// </summary>
                [Argument(default, "download-speed-limit")]
                [EnvironmentVariable("DOWNLOAD_SPEED_LIMIT")]
                [Description("the total download speed limit")]
                [Range(1, int.MaxValue)]
                public int SpeedLimit { get; init; } = int.MaxValue;

                /// <summary>
                ///     Gets the scheduled download speed limits.
                /// </summary>
                [Validate]
                public ScheduledSpeedLimitOptions ScheduledLimits { get; init; } = new();

                /// <summary>
                ///     Gets direct Soulseek download retry options.
                /// </summary>
                [Validate]
                public DownloadRetryOptions Retry { get; init; } = new DownloadRetryOptions();

                /// <summary>
                ///     Gets the completed download folder layout.
                /// </summary>
                [Argument(default, "download-completed-layout")]
                [EnvironmentVariable("DOWNLOAD_COMPLETED_LAYOUT")]
                [Description("completed download folder layout: remote_folder, uploader_folder, batch_id, or flat")]
                public string CompletedLayout { get; init; } = "remote_folder";

                /// <summary>
                ///     Gets the completed download path template. When set, takes precedence over CompletedLayout.
                ///     Supported tokens: {uploader}, {remote_folder}, {remote_parent}, {remote_filename}, {batch_id},
                ///     {request_name}, {date}, {date:format}. Path separator is /.
                /// </summary>
                [Argument(default, "download-completed-path-template")]
                [EnvironmentVariable("DOWNLOAD_COMPLETED_PATH_TEMPLATE")]
                [Description("completed download path template, e.g. {uploader}/{remote_folder}")]
                public string CompletedPathTemplate { get; init; } = string.Empty;

                /// <summary>
                ///     Gets a value indicating whether auto-replace for stuck downloads is enabled.
                /// </summary>
                [Argument(default, "auto-replace-stuck")]
                [EnvironmentVariable("AUTO_REPLACE_STUCK")]
                [Description("automatically replace stuck downloads with alternative sources")]
                public bool AutoReplaceStuck { get; init; } = false;

                /// <summary>
                ///     Gets the maximum size difference percentage for auto-replacement.
                /// </summary>
                [Argument(default, "auto-replace-threshold")]
                [EnvironmentVariable("AUTO_REPLACE_THRESHOLD")]
                [Description("maximum size difference percentage for auto-replacement (e.g. 5.0 for 5%)")]
                [Range(0.1, 50.0)]
                public double AutoReplaceThreshold { get; init; } = 5.0;

                /// <summary>
                ///     Gets the interval in seconds between auto-replace checks.
                /// </summary>
                [Argument(default, "auto-replace-interval")]
                [EnvironmentVariable("AUTO_REPLACE_INTERVAL")]
                [Description("interval in seconds between auto-replace checks")]
                [Range(10, 3600)]
                public int AutoReplaceInterval { get; init; } = 60;

                /// <summary>
                ///     Gets a value indicating whether cost-based scheduling is enabled for multi-source downloads.
                /// </summary>
                [Argument(default, "cost-based-scheduling")]
                [EnvironmentVariable("COST_BASED_SCHEDULING")]
                [Description("enable cost-based scheduling for multi-source downloads")]
                [RequiresRestart]
                public bool CostBasedScheduling { get; init; } = true;

                /// <summary>
                ///     Gets options for automatically re-queuing failed downloads.
                /// </summary>
                [Validate]
                public AutoRetryOptions AutoRetry { get; init; } = new();

                /// <summary>
                ///     Direct Soulseek download retry options.
                /// </summary>
                public class DownloadRetryOptions
                {
                    /// <summary>
                    ///     Gets a value indicating how partial files are handled before a retry.
                    /// </summary>
                    [Argument(default, "download-retry-incomplete")]
                    [EnvironmentVariable("DOWNLOAD_RETRY_INCOMPLETE")]
                    [Description("how to handle partial files when retrying a direct Soulseek download: overwrite or resume")]
                    [Enum(typeof(slskd.Transfers.RetryIncompleteStrategy))]
                    public string Incomplete { get; init; } = slskd.Transfers.RetryIncompleteStrategy.Resume.ToString().ToLowerInvariant();

                    /// <summary>
                    ///     Gets the maximum number of direct Soulseek transfer attempts.
                    /// </summary>
                    [Argument(default, "download-retry-attempts")]
                    [EnvironmentVariable("DOWNLOAD_RETRY_ATTEMPTS")]
                    [Description("maximum number of direct Soulseek download attempts")]
                    [Range(1, 20)]
                    public int Attempts { get; init; } = 1;

                    /// <summary>
                    ///     Gets the initial retry delay in milliseconds.
                    /// </summary>
                    [Argument(default, "download-retry-delay")]
                    [EnvironmentVariable("DOWNLOAD_RETRY_DELAY")]
                    [Description("initial delay between direct Soulseek download attempts in milliseconds")]
                    [Range(0, 3600000)]
                    public int Delay { get; init; } = 5000;

                    /// <summary>
                    ///     Gets the maximum retry delay in milliseconds.
                    /// </summary>
                    [Argument(default, "download-retry-max-delay")]
                    [EnvironmentVariable("DOWNLOAD_RETRY_MAX_DELAY")]
                    [Description("maximum delay between direct Soulseek download attempts in milliseconds")]
                    [Range(1000, 86400000)]
                    public int MaxDelay { get; init; } = 60000;
                }

                /// <summary>
                ///     Options for automatically re-queuing failed downloads.
                /// </summary>
                public class AutoRetryOptions
                {
                    /// <summary>
                    ///     Gets a value indicating whether failed downloads are automatically re-queued.
                    /// </summary>
                    public bool Enabled { get; init; } = true;

                    /// <summary>
                    ///     Gets the minimum time in seconds a download must remain in a failed state before it is retried.
                    /// </summary>
                    [Range(10, 86400)]
                    public int RetryDelaySeconds { get; init; } = 1800;

                    /// <summary>
                    ///     Gets the interval in seconds between auto-retry scans.
                    /// </summary>
                    [Range(10, 3600)]
                    public int CheckIntervalSeconds { get; init; } = 300;

                    /// <summary>
                    ///     Gets the maximum number of automatic retry attempts per persisted download request. 0 means unlimited.
                    /// </summary>
                    [Range(0, 100)]
                    public int MaxAttempts { get; init; } = 5;

                    /// <summary>
                    ///     Gets the maximum number of failed files automatically re-queued in one scan.
                    /// </summary>
                    [Range(1, 100)]
                    public int MaxFilesPerCycle { get; init; } = 10;

                    /// <summary>
                    ///     Gets the maximum number of failed files automatically re-queued for one peer in one scan.
                    /// </summary>
                    [Range(1, 20)]
                    public int MaxFilesPerPeerPerCycle { get; init; } = 1;

                    /// <summary>
                    ///     Gets the minimum time in seconds before auto-retry contacts the same peer again.
                    /// </summary>
                    [Range(60, 86400)]
                    public int PeerCooldownSeconds { get; init; } = 900;

                    /// <summary>
                    ///     Gets a value indicating whether auto-retry can try alternate sources before falling back to the original peer.
                    /// </summary>
                    public bool AlternateSourcesEnabled { get; init; } = true;

                    /// <summary>
                    ///     Gets the maximum number of network alternative-source searches started in one auto-retry scan.
                    /// </summary>
                    [Range(0, 10)]
                    public int MaxAlternateSourceSearchesPerCycle { get; init; } = 1;

                    /// <summary>
                    ///     Gets the maximum size difference percentage accepted for alternate-source retry candidates.
                    /// </summary>
                    [Range(0.0, 100.0)]
                    public double AlternateSourceSizeTolerancePercent { get; init; } = 5.0;
                }
            }
        }

        /// <summary>
        ///     Limit options.
        /// </summary>
        public class LimitsOptions
        {
            /// <summary>
            ///     Gets limits for queued transfers.
            /// </summary>
            [Validate]
            public Limits Queued { get; init; } = new Limits();

            /// <summary>
            ///     Gets daily limits for transfers.
            /// </summary>
            [Validate]
            public Limits Daily { get; init; } = new Limits();

            /// <summary>
            ///     Gets weekly limits for transfers.
            /// </summary>
            [Validate]
            public Limits Weekly { get; init; } = new Limits();

            /// <summary>
            ///     Limits.
            /// </summary>
            public class Limits
            {
                /// <summary>
                ///     Gets the limit for number of files.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int? Files { get; init; } = null;

                /// <summary>
                ///     Gets the limit for number of megabytes.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int? Megabytes { get; init; } = null;

                /// <summary>
                ///     Gets the limit for number of failures.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int? Failures { get; init; } = null;
            }
        }

        /// <summary>
        ///     User groups.
        /// </summary>
        public class GroupsOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets options for the default user group.
            /// </summary>
            /// <remarks>
            ///     These options apply to users that are not privileged, have not been identified as leechers,
            ///     and have not been added as a member of any group.
            /// </remarks>
            [Validate]
            public BuiltInOptions Default { get; init; } = new BuiltInOptions();

            /// <summary>
            ///     Gets options for the leecher user group.
            /// </summary>
            /// <remarks>
            ///     These options apply to users that have been identified as leechers, and have not been added as a member of any group.
            /// </remarks>
            [Validate]
            public LeecherOptions Leechers { get; init; } = new LeecherOptions();

            /// <summary>
            ///     Gets options for the blacklisted user group.
            /// </summary>
            [Validate]
            public BlacklistedOptions Blacklisted { get; init; } = new BlacklistedOptions();

            /// <summary>
            ///     Gets user defined groups and options.
            /// </summary>
            [Validate]
            public Dictionary<string, UserDefinedOptions> UserDefined { get; init; } = new Dictionary<string, UserDefinedOptions>();

            /// <summary>
            ///     Extended validation.
            /// </summary>
            /// <param name="validationContext"></param>
            /// <returns></returns>
            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                var builtInGroups = new[] { Application.PrivilegedGroup, Application.DefaultGroup, Application.LeecherGroup };
                var intersection = UserDefined.Keys.Intersect(builtInGroups);

                foreach (var group in intersection)
                {
                    yield return new ValidationResult($"User defined group '{group}' collides with a built in group.  Choose a different name.");
                }

                var explicitMemberships = UserDefined
                    .SelectMany(group => (group.Value.Members ?? Array.Empty<string>())
                        .Where(member => !string.IsNullOrWhiteSpace(member))
                        .Select(member => new { Username = member.Trim(), Group = group.Key }))
                    .Concat((Blacklisted.Members ?? Array.Empty<string>())
                        .Where(member => !string.IsNullOrWhiteSpace(member))
                        .Select(member => new { Username = member.Trim(), Group = Application.BlacklistedGroup }))
                    .ToList();

                var duplicatedUsers = explicitMemberships
                    .GroupBy(member => member.Username, StringComparer.OrdinalIgnoreCase)
                    .Where(group => group.Select(member => member.Group).Distinct(StringComparer.OrdinalIgnoreCase).Count() > 1)
                    .Select(group => group.Key)
                    .OrderBy(username => username, StringComparer.OrdinalIgnoreCase)
                    .ToList();

                if (duplicatedUsers.Count > 0)
                {
                    yield return new ValidationResult(
                        $"One or more users are defined in multiple groups: {string.Join(", ", duplicatedUsers)}. Each user can only belong to one explicit group.");
                }
            }

            /// <summary>
            ///     Options that are common to all groups.
            /// </summary>
            public class GroupOptions
            {
                /// <summary>
                ///     Gets upload options.
                /// </summary>
                [Validate]
                public UploadOptions Upload { get; init; } = new UploadOptions();

                /// <summary>
                ///     Gets limit options.
                /// </summary>
                [Validate]
                public LimitsOptions Limits { get; init; } = new LimitsOptions();
            }

            /// <summary>
            ///     Built in user group options.
            /// </summary>
            public class BuiltInOptions : GroupOptions
            {
            }

            /// <summary>
            ///     Built in blacklisted group options.
            /// </summary>
            public class BlacklistedOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the list of group member usernames.
                /// </summary>
                public string[] Members { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets the list of group CIDRs.
                /// </summary>
                public string[] Cidrs { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets the list of regular expression patterns matched against usernames.
                /// </summary>
                public string[] Patterns { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    foreach (var cidr in Cidrs ?? Array.Empty<string>())
                    {
                        try
                        {
                            if (cidr.StartsWith("::ffff", StringComparison.OrdinalIgnoreCase))
                            {
                                throw new Exception("IPv4 mapped IPv6 addresses are not allowed");
                            }

                            _ = IPAddressRange.Parse(cidr);
                        }
                        catch (Exception)
                        {
                            results.Add(new ValidationResult($"CIDR {cidr} is invalid"));
                        }
                    }

                    foreach (var pattern in Patterns ?? Array.Empty<string>())
                    {
                        try
                        {
                            _ = new Regex(pattern);
                        }
                        catch (ArgumentException)
                        {
                            results.Add(new ValidationResult($"Blacklist pattern {pattern} is invalid"));
                        }
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Built in leecher group options.
            /// </summary>
            public class LeecherOptions : GroupOptions
            {
                /// <summary>
                ///     Gets leecher threshold options.
                /// </summary>
                [Validate]
                public ThresholdOptions Thresholds { get; init; } = new ThresholdOptions();
            }

            /// <summary>
            ///     Leecher threshold options.
            /// </summary>
            public class ThresholdOptions
            {
                /// <summary>
                ///     Gets the minimum number of shared files required to avoid being classified as a leecher.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int Files { get; init; } = 1;

                /// <summary>
                ///     Gets the minimum number of shared directories required to avoid being classified as a leecher.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int Directories { get; init; } = 1;
            }

            /// <summary>
            ///     User defined user group options.
            /// </summary>
            public class UserDefinedOptions : GroupOptions
            {
                /// <summary>
                ///     Gets the list of group member usernames.
                /// </summary>
                public string[] Members { get; init; } = Array.Empty<string>();
            }

            /// <summary>
            ///     User group upload options.
            /// </summary>
            public class UploadOptions
            {
                /// <summary>
                ///     Gets the priority of the group.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int Priority { get; init; } = 1;

                /// <summary>
                ///     Gets the queue strategy for the group.
                /// </summary>
                [Enum(typeof(Transfers.QueueStrategy))]
                public string Strategy { get; init; } = Transfers.QueueStrategy.RoundRobin.ToString().ToLowerInvariant();

                /// <summary>
                ///     Gets the limit for the total number of upload slots for the group.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int Slots { get; init; } = int.MaxValue;

                /// <summary>
                ///     Gets the total upload speed limit for the group, in kibibytes.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int SpeedLimit { get; init; } = int.MaxValue;

                /// <summary>
                ///     Gets the list of allowed file extensions for this group (e.g. ".mp3", ".flac").
                ///     When non-empty, only files matching one of these extensions will be uploaded.
                ///     Empty means no restriction.
                /// </summary>
                public string[] AllowedFileTypes { get; init; } = Array.Empty<string>();
            }
        }

        /// <summary>
        ///     Feature options.
        /// </summary>
        public class FeatureOptions
        {
            /// <summary>
            ///     Gets a value indicating whether swagger documentation and UI should be enabled.
            /// </summary>
            [Argument(default, "swagger")]
            [EnvironmentVariable("SWAGGER")]
            [Description("enable swagger documentation and UI")]
            [RequiresRestart]
            public bool Swagger { get; init; } = true;

            /// <summary>ShareGroups, Collections, ShareGrants, manifest, token. When false, related APIs return 404.</summary>
            public bool CollectionsSharing { get; init; } = true;

            /// <summary>GET /api/v0/streams/{contentId} with range and token or normal auth. When false, streaming API returns 404.</summary>
            public bool Streaming { get; init; } = true;

            /// <summary>Relay streaming fallback (controller proxies to agent). Defer; when false, relay/streams returns 404.</summary>
            public bool StreamingRelayFallback { get; init; } = true;

            /// <summary>Run mesh overlay search in parallel with Soulseek and merge results. Can align with VirtualSoulfind.MeshSearch.Enabled.</summary>
            public bool MeshParallelSearch { get; init; } = true;

            /// <summary>Publish availability to mesh/DHT. Defer.</summary>
            public bool MeshPublishAvailability { get; init; } = true;

            /// <summary>
            /// Identity and friends (profiles, contacts, nearby-peer browsing, invites). When false, related APIs return 404;
            /// startup advertising is configured separately.
            /// </summary>
            public bool IdentityFriends { get; init; } = true;

            /// <summary>
            /// Enable Solid / WebID / Solid-OIDC integration. When false, Solid APIs return 404.
            /// Default: true (enabled). Note: Even when enabled, remote fetches are blocked until AllowedHosts is configured.
            /// </summary>
            public bool Solid { get; init; } = true;

            /// <summary>Scene ↔ Pod Bridging: Unified search aggregation from Pod/Mesh and Soulseek Scene. When false, search behaves as before.</summary>
            public bool ScenePodBridge { get; init; } = false;

            /// <summary>SongID analysis/evidence APIs. Experimental and gated.</summary>
            public bool SongId { get; init; } = true;

            /// <summary>Mesh overlay/hash gossip APIs. Experimental and gated.</summary>
            public bool Mesh { get; init; } = true;

            /// <summary>DHT rendezvous and overlay discovery APIs. Experimental and gated.</summary>
            public bool Dht { get; init; } = true;

            /// <summary>Pod community APIs. Experimental and gated.</summary>
            public bool Pods { get; init; } = true;

            /// <summary>Social federation APIs. Experimental and gated.</summary>
            public bool SocialFederation { get; init; } = true;

            /// <summary>VirtualSoulfind APIs. Experimental and gated.</summary>
            public bool VirtualSoulfind { get; init; } = true;

            /// <summary>Multi-source/swarm download APIs. Experimental and gated.</summary>
            public bool MultiSourceDownloads { get; init; } = true;

            /// <summary>Scene ↔ Pod Bridging options.</summary>
            public ScenePodBridgeOptions ScenePodBridgeOptions { get; init; } = new ScenePodBridgeOptions();
        }

        /// <summary>
        ///     Scene ↔ Pod Bridging options.
        /// </summary>
        public class ScenePodBridgeOptions
        {
            /// <summary>Proxy scene downloads through pod (future feature, keep OFF). When false, scene downloads use existing Soulseek pipeline.</summary>
            public bool ProxyTransfers { get; init; } = false;

            /// <summary>Export pod availability to scene (future feature, keep OFF). When false, pod content is never advertised to scene.</summary>
            public bool ExportPodAvailability { get; init; } = false;
        }

        /// <summary>
        ///     Web player options.
        /// </summary>
        public class PlayerOptions
        {
            /// <summary>
            ///     Gets external visualizer launcher options.
            /// </summary>
            public ExternalVisualizerOptions ExternalVisualizer { get; init; } = new ExternalVisualizerOptions();

            /// <summary>
            ///     External visualizer launcher options.
            /// </summary>
            public class ExternalVisualizerOptions
            {
                /// <summary>
                ///     Gets a value indicating whether the authenticated launch endpoint is enabled.
                /// </summary>
                public bool Enabled { get; init; }

                /// <summary>
                ///     Gets the executable or launcher script path.
                /// </summary>
                public string? Path { get; init; }

                /// <summary>
                ///     Gets command-line arguments passed to the configured launcher.
                /// </summary>
                public string[] Arguments { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets the working directory for the configured launcher.
                /// </summary>
                public string? WorkingDirectory { get; init; }

                /// <summary>
                ///     Gets a display name for the configured launcher.
                /// </summary>
                public string Name { get; init; } = "MilkDrop3";
            }
        }

        /// <summary>
        ///     Solid options (WebID, Solid-OIDC, Pod metadata).
        /// </summary>
        public class SolidOptions
        {
            /// <summary>
            /// If true, allow plain http:// WebID/Pod URLs (ONLY for dev/test). Keep false in prod.
            /// </summary>
            public bool AllowInsecureHttp { get; init; } = false;

            /// <summary>
            /// When true, allow localhost and loopback for WebID fetches (E2E/testing only). Keep false in prod.
            /// </summary>
            public bool AllowLocalhostForWebId { get; init; } = false;

            /// <summary>Max bytes we will read from WebID profile / Pod metadata resources.</summary>
            public int MaxFetchBytes { get; init; } = 1_000_000;

            /// <summary>HTTP timeout for WebID/Pod fetches.</summary>
            public int TimeoutSeconds { get; init; } = 10;

            /// <summary>
            /// Allowed Pod/WebID hostnames (exact match). Empty = deny all remote fetches unless explicitly set.
            /// </summary>
            public string[] AllowedHosts { get; init; } = Array.Empty<string>();

            /// <summary>
            /// Canonical absolute URL for the Solid-OIDC Client ID document. Empty disables the document endpoint.
            /// </summary>
            public string? ClientIdUrl { get; init; }

            /// <summary>
            /// Redirect URI path used for Solid-OIDC (default: /solid/callback). (Callback wiring can come later.)
            /// </summary>
            public string RedirectPath { get; init; } = "/solid/callback";
        }

        /// <summary>
        ///     Sharing options (collections, share-grants, token signing).
        /// </summary>
        public class SharingOptions : IValidatableObject
        {
            /// <summary>
            ///     Base URL recipients can use to reach this instance's share streaming API.
            ///     Leave empty when this instance is not reachable by other peers.
            /// </summary>
            [EnvironmentVariable("SHARING_EXTERNAL_ENDPOINT")]
            [Description("absolute HTTP(S) base URL recipients can use to reach this instance, including any URL base path")]
            [RequiresRestart]
            public string ExternalEndpoint { get; init; } = string.Empty;

            /// <summary>
            ///     Exact private or loopback IP origins trusted for incoming share backfill requests.
            ///     Only these origins may bypass the public-address outbound guard.
            /// </summary>
            [EnvironmentVariable("SHARING_TRUSTED_PRIVATE_OWNER_ORIGINS")]
            [Description("exact private or loopback IP origins allowed for incoming share backfills")]
            [RequiresRestart]
            public string[] TrustedPrivateOwnerOrigins { get; init; } = Array.Empty<string>();

            /// <summary>
            ///     Base64-encoded key for HMAC-SHA256 signing of share tokens. Decoded key must be at least 32 bytes.
            ///     When empty, IShareTokenService.Create throws. Used for token auth on streams and manifest.
            /// </summary>
            [Argument(default, "sharing-token-key")]
            [EnvironmentVariable("SHARING_TOKEN_KEY")]
            [Description("base64-encoded HMAC key for share tokens (min 32 bytes decoded)")]
            [Secret]
            public string TokenSigningKey { get; init; } = string.Empty;

            /// <inheritdoc />
            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                if (!string.IsNullOrWhiteSpace(ExternalEndpoint) &&
                    (!Uri.TryCreate(ExternalEndpoint, UriKind.Absolute, out var externalEndpoint) ||
                     !IsHttpUri(externalEndpoint) ||
                     !string.IsNullOrEmpty(externalEndpoint.UserInfo) ||
                     !string.IsNullOrEmpty(externalEndpoint.Query) ||
                     !string.IsNullOrEmpty(externalEndpoint.Fragment)))
                {
                    yield return new ValidationResult(
                        "Sharing.ExternalEndpoint must be an absolute HTTP(S) URL without credentials, query, or fragment.",
                        new[] { nameof(ExternalEndpoint) });
                }

                foreach (var origin in TrustedPrivateOwnerOrigins ?? Array.Empty<string>())
                {
                    if (!Uri.TryCreate(origin, UriKind.Absolute, out var uri) ||
                        !IsHttpUri(uri) ||
                        !string.IsNullOrEmpty(uri.UserInfo) ||
                        !string.IsNullOrEmpty(uri.Query) ||
                        !string.IsNullOrEmpty(uri.Fragment) ||
                        (uri.AbsolutePath != string.Empty && uri.AbsolutePath != "/") ||
                        !IPAddress.TryParse(uri.DnsSafeHost, out var address) ||
                        !IsTrustedPrivateOwnerAddress(address))
                    {
                        yield return new ValidationResult(
                            "Each Sharing.TrustedPrivateOwnerOrigins entry must be an exact HTTP(S) origin with a private, unique-local, or loopback IP literal; link-local and reserved addresses are not allowed.",
                            new[] { nameof(TrustedPrivateOwnerOrigins) });
                    }
                }
            }

            private static bool IsHttpUri(Uri uri) =>
                string.Equals(uri.Scheme, Uri.UriSchemeHttp, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(uri.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase);

            private static bool IsTrustedPrivateOwnerAddress(IPAddress address)
            {
                return Common.Security.IpRangeClassifier.Classify(address) is
                    Common.Security.IpRangeClassifier.IpClassification.Loopback or
                    Common.Security.IpRangeClassifier.IpClassification.PrivateRfc1918 or
                    Common.Security.IpRangeClassifier.IpClassification.PrivateUla;
            }
        }

        /// <summary>
        ///     SongID options.
        /// </summary>
        public class SongIdOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets the number of SongID runs processed concurrently.
            /// </summary>
            [Argument(default, "songid-max-concurrent-runs")]
            [EnvironmentVariable("SONGID_MAX_CONCURRENT_RUNS")]
            [Description("number of SongID runs processed concurrently")]
            [RequiresRestart]
            public int MaxConcurrentRuns { get; init; } = 2;

            /// <inheritdoc />
            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                if (MaxConcurrentRuns < 1)
                {
                    yield return new ValidationResult("SongId.MaxConcurrentRuns must be at least 1.", new[] { nameof(MaxConcurrentRuns) });
                }
            }
        }

        /// <summary>
        ///     Blacklist options.
        /// </summary>
        public class BlacklistOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets a value indicating whether blacklist file support should be enabled.
            /// </summary>
            [Argument(default, "enable-blacklist")]
            [EnvironmentVariable("BLACKLIST")]
            [Description("enable blacklist file support")]
            [RequiresRestart]
            public bool Enabled { get; init; }

            /// <summary>
            ///     Gets the path to the blacklist file.
            /// </summary>
            [Argument(default, "blacklist-file")]
            [EnvironmentVariable("BLACKLIST_FILE")]
            [Description("path to blacklist file")]
            [FileExists(FileAccess.Read)]
            public string File { get; init; } = string.Empty;

            /// <summary>
            ///     Extended validation.
            /// </summary>
            /// <param name="validationContext"></param>
            /// <returns></returns>
            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                var results = new List<ValidationResult>();

                if (!Enabled)
                {
                    return results;
                }

                // loading/validating the entire list will be costly on low spec systems
                // just make sure that we can detect a valid format and leave it at that
                // if there's a problem with any of the entries, the load will fail and
                // kill the application
                try
                {
                    _ = slskd.Blacklist.DetectFormatSync(File);
                }
                catch
                {
                    results.Add(new ValidationResult("Failed to detect blacklist format. Only CIDR, P2P and DAT formats are supported"));
                }

                return results;
            }
        }

        /// <summary>
        ///     Filter options.
        /// </summary>
        public class FiltersOptions
        {
            /// <summary>
            ///     Gets search filter options.
            /// </summary>
            [Validate]
            public SearchOptions Search { get; init; } = new SearchOptions();

            /// <summary>
            ///     Gets outbound download filter options.
            /// </summary>
            [Validate]
            public DownloadFilterOptions Download { get; init; } = new DownloadFilterOptions();

            /// <summary>
            ///     Gets search retention options.
            /// </summary>
            public SearchRetentionOptions SearchRetention { get; init; } = new SearchRetentionOptions();

            /// <summary>
            ///     Search filter options.
            /// </summary>
            public class SearchOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the list of search request filters.
                /// </summary>
                [Argument(default, "search-request-filter")]
                [EnvironmentVariable("SEARCH_REQUEST_FILTER")]
                [Description("regular expressions to filter incoming search requests")]
                public string[] Request { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    foreach (var filter in Request)
                    {
                        if (!filter.IsValidRegex())
                        {
                            results.Add(new ValidationResult($"Search request filter '{filter}' is not a valid regular expression"));
                        }
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Outbound download filter options.
            /// </summary>
            public class DownloadFilterOptions : IValidatableObject
            {
                private const int MaximumExclusionCount = 100;
                private const int MaximumExclusionLength = 256;

                /// <summary>
                ///     Gets literal, case-insensitive terms that block outbound downloads when present in a remote path.
                /// </summary>
                [Argument(default, "download-filter-exclude")]
                [EnvironmentVariable("DOWNLOAD_FILTER_EXCLUDE")]
                [Description("literal terms that block outbound downloads when present in a remote filename or path")]
                public string[] Exclude { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Validates configured download exclusions.
                /// </summary>
                /// <param name="validationContext">The validation context.</param>
                /// <returns>Validation errors, if any.</returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();
                    var exclusions = Exclude ?? Array.Empty<string>();

                    if (exclusions.Length > MaximumExclusionCount)
                    {
                        results.Add(new ValidationResult($"Download filter supports at most {MaximumExclusionCount} exclusions"));
                    }

                    for (var index = 0; index < exclusions.Length; index++)
                    {
                        var exclusion = exclusions[index]?.Trim();
                        if (string.IsNullOrWhiteSpace(exclusion))
                        {
                            results.Add(new ValidationResult($"Download filter exclusion at index {index} must not be blank"));
                        }
                        else if (exclusion.Length > MaximumExclusionLength)
                        {
                            results.Add(new ValidationResult($"Download filter exclusion '{exclusion}' exceeds the maximum length of {MaximumExclusionLength} characters"));
                        }
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Search retention options.
            /// </summary>
            public class SearchRetentionOptions
            {
                /// <summary>
                ///     Gets the maximum age of search records, in days. Searches older than this are deleted during cleanup.
                /// </summary>
                [Argument(default, "search-retention-max-age-days")]
                [EnvironmentVariable("SEARCH_RETENTION_MAX_AGE_DAYS")]
                [Description("maximum age of search records in days (0 = no limit)")]
                [Range(0, int.MaxValue)]
                public int MaxAgeDays { get; init; } = 30;

                /// <summary>
                ///     Gets the maximum number of search records to retain. Oldest searches are deleted when this limit is exceeded.
                /// </summary>
                [Argument(default, "search-retention-max-count")]
                [EnvironmentVariable("SEARCH_RETENTION_MAX_COUNT")]
                [Description("maximum number of search records to retain (0 = no limit)")]
                [Range(0, int.MaxValue)]
                public int MaxCount { get; init; } = 250;

                /// <summary>
                ///     Gets the interval between automatic search cleanup runs, in seconds.
                /// </summary>
                [Argument(default, "search-retention-cleanup-interval")]
                [EnvironmentVariable("SEARCH_RETENTION_CLEANUP_INTERVAL")]
                [Description("interval between automatic search cleanup runs in seconds")]
                [Range(3600, int.MaxValue)]
                public int CleanupIntervalSeconds { get; init; } = 86400;
            }
        }

        /// <summary>
        ///     Wishlist options.
        /// </summary>
        public class WishlistOptions
        {
            /// <summary>
            ///     Gets a value indicating whether wishlist background searching is enabled.
            /// </summary>
            [Argument(default, "wishlist-enabled")]
            [EnvironmentVariable("WISHLIST_ENABLED")]
            [Description("enable automatic wishlist background searching")]
            public bool Enabled { get; init; } = true;

            /// <summary>
            ///     Gets the interval between wishlist searches, in seconds.
            /// </summary>
            [Argument(default, "wishlist-interval")]
            [EnvironmentVariable("WISHLIST_INTERVAL")]
            [Description("interval between wishlist searches in seconds")]
            [Range(300, int.MaxValue)]
            public int IntervalSeconds { get; init; } = 3600;

            /// <summary>
            ///     Gets a value indicating whether to auto-download matches by default.
            /// </summary>
            [Argument(default, "wishlist-auto-download")]
            [EnvironmentVariable("WISHLIST_AUTO_DOWNLOAD")]
            [Description("automatically download matches from wishlist searches")]
            public bool AutoDownload { get; init; } = false;

            /// <summary>
            ///     Gets the maximum results per wishlist search.
            /// </summary>
            [Argument(default, "wishlist-max-results")]
            [EnvironmentVariable("WISHLIST_MAX_RESULTS")]
            [Description("maximum results per wishlist search")]
            [Range(10, 1000)]
            public int MaxResults { get; init; } = 100;
        }

        /// <summary>
        ///     Auto-replace options for automatic retry/replacement of stuck downloads.
        /// </summary>
        public class AutoReplaceOptions
        {
            /// <summary>
            ///     Gets the interval between auto-replace cycles, in seconds.
            /// </summary>
            [Argument(default, "auto-replace-interval")]
            [EnvironmentVariable("AUTO_REPLACE_INTERVAL")]
            [Description("interval between auto-replace cycles in seconds")]
            [Range(60, int.MaxValue)]
            public int IntervalSeconds { get; init; } = 300;

            /// <summary>
            ///     Gets the maximum size difference percentage for alternative sources.
            /// </summary>
            [Argument(default, "auto-replace-threshold")]
            [EnvironmentVariable("AUTO_REPLACE_THRESHOLD")]
            [Description("maximum size difference percentage for alternative sources (0 = exact match only)")]
            [Range(0, 100)]
            public double SizeThresholdPercent { get; init; } = 0.0;

            /// <summary>
            ///     Gets the maximum number of retry attempts before giving up on a download.
            /// </summary>
            [Argument(default, "auto-replace-max-retries")]
            [EnvironmentVariable("AUTO_REPLACE_MAX_RETRIES")]
            [Description("maximum retry attempts before giving up on a download (0 = unlimited)")]
            [Range(0, 100)]
            public int MaxRetries { get; init; } = 3;
        }

        /// <summary>
        ///     Download destination options.
        /// </summary>
        public class DestinationsOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets the list of download destinations.
            /// </summary>
            public List<DestinationOption> Folders { get; init; } = new List<DestinationOption>();

            /// <summary>
            ///     Validates configured download destinations.
            /// </summary>
            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                var folders = Folders ?? new List<DestinationOption>();

                if (folders.Count(destination => destination.Default) > 1)
                {
                    yield return new ValidationResult("Only one download destination can be marked as default");
                }

                foreach (var destination in folders)
                {
                    if (string.IsNullOrWhiteSpace(destination.Path))
                    {
                        yield return new ValidationResult("Each download destination requires a path");
                    }
                    else if (!Path.IsPathFullyQualified(destination.Path.LocalizePath()))
                    {
                        yield return new ValidationResult($"Download destination {destination.Path} contains a relative path; only absolute paths are supported");
                    }
                }
            }
        }

        /// <summary>
        ///     A download destination folder.
        /// </summary>
        public class DestinationOption
        {
            /// <summary>
            ///     Gets the display name for this destination.
            /// </summary>
            public string Name { get; init; } = string.Empty;

            /// <summary>
            ///     Gets the path to this destination.
            /// </summary>
            public string Path { get; init; } = string.Empty;

            /// <summary>
            ///     Gets a value indicating whether this is the default destination.
            /// </summary>
            public bool Default { get; init; } = false;
        }

        /// <summary>
        ///     Logger options.
        /// </summary>
        public class LoggerOptions
        {
            /// <summary>
            ///     Gets the URL to a Grafana Loki instance to which to log.
            /// </summary>
            [Argument(default, "loki")]
            [EnvironmentVariable("LOKI")]
            [Description("optional; url to a Grafana Loki instance to which to log")]
            [RequiresRestart]
            public string Loki { get; init; } = string.Empty;

            /// <summary>
            ///     Gets a value indicating whether to write logs to disk.
            /// </summary>
            [Argument(default, "disk-logger")]
            [EnvironmentVariable("DISK_LOGGER")]
            [Description("enable logging to disk")]
            [RequiresRestart]
            public bool Disk { get; init; } = true;

            /// <summary>
            ///     Gets a value indicating whether to suppress colorization of console logs.
            /// </summary>
            [Argument(default, "no-color")]
            [EnvironmentVariable("NO_COLOR")]
            [Description("disable console log colors")]
            [RequiresRestart]
            public bool NoColor { get; init; } = false;
        }

        /// <summary>
        ///     Diagnostics options (e.g. memory dump).
        /// </summary>
        public class DiagnosticsOptions
        {
            /// <summary>
            ///     Gets a value indicating whether the memory dump endpoint is allowed. When false, dump returns 404/403.
            /// </summary>
            [EnvironmentVariable("ALLOW_MEMORY_DUMP")]
            [Description("when true, allow memory dump endpoint; when false, dump returns 404/403")]
            [RequiresRestart]
            public bool AllowMemoryDump { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether the dump endpoint may be called from non-loopback. When false, only loopback is allowed.
            /// </summary>
            [EnvironmentVariable("ALLOW_REMOTE_DUMP")]
            [Description("when true, allow dump from remote IPs; when false, only loopback (127.0.0.1, ::1) is allowed")]
            [RequiresRestart]
            public bool AllowRemoteDump { get; init; } = false;
        }

        /// <summary>
        ///     Rescue mode options (underperformance detection and overlay backfill).
        /// </summary>
        public class RescueModeOptions
        {
            /// <summary>
            ///     Gets a value indicating whether rescue mode and underperformance detection are enabled.
            /// </summary>
            public bool Enabled { get; init; } = true;

            /// <summary>
            ///     Maximum time a download may remain queued before rescue is triggered, in seconds.
            /// </summary>
            [Range(60, 86400)]
            public int MaxQueueTimeSeconds { get; init; } = 1800;

            /// <summary>
            ///     Minimum throughput in KB/s below which an in-progress transfer is considered underperforming.
            /// </summary>
            [Range(1, 10000)]
            public int MinThroughputKBps { get; init; } = 10;

            /// <summary>
            ///     Minimum time an in-progress transfer must have been running before throughput is evaluated, in seconds.
            /// </summary>
            [Range(60, 3600)]
            public int MinDurationSeconds { get; init; } = 300;

            /// <summary>
            ///     Time with no progress in bytes before an in-progress transfer is considered stalled, in seconds.
            /// </summary>
            [Range(30, 600)]
            public int StalledTimeoutSeconds { get; init; } = 120;

            /// <summary>
            ///     Interval between underperformance check runs, in seconds.
            /// </summary>
            [Range(15, 300)]
            public int CheckIntervalSeconds { get; init; } = 45;
        }

        /// <summary>
        ///     Retention options.
        /// </summary>
        public class RetentionOptions
        {
            /// <summary>
            ///     Gets the time to retain searches, in minutes.
            /// </summary>
            [Argument(default, "retention-search")]
            [EnvironmentVariable("RETENTION_SEARCH")]
            [Description("time to retain completed search records, in minutes")]
            [Range(5, maximum: int.MaxValue)]
            public int? Search { get; init; } = null;

            /// <summary>
            ///     Gets the time to retain events, in days. Defaults to 30 days.
            /// </summary>
            [Argument(default, "retention-events")]
            [EnvironmentVariable("RETENTION_EVENTS")]
            [Description("time to retain event records, in days")]
            [Range(1, maximum: int.MaxValue)]
            public int Events { get; init; } = 30;

            /// <summary>
            ///     Gets the maximum number of event records to retain. Defaults to 10,000; zero disables the count limit.
            /// </summary>
            [Argument(default, "retention-events-max-count")]
            [EnvironmentVariable("RETENTION_EVENTS_MAX_COUNT")]
            [Description("maximum number of event records to retain (0 = no count limit)")]
            [Range(0, maximum: int.MaxValue)]
            public int EventsMaxCount { get; init; } = 10_000;

            /// <summary>
            ///     Gets transfer retention options.
            /// </summary>
            [Validate]
            public TransferRetentionOptions Transfers { get; init; } = new TransferRetentionOptions();

            /// <summary>
            ///     Gets file retention options.
            /// </summary>
            [Validate]
            public FileRetentionOptions Files { get; init; } = new FileRetentionOptions();

            /// <summary>
            ///     Gets the time to retain logs, in days.
            /// </summary>
            [Argument(default, "retention-logs")]
            [EnvironmentVariable("RETENTION_LOGS")]
            [Description("time to retain application logs, in days (minimum 2)")]
            [Range(2, maximum: int.MaxValue)]
            public int Logs { get; init; } = 14;

            /// <summary>
            ///     Transfer retention options.
            /// </summary>
            public class TransferRetentionOptions
            {
                /// <summary>
                ///     Gets the time to retain soft-removed, completed transfers, in minutes. Defaults to seven days.
                /// </summary>
                [Argument(default, "retention-transfers-removed")]
                [EnvironmentVariable("RETENTION_TRANSFERS_REMOVED")]
                [Description("time to retain soft-removed transfers, in minutes")]
                [Range(5, maximum: int.MaxValue)]
                public int? Removed { get; init; } = 10_080;

                /// <summary>
                ///     Gets upload retention options.
                /// </summary>
                [Validate]
                public UploadTransferRetentionOptions Upload { get; init; } = new UploadTransferRetentionOptions();

                /// <summary>
                ///     Gets download retention options.
                /// </summary>
                [Validate]
                public DownloadTransferRetentionOptions Download { get; init; } = new DownloadTransferRetentionOptions();

                /// <summary>
                ///     Upload retention options.
                /// </summary>
                public class UploadTransferRetentionOptions
                {
                    /// <summary>
                    ///     Gets the time to retain successful transfers, in minutes.
                    /// </summary>
                    [Argument(default, "retention-transfers-upload-succeeded")]
                    [EnvironmentVariable("RETENTION_TRANSFERS_UPLOAD_SUCCEEDED")]
                    [Description("time to retain succeeded uploads, in minutes")]
                    [Range(5, maximum: int.MaxValue)]
                    public int? Succeeded { get; init; } = null;

                    /// <summary>
                    ///     Gets the time to retain errored transfers, in minutes.
                    /// </summary>
                    [Argument(default, "retention-transfers-upload-errored")]
                    [EnvironmentVariable("RETENTION_TRANSFERS_UPLOAD_ERRORED")]
                    [Description("time to retain errored uploads, in minutes")]
                    [Range(5, maximum: int.MaxValue)]
                    public int? Errored { get; init; } = null;

                    /// <summary>
                    ///     Gets the time to retain cancelled transfers, in minutes.
                    /// </summary>
                    [Argument(default, "retention-transfers-upload-cancelled")]
                    [EnvironmentVariable("RETENTION_TRANSFERS_UPLOAD_CANCELLED")]
                    [Description("time to retain cancelled uploads, in minutes")]
                    [Range(5, maximum: int.MaxValue)]
                    public int? Cancelled { get; init; } = null;
                }

                /// <summary>
                ///     Download retention options.
                /// </summary>
                public class DownloadTransferRetentionOptions
                {
                    /// <summary>
                    ///     Gets the time to retain successful transfers, in minutes.
                    /// </summary>
                    [Argument(default, "retention-transfers-download-succeeded")]
                    [EnvironmentVariable("RETENTION_TRANSFERS_DOWNLOAD_SUCCEEDED")]
                    [Description("time to retain succeeded downloads, in minutes")]
                    [Range(5, maximum: int.MaxValue)]
                    public int? Succeeded { get; init; } = null;

                    /// <summary>
                    ///     Gets the time to retain errored transfers, in minutes.
                    /// </summary>
                    [Argument(default, "retention-transfers-download-errored")]
                    [EnvironmentVariable("RETENTION_TRANSFERS_DOWNLOAD_ERRORED")]
                    [Description("time to retain errored downloads, in minutes")]
                    [Range(5, maximum: int.MaxValue)]
                    public int? Errored { get; init; } = null;

                    /// <summary>
                    ///     Gets the time to retain cancelled transfers, in minutes.
                    /// </summary>
                    [Argument(default, "retention-transfers-download-cancelled")]
                    [EnvironmentVariable("RETENTION_TRANSFERS_DOWNLOAD_CANCELLED")]
                    [Description("time to retain cancelled downloads, in minutes")]
                    [Range(5, maximum: int.MaxValue)]
                    public int? Cancelled { get; init; } = null;
                }
            }

            /// <summary>
            ///     File retention options.
            /// </summary>
            public class FileRetentionOptions
            {
                /// <summary>
                ///     Gets the time to retain completed files, in minutes.
                /// </summary>
                [Argument(default, "retention-files-complete")]
                [EnvironmentVariable("RETENTION_FILES_COMPLETE")]
                [Description("time to retain completed files, in minutes")]
                [Range(30, maximum: int.MaxValue)]
                public int? Complete { get; init; } = null;

                /// <summary>
                ///     Gets the time to retain incomplete files, in minutes.
                /// </summary>
                [Argument(default, "retention-files-incomplete")]
                [EnvironmentVariable("RETENTION_FILES_INCOMPLETE")]
                [Description("time to retain incomplete files, in minutes")]
                [Range(30, maximum: int.MaxValue)]
                public int? Incomplete { get; init; } = null;
            }
        }

        /// <summary>
        ///     Metrics options.
        /// </summary>
        public class MetricsOptions : IValidatableObject
        {
            /// <summary>
            ///     Gets a value indicating whether the metrics endpoint should be enabled.
            /// </summary>
            [Argument(default, "metrics")]
            [EnvironmentVariable("METRICS")]
            [Description("enable metrics")]
            [RequiresRestart]
            public bool Enabled { get; init; } = false;

            /// <summary>
            ///     Gets the url for the metrics endpoint.
            /// </summary>
            [Argument(default, "metrics-url")]
            [EnvironmentVariable("METRICS_URL")]
            [Description("url for metrics")]
            [RequiresRestart]
            public string Url { get; init; } = "/metrics";

            /// <summary>
            ///     Gets metrics endpoint authentication options.
            /// </summary>
            [Validate]
            public MetricsAuthenticationOptions Authentication { get; init; } = new MetricsAuthenticationOptions();

            public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
            {
                var results = new List<ValidationResult>();

                if (!Enabled || Authentication.Disabled)
                {
                    return results;
                }

                if (string.IsNullOrWhiteSpace(Authentication.Username))
                {
                    results.Add(new ValidationResult(
                        "Metrics authentication username must be configured when metrics auth is enabled.",
                        [nameof(Authentication.Username)]));
                }
                else if (Authentication.Username.Length > 255)
                {
                    results.Add(new ValidationResult(
                        "Metrics authentication username must be 255 characters or fewer.",
                        [nameof(Authentication.Username)]));
                }

                if (string.IsNullOrWhiteSpace(Authentication.Password))
                {
                    results.Add(new ValidationResult(
                        "Metrics authentication password must be configured when metrics auth is enabled.",
                        [nameof(Authentication.Password)]));
                }
                else if (Authentication.Password.Length > 255)
                {
                    results.Add(new ValidationResult(
                        "Metrics authentication password must be 255 characters or fewer.",
                        [nameof(Authentication.Password)]));
                }

                return results;
            }

            /// <summary>
            ///     Metrics endpoint authentication options.
            /// </summary>
            public class MetricsAuthenticationOptions
            {
                /// <summary>
                ///     Gets a value indicating whether authentication should be disabled.
                /// </summary>
                [Argument(default, "metrics-no-auth")]
                [EnvironmentVariable("METRICS_NO_AUTH")]
                [Description("disable authentication for metrics requests")]
                [RequiresRestart]
                public bool Disabled { get; init; } = false;

                /// <summary>
                ///     Gets the username for the metrics endpoint.
                /// </summary>
                [Argument(default, "metrics-username")]
                [EnvironmentVariable("METRICS_USERNAME")]
                [Description("username for metrics")]
                [RequiresRestart]
                public string Username { get; init; } = Program.AppName;

                /// <summary>
                ///     Gets the password for the metrics endpoint.
                /// </summary>
                [Argument(default, "metrics-password")]
                [EnvironmentVariable("METRICS_PASSWORD")]
                [Description("password for metrics")]
                [Secret]
                [RequiresRestart]
                public string Password { get; init; } = string.Empty; // must be set explicitly; empty default forces configuration
            }
        }

        /// <summary>
        ///     Soulseek client options.
        /// </summary>
        public class SoulseekOptions
        {
            /// <summary>
            ///     Gets the address of the Soulseek server.
            /// </summary>
            [Argument(default, "slsk-address")]
            [EnvironmentVariable("SLSK_ADDRESS")]
            [Description("address of the Soulseek server")]
            [RequiresReconnect]
            public string Address { get; init; } = "vps.slsknet.org";

            /// <summary>
            ///     Gets the port of the Soulseek server.
            /// </summary>
            [Argument(default, "slsk-port")]
            [EnvironmentVariable("SLSK_PORT")]
            [Description("port of the Soulseek server")]
            [RequiresReconnect]
            [Range(1024, 65535)]
            public int Port { get; init; } = 2271;

            /// <summary>
            ///     Gets the username for the Soulseek network.
            /// </summary>
            [Argument(default, "slsk-username")]
            [EnvironmentVariable("SLSK_USERNAME")]
            [Description("username for the Soulseek network")]
            [RequiresReconnect]
            public string Username { get; init; } = string.Empty;

            /// <summary>
            ///     Gets the password for the Soulseek network.
            /// </summary>
            [Argument(default, "slsk-password")]
            [EnvironmentVariable("SLSK_PASSWORD")]
            [Description("password for the Soulseek network")]
            [Secret]
            [RequiresReconnect]
            public string Password { get; init; } = string.Empty;

            /// <summary>
            ///     Gets the description of the Soulseek user.
            /// </summary>
            [Argument(default, "slsk-description")]
            [EnvironmentVariable("SLSK_DESCRIPTION")]
            [Description("user description for the Soulseek network")]
            public string Description { get; init; } = "A slskdN user. Unofficial fork of slskd: https://github.com/snapetech/slskdn";

            /// <summary>
            ///     Gets the file path for the user's profile picture.
            /// </summary>
            [Argument(default, "slsk-picture")]
            [EnvironmentVariable("SLSK_PICTURE")]
            [Description("user picture for the Soulseek network")]
            [FileExists(FileAccess.Read)]
            public string Picture { get; init; } = string.Empty;

            /// <summary>
            ///     Gets the native Soulseek interests to publish as likes after login.
            /// </summary>
            [Argument(default, "slsk-liked-interests")]
            [EnvironmentVariable("SLSK_LIKED_INTERESTS")]
            [Description("native Soulseek interests to publish as likes after login")]
            public string[] LikedInterests { get; init; } = Array.Empty<string>();

            /// <summary>
            ///     Gets the native Soulseek interests to publish as dislikes after login.
            /// </summary>
            [Argument(default, "slsk-hated-interests")]
            [EnvironmentVariable("SLSK_HATED_INTERESTS")]
            [Description("native Soulseek interests to publish as dislikes after login")]
            public string[] HatedInterests { get; init; } = Array.Empty<string>();

            /// <summary>
            ///     Gets the local IP address on which to listen for incoming connections.
            /// </summary>
            [Argument(default, "slsk-listen-ip-address")]
            [EnvironmentVariable("SLSK_LISTEN_IP_ADDRESS")]
            [Description("local IP address on which to listen for incoming connections")]
            [IPAddress]
            public string ListenIpAddress { get; init; } = "0.0.0.0";

            /// <summary>
            ///     Gets the port on which to listen for incoming connections.
            /// </summary>
            [Argument(default, "slsk-listen-port")]
            [EnvironmentVariable("SLSK_LISTEN_PORT")]
            [Description("port on which to listen for incoming connections")]
            [Range(1024, 65535)]
            public int ListenPort { get; init; } = 50300;

            /// <summary>
            ///     Gets Soulseek type-1 peer/distributed/transfer obfuscation options.
            /// </summary>
            [Validate]
            public ObfuscationOptions Obfuscation { get; init; } = new ObfuscationOptions();

            /// <summary>
            ///     Gets private-message auto response options.
            /// </summary>
            [Validate]
            public PrivateMessageAutoResponseOptions PrivateMessageAutoResponse { get; init; } = new PrivateMessageAutoResponseOptions();

            /// <summary>
            ///     Gets the minimum diagnostic level.
            /// </summary>
            [Argument(default, "slsk-diag-level")]
            [EnvironmentVariable("SLSK_DIAG_LEVEL")]
            [Description("minimum diagnostic level (None, Warning, Info, Debug)")]
            [Enum(typeof(SoulseekDiagnostics.DiagnosticLevel))]
            [RequiresRestart]
            public string DiagnosticLevel { get; init; } = SoulseekDiagnostics.DiagnosticLevel.Info.ToString().ToLowerInvariant();

            /// <summary>
            ///     Gets options for the distributed network.
            /// </summary>
            [Validate]
            public DistributedNetworkOptions DistributedNetwork { get; init; } = new DistributedNetworkOptions();

            /// <summary>
            ///     Gets connection options.
            /// </summary>
            [Validate]
            public ConnectionOptions Connection { get; init; } = new ConnectionOptions();

            /// <summary>
            ///     Gets safety cap options for Soulseek activity (H-08).
            /// </summary>
            [Validate]
            public SafetyOptions Safety { get; init; } = new SafetyOptions();

            /// <summary>
            ///     Private-message auto response options.
            /// </summary>
            public class PrivateMessageAutoResponseOptions
            {
                /// <summary>
                ///     Gets a value indicating whether recognized gatekeeping private messages should receive an automatic response.
                /// </summary>
                [Argument(default, "slsk-private-message-auto-response")]
                [EnvironmentVariable("SLSK_PRIVATE_MESSAGE_AUTO_RESPONSE")]
                [Description("automatically reply to private messages that look like human-check or share-gate prompts")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the response sent to matching human-check private messages.
                /// </summary>
                [Argument(default, "slsk-private-message-auto-response-message")]
                [EnvironmentVariable("SLSK_PRIVATE_MESSAGE_AUTO_RESPONSE_MESSAGE")]
                [Description("response sent to recognized gatekeeping private messages")]
                public string Message { get; init; } = "Hi, I'm human and testing a slskdN client. Shares may be temporarily unavailable while I validate the client.";

                /// <summary>
                ///     Gets the minimum minutes between automatic responses to the same user.
                /// </summary>
                [Argument(default, "slsk-private-message-auto-response-cooldown-minutes")]
                [EnvironmentVariable("SLSK_PRIVATE_MESSAGE_AUTO_RESPONSE_COOLDOWN_MINUTES")]
                [Description("minimum minutes between automatic private-message responses to the same user")]
                [Range(1, 1440)]
                public int CooldownMinutes { get; init; } = 360;
            }

            /// <summary>
            ///     Soulseek type-1 peer/distributed/transfer obfuscation options.
            /// </summary>
            public class ObfuscationOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether type-1 peer/distributed/transfer obfuscation is enabled.
                /// </summary>
                [Argument(default, "slsk-obfuscation")]
                [EnvironmentVariable("SLSK_OBFUSCATION")]
                [Description("enable Soulseek type-1 peer/distributed/transfer obfuscation options")]
                [RequiresReconnect]
                public bool Enabled { get; init; } = true;

                /// <summary>
                ///     Gets the obfuscation posture.
                /// </summary>
                [Argument(default, "slsk-obfuscation-mode")]
                [EnvironmentVariable("SLSK_OBFUSCATION_MODE")]
                [Description("Soulseek type-1 obfuscation posture (Compatibility, Prefer, Only)")]
                [Enum(typeof(SoulseekObfuscationMode))]
                [RequiresReconnect]
                public string Mode { get; init; } = SoulseekObfuscationMode.Compatibility.ToString().ToLowerInvariant();

                /// <summary>
                ///     Gets the dedicated type-1 obfuscated peer/distributed/transfer listen port.
                /// </summary>
                [Argument(default, "slsk-obfuscation-listen-port")]
                [EnvironmentVariable("SLSK_OBFUSCATION_LISTEN_PORT")]
                [Description("dedicated type-1 obfuscated peer/distributed/transfer listen port (0 = share the regular listen port; plain and obfuscated connections are distinguished per-connection)")]
                [Range(0, 65535)]
                [RequiresReconnect]
                public int ListenPort { get; init; } = 0;

                /// <summary>
                ///     Gets a value indicating whether to advertise the regular peer/distributed/transfer port alongside obfuscation metadata.
                /// </summary>
                [Argument(default, "slsk-obfuscation-advertise-regular-port")]
                [EnvironmentVariable("SLSK_OBFUSCATION_ADVERTISE_REGULAR_PORT")]
                [Description("advertise the regular peer/distributed/transfer port alongside type-1 obfuscation metadata")]
                [RequiresReconnect]
                public bool AdvertiseRegularPort { get; init; } = true;

                /// <summary>
                ///     Gets a value indicating whether prefer mode should choose compatible obfuscated metadata before regular outbound dials.
                /// </summary>
                [Argument(default, "slsk-obfuscation-prefer-outbound")]
                [EnvironmentVariable("SLSK_OBFUSCATION_PREFER_OUTBOUND")]
                [Description("in prefer mode, choose type-1 obfuscated outbound peer/distributed/transfer connections when peer metadata supports them")]
                [RequiresReconnect]
                public bool PreferOutbound { get; init; } = true;

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    if (!System.Enum.TryParse<SoulseekObfuscationMode>(Mode, ignoreCase: true, out var mode))
                    {
                        results.Add(new ValidationResult(
                            "Soulseek obfuscation mode must be one of Compatibility, Prefer, or Only.",
                            [nameof(Mode)]));

                        return results;
                    }

                    if (ListenPort is > 0 and < 1024)
                    {
                        results.Add(new ValidationResult(
                            "Soulseek obfuscation listen port must be 0 or a non-privileged port between 1024 and 65535.",
                            [nameof(ListenPort)]));
                    }

                    if (Enabled && !AdvertiseRegularPort)
                    {
                        results.Add(new ValidationResult(
                            "Soulseek obfuscation requires the regular peer port to remain advertised for legacy compatibility.",
                            [nameof(AdvertiseRegularPort)]));
                    }

                    if (Enabled && mode == SoulseekObfuscationMode.Only)
                    {
                        results.Add(new ValidationResult(
                            "Soulseek obfuscation only mode is not currently supported because the runtime keeps regular Soulseek fallback for legacy compatibility.",
                            [nameof(Mode)]));
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Connection options.
            /// </summary>
            public class ConnectionOptions
            {
                /// <summary>
                ///     Gets an optional path MTU cap for the Soulseek server TCP connection. Null uses the operating system default.
                /// </summary>
                [Argument(default, "slsk-connection-mtu")]
                [EnvironmentVariable("SLSK_CONNECTION_MTU")]
                [Description("optional MTU cap for the Soulseek server TCP connection")]
                [Range(1280, 9000)]
                public int? Mtu { get; init; }

                /// <summary>
                ///     Gets connection timeout options.
                /// </summary>
                [Validate]
                public TimeoutOptions Timeout { get; init; } = new TimeoutOptions();

                /// <summary>
                ///     Gets connection buffer options.
                /// </summary>
                [Validate]
                public BufferOptions Buffer { get; init; } = new BufferOptions();

                /// <summary>
                ///     Gets connection proxy options.
                /// </summary>
                [Validate]
                public ProxyOptions Proxy { get; init; } = new ProxyOptions();

                /// <summary>
                ///     Connection buffer options.
                /// </summary>
                public class BufferOptions
                {
                    /// <summary>
                    ///     Gets the connection read buffer size, in bytes.
                    /// </summary>
                    [Argument(default, "slsk-read-buffer")]
                    [EnvironmentVariable("SLSK_READ_BUFFER")]
                    [Description("read buffer size for connections")]
                    [Range(1024, int.MaxValue)]
                    public int Read { get; init; } = 16384;

                    /// <summary>
                    ///     Gets the connection write buffer size, in bytes.
                    /// </summary>
                    [Argument(default, "slsk-write-buffer")]
                    [EnvironmentVariable("SLSK_WRITE_BUFFER")]
                    [Description("write buffer size for connections")]
                    [Range(1024, int.MaxValue)]
                    public int Write { get; init; } = 16384;

                    /// <summary>
                    ///     Gets the read/write buffer size for transfers, in bytes.
                    /// </summary>
                    [Argument(default, "slsk-transfer-buffer")]
                    [EnvironmentVariable("SLSK_TRANSFER_BUFFER")]
                    [Description("read/write buffer size for transfers")]
                    [Range(81920, int.MaxValue)]
                    public int Transfer { get; init; } = 262144;

                    /// <summary>
                    ///     Gets the size of the queue for double buffered writes.
                    /// </summary>
                    [Argument(default, "slsk-write-queue")]
                    [EnvironmentVariable("SLSK_WRITE_QUEUE")]
                    [Description("queue size for double buffered writes")]
                    [Range(5, 5000)]
                    public int WriteQueue { get; init; } = 50;
                }

                /// <summary>
                ///     Connection timeout options.
                /// </summary>
                public class TimeoutOptions
                {
                    /// <summary>
                    ///     Gets the connection timeout value, in milliseconds.
                    /// </summary>
                    [Argument(default, "slsk-connection-timeout")]
                    [EnvironmentVariable("SLSK_CONNECTION_TIMEOUT")]
                    [Description("connection timeout, in milliseconds")]
                    [Range(1000, int.MaxValue)]
                    public int Connect { get; init; } = 10000;

                    /// <summary>
                    ///     Gets the connection inactivity timeout, in milliseconds.
                    /// </summary>
                    [Argument(default, "slsk-inactivity-timeout")]
                    [EnvironmentVariable("SLSK_INACTIVITY_TIMEOUT")]
                    [Description("connection inactivity timeout, in milliseconds")]
                    [Range(1000, int.MaxValue)]
                    public int Inactivity { get; init; } = 60000;

                    /// <summary>
                    ///     Gets the transfer connection timeout, in milliseconds.
                    /// </summary>
                    [Argument(default, "slsk-transfer-timeout")]
                    [EnvironmentVariable("SLSK_TRANSFER_TIMEOUT")]
                    [Description("transfer connection timeout, in milliseconds")]
                    [Range(30_000, int.MaxValue)]
                    public int Transfer { get; init; } = 60000;
                }

                /// <summary>
                ///     Connection proxy options.
                /// </summary>
                public class ProxyOptions : IValidatableObject
                {
                    /// <summary>
                    ///     Gets a value indicating whether the proxy is enabled.
                    /// </summary>
                    [Argument(default, "slsk-proxy")]
                    [EnvironmentVariable("SLSK_PROXY_ENABLED")]
                    [Description("enable connection proxy")]
                    public bool Enabled { get; init; } = false;

                    /// <summary>
                    ///     Gets the proxy address.
                    /// </summary>
                    [Argument(default, "slsk-proxy-address")]
                    [EnvironmentVariable("SLSK_PROXY_ADDRESS")]
                    [Description("connection proxy address")]
                    public string Address { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the proxy port.
                    /// </summary>
                    [Argument(default, "slsk-proxy-port")]
                    [EnvironmentVariable("SLSK_PROXY_PORT")]
                    [Description("connection proxy port")]
                    [Range(1, 65535)]
                    public int? Port { get; init; }

                    /// <summary>
                    ///     Gets the proxy username, if applicable.
                    /// </summary>
                    [Argument(default, "slsk-proxy-username")]
                    [EnvironmentVariable("SLSK_PROXY_USERNAME")]
                    [Description("connection proxy username")]
                    public string Username { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the proxy password, if applicable.
                    /// </summary>
                    [Argument(default, "slsk-proxy-password")]
                    [EnvironmentVariable("SLSK_PROXY_PASSWORD")]
                    [Description("connection proxy password")]
                    [Secret]
                    public string Password { get; init; } = string.Empty;

                    /// <summary>
                    ///     Extended validation.
                    /// </summary>
                    /// <param name="validationContext"></param>
                    /// <returns></returns>
                    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                    {
                        var results = new List<ValidationResult>();

                        if (Enabled && string.IsNullOrWhiteSpace(Address))
                        {
                            results.Add(new ValidationResult($"The Enabled field is true, but no Address has been specified."));
                        }
                        else if (!string.IsNullOrWhiteSpace(Address) && Address.Length > 255)
                        {
                            results.Add(new ValidationResult("The field Address must be a string with a maximum length of 255."));
                        }

                        if (Enabled && !Port.HasValue)
                        {
                            results.Add(new ValidationResult($"The Enabled field is true, but no Port has been specified."));
                        }

                        if (!string.IsNullOrWhiteSpace(Username) && Username.Length > 255)
                        {
                            results.Add(new ValidationResult("The field Username must be a string with a maximum length of 255."));
                        }

                        if (!string.IsNullOrWhiteSpace(Password) && Password.Length > 255)
                        {
                            results.Add(new ValidationResult("The field Password must be a string with a maximum length of 255."));
                        }

                        return results;
                    }
                }
            }

            /// <summary>
            ///     Safety cap options (H-08: Soulseek-Specific Safety Caps).
            /// </summary>
            public class SafetyOptions
            {
                /// <summary>
                ///     Gets the maximum number of searches per minute.
                /// </summary>
                [Argument(default, "slsk-safety-max-searches-per-minute")]
                [EnvironmentVariable("SLSK_SAFETY_MAX_SEARCHES_PER_MINUTE")]
                [Description("maximum Soulseek searches per minute (0 = unlimited)")]
                [Range(0, 1000)]
                public int MaxSearchesPerMinute { get; init; } = 10;

                /// <summary>
                ///     Gets the maximum number of browse requests per minute.
                /// </summary>
                [Argument(default, "slsk-safety-max-browses-per-minute")]
                [EnvironmentVariable("SLSK_SAFETY_MAX_BROWSES_PER_MINUTE")]
                [Description("maximum Soulseek browse requests per minute (0 = unlimited)")]
                [Range(0, 100)]
                public int MaxBrowsesPerMinute { get; init; } = 5;

                /// <summary>
                ///     Gets the maximum number of download slots to use.
                /// </summary>
                [Argument(default, "slsk-safety-max-download-slots")]
                [EnvironmentVariable("SLSK_SAFETY_MAX_DOWNLOAD_SLOTS")]
                [Description("maximum concurrent Soulseek download slots (0 = unlimited)")]
                [Range(0, 1000)]
                public int MaxDownloadSlotsUsed { get; init; } = 50;

                /// <summary>
                ///     Gets the maximum number of concurrent swarm (multi-source) connections per download.
                ///     Each swarm source opens a Soulseek peer connection; uncapped this can exhaust router
                ///     connection tables on high-source-count downloads. Default 10. Set 0 to disable.
                /// </summary>
                [Argument(default, "slsk-safety-max-swarm-connections")]
                [EnvironmentVariable("SLSK_SAFETY_MAX_SWARM_CONNECTIONS")]
                [Description("maximum concurrent swarm connections per download (0 = unlimited)")]
                [Range(0, 500)]
                public int MaxConcurrentSwarmConnections { get; init; } = 10;

                /// <summary>
                ///     Gets a value indicating whether safety caps are enabled.
                /// </summary>
                [Argument(default, "slsk-safety-enabled")]
                [EnvironmentVariable("SLSK_SAFETY_ENABLED")]
                [Description("enable Soulseek safety caps")]
                public bool Enabled { get; init; } = true;
            }

            /// <summary>
            ///     Distributed network options.
            /// </summary>
            public class DistributedNetworkOptions
            {
                /// <summary>
                ///     Gets a value indicating whether the distributed network should be disabled.
                /// </summary>
                [Argument(default, "slsk-no-dnet")]
                [EnvironmentVariable("SLSK_NO_DNET")]
                [Description("disable the distributed network")]
                public bool Disabled { get; init; } = false;

                /// <summary>
                ///     Gets a value indicating whether to accept distributed child connections.
                /// </summary>
                [Argument(default, "slsk-dnet-no-children")]
                [EnvironmentVariable("SLSK_DNET_NO_CHILDREN")]
                [Description("do not accept distributed children")]
                public bool DisableChildren { get; init; } = false;

                /// <summary>
                ///     Gets the distributed child connection limit.
                /// </summary>
                [Argument(default, "slsk-dnet-children")]
                [EnvironmentVariable("SLSK_DNET_CHILDREN")]
                [Description("max number of distributed children")]
                [Range(1, int.MaxValue)]
                public int ChildLimit { get; init; } = 25;

                /// <summary>
                ///     Gets a value indicating whether distributed network logging should be enabled.
                /// </summary>
                [Argument(default, "slsk-dnet-logging")]
                [EnvironmentVariable("SLSK_DNET_LOGGING")]
                [Description("enable distributed network logging")]
                public bool Logging { get; init; } = false;
            }
        }

        /// <summary>
        ///     Web server options.
        /// </summary>
        public class WebOptions
        {
            /// <summary>
            ///     Gets the HTTP listen port.
            /// </summary>
            [Argument('l', "http-port")]
            [EnvironmentVariable("HTTP_PORT")]
            [Description("HTTP listen port for web UI")]
            [Range(1, 65535)]
            [RequiresRestart]
            public int Port { get; init; } = 5030;

            /// <summary>
            ///     Gets the HTTP listen address. Use "*" for all interfaces, "127.0.0.1" for localhost only.
            /// </summary>
            [Argument(default, "http-address")]
            [EnvironmentVariable("HTTP_ADDRESS")]
            [Description("HTTP listen address for web UI (* for all interfaces, 127.0.0.1 for localhost)")]
            [RequiresRestart]
            public string Address { get; init; } = "127.0.0.1";

            /// <summary>
            ///     Gets the HTTP listen unix domain socket (UDS) path.
            /// </summary>
            [Argument(default, "http-socket")]
            [EnvironmentVariable("HTTP_SOCKET")]
            [Description("HTTP listen unix domain socket (UDS) path for web UI")]
            [AbsoluteFilePath]
            [RequiresRestart]
            public string Socket { get; init; } = string.Empty;

            /// <summary>
            ///     Gets HTTPS options.
            /// </summary>
            [Validate]
            [RequiresRestart]
            public HttpsOptions Https { get; init; } = new HttpsOptions();

            /// <summary>
            ///     Gets the base url for web requests.
            /// </summary>
            [Argument(default, "url-base")]
            [EnvironmentVariable("URL_BASE")]
            [Description("base url for web requests")]
            [RequiresRestart]
            public string UrlBase { get; init; } = "/";

            /// <summary>
            ///     Gets the path to static web content.
            /// </summary>
            [Argument(default, "content-path")]
            [EnvironmentVariable("CONTENT_PATH")]
            [Description("path to static web content")]
            [StringLength(255, MinimumLength = 1)]
            [DirectoryExists(relativeToApplicationDirectory: true)]
            [RequiresRestart]
            public string ContentPath { get; init; } = "wwwroot";

            /// <summary>
            ///     Gets a value indicating whether HTTP request logging should be enabled.
            /// </summary>
            [Argument(default, "http-logging")]
            [EnvironmentVariable("HTTP_LOGGING")]
            [Description("enable http request logging")]
            [RequiresRestart]
            public bool Logging { get; init; } = false;

            /// <summary>
            ///     Gets authentication options.
            /// </summary>
            [Validate]
            public WebAuthenticationOptions Authentication { get; init; } = new WebAuthenticationOptions();

            /// <summary>
            ///     Gets a value indicating whether to enforce strict security checks at startup (fail-fast on dangerous configs).
            /// </summary>
            [Argument(default, "enforce-security")]
            [EnvironmentVariable("ENFORCE_SECURITY")]
            [Description("when true, refuse to start if auth disabled + non-loopback, CORS credentials+wildcard, or memory dump+no-auth")]
            [RequiresRestart]
            public bool EnforceSecurity { get; init; } = false;

            /// <summary>
            ///     Gets a value indicating whether to allow remote (non-loopback) access when authentication is disabled.
            /// </summary>
            [Argument(default, "allow-remote-no-auth")]
            [EnvironmentVariable("ALLOW_REMOTE_NO_AUTH")]
            [Description("when true, allow no-auth from non-loopback; when false, passthrough is loopback-only")]
            [RequiresRestart]
            public bool AllowRemoteNoAuth { get; init; } = false;

            /// <summary>
            ///     Kestrel max request body size in bytes (PR-09). Default 10 MB. Used for Limits.MaxRequestBodySize.
            /// </summary>
            [Description("Kestrel max request body size in bytes; default 10485760 (10 MB)")]
            [Range(1, int.MaxValue)]
            [RequiresRestart]
            public long MaxRequestBodySize { get; init; } = 10 * 1024 * 1024;

            /// <summary>
            ///     Gets CORS options. When Cors.Enabled is false, CORS middleware is not applied (no CORS headers).
            /// </summary>
            public CorsOptions Cors { get; init; } = new CorsOptions();

            /// <summary>
            ///     CORS options.
            /// </summary>
            public class CorsOptions
            {
                /// <summary>
                ///     Gets a value indicating whether CORS is enabled. When false, app.UseCors is not called (no CORS headers).
                /// </summary>
                [Description("when true, use AllowedOrigins and AllowCredentials; when false, no CORS middleware")]
                [RequiresRestart]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets a value indicating whether to allow credentials in CORS. When true, AllowedOrigins must not be wildcard/any when EnforceSecurity.
                /// </summary>
                [Description("allow credentials; when true with EnforceSecurity, AllowedOrigins must be an explicit allowlist")]
                [RequiresRestart]
                public bool AllowCredentials { get; init; } = false;

                /// <summary>
                ///     Gets the allowed origins. Null, empty, or '*' is treated as any. When AllowCredentials is true and EnforceSecurity, any/wildcard is invalid.
                /// </summary>
                [Description("allowed CORS origins; when Cors.Enabled and AllowCredentials, must be explicit (no wildcard) when EnforceSecurity")]
                [RequiresRestart]
                public string[] AllowedOrigins { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets the allowed headers. Empty or null = any (AllowAnyHeader).
                /// </summary>
                [Description("allowed CORS headers; empty = any")]
                [RequiresRestart]
                public string[] AllowedHeaders { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets the allowed methods. Empty or null = any (AllowAnyMethod).
                /// </summary>
                [Description("allowed CORS methods; empty = any")]
                [RequiresRestart]
                public string[] AllowedMethods { get; init; } = Array.Empty<string>();
            }

            /// <summary>
            ///     HTTP rate limiting options (PR-09). When Enabled, applies policies: Api (generous), FederationInbox (tighter), MeshGateway (tighter).
            /// </summary>
            [Description("HTTP rate limiting; when enabled, applies policies per path (api, federation inbox, mesh gateway)")]
            public RateLimitingOptions RateLimiting { get; init; } = new RateLimitingOptions();

            /// <summary>
            ///     Rate limiting policy limits.
            /// </summary>
            public class RateLimitingOptions
            {
                /// <summary>When true, apply ASP.NET Core rate limiter with Api, FederationInbox, and MeshGateway policies. When false, no 429 from this layer.</summary>
                [Description("enable HTTP rate limiting (policies: api, federation inbox, mesh gateway)")]
                public bool Enabled { get; init; } = true;

                /// <summary>Default API: requests per window (generous).</summary>
                [Description("api policy: permit count per window")]
                public int ApiPermitLimit { get; init; } = 200;

                /// <summary>Default API: window in seconds.</summary>
                [Description("api policy: window seconds")]
                public int ApiWindowSeconds { get; init; } = 60;

                /// <summary>Federation inbox (POST /actors/*/inbox): requests per window (tighter).</summary>
                [Description("federation inbox policy: permit count per window")]
                public int FederationPermitLimit { get; init; } = 30;

                /// <summary>Federation inbox: window in seconds.</summary>
                [Description("federation inbox policy: window seconds")]
                public int FederationWindowSeconds { get; init; } = 60;

                /// <summary>Mesh gateway (/mesh/*): requests per window (tighter).</summary>
                [Description("mesh gateway policy: permit count per window")]
                public int MeshGatewayPermitLimit { get; init; } = 60;

                /// <summary>Mesh gateway: window in seconds.</summary>
                [Description("mesh gateway policy: window seconds")]
                public int MeshGatewayWindowSeconds { get; init; } = 60;
            }

            /// <summary>
            ///     Authentication options.
            /// </summary>
            public class WebAuthenticationOptions
            {
                /// <summary>
                ///     Gets a value indicating whether authentication should be disabled.
                /// </summary>
                [Argument('X', "no-auth")]
                [EnvironmentVariable("NO_AUTH")]
                [Description("disable authentication for web requests")]
                [RequiresRestart]
                public bool Disabled { get; init; } = false;

                /// <summary>
                ///     Gets the username for the web UI.
                /// </summary>
                [Argument('u', "username")]
                [EnvironmentVariable("USERNAME")]
                [Description("username for web UI")]
                [StringLength(255, MinimumLength = 1)]
                public string Username { get; init; } = Program.AppName;

                /// <summary>
                ///     Gets the password for the web UI.
                /// </summary>
                [Argument('p', "password")]
                [EnvironmentVariable("PASSWORD")]
                [Description("password for web UI")]
                [StringLength(255, MinimumLength = 1)]
                [Secret]
                public string Password { get; init; } = Program.AppName;

                /// <summary>
                ///     Gets JWT options.
                /// </summary>
                [Validate]
                [RequiresRestart]
                public JwtOptions Jwt { get; init; } = new JwtOptions();

                /// <summary>
                ///     Gets API keys.
                /// </summary>
                [Validate]
                public Dictionary<string, ApiKeyOptions> ApiKeys { get; init; } = new Dictionary<string, ApiKeyOptions>();

                /// <summary>
                ///     Passthrough (no-auth) options. When auth is disabled, AllowedCidrs can allow specific non-loopback networks in addition to loopback (PR-03).
                /// </summary>
                [Description("passthrough no-auth: allowed_cidrs e.g. 127.0.0.1/32,::1/128 for explicit allowlist in addition to loopback")]
                public PassthroughOptions Passthrough { get; init; } = new PassthroughOptions();

                /// <summary>
                ///     JWT options.
                /// </summary>
                public class JwtOptions
                {
                    /// <summary>
                    ///     Gets the key with which to sign JWTs.
                    /// </summary>
                    [Argument(default, "jwt-key")]
                    [EnvironmentVariable("JWT_KEY")]
                    [Description("JWT signing key")]
                    [StringLength(255, MinimumLength = 32)]
                    [Secret]
                    [RequiresRestart]
                    public string Key { get; init; } = Cryptography.Random.GetBytes(32).ToBase62();

                    /// <summary>
                    ///     Gets the TTL for JWTs, in milliseconds.
                    /// </summary>
                    [Argument(default, "jwt-ttl")]
                    [EnvironmentVariable("JWT_TTL")]
                    [Description("TTL for JWTs")]
                    [Range(3600, int.MaxValue)]
                    [RequiresRestart]
                    public int Ttl { get; init; } = 3600000; // default 1 hour (was 7 days)
                }

                /// <summary>
                ///     API key options.
                /// </summary>
                public class ApiKeyOptions : IValidatableObject
                {
                    /// <summary>
                    ///     Gets the API key value.
                    /// </summary>
                    [Description("API key value")]
                    [StringLength(255, MinimumLength = 16)]
                    [Secret]
                    public string Key { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the role for the key.
                    /// </summary>
                    [Description("user role for the key; readonly, readwrite, administrator")]
                    [Enum(typeof(Role))]
                    public string Role { get; init; } = slskd.Authentication.Role.ReadOnly.ToString();

                    /// <summary>
                    ///     Gets the comma separated list of CIDRs that are authorized to use the key.
                    /// </summary>
                    [Description("optional; comma separated list of CIDRs that are authorized to use the key")]
                    public string Cidr { get; init; } = "127.0.0.1/32,::1/128";

                    /// <summary>
                    ///     Gets the comma-separated list of scopes granted to the key. Use <c>*</c>
                    ///     (the default) for universal access. HARDENING-2026-04-20 H13: scope a key
                    ///     to e.g. <c>nowplaying</c> so a Plex/Jellyfin webhook token can only call
                    ///     the now-playing endpoint, not the whole API.
                    /// </summary>
                    [Description("optional; comma separated list of scope tags (e.g., 'nowplaying'). '*' = all scopes")]
                    public string Scopes { get; init; } = "*";

                    /// <summary>
                    ///     Extended validation.
                    /// </summary>
                    /// <param name="validationContext"></param>
                    /// <returns></returns>
                    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                    {
                        var results = new List<ValidationResult>();

                        foreach (var cidr in Cidr.Split(','))
                        {
                            try
                            {
                                if (cidr.StartsWith("::ffff", StringComparison.OrdinalIgnoreCase))
                                {
                                    throw new Exception("IPv4 mapped IPv6 addresses are not allowed");
                                }

                                _ = IPAddressRange.Parse(cidr);
                            }
                            catch (Exception)
                            {
                                results.Add(new ValidationResult($"CIDR {cidr} is invalid"));
                            }
                        }

                        return results;
                    }
                }

                /// <summary>
                ///     Passthrough (no-auth) options. AllowedCidrs: comma-separated CIDRs allowed when no-auth in addition to loopback.
                /// </summary>
                public class PassthroughOptions
                {
                    /// <summary>Comma-separated CIDRs allowed when no-auth (in addition to loopback). E.g. 127.0.0.1/32,::1/128.</summary>
                    [Description("comma-separated CIDRs allowed when no-auth in addition to loopback; e.g. 127.0.0.1/32,::1/128")]
                    public string? AllowedCidrs { get; init; }
                }
            }

            /// <summary>
            ///     HTTPS options.
            /// </summary>
            public class HttpsOptions
            {
                /// <summary>
                ///     Gets a value indicating whether HTTPS should be disabled.
                /// </summary>
                [Argument(default, "no-https")]
                [EnvironmentVariable("NO_HTTPS")]
                [Description("disable HTTPS")]
                [RequiresRestart]
                public bool Disabled { get; init; } = false;

                /// <summary>
                ///     Gets the HTTPS listen port.
                /// </summary>
                [Argument('L', "https-port")]
                [EnvironmentVariable("HTTPS_PORT")]
                [Description("HTTPS listen port for web UI")]
                [Range(1, 65535)]
                [RequiresRestart]
                public int Port { get; init; } = 5031;

                /// <summary>
                ///     Gets a value indicating whether HTTP requests should be redirected to HTTPS.
                /// </summary>
                [Argument('f', "force-https")]
                [EnvironmentVariable("HTTPS_FORCE")]
                [Description("redirect HTTP to HTTPS")]
                [RequiresRestart]
                public bool Force { get; init; } = false;

                /// <summary>
                ///     Gets certificate options.
                /// </summary>
                [Validate]
                [RequiresRestart]
                public CertificateOptions Certificate { get; init; } = new CertificateOptions();

                /// <summary>
                ///     Certificate options.
                /// </summary>
                [X509Certificate]
                public class CertificateOptions
                {
                    /// <summary>
                    ///     Gets the path to the the X509 certificate .pfx file.
                    /// </summary>
                    [Argument(default, "https-cert-pfx")]
                    [EnvironmentVariable("HTTPS_CERT_PFX")]
                    [Description("path to X509 certificate .pfx")]
                    [FileExists(FileAccess.Read)]
                    [RequiresRestart]
                    public string Pfx { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the password for the X509 certificate.
                    /// </summary>
                    [Argument(default, "https-cert-password")]
                    [EnvironmentVariable("HTTPS_CERT_PASSWORD")]
                    [Description("X509 certificate password")]
                    [RequiresRestart]
                    [Secret]
                    public string Password { get; init; } = string.Empty;
                }
            }
        }

        /// <summary>
        ///     Options for external integrations.
        /// </summary>
        public class IntegrationOptions
        {
            /// <summary>
            ///     Gets VPN options.
            /// </summary>
            [Validate]
            public VpnOptions Vpn { get; init; } = new();

            /// <summary>
            ///     Gets webhook configuration.
            /// </summary>
            [Validate]
            public Dictionary<string, WebhookOptions> Webhooks { get; init; } = [];

            /// <summary>
            ///     Gets script configuration.
            /// </summary>
            [Validate]
            public Dictionary<string, ScriptOptions> Scripts { get; init; } = [];

            /// <summary>
            ///     Gets FTP options.
            /// </summary>
            [Validate]
            public FtpOptions Ftp { get; init; } = new FtpOptions();

            /// <summary>
            ///     Gets Pushbullet options.
            /// </summary>
            [Validate]
            public PushbulletOptions Pushbullet { get; init; } = new PushbulletOptions();

            /// <summary>
            ///     Gets Ntfy options.
            /// </summary>
            [Validate]
            public NtfyOptions Ntfy { get; init; } = new NtfyOptions();

            /// <summary>
            ///     Gets Pushover options.
            /// </summary>
            [Validate]
            public PushoverOptions Pushover { get; init; } = new PushoverOptions();

            /// <summary>
            ///     Gets Chromaprint integration options.
            /// </summary>
            [Validate]
            public ChromaprintOptions Chromaprint { get; init; } = new ChromaprintOptions();

            /// <summary>
            ///     Gets AcoustID integration options.
            /// </summary>
            [Validate]
            [YamlMember(Alias = "acoustid")]
            public AcoustIdOptions AcoustId { get; init; } = new AcoustIdOptions();

            /// <summary>
            ///     Gets MusicBrainz integration options.
            /// </summary>
            [Validate]
            [YamlMember(Alias = "musicbrainz")]
            public MusicBrainzOptions MusicBrainz { get; init; } = new MusicBrainzOptions();

            /// <summary>
            ///     Gets Lidarr integration options.
            /// </summary>
            [Validate]
            public LidarrOptions Lidarr { get; init; } = new LidarrOptions();

            /// <summary>
            ///     Gets Spotify source feed import options.
            /// </summary>
            [Validate]
            public SpotifyOptions Spotify { get; init; } = new SpotifyOptions();

            /// <summary>
            ///     Gets YouTube source feed import options.
            /// </summary>
            [Validate]
            [YamlMember(Alias = "youtube")]
            public YouTubeOptions YouTube { get; init; } = new YouTubeOptions();

            /// <summary>
            ///     Gets Last.fm source feed import options.
            /// </summary>
            [Validate]
            [YamlMember(Alias = "lastfm")]
            public LastFmOptions LastFm { get; init; } = new LastFmOptions();

            /// <summary>
            ///     VPN options.
            /// </summary>
            public class VpnOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether the VPN integration is enabled.
                /// </summary>
                [Argument(default, "vpn")]
                [EnvironmentVariable("VPN")]
                [Description("enable VPN integration")]
                [RequiresRestart]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets a value indicating whether the configured VPN supports dynamic port forwarding.
                /// </summary>
                [Argument(default, "vpn-port-forwarding")]
                [EnvironmentVariable("VPN_PORT_FORWARDING")]
                [Description("VPN supports dynamic port forwarding")]
                public bool PortForwarding { get; init; } = false;

                /// <summary>
                ///     Gets a value indicating whether the configured endpoint is the slskdN self-hosted relay companion.
                /// </summary>
                [Argument(default, "vpn-self-hosted-relay")]
                [EnvironmentVariable("VPN_SELF_HOSTED_RELAY")]
                [Description("VPN endpoint is the slskdN self-hosted relay companion")]
                public bool SelfHostedRelay { get; init; } = false;

                /// <summary>
                ///     Gets the rate at which to poll the configured VPN client for status updates, in milliseconds.
                /// </summary>
                [Argument(default, "vpn-polling-interval")]
                [EnvironmentVariable("VPN_POLLING_INTERVAL")]
                [Description("VPN client status polling interval")]
                [Range(500, int.MaxValue)]
                [RequiresRestart]
                public int PollingInterval { get; init; } = 2500;

                /// <summary>
                ///     Gets Gluetun options.
                /// </summary>
                [Validate]
                public GluetunVpnOptions Gluetun { get; init; } = new GluetunVpnOptions();

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (Enabled)
                    {
                        // as/if more VPN clients are added, update this logic to ensure that exactly one is configured
                        if (string.IsNullOrWhiteSpace(Gluetun?.Url))
                        {
                            yield return new ValidationResult("VPN is enabled but no client is configured");
                            yield break;
                        }

                        if (!Uri.TryCreate(Gluetun.Url, UriKind.Absolute, out _))
                        {
                            yield return new ValidationResult("The gluetun URL must be absolute, e.g. 'http://127.0.0.1:8000'");
                        }

                        if (SelfHostedRelay && !PortForwarding)
                        {
                            yield return new ValidationResult("Self-hosted relay mode requires VPN port forwarding");
                        }
                    }
                }

                /// <summary>
                ///     Gluetun options.
                /// </summary>
                public class GluetunVpnOptions
                {
                    /// <summary>
                    ///     Gets the Gluetun integration version.
                    /// </summary>
                    [Range(1, 1)]
                    public int Version { get; init; } = 1;

                    /// <summary>
                    ///     Gets the fully qualified root URL for the Gluetun control server.
                    /// </summary>
                    [Argument(default, "vpn-gluetun-url")]
                    [EnvironmentVariable("VPN_GLUETUN_URL")]
                    [Description("URL for gluetun control server")]
                    public string Url { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the timeout for HTTP requests to the Gluetun control server, in milliseconds.
                    /// </summary>
                    [Argument(default, "vpn-gluetun-timeout")]
                    [EnvironmentVariable("VPN_GLUETUN_TIMEOUT")]
                    [Description("timeout for HTTP requests to gluetun control server")]
                    [Range(500, 10_000)]
                    public int Timeout { get; init; } = 1000;

                    /// <summary>
                    ///     Gets the username used for basic auth.
                    /// </summary>
                    [Argument(default, "vpn-gluetun-username")]
                    [EnvironmentVariable("VPN_GLUETUN_USERNAME")]
                    [Description("username for gluetun control server")]
                    public string Username { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the password used for basic auth.
                    /// </summary>
                    [Argument(default, "vpn-gluetun-password")]
                    [EnvironmentVariable("VPN_GLUETUN_PASSWORD")]
                    [Description("password for gluetun control server")]
                    [Secret]
                    public string Password { get; init; } = string.Empty;

                    /// <summary>
                    ///     Gets the API key used for API key auth.
                    /// </summary>
                    [Argument(default, "vpn-gluetun-api-key")]
                    [EnvironmentVariable("VPN_GLUETUN_API_KEY")]
                    [Description("API key for gluetun control server")]
                    [Secret]
                    public string ApiKey { get; init; } = string.Empty;
                }
            }

            /// <summary>
            ///     Webhook configuration.
            /// </summary>
            public class WebhookOptions
            {
                /// <summary>
                ///     Gets the list of Event types that trigger the webhook.
                /// </summary>
                [Enum(typeof(EventType))]
                public string[] On { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets details about the webhook call.
                /// </summary>
                [Validate]
                public WebhookHttpOptions Call { get; init; } = new WebhookHttpOptions();

                /// <summary>
                ///     Gets the time to wait before timing out, in milliseconds.
                /// </summary>
                [Range(500, int.MaxValue)]
                public int Timeout { get; init; } = 5000;

                /// <summary>
                ///     Gets the retry configuration.
                /// </summary>
                [Validate]
                public RetryOptions Retry { get; init; } = new RetryOptions();
            }

            /// <summary>
            ///     Webhook HTTP options.
            /// </summary>
            public class WebhookHttpOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the fully qualified URL for the webhook.
                /// </summary>
                [NotNullOrWhiteSpace]
                public string Url { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the HTTP headers to include with the webhook.
                /// </summary>
                [Validate]
                public WebhookHttpHeader[] Headers { get; init; } = [];

                /// <summary>
                ///     Gets a value indicating whether webhook HTTPS certificate validation failures for
                ///     self-signed/untrusted-root chains should be tolerated.
                /// </summary>
                public bool IgnoreCertificateErrors { get; init; } = false;

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (!Url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) && !Url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                    {
                        yield return new ValidationResult($"The {nameof(Url)} field must contain a fully qualified URL, including protocol (e.g. http:// or https://)");
                    }
                }
            }

            /// <summary>
            ///     Webhook HTTP header configuration.
            /// </summary>
            public class WebhookHttpHeader
            {
                /// <summary>
                ///     Gets the name of the header.
                /// </summary>
                [NotNullOrWhiteSpace]
                public string Name { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the header's value.
                /// </summary>
                [Secret]
                public string Value { get; init; } = string.Empty;
            }

            /// <summary>
            ///     Retry configuration.
            /// </summary>
            public class RetryOptions
            {
                /// <summary>
                ///     Gets the number of attempts to make before failing.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int Attempts { get; init; } = 1;
            }

            /// <summary>
            ///     Script configuration.
            /// </summary>
            public class ScriptOptions
            {
                /// <summary>
                ///     Gets the list of Event types that trigger the script.
                /// </summary>
                [Enum(typeof(EventType))]
                public string[] On { get; init; } = Array.Empty<string>();

                /// <summary>
                ///     Gets the shell script to invoke.
                /// </summary>
                public ScriptRunOptions Run { get; init; } = new ScriptRunOptions();
            }

            /// <summary>
            ///     Script run options.
            /// </summary>
            public class ScriptRunOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the shell command to run.
                /// </summary>
                public string Command { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the executable to start.
                /// </summary>
                public string Executable { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the arguments to pass to the executable.
                /// </summary>
                /// <remarks>
                ///     Mutually exclusive with <see cref="Arglist"/>.
                /// </remarks>
                public string Args { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the list of arguments to pass to the executable.
                /// </summary>
                /// <remarks>
                ///     Mutually exclusive with <see cref="Args"/>.
                /// </remarks>
                public string[] Arglist { get; init; } = Array.Empty<string>();

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var cmdIsSet = !string.IsNullOrWhiteSpace(Command);
                    var exeIsSet = !string.IsNullOrWhiteSpace(Executable);

                    if ((cmdIsSet && exeIsSet) || (!cmdIsSet && !exeIsSet))
                    {
                        yield return new ValidationResult($"One and only one of the fields {nameof(Command)} or {nameof(Executable)} may be specified for a single script. If you intend to use the system shell, omit 'executable'. If you intend to use an executable other than the system shell, omit 'command' and specify either 'args' or 'args_list'.");
                    }

                    var argsIsSet = !string.IsNullOrWhiteSpace(Args);
                    var argsListIsSet = Arglist is not null;

                    if (argsIsSet && argsListIsSet)
                    {
                        yield return new ValidationResult($"Only one of the fields {nameof(Args)} or {nameof(Arglist)} may be specified for a single script. Specify 'args' if you intend to construct a single quoted string yourself, and specify 'args_list' if you'd like slskd to handle quoting for you.");
                    }
                }
            }

            /// <summary>
            ///     FTP options.
            /// </summary>
            public class FtpOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether the FTP integration is enabled.
                /// </summary>
                [Argument(default, "ftp")]
                [EnvironmentVariable("FTP")]
                [Description("enable FTP integration")]
                public bool Enabled { get; init; }

                /// <summary>
                ///     Gets the FTP address.
                /// </summary>
                [Argument(default, "ftp-address")]
                [EnvironmentVariable("FTP_ADDRESS")]
                [Description("FTP address")]
                public string Address { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the FTP port.
                /// </summary>
                [Argument(default, "ftp-port")]
                [EnvironmentVariable("FTP_PORT")]
                [Description("FTP port")]
                [Range(1, 65535)]
                public int Port { get; init; } = 21;

                /// <summary>
                ///     Gets the FTP encryption mode.
                /// </summary>
                [Argument(default, "ftp-encryption-mode")]
                [EnvironmentVariable("FTP_ENCRYPTION_MODE")]
                [Description("FTP encryption mode; none, implicit, explicit, auto")]
                [Enum(typeof(FtpEncryptionMode))]
                public string EncryptionMode { get; init; } = FtpEncryptionMode.Auto.ToString().ToLowerInvariant();

                /// <summary>
                ///     Gets a value indicating whether FTP certificate validation failures for
                ///     self-signed/untrusted-root chains should be tolerated.
                /// </summary>
                [Argument(default, "ftp-ignore-certificate-errors")]
                [EnvironmentVariable("FTP_IGNORE_CERTIFICATE_ERRORS")]
                [Description("allow self-signed/untrusted-root certificates for FTP")]
                public bool IgnoreCertificateErrors { get; init; } = false;

                /// <summary>
                ///     Gets the FTP username.
                /// </summary>
                [Argument(default, "ftp-username")]
                [EnvironmentVariable("FTP_USERNAME")]
                [Description("FTP username")]
                public string Username { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the FTP password.
                /// </summary>
                [Argument(default, "ftp-password")]
                [EnvironmentVariable("FTP_PASSWORD")]
                [Description("FTP password")]
                [Secret]
                public string Password { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the remote path for uploads.
                /// </summary>
                [Argument(default, "ftp-remote-path")]
                [EnvironmentVariable("FTP_REMOTE_PATH")]
                [Description("remote path for FTP uploads")]
                public string RemotePath { get; init; } = "/";

                /// <summary>
                ///     Gets a value indicating whether existing files should be overwritten.
                /// </summary>
                [Argument(default, "ftp-overwrite-existing")]
                [EnvironmentVariable("FTP_OVERWRITE_EXISTING")]
                [Description("overwrite existing files when uploading to FTP")]
                public bool OverwriteExisting { get; init; } = true;

                /// <summary>
                ///     Gets the connection timeout value, in milliseconds.
                /// </summary>
                [Argument(default, "ftp-connection-timeout")]
                [EnvironmentVariable("FTP_CONNECTION_TIMEOUT")]
                [Description("FTP connection timeout, in milliseconds")]
                [Range(0, int.MaxValue)]
                public int ConnectionTimeout { get; init; } = 5000;

                /// <summary>
                ///     Gets the number of times failing uploads will be retried.
                /// </summary>
                [Argument(default, "ftp-retry-attempts")]
                [EnvironmentVariable("FTP_RETRY_ATTEMPTS")]
                [Description("number of times failing FTP uploads will be retried")]
                [Range(0, 5)]
                public int RetryAttempts { get; init; } = 3;

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    if (Enabled && string.IsNullOrWhiteSpace(Address))
                    {
                        results.Add(new ValidationResult($"The Enabled field is true, but no Address has been specified."));
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Pushbullet options.
            /// </summary>
            public class PushbulletOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether the Pushbullet integration is enabled.
                /// </summary>
                [Argument(default, "pushbullet")]
                [EnvironmentVariable("PUSHBULLET")]
                [Description("enable Pushbullet integration")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the Pushbullet API access token.
                /// </summary>
                [Argument(default, "pushbullet-token")]
                [EnvironmentVariable("PUSHBULLET_ACCESS_TOKEN")]
                [Description("Pushbullet access token")]
                [Secret]
                public string AccessToken { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the prefix for Pushbullet notification titles.
                /// </summary>
                [Argument(default, "pushbullet-prefix")]
                [EnvironmentVariable("PUSHBULLET_NOTIFICATION_PREFIX")]
                [Description("prefix for Pushbullet notification titles")]
                public string NotificationPrefix { get; init; } = "From slskdN:";

                /// <summary>
                ///     Gets a value indicating whether a Pushbullet notification should be sent when a private message is received.
                /// </summary>
                [Argument(default, "pushbullet-notify-on-pm")]
                [EnvironmentVariable("PUSHBULLET_NOTIFY_ON_PRIVATE_MESSAGE")]
                [Description("send Pushbullet notifications when private messages are received")]
                public bool NotifyOnPrivateMessage { get; init; } = true;

                /// <summary>
                ///     Gets a value indicating whether a Pushbullet notification should be sent when the currently logged
                ///     in user's username is mentioned in a room.
                /// </summary>
                [Argument(default, "pushbullet-notify-on-room-mention")]
                [EnvironmentVariable("PUSHBULLET_NOTIFY_ON_ROOM_MENTION")]
                [Description("send Pushbullet notifications when your username is mentioned in a room")]
                public bool NotifyOnRoomMention { get; init; } = true;

                /// <summary>
                ///     Gets the number of times failing Pushbullet notifications will be retried.
                /// </summary>
                [Argument(default, "pushbullet-retry-attempts")]
                [EnvironmentVariable("PUSHBULLET_RETRY_ATTEMPTS")]
                [Description("number of times failing Pushbullet notifications will be retried")]
                [Range(0, 5)]
                public int RetryAttempts { get; init; } = 3;

                /// <summary>
                ///     Gets the cooldown time for Pushbullet notifications, in milliseconds.
                /// </summary>
                [Argument(default, "pushbullet-cooldown")]
                [EnvironmentVariable("PUSHBULLET_COOLDOWN_TIME")]
                [Description("cooldown time for Pushbullet notifications, in milliseconds")]
                public int CooldownTime { get; init; } = 900000; // 15 minutes

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <param name="validationContext"></param>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    if (Enabled && string.IsNullOrWhiteSpace(AccessToken))
                    {
                        results.Add(new ValidationResult($"The Enabled field is true, but no AccessToken has been specified."));
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Ntfy options.
            /// </summary>
            public class NtfyOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether the Ntfy integration is enabled.
                /// </summary>
                [Argument(default, "ntfy")]
                [EnvironmentVariable("NTFY")]
                [Description("enable Ntfy integration")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the Ntfy topic URL.
                /// </summary>
                [Argument(default, "ntfy-url")]
                [EnvironmentVariable("NTFY_URL")]
                [Description("Ntfy topic URL (e.g. https://ntfy.sh/mytopic)")]
                public string Url { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Ntfy access token (optional).
                /// </summary>
                [Argument(default, "ntfy-token")]
                [EnvironmentVariable("NTFY_TOKEN")]
                [Description("Ntfy access token (optional)")]
                [Secret]
                public string AccessToken { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the prefix for Ntfy notification titles.
                /// </summary>
                [Argument(default, "ntfy-prefix")]
                [EnvironmentVariable("NTFY_NOTIFICATION_PREFIX")]
                [Description("prefix for Ntfy notification titles")]
                public string NotificationPrefix { get; init; } = "slskdN";

                /// <summary>
                ///     Gets a value indicating whether an Ntfy notification should be sent when a private message is received.
                /// </summary>
                [Argument(default, "ntfy-notify-on-pm")]
                [EnvironmentVariable("NTFY_NOTIFY_ON_PRIVATE_MESSAGE")]
                [Description("send Ntfy notifications when private messages are received")]
                public bool NotifyOnPrivateMessage { get; init; } = true;

                /// <summary>
                ///     Gets a value indicating whether an Ntfy notification should be sent when the currently logged
                ///     in user's username is mentioned in a room.
                /// </summary>
                [Argument(default, "ntfy-notify-on-room-mention")]
                [EnvironmentVariable("NTFY_NOTIFY_ON_ROOM_MENTION")]
                [Description("send Ntfy notifications when the username is mentioned in a chat room")]
                public bool NotifyOnRoomMention { get; init; } = true;

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    if (Enabled && string.IsNullOrWhiteSpace(Url))
                    {
                        results.Add(new ValidationResult($"The Enabled field is true, but no Url has been specified for Ntfy."));
                    }

                    return results;
                }
            }

            /// <summary>
            ///     Pushover options.
            /// </summary>
            public class PushoverOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether the Pushover integration is enabled.
                /// </summary>
                [Argument(default, "pushover")]
                [EnvironmentVariable("PUSHOVER")]
                [Description("enable Pushover integration")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the Pushover user key.
                /// </summary>
                [Argument(default, "pushover-user-key")]
                [EnvironmentVariable("PUSHOVER_USER_KEY")]
                [Description("Pushover user key")]
                [Secret]
                public string UserKey { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Pushover API token.
                /// </summary>
                [Argument(default, "pushover-token")]
                [EnvironmentVariable("PUSHOVER_TOKEN")]
                [Description("Pushover API token")]
                [Secret]
                public string Token { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the prefix for Pushover notification titles.
                /// </summary>
                [Argument(default, "pushover-prefix")]
                [EnvironmentVariable("PUSHOVER_NOTIFICATION_PREFIX")]
                [Description("prefix for Pushover notification titles")]
                public string NotificationPrefix { get; init; } = "slskdN";

                /// <summary>
                ///     Gets a value indicating whether a Pushover notification should be sent when a private message is received.
                /// </summary>
                [Argument(default, "pushover-notify-on-pm")]
                [EnvironmentVariable("PUSHOVER_NOTIFY_ON_PRIVATE_MESSAGE")]
                [Description("send Pushover notifications when private messages are received")]
                public bool NotifyOnPrivateMessage { get; init; } = true;

                /// <summary>
                ///     Gets a value indicating whether a Pushover notification should be sent when the currently logged
                ///     in user's username is mentioned in a room.
                /// </summary>
                [Argument(default, "pushover-notify-on-room-mention")]
                [EnvironmentVariable("PUSHOVER_NOTIFY_ON_ROOM_MENTION")]
                [Description("send Pushover notifications when the username is mentioned in a chat room")]
                public bool NotifyOnRoomMention { get; init; } = true;

                /// <summary>
                ///     Extended validation.
                /// </summary>
                /// <returns></returns>
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    var results = new List<ValidationResult>();

                    if (Enabled)
                    {
                        if (string.IsNullOrWhiteSpace(UserKey))
                        {
                            results.Add(new ValidationResult($"The Enabled field is true, but no UserKey has been specified for Pushover."));
                        }

                        if (string.IsNullOrWhiteSpace(Token))
                        {
                            results.Add(new ValidationResult($"The Enabled field is true, but no Token has been specified for Pushover."));
                        }
                    }

                    return results;
                }
            }

            /// <summary>
            ///     MusicBrainz integration options.
            /// </summary>
            public class MusicBrainzOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets the base URL for MusicBrainz queries.
                /// </summary>
                [NotNullOrWhiteSpace]
                public string BaseUrl { get; init; } = "https://musicbrainz.org/ws/2";

                /// <summary>
                ///     Gets the User-Agent that will be sent to MusicBrainz.
                /// </summary>
                [NotNullOrWhiteSpace]
                public string UserAgent { get; init; } = $"{Program.AppName}/{Program.SemanticVersion} (https://github.com/snapetech/slskdn)";

                /// <summary>
                ///     Gets the timeout for individual HTTP requests, in seconds.
                /// </summary>
                public double TimeoutSeconds { get; init; } = 20;

                /// <summary>
                ///     Gets the number of retry attempts for MusicBrainz requests.
                /// </summary>
                [Range(1, int.MaxValue)]
                public int RetryAttempts { get; init; } = 2;

                /// <summary>
                ///     Gets the timeout as a <see cref="TimeSpan"/>.
                /// </summary>
                public TimeSpan Timeout => TimeSpan.FromSeconds(TimeoutSeconds);

                /// <inheritdoc />
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (!Uri.TryCreate(BaseUrl, UriKind.Absolute, out _))
                    {
                        yield return new ValidationResult($"The {nameof(BaseUrl)} field must be an absolute URL.", new[] { nameof(BaseUrl) });
                    }

                    if (string.IsNullOrWhiteSpace(UserAgent))
                    {
                        yield return new ValidationResult($"The {nameof(UserAgent)} field must not be empty.", new[] { nameof(UserAgent) });
                    }

                    if (TimeoutSeconds <= 0)
                    {
                        yield return new ValidationResult($"The {nameof(TimeoutSeconds)} field must be a positive number.", new[] { nameof(TimeoutSeconds) });
                    }

                    if (RetryAttempts <= 0)
                    {
                        yield return new ValidationResult($"The {nameof(RetryAttempts)} field must be greater than zero.", new[] { nameof(RetryAttempts) });
                    }
                }
            }

            /// <summary>
            ///     Lidarr integration options.
            /// </summary>
            public class LidarrOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether the Lidarr integration is enabled.
                /// </summary>
                [Argument(default, "lidarr")]
                [EnvironmentVariable("LIDARR")]
                [Description("enable Lidarr integration")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the Lidarr base URL.
                /// </summary>
                [Argument(default, "lidarr-url")]
                [EnvironmentVariable("LIDARR_URL")]
                [Description("Lidarr base URL")]
                public string Url { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Lidarr API key.
                /// </summary>
                [Argument(default, "lidarr-api-key")]
                [EnvironmentVariable("LIDARR_API_KEY")]
                [Description("Lidarr API key")]
                [Secret]
                public string ApiKey { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the timeout for HTTP requests to Lidarr, in seconds.
                /// </summary>
                [Argument(default, "lidarr-timeout")]
                [EnvironmentVariable("LIDARR_TIMEOUT")]
                [Description("timeout for HTTP requests to Lidarr")]
                [Range(1, 120)]
                public int TimeoutSeconds { get; init; } = 20;

                /// <summary>
                ///     Gets a value indicating whether Lidarr wanted albums should be synced into Wishlist.
                /// </summary>
                [Argument(default, "lidarr-sync-wanted")]
                [EnvironmentVariable("LIDARR_SYNC_WANTED")]
                [Description("sync Lidarr wanted albums into slskdN Wishlist")]
                public bool SyncWantedToWishlist { get; init; } = false;

                /// <summary>
                ///     Gets the interval between wanted syncs, in seconds.
                /// </summary>
                [Argument(default, "lidarr-sync-interval")]
                [EnvironmentVariable("LIDARR_SYNC_INTERVAL")]
                [Description("interval between Lidarr wanted syncs in seconds")]
                [Range(300, int.MaxValue)]
                public int SyncIntervalSeconds { get; init; } = 3600;

                /// <summary>
                ///     Gets the maximum wanted albums to sync per run.
                /// </summary>
                [Argument(default, "lidarr-sync-max-items")]
                [EnvironmentVariable("LIDARR_SYNC_MAX_ITEMS")]
                [Description("maximum Lidarr wanted albums to sync per run")]
                [Range(1, 1000)]
                public int MaxItemsPerSync { get; init; } = 100;

                /// <summary>
                ///     Gets a value indicating whether synced Wishlist items should auto-download.
                /// </summary>
                [Argument(default, "lidarr-auto-download")]
                [EnvironmentVariable("LIDARR_AUTO_DOWNLOAD")]
                [Description("auto-download Wishlist items created from Lidarr wanted albums")]
                public bool AutoDownload { get; init; } = false;

                /// <summary>
                ///     Gets the optional Wishlist filter for Lidarr-created searches.
                /// </summary>
                [Argument(default, "lidarr-wishlist-filter")]
                [EnvironmentVariable("LIDARR_WISHLIST_FILTER")]
                [Description("Wishlist filter for Lidarr-created searches")]
                public string WishlistFilter { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the maximum search results retained by Lidarr-created Wishlist items.
                /// </summary>
                [Argument(default, "lidarr-wishlist-max-results")]
                [EnvironmentVariable("LIDARR_WISHLIST_MAX_RESULTS")]
                [Description("maximum search results for Lidarr-created Wishlist items")]
                [Range(10, 1000)]
                public int WishlistMaxResults { get; init; } = 100;

                /// <summary>
                ///     Gets a value indicating whether completed slskdN download directories should be imported into Lidarr.
                /// </summary>
                [Argument(default, "lidarr-auto-import-completed")]
                [EnvironmentVariable("LIDARR_AUTO_IMPORT_COMPLETED")]
                [Description("auto-import completed slskdN download directories into Lidarr")]
                public bool AutoImportCompleted { get; init; } = false;

                /// <summary>
                ///     Gets the delay before the first automatic import attempt after a download completes,
                ///     in seconds. Gives a path-mapped or network-shared destination time to become visible
                ///     to Lidarr before the initial manual-import scan. Does not apply to manually-triggered imports.
                /// </summary>
                [Argument(default, "lidarr-import-delay")]
                [EnvironmentVariable("LIDARR_IMPORT_DELAY")]
                [Description("delay before the first automatic import attempt, in seconds")]
                [Range(0, 600)]
                public int ImportDelaySeconds { get; init; } = 0;

                /// <summary>
                ///     Gets the number of additional automatic retry attempts when a Lidarr manual-import
                ///     call fails transiently (a non-2xx response or timeout). 0 disables automatic retry,
                ///     leaving failures to be retried manually from the import history.
                /// </summary>
                [Argument(default, "lidarr-import-retry-max-attempts")]
                [EnvironmentVariable("LIDARR_IMPORT_RETRY_MAX_ATTEMPTS")]
                [Description("additional automatic retry attempts on a transient Lidarr import failure")]
                [Range(0, 10)]
                public int ImportRetryMaxAttempts { get; init; } = 2;

                /// <summary>
                ///     Gets the base delay between automatic retry attempts, in seconds. Doubles after each
                ///     failed attempt.
                /// </summary>
                [Argument(default, "lidarr-import-retry-delay")]
                [EnvironmentVariable("LIDARR_IMPORT_RETRY_DELAY")]
                [Description("base delay between automatic retry attempts, in seconds (doubles each attempt)")]
                [Range(1, 3600)]
                public int ImportRetryDelaySeconds { get; init; } = 30;

                /// <summary>
                ///     Gets the local slskdN completed path prefix to rewrite before calling Lidarr.
                /// </summary>
                [Argument(default, "lidarr-import-path-from")]
                [EnvironmentVariable("LIDARR_IMPORT_PATH_FROM")]
                [Description("local slskdN completed path prefix to rewrite for Lidarr")]
                public string ImportPathFrom { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Lidarr-visible completed path prefix.
                /// </summary>
                [Argument(default, "lidarr-import-path-to")]
                [EnvironmentVariable("LIDARR_IMPORT_PATH_TO")]
                [Description("Lidarr-visible completed path prefix")]
                public string ImportPathTo { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Lidarr manual import mode.
                /// </summary>
                [Argument(default, "lidarr-import-mode")]
                [EnvironmentVariable("LIDARR_IMPORT_MODE")]
                [Description("Lidarr manual import mode: move or copy")]
                public string ImportMode { get; init; } = "move";

                /// <summary>
                ///     Gets a value indicating whether Lidarr may replace existing files during auto-import.
                /// </summary>
                [Argument(default, "lidarr-import-replace-existing")]
                [EnvironmentVariable("LIDARR_IMPORT_REPLACE_EXISTING")]
                [Description("allow Lidarr auto-import to replace existing files")]
                public bool ImportReplaceExistingFiles { get; init; } = false;

                /// <summary>
                ///     Gets a value indicating whether a completed directory should be skipped, without
                ///     calling Lidarr's manual-import scan, when Lidarr already has every track of the
                ///     identified album on disk. Some Lidarr versions throw an internal error scanning a
                ///     download folder that duplicates an already-owned album, so this check avoids the
                ///     call entirely for the common re-download/re-search case. Has no effect when
                ///     <see cref="ImportReplaceExistingFiles"/> is enabled, since that means existing files
                ///     should intentionally be replaced.
                /// </summary>
                [Argument(default, "lidarr-skip-already-owned-albums")]
                [EnvironmentVariable("LIDARR_SKIP_ALREADY_OWNED_ALBUMS")]
                [Description("skip auto-import, without calling Lidarr, when the identified album is already fully owned")]
                public bool SkipAlreadyOwnedAlbums { get; init; } = true;

                [Argument(default, "lidarr-delete-rejected-downloads")]
                [EnvironmentVariable("LIDARR_DELETE_REJECTED_DOWNLOADS")]
                [Description("delete completed download files rejected by Lidarr automatic import")]
                public bool DeleteRejectedDownloads { get; init; } = false;

                [Argument(default, "lidarr-blacklist-rejected-downloads")]
                [EnvironmentVariable("LIDARR_BLACKLIST_REJECTED_DOWNLOADS")]
                [Description("exclude a rejected Wishlist peer and directory from future automatic downloads")]
                public bool BlacklistRejectedDownloads { get; init; } = false;

                /// <summary>
                ///     Gets how Wishlist auto-download selection treats candidates whose track
                ///     count/duration/edition don't match Lidarr's monitored release.
                /// </summary>
                [Argument(default, "lidarr-edition-match-mode")]
                [EnvironmentVariable("LIDARR_EDITION_MATCH_MODE")]
                [Description("how to treat candidates that don't match Lidarr's monitored release: exclude, prefer, or off")]
                public string EditionMatchMode { get; init; } = "exclude";

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (!Enabled)
                    {
                        yield break;
                    }

                    if (string.IsNullOrWhiteSpace(Url) || !Uri.TryCreate(Url, UriKind.Absolute, out _))
                    {
                        yield return new ValidationResult("Lidarr is enabled but integrations.lidarr.url is not an absolute URL.", new[] { nameof(Url) });
                    }

                    if (string.IsNullOrWhiteSpace(ApiKey))
                    {
                        yield return new ValidationResult("Lidarr is enabled but integrations.lidarr.api_key is empty.", new[] { nameof(ApiKey) });
                    }

                    if (AutoImportCompleted &&
                        !string.IsNullOrWhiteSpace(ImportPathFrom) != !string.IsNullOrWhiteSpace(ImportPathTo))
                    {
                        yield return new ValidationResult("Lidarr import path mapping requires both import_path_from and import_path_to.", new[] { nameof(ImportPathFrom), nameof(ImportPathTo) });
                    }

                    if (ImportMode is not ("move" or "copy" or "Move" or "Copy"))
                    {
                        yield return new ValidationResult("Lidarr import_mode must be 'move' or 'copy'.", new[] { nameof(ImportMode) });
                    }

                    if (!string.Equals(EditionMatchMode, "exclude", StringComparison.OrdinalIgnoreCase) &&
                        !string.Equals(EditionMatchMode, "prefer", StringComparison.OrdinalIgnoreCase) &&
                        !string.Equals(EditionMatchMode, "off", StringComparison.OrdinalIgnoreCase))
                    {
                        yield return new ValidationResult("Lidarr edition_match_mode must be 'exclude', 'prefer', or 'off'.", new[] { nameof(EditionMatchMode) });
                    }
                }
            }

            /// <summary>
            ///     Spotify source feed import options.
            /// </summary>
            public class SpotifyOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether Spotify provider imports and account connection are enabled.
                /// </summary>
                [Argument(default, "spotify")]
                [EnvironmentVariable("SPOTIFY")]
                [Description("enable Spotify source feed imports and account connection")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the Spotify application client ID.
                /// </summary>
                [Argument(default, "spotify-client-id")]
                [EnvironmentVariable("SPOTIFY_CLIENT_ID")]
                [Description("Spotify application client ID")]
                [Secret]
                public string ClientId { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Spotify application client secret.
                /// </summary>
                [Argument(default, "spotify-client-secret")]
                [EnvironmentVariable("SPOTIFY_CLIENT_SECRET")]
                [Description("Spotify application client secret")]
                [Secret]
                public string ClientSecret { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the Spotify OAuth redirect URI. Leave empty to infer from the current request host.
                /// </summary>
                [Argument(default, "spotify-redirect-uri")]
                [EnvironmentVariable("SPOTIFY_REDIRECT_URI")]
                [Description("Spotify OAuth redirect URI")]
                public string RedirectUri { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the timeout for Spotify HTTP requests, in seconds.
                /// </summary>
                [Argument(default, "spotify-timeout")]
                [EnvironmentVariable("SPOTIFY_TIMEOUT")]
                [Description("timeout for Spotify HTTP requests")]
                [Range(1, 120)]
                public int TimeoutSeconds { get; init; } = 20;

                /// <summary>
                ///     Gets the maximum imported source feed items per request.
                /// </summary>
                [Argument(default, "spotify-max-items-per-import")]
                [EnvironmentVariable("SPOTIFY_MAX_ITEMS_PER_IMPORT")]
                [Description("maximum Spotify source feed items per import")]
                [Range(1, 5000)]
                public int MaxItemsPerImport { get; init; } = 500;

                /// <summary>
                ///     Gets the market used for artist top-track lookups.
                /// </summary>
                [Argument(default, "spotify-market")]
                [EnvironmentVariable("SPOTIFY_MARKET")]
                [Description("Spotify market code for artist top-track lookups")]
                public string Market { get; init; } = "US";

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (!Enabled)
                    {
                        yield break;
                    }

                    if (string.IsNullOrWhiteSpace(ClientId))
                    {
                        yield return new ValidationResult("Spotify is enabled but integrations.spotify.client_id is empty.", new[] { nameof(ClientId) });
                    }

                    if (string.IsNullOrWhiteSpace(Market) || Market.Length != 2)
                    {
                        yield return new ValidationResult("Spotify market must be a two-letter market code.", new[] { nameof(Market) });
                    }
                }
            }

            /// <summary>
            ///     YouTube source feed import options.
            /// </summary>
            public class YouTubeOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether YouTube playlist source feed expansion is enabled.
                /// </summary>
                [Argument(default, "youtube")]
                [EnvironmentVariable("YOUTUBE")]
                [Description("enable YouTube source feed playlist expansion")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the YouTube Data API key used for playlist expansion.
                /// </summary>
                [Argument(default, "youtube-api-key")]
                [EnvironmentVariable("YOUTUBE_API_KEY")]
                [Description("YouTube Data API key for source feed playlist imports")]
                [Secret]
                public string ApiKey { get; init; } = string.Empty;

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (Enabled && string.IsNullOrWhiteSpace(ApiKey))
                    {
                        yield return new ValidationResult("YouTube source feed imports are enabled but integrations.youtube.api_key is empty.", new[] { nameof(ApiKey) });
                    }
                }
            }

            /// <summary>
            ///     Last.fm source feed import options.
            /// </summary>
            public class LastFmOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether Last.fm source feed expansion is enabled.
                /// </summary>
                [Argument(default, "lastfm")]
                [EnvironmentVariable("LASTFM")]
                [Description("enable Last.fm source feed imports")]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the Last.fm API key used for loved/recent/top track imports.
                /// </summary>
                [Argument(default, "lastfm-api-key")]
                [EnvironmentVariable("LASTFM_API_KEY")]
                [Description("Last.fm API key for source feed imports")]
                [Secret]
                public string ApiKey { get; init; } = string.Empty;

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (Enabled && string.IsNullOrWhiteSpace(ApiKey))
                    {
                        yield return new ValidationResult("Last.fm source feed imports are enabled but integrations.lastfm.api_key is empty.", new[] { nameof(ApiKey) });
                    }
                }
            }

            /// <summary>
            ///     Chromaprint integration options.
            /// </summary>
            public class ChromaprintOptions : IValidatableObject
            {
                public bool Enabled { get; init; } = false;

                public ChromaprintAlgorithm Algorithm { get; init; } = ChromaprintAlgorithm.Default;

                [NotNullOrWhiteSpace]
                public string FfmpegPath { get; init; } = "ffmpeg";

                public int SampleRate { get; init; } = 44100;

                public int Channels { get; init; } = 2;

                public int DurationSeconds { get; init; } = 120;

                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (Enabled && (int)Algorithm <= 0)
                    {
                        yield return new ValidationResult("Chromaprint algorithm must be a positive value", new[] { nameof(Algorithm) });
                    }

                    if (Enabled && SampleRate <= 0)
                    {
                        yield return new ValidationResult("Sample rate must be positive", new[] { nameof(SampleRate) });
                    }

                    if (Enabled && Channels <= 0)
                    {
                        yield return new ValidationResult("Channels must be positive", new[] { nameof(Channels) });
                    }

                    if (Enabled && DurationSeconds <= 0)
                    {
                        yield return new ValidationResult("Duration must be positive seconds", new[] { nameof(DurationSeconds) });
                    }
                }
            }

            /// <summary>
            ///     AcoustID integration options.
            /// </summary>
            public class AcoustIdOptions : IValidatableObject
            {
                /// <summary>
                ///     Gets a value indicating whether AcoustID lookup is enabled.
                /// </summary>
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the AcoustID API key (client identifier).
                /// </summary>
                public string ClientId { get; init; } = string.Empty;

                /// <summary>
                ///     Gets the AcoustID base URL.
                /// </summary>
                [NotNullOrWhiteSpace]
                public string BaseUrl { get; init; } = "https://api.acoustid.org/v2";

                /// <inheritdoc />
                public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
                {
                    if (Enabled && string.IsNullOrWhiteSpace(ClientId))
                    {
                        yield return new ValidationResult("AcoustID client id must be supplied when enabled", new[] { nameof(ClientId) });
                    }

                    if (Enabled && !Uri.IsWellFormedUriString(BaseUrl, UriKind.Absolute))
                    {
                        yield return new ValidationResult("AcoustID BaseUrl must be an absolute URL", new[] { nameof(BaseUrl) });
                    }
                }
            }
        }

        /// <summary>
        ///     Scheduled speed limit options for day/night schedules.
        /// </summary>
        public class ScheduledSpeedLimitOptions
        {
            /// <summary>
            ///     Gets a value indicating whether scheduled speed limits are enabled.
            /// </summary>
            [Argument(default, "scheduled-limits-enabled")]
            [EnvironmentVariable("SCHEDULED_LIMITS_ENABLED")]
            [Description("enable scheduled speed limits (day/night)")]
            public bool Enabled { get; init; } = false;

            /// <summary>
            ///     Gets the start hour for "night" period (when lower speed limits apply).
            /// </summary>
            [Argument(default, "night-start-hour")]
            [EnvironmentVariable("NIGHT_START_HOUR")]
            [Description("hour when night period starts (0-23)")]
            [Range(0, 23)]
            public int NightStartHour { get; init; } = 22;

            /// <summary>
            ///     Gets the end hour for "night" period (when lower speed limits apply).
            /// </summary>
            [Argument(default, "night-end-hour")]
            [EnvironmentVariable("NIGHT_END_HOUR")]
            [Description("hour when night period ends (0-23)")]
            [Range(0, 23)]
            public int NightEndHour { get; init; } = 6;

            /// <summary>
            ///     Gets the upload speed limit during night hours, in kibibytes.
            /// </summary>
            [Argument(default, "night-upload-speed-limit")]
            [EnvironmentVariable("NIGHT_UPLOAD_SPEED_LIMIT")]
            [Description("upload speed limit during night hours")]
            [Range(1, int.MaxValue)]
            public int NightUploadSpeedLimit { get; init; } = 100;

            /// <summary>
            ///     Gets the download speed limit during night hours, in kibibytes.
            /// </summary>
            [Argument(default, "night-download-speed-limit")]
            [EnvironmentVariable("NIGHT_DOWNLOAD_SPEED_LIMIT")]
            [Description("download speed limit during night hours")]
            [Range(1, int.MaxValue)]
            public int NightDownloadSpeedLimit { get; init; } = 200;
        }

        /// <summary>
        ///     Throttling options.
        /// </summary>
        public class ThrottlingOptions
        {
            /// <summary>
            ///     Gets search throttling options.
            /// </summary>
            [Validate]
            public SearchThrottlingOptions Search { get; init; } = new SearchThrottlingOptions();

            /// <summary>
            ///     Search throttling options.
            /// </summary>
            public class SearchThrottlingOptions
            {
                /// <summary>
                ///     Gets incoming search throttling options.
                /// </summary>
                [Validate]
                public IncomingSearchThrottlingOptions Incoming { get; init; } = new IncomingSearchThrottlingOptions();

                /// <summary>
                ///     Search response throttling options.
                /// </summary>
                public class IncomingSearchThrottlingOptions
                {
                    /// <summary>
                    ///     Gets the limit for the number of concurrent search response operations.
                    /// </summary>
                    [Argument(default, "throttling-search-incoming-concurrency")]
                    [EnvironmentVariable("THROTTLING_SEARCH_INCOMING_CONCURRENCY")]
                    [Range(1, 100)]
                    [RequiresRestart]
                    public int Concurrency { get; init; } = 10;

                    /// <summary>
                    ///     Gets the limit for the number of queued search response operations, after which requests will be discarded.
                    /// </summary>
                    [Argument(default, "throttling-search-incoming-circuit-breaker")]
                    [EnvironmentVariable("THROTTLING_SEARCH_INCOMING_CIRCUIT_BREAKER")]
                    [Range(100, 10000)]
                    public int CircuitBreaker { get; init; } = 500;

                    /// <summary>
                    ///     Gets the limit for the number of files that can be returned in a single search request.
                    /// </summary>
                    [Argument(default, "throttling-search-incoming-response-file-limit")]
                    [EnvironmentVariable("THROTTLING_SEARCH_INCOMING_RESPONSE_FILE_LIMIT")]
                    [Range(100, 5000)]
                    public int ResponseFileLimit { get; init; } = 500;
                }
            }
        }

        /// <summary>
        ///     Telemetry options for OpenTelemetry distributed tracing.
        /// </summary>
        public class TelemetryOptions
        {
            /// <summary>
            ///     Gets tracing options.
            /// </summary>
            [Validate]
            public TracingOptions Tracing { get; init; } = new TracingOptions();

            /// <summary>
            ///     Tracing options for OpenTelemetry.
            /// </summary>
            public class TracingOptions
            {
                /// <summary>
                ///     Gets a value indicating whether distributed tracing is enabled.
                /// </summary>
                [Argument(default, "telemetry-tracing")]
                [EnvironmentVariable("TELEMETRY_TRACING")]
                [Description("enable OpenTelemetry distributed tracing")]
                [RequiresRestart]
                public bool Enabled { get; init; } = false;

                /// <summary>
                ///     Gets the tracing exporter type (console, jaeger, otlp).
                /// </summary>
                [Argument(default, "telemetry-tracing-exporter")]
                [EnvironmentVariable("TELEMETRY_TRACING_EXPORTER")]
                [Description("tracing exporter type (console, jaeger, otlp)")]
                [RequiresRestart]
                public string Exporter { get; init; } = "console";

                /// <summary>
                ///     Gets the Jaeger OTLP collector endpoint (URL, host:port, or host).
                /// </summary>
                [Argument(default, "telemetry-jaeger-endpoint")]
                [EnvironmentVariable("TELEMETRY_JAEGER_ENDPOINT")]
                [Description("Jaeger OTLP collector endpoint (URL, host:port, or host)")]
                [RequiresRestart]
                public string? JaegerEndpoint { get; init; }

                /// <summary>
                ///     Gets the Jaeger OTLP collector port (if not specified in endpoint).
                /// </summary>
                [Argument(default, "telemetry-jaeger-port")]
                [EnvironmentVariable("TELEMETRY_JAEGER_PORT")]
                [Description("Jaeger OTLP collector port (if not specified in endpoint)")]
                [RequiresRestart]
                public int? JaegerPort { get; init; }

                /// <summary>
                ///     Gets the OTLP endpoint URL.
                /// </summary>
                [Argument(default, "telemetry-otlp-endpoint")]
                [EnvironmentVariable("TELEMETRY_OTLP_ENDPOINT")]
                [Description("OTLP endpoint URL")]
                [RequiresRestart]
                public string? OtlpEndpoint { get; init; }
            }
        }

        /// <summary>
        ///     LAN discovery advertising options.
        /// </summary>
        public class LanDiscoveryOptions
        {
            /// <summary>
            ///     Gets a value indicating whether this instance advertises its identity on the local network.
            /// </summary>
            [Description("advertise peer identity on the local network")]
            [RequiresRestart]
            public bool Advertise { get; init; } = false;
        }
    }
}

/// <summary>
///     Chromaprint algorithm versions.
/// </summary>
public enum ChromaprintAlgorithm
{
    /// <summary>
    ///     Default fingerprint algorithm (1).
    /// </summary>
    Default = 1,
}
