// <copyright file="Program.cs" company="slskd Team">
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

// <copyright file="Program.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using slskd.Bootstrap;

namespace slskd
{
    using System;
    using System.IO;
    using System.Threading;
    using Microsoft.Extensions.Configuration;
    using slskd.Configuration;
    using slskd.Relay;
    using Utility.CommandLine;
    using Utility.EnvironmentVariables;

    /// <summary>
    ///     Bootstraps configuration and handles primitive command-line instructions.
    /// </summary>
    public static class Program
    {
        /// <summary>
        ///     The name of the application.
        /// </summary>
        public static readonly string AppName = "slskd";

        /// <summary>
        ///     The DateTime of the 'genesis' of the application (the initial commit).
        /// </summary>
        public static readonly DateTime GenesisDateTime = new(2020, 12, 30, 6, 22, 0, DateTimeKind.Utc);

        /// <summary>
        ///     The name of the local share host.
        /// </summary>
        public static readonly string LocalHostName = "local";

        /// <summary>
        ///     The url to the issues/support site.
        /// </summary>
        public static readonly string IssuesUrl = "https://github.com/snapetech-org/slskdN/issues";

        /// <summary>
        ///     The global prefix for environment variables.
        /// </summary>
        public static readonly string EnvironmentVariablePrefix = $"{AppName.ToUpperInvariant()}_";

        /// <summary>
        ///     The default XML documentation filename.
        /// </summary>
        public static readonly string XmlDocumentationFile = Path.Combine(AppContext.BaseDirectory, "etc", $"{AppName}.xml");

        /// <summary>
        ///     Soulseek.NET requires a caller-owned minor-version slot.
        ///     slskdN uses the self-assigned range 7700000-7709999, chosen outside the
        ///     760-7699999 range reserved by upstream slskd. This range is not yet
        ///     registered in the Soulseek.NET README registry; that registration is
        ///     still owed (see memory-bank/license-rollback-plan.md, Soulseek.NET §5).
        /// </summary>
        public static readonly int SoulseekMinorVersion = 7700000;

