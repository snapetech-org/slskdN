// <copyright file="ApplicationStartupTaskExtensions.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Bootstrap;

using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Serilog;
using slskd.Audio;
using slskd.Integrations.Scripts;
using slskd.Integrations.VPN;
using slskd.Integrations.Webhooks;

public static class ApplicationStartupTaskExtensions
{
    public static WebApplication RunSlskdStartupTasks(this WebApplication app, OptionsAtStartup optionsAtStartup)
    {
        if (!optionsAtStartup.Flags.Volatile)
        {
            Log.Debug("Running Migrate()...");

            // If this throws, a database registration is missing its Migrator setup.
            app.Services.GetRequiredService<Migrator>().Migrate(force: optionsAtStartup.Flags.ForceMigrations);
        }

        if (optionsAtStartup.Flags.AudioReanalyze && !optionsAtStartup.Flags.Volatile)
        {
            Log.Information("[AudioReanalyze] Running analyzer migration (force={Force})...", optionsAtStartup.Flags.AudioReanalyzeForce);
            var migrationService = app.Services.GetRequiredService<IAnalyzerMigrationService>();
            var n = migrationService.MigrateAsync("audioqa-2", optionsAtStartup.Flags.AudioReanalyzeForce, default).GetAwaiter().GetResult();
            Log.Information("[AudioReanalyze] Updated {Count} variants", n);
        }

        Log.Debug("[DI] Forcing construction of ScriptService, WebhookService, and VPNService...");
        _ = app.Services.GetService<ScriptService>();
        _ = app.Services.GetService<WebhookService>();
        _ = app.Services.GetService<VPNService>();
        if (optionsAtStartup.Feature.VirtualSoulfind)
        {
            _ = app.Services.GetService<VirtualSoulfind.Capture.TrafficObserverIntegrationService>();
        }

        Log.Debug("[DI] Required startup integration services constructed");

        return app;
    }
}
