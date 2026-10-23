// <copyright file="UserDataServiceCollectionExtensions.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Bootstrap;

using System.Data;
using System.IO;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

public static class UserDataServiceCollectionExtensions
{
    public static IServiceCollection AddSlskdUserData(this IServiceCollection services)
    {
        return AddSlskdUserData(services, Program.AppDirectory);
    }

    internal static IServiceCollection AddSlskdUserData(IServiceCollection services, string appDirectory)
    {
        // User Notes services
        var userNotesDbPath = Path.Combine(appDirectory, "user_notes.db");
        services.AddDbContextFactory<Users.Notes.UserNotesDbContext>(options =>
        {
            options.UseSqlite($"Data Source={userNotesDbPath}");
        });

        // Ensure user notes database is created
        using (var userNotesContext = new Users.Notes.UserNotesDbContext(
            new DbContextOptionsBuilder<Users.Notes.UserNotesDbContext>()
                .UseSqlite($"Data Source={userNotesDbPath}")
                .Options))
        {
            userNotesContext.Database.EnsureCreated();
            userNotesContext.Database.ExecuteSqlRaw("CREATE TABLE IF NOT EXISTS UserBlocks (Username TEXT COLLATE NOCASE NOT NULL PRIMARY KEY, CreatedAt TEXT NOT NULL)");
        }

        services.AddSingleton<Users.Notes.IUserNoteService, Users.Notes.UserNoteService>();
        services.AddSingleton<Users.Notes.IUserBlockService, Users.Notes.UserBlockService>();

        // Collections / sharing (ShareGroup, Collection, ShareGrant) — behind Feature.CollectionsSharing
        var collectionsDbPath = Path.Combine(appDirectory, "collections.db");
        services.AddDbContextFactory<Sharing.CollectionsDbContext>(options =>
        {
            options.UseSqlite($"Data Source={collectionsDbPath}");
        });
        using (var collectionsContext = new Sharing.CollectionsDbContext(
            new DbContextOptionsBuilder<Sharing.CollectionsDbContext>()
                .UseSqlite($"Data Source={collectionsDbPath}")
                .Options))
        {
            collectionsContext.Database.EnsureCreated();

            // EnsureCreated does not update tables in an existing database. Check the
            // schema first so an already-applied migration is the only ignored case.
            EnsureColumnExists(collectionsContext, "ShareGrants", "OwnerEndpoint", "TEXT");
            EnsureColumnExists(collectionsContext, "ShareGrants", "ShareToken", "TEXT");
            EnsureColumnExists(collectionsContext, "CollectionItems", "FileName", "TEXT");
            EnsureColumnExists(collectionsContext, "CollectionItems", "Title", "TEXT");
            EnsureColumnExists(collectionsContext, "CollectionItems", "Artist", "TEXT");
            EnsureColumnExists(collectionsContext, "CollectionItems", "Album", "TEXT");
            collectionsContext.Database.ExecuteSqlRaw(Sharing.CollectionsDbContext.ContentLookupIndexSql);
        }

        services.AddSingleton<Sharing.IShareGroupRepository, Sharing.ShareGroupRepository>();
        services.AddSingleton<Sharing.ICollectionRepository, Sharing.CollectionRepository>();
        services.AddSingleton<Sharing.IShareGrantRepository, Sharing.ShareGrantRepository>();
        services.AddSingleton<Sharing.ISharingService, Sharing.SharingService>();
        services.AddSingleton<Sharing.ShareGrantAnnouncementService>();

        // Identity / friends (PeerProfile, Contact) — behind Feature.IdentityFriends
        var identityDbPath = Path.Combine(appDirectory, "identity.db");
        services.AddDbContextFactory<Identity.IdentityDbContext>(options =>
        {
            options.UseSqlite($"Data Source={identityDbPath}");
        });
        using (var identityContext = new Identity.IdentityDbContext(
            new DbContextOptionsBuilder<Identity.IdentityDbContext>()
                .UseSqlite($"Data Source={identityDbPath}")
                .Options))
        {
            identityContext.Database.EnsureCreated();
        }

        services.AddSingleton<Identity.IContactRepository, Identity.ContactRepository>();
        services.AddSingleton<Identity.IContactService, Identity.ContactService>();
        services.AddSingleton<Identity.IProfileService, Identity.ProfileService>();
        services.AddSingleton<Identity.ILanDiscoveryService, Identity.LanDiscoveryService>();

        // Solid / WebID / Solid-OIDC (optional; gated per-request by Feature.Solid)
        services.AddSingleton<slskd.Solid.ISolidClientIdDocumentService, slskd.Solid.SolidClientIdDocumentService>();
        services.AddSingleton<slskd.Solid.ISolidWebIdResolver, slskd.Solid.SolidWebIdResolver>();
        services.AddSingleton<slskd.Solid.ISolidFetchPolicy, slskd.Solid.SolidFetchPolicy>();

        return services;
    }

    private static void EnsureColumnExists(DbContext context, string tableName, string columnName, string columnType)
    {
        var allowedColumns = tableName switch
        {
            "ShareGrants" => new[] { "OwnerEndpoint", "ShareToken" },
            "CollectionItems" => new[] { "FileName", "Title", "Artist", "Album" },
            _ => Array.Empty<string>(),
        };

        if (!allowedColumns.Contains(columnName, StringComparer.Ordinal) || columnType != "TEXT")
        {
            throw new ArgumentException("The requested user-data schema change is not supported.");
        }

        var connection = context.Database.GetDbConnection();
        var closeConnection = connection.State != ConnectionState.Open;
        if (closeConnection)
        {
            context.Database.OpenConnection();
        }

        try
        {
            using var schemaCommand = connection.CreateCommand();

            // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- tableName is selected from fixed internal migrations and quoted as a SQLite identifier.
            schemaCommand.CommandText = $"PRAGMA table_info(\"{tableName.Replace("\"", "\"\"", StringComparison.Ordinal)}\")";
            using var reader = schemaCommand.ExecuteReader();
            var columnExists = false;
            while (reader.Read())
            {
                if (string.Equals(reader.GetString(1), columnName, StringComparison.OrdinalIgnoreCase))
                {
                    columnExists = true;
                    break;
                }
            }

            reader.Close();
            if (!columnExists)
            {
                using var migrationCommand = connection.CreateCommand();

                // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- tableName and columnName are allowlisted, columnType is fixed to TEXT, and identifiers are quoted.
                migrationCommand.CommandText = $"ALTER TABLE \"{tableName.Replace("\"", "\"\"", StringComparison.Ordinal)}\" ADD COLUMN \"{columnName.Replace("\"", "\"\"", StringComparison.Ordinal)}\" {columnType}";
                migrationCommand.ExecuteNonQuery();
            }
        }
        finally
        {
            if (closeConnection)
            {
                context.Database.CloseConnection();
            }
        }
    }
}