        /// <summary>
        ///     The default application data directory.
        /// </summary>
        public static readonly string DefaultAppDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData, Environment.SpecialFolderOption.DoNotVerify), AppName);

        /// <summary>
        ///     Gets the unique Id of this application invocation.
        /// </summary>
        public static readonly Guid InvocationId = Guid.NewGuid();

        /// <summary>
        ///     Gets the Id of the current application process.
        /// </summary>
        public static readonly int ProcessId = Environment.ProcessId;

        /// <summary>
        ///     Gets the application's base directory.
        /// </summary>
        public static readonly string BaseDirectory = AppContext.BaseDirectory;

        /// <summary>
        ///     Gets the current executable path when available.
        /// </summary>
        public static readonly string ExecutablePath = ApplicationRuntimeInfo.TryGetExecutablePath();

        /// <summary>
        ///     Occurs when a new log event is emitted.
        /// </summary>
        public static event EventHandler<LogRecord> LogEmitted = (_, _) => { };

        /// <summary>
        ///     Gets the semantic application version.
        /// </summary>
        public static string SemanticVersion { get; } = ApplicationRuntimeInfo.SemanticVersion;

        /// <summary>
        ///     Gets the full application version, including both assembly and informational versions.
        /// </summary>
        public static string FullVersion { get; } = ApplicationRuntimeInfo.FullVersion;

        /// <summary>
        ///     Gets a value indicating whether the current version is a Canary build.
        /// </summary>
        public static bool IsCanary { get; } = ApplicationRuntimeInfo.IsCanary;

        /// <summary>
        ///     Gets a value indicating whether the current version is a Development build.
        /// </summary>
        public static bool IsDevelopment { get; } = ApplicationRuntimeInfo.IsDevelopment;

        private static void RaiseLogEmitted(LogRecord record)
        {
            foreach (EventHandler<LogRecord> handler in LogEmitted.GetInvocationList())
            {
                try
                {
                    handler.Invoke(null, record);
                }
                catch (Exception ex)
                {
                    Log.Warning(ex, "LogEmitted subscriber failed");
                }
            }
        }

        /// <summary>
        ///     Gets a value indicating whether the application is being run in Relay Agent mode.
        /// </summary>
        public static bool IsRelayAgent { get; private set; }

        /// <summary>
        ///     Gets the application flags.
        /// </summary>
        public static Options.FlagsOptions Flags { get; private set; } = new();

        /// <summary>
        ///     Gets the path where application data is saved.
        /// </summary>
        [Argument('a', "app-dir", "path where application data is saved")]
        [EnvironmentVariable("APP_DIR")]
        public static string AppDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the fully qualified path to the application configuration file.
        /// </summary>
        [Argument('c', "config", "path to configuration file")]
        [EnvironmentVariable("CONFIG")]
        public static string ConfigurationFile { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the current configuration overlay, if one has been applied.
        /// </summary>
        public static OptionsOverlay? ConfigurationOverlay => VolatileOverlayConfigurationSource?.CurrentValue;

        /// <summary>
        ///     Gets the path where persistent data is saved.
        /// </summary>
        public static string DataDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the path where backups of persistent data saved.
        /// </summary>
        public static string DataBackupDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the default fully qualified path to the configuration file.
        /// </summary>
        public static string DefaultConfigurationFile { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the default downloads directory.
        /// </summary>
        public static string DefaultDownloadsDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the default incomplete download directory.
        /// </summary>
        public static string DefaultIncompleteDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the path where application logs are saved.
        /// </summary>
        public static string LogDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets the path where user-defined scripts are stored.
        /// </summary>
        public static string ScriptDirectory { get; private set; } = string.Empty;

        /// <summary>
        ///     Gets a buffer containing the last few log events.
        /// </summary>
        public static ConcurrentFixedSizeQueue<LogRecord> LogBuffer { get; } = new ConcurrentFixedSizeQueue<LogRecord>(size: 100);

        /// <summary>
        ///     Gets the master cancellation token source for the program.
        /// </summary>
        /// <remarks>
        ///     The token from this source should be used (or linked) to any long-running asynchronous task, so that when the application
        ///     begins to shut down these tasks also shut down in a timely manner. Actions that control the lifecycle of the program
        ///     (POSIX signals, a restart from the API, etc) should cancel this source.
        /// </remarks>
        public static CancellationTokenSource MasterCancellationTokenSource { get; } = new CancellationTokenSource();

        private static IConfigurationRoot? Configuration { get; set; }
        private static OptionsAtStartup OptionsAtStartup { get; } = new OptionsAtStartup();

        // Explicit Serilog.ILogger type to avoid ambiguity with Microsoft.Extensions.Logging.ILogger
        private static Serilog.ILogger Log { get; set; } = new Serilog.LoggerConfiguration()
            .WriteTo.Sink(new ConsoleWriteLineLogger())
            .CreateLogger();

        // Mutex is created lazily after AppDirectory is set to allow multiple test instances with different app dirs.
        private static Mutex? Mutex { get; set; }

        private static VolatileOverlayConfigurationSource<OptionsOverlay> VolatileOverlayConfigurationSource { get; set; } = new VolatileOverlayConfigurationSource<OptionsOverlay>();

        [Argument('g', "generate-cert", "generate X509 certificate and password for HTTPs")]
        private static bool GenerateCertificate { get; set; }

        [Argument('k', "generate-secret", "generate random secret of the specified length")]
        private static int GenerateSecret { get; set; }

        [Argument('n', "no-logo", "suppress logo on startup")]
        private static bool NoLogo { get; set; }

        [Argument('e', "envars", "display environment variables")]
        private static bool ShowEnvironmentVariables { get; set; }

        [Argument('h', "help", "display command line usage")]
        private static bool ShowHelp { get; set; }

        [Argument('v', "version", "display version information")]
        private static bool ShowVersion { get; set; }

        /// <summary>
        ///     Panic.
        /// </summary>
        /// <param name="code">An optional exit code.</param>
        public static void Exit(int code = 1) => Environment.Exit(code);

        /// <summary>
        ///     Apply an instance of <see cref="OptionsOverlay"/> on top of the existing application configuration.
        /// </summary>
        /// <param name="overlay">The overlay containing the property values to be overlaid.</param>
        public static void ApplyConfigurationOverlay(OptionsOverlay overlay) => VolatileOverlayConfigurationSource.Apply(overlay);

        /// <summary>
        ///     Entrypoint.
        /// </summary>
        /// <param name="args">Command line arguments.</param>
        public static void Main(string[] args)
        {
            EnvironmentVariables.Populate(prefix: EnvironmentVariablePrefix);

            try
            {
                Arguments.Populate(clearExistingValues: false);
            }
            catch (Exception ex)
            {
                Log.Error($"Invalid command line input: {ex.Message.Replace(".  See inner exception for details.", string.Empty)}");
                return;
            }

            if (StartupCommandMode.TryRun(
                new StartupCommandModeOptions(ShowVersion, ShowHelp, ShowEnvironmentVariables, NoLogo, GenerateCertificate, GenerateSecret),
                FullVersion,
                EnvironmentVariablePrefix,
                AppName,
                BaseDirectory,
                typeof(Options),
                IsDevelopment,
                IsCanary,
                Log,
                Exit))
            {
                return;
            }

            var preparedDirectories = StartupApplicationDirectoryResolver.TryPrepare(
                AppDirectory,
                DefaultAppDirectory,
                AppName,
                ConfigurationFile,
                Log,
                Exit);

            if (preparedDirectories is null)
            {
                return;
            }

            var directories = preparedDirectories.Directories;
            AppDirectory = directories.AppDirectory;
            Mutex = preparedDirectories.Mutex;
            DataDirectory = directories.DataDirectory;
            DataBackupDirectory = directories.DataBackupDirectory;
            LogDirectory = directories.LogDirectory;
            ScriptDirectory = directories.ScriptDirectory;
            DefaultConfigurationFile = directories.DefaultConfigurationFile;
            DefaultDownloadsDirectory = directories.DefaultDownloadsDirectory;
            DefaultIncompleteDirectory = directories.DefaultIncompleteDirectory;
            ConfigurationFile = preparedDirectories.ConfigurationFile;

            Configuration = StartupConfiguration.TryLoadAndValidate(
                EnvironmentVariablePrefix,
                ConfigurationFile,
                VolatileOverlayConfigurationSource,
                OptionsAtStartup,
                AppName,
                Log,
                Exit);

            if (Configuration is null)
            {
                return;
            }

            IsRelayAgent = OptionsAtStartup.Relay.Enabled && OptionsAtStartup.Relay.Mode.ToEnum<RelayMode>() == RelayMode.Agent;
            Flags = OptionsAtStartup.Flags;

            Log = StartupLogging.Configure(
                OptionsAtStartup,
                AppName,
                LogDirectory,
                InvocationId,
                ProcessId,
                record =>
                {
                    LogBuffer.Enqueue(record);
                    RaiseLogEmitted(record);
                });
            Log = Serilog.Log.ForContext(typeof(Program));

            // Install hard telemetry to catch silent exits
            StartupShutdownTelemetry.Install(
                () => Application.IsShuttingDown,
                StartupExceptionClassifier.IsBenignUnobservedTaskException,
                SoulseekExceptions.SoulseekNetworkExceptionClassifier.IsExpected,
                () => Log);

            var startupDiagnosticsContext = new StartupDiagnosticsContext(
                FullVersion,
                IsDevelopment,
                IsCanary,
                IssuesUrl,
                ProcessId,
                ExecutablePath,
                BaseDirectory,
                InvocationId,
                AppDirectory,
                ConfigurationFile,
                DataDirectory,
                LogDirectory);

            StartupDiagnostics.LogStartupIdentity(
                OptionsAtStartup,
                startupDiagnosticsContext,
                Log);

            // SQLite must have specific capabilities to function properly. this shouldn't be a concern for shrinkwrapped
            // binaries or in Docker, but if someone builds from source weird things can happen.
            StartupSqlite.InitOrFailFast(Log);

            StartupDiagnostics.LogConfigurationUsage(
                OptionsAtStartup,
                startupDiagnosticsContext,
                AppName,
                Log);

            StartupWebApplicationRunner.Run(
                new StartupWebApplicationContext(
                    args,
                    EnvironmentVariablePrefix,
                    ConfigurationFile,
                    VolatileOverlayConfigurationSource,
                    Configuration!,
                    AppName,
                    DataDirectory,
                    XmlDocumentationFile,
                    SoulseekMinorVersion),
                OptionsAtStartup,
                Log,
                Exit);
        }

    }
}
