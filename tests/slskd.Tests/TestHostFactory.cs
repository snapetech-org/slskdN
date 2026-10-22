// <copyright file="TestHostFactory.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests;

using System;
using System.IO;
using System.Net;
using System.Security.Claims;
using System.Text;
using System.Linq;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.ApplicationParts;
using Microsoft.AspNetCore.Mvc.Authorization;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using Asp.Versioning;
using slskd;
using slskd.Authentication;
using slskd.Core.API;
using slskd.Core.Security;

/// <summary>
/// Minimal test host factory that boots the API with test settings.
/// Used for smoke and regression tests (e.g. GET /api/v0/session/enabled).
/// </summary>
public class TestHostFactory : WebApplicationFactory<ProgramStub>
{
    protected override IHostBuilder CreateHostBuilder()
    {
        var solutionRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
        var contentRoot = Path.Combine(solutionRoot, "tests", "slskd.Tests");
        Directory.CreateDirectory(contentRoot);
        // Base WebApplicationFactory resolves content root to solutionRoot/slskd.Tests; ensure it exists.
        Directory.CreateDirectory(Path.Combine(solutionRoot, "slskd.Tests"));

        return new HostBuilder()
            .UseContentRoot(contentRoot)
            .UseEnvironment("Test")
            .ConfigureWebHostDefaults(web =>
            {
                web.UseTestServer();
                web.UseContentRoot(contentRoot);
                web.ConfigureServices(services =>
                {
                    var optionsAtStartup = new OptionsAtStartup();
                    services.AddSingleton(optionsAtStartup);
                    services.AddOptions<slskd.Options>();
                    services.AddSingleton<IOptionsSnapshot<slskd.Options>>(sp =>
                    {
                        var opts = sp.GetRequiredService<IOptions<slskd.Options>>();
                        return new StaticOptionsSnapshot(opts.Value);
                    });
                    services.AddSingleton<ISecurityService, StubSecurityService>();

                    services.AddApiVersioning(o =>
                    {
                        o.DefaultApiVersion = new ApiVersion(0, 0);
                        o.AssumeDefaultVersionWhenUnspecified = true;
                        o.ReportApiVersions = true;
                    }).AddMvc().AddApiExplorer(o =>
                    {
                        o.GroupNameFormat = "'v'VVV";
                        o.SubstituteApiVersionInUrl = true;
                    });

                    services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
                        .AddJwtBearer();
                    services.AddAuthorization(o =>
                        o.AddPolicy(AuthPolicy.Any, p => p.RequireAuthenticatedUser()));
                    services.AddControllers(o =>
                        o.Filters.Add(new AuthorizeFilter(AuthPolicy.Any)))
                        .ConfigureApplicationPartManager(manager =>
                        {
                            var existing = manager.FeatureProviders
                                .OfType<IApplicationFeatureProvider<ControllerFeature>>().ToList();
                            foreach (var provider in existing)
                            {
                                manager.FeatureProviders.Remove(provider);
                            }

                            manager.FeatureProviders.Add(new slskd.Common.CodeQuality.SafeControllerFeatureProvider());
                        })
                        .AddApplicationPart(typeof(SessionController).Assembly);
                });
                web.Configure(app =>
                {
                    app.UseRouting();
                    app.UseAuthentication();
                    app.UseAuthorization();
                    app.UseEndpoints(e => e.MapControllers());
                });
            });
    }
}

/// <summary>Marker for WebApplicationFactory; host is built in CreateHostBuilder.</summary>
public class ProgramStub
{
    public static IHostBuilder CreateHostBuilder(string[] args) => new HostBuilder();
}

internal class StaticOptionsSnapshot : IOptionsSnapshot<slskd.Options>
{
    private readonly slskd.Options _value;
    public StaticOptionsSnapshot(slskd.Options value) => _value = value;
    public slskd.Options Value => _value;
    public slskd.Options Get(string? name) => _value;
}

internal class StubSecurityService : ISecurityService
{
    public JwtSecurityToken GenerateJwt(
        string username,
        Role role,
        int? ttl = null,
        string[]? scopes = null,
        IEnumerable<Claim>? additionalClaims = null)
    {
        var claims = new List<Claim>(additionalClaims ?? Array.Empty<Claim>());
        var effectiveScopes = scopes is { Length: > 0 } ? scopes : new[] { SlskdClaims.ScopeAll };
        claims.AddRange(effectiveScopes.Select(scope => new Claim(SlskdClaims.ScopeClaim, scope)));

        return new JwtSecurityToken(
            issuer: "test",
            audience: "test",
            claims: claims,
            notBefore: DateTime.UtcNow,
            expires: DateTime.UtcNow.AddMilliseconds(ttl ?? TimeSpan.FromHours(1).TotalMilliseconds),
            signingCredentials: new SigningCredentials(
                new SymmetricSecurityKey(Encoding.UTF8.GetBytes("test-key-must-be-32-bytes!!!!!!!")),
                "HS256"));
    }

    public bool AuthenticateAdminCredentials(string username, string password) => true;

    public (string Name, Role Role, string[] Scopes) AuthenticateWithApiKey(string key, IPAddress callerIpAddress) =>
        ("test", Role.Administrator, new[] { SlskdClaims.ScopeAll });

    public void RevokeToken(string jti, DateTimeOffset expiresAt)
    {
    }

    public bool IsTokenRevoked(string jti) => false;
}
