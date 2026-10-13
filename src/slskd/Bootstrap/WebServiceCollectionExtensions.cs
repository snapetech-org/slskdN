// <copyright file="WebServiceCollectionExtensions.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Bootstrap;

using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Serialization;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.ApplicationParts;
using Microsoft.AspNetCore.Mvc.Authorization;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi;
using Prometheus.DotNetRuntime;
using Prometheus.SystemMetrics;
using Serilog;
using slskd.Authentication;
using slskd.Common.Security;
using slskd.Core.API;
using slskd.Core.Security;
using slskd.Mesh;
using slskd.Cryptography;
using slskd.Shares;
using slskd.SocialFederation;
using slskd.Validation;
using Utility.EnvironmentVariables;

public static class WebServiceCollectionExtensions
{
    internal const string ApiKeyOrJwtAuthenticationScheme = "ApiKeyOrJwt";

    private static class DotNetRuntimeStatsHolder
    {
        public static IDisposable? Value { get; set; }
    }

    public static IServiceCollection AddSlskdWebServices(
        this IServiceCollection services,
        IConfiguration configuration,
        OptionsAtStartup optionsAtStartup,
        string appName,
        string dataDirectory,
        string environmentVariablePrefix,
        string xmlDocumentationFile)
    {
        Log.Debug("[ASP] Starting ConfigureAspDotNetServices...");

        services.AddCors(options =>
        {
            var c = optionsAtStartup.Web.Cors;
            if (c.Enabled && c.AllowedOrigins != null && c.AllowedOrigins.Length > 0)
            {
                options.AddPolicy("ConfiguredCors", b =>
                {
                    // Handle wildcard origin for E2E tests (when credentials are disabled)
                    var hasWildcard = c.AllowedOrigins.Contains("*") || c.AllowedOrigins.Contains("/*");
                    if (hasWildcard && !c.AllowCredentials)
                    {
                        // E2E tests: allow any origin (no credentials)
                        b.AllowAnyOrigin();
                    }
                    else
                    {
                        b.WithOrigins(c.AllowedOrigins);
                        if (c.AllowCredentials)
                        {
                            b.AllowCredentials();
                        }
                    }

                    b.WithExposedHeaders("X-URL-Base", "X-Total-Count", "X-Slskd-Error-Code")
                        .SetPreflightMaxAge(TimeSpan.FromHours(1));
                    if (c.AllowedHeaders != null && c.AllowedHeaders.Length > 0)
                    {
                        b.WithHeaders(c.AllowedHeaders);
                    }
                    else
                    {
                        b.AllowAnyHeader();
                    }

                    if (c.AllowedMethods != null && c.AllowedMethods.Length > 0)
                    {
                        b.WithMethods(c.AllowedMethods);
                    }
                    else
                    {
                        b.AllowAnyMethod();
                    }
                });
            }
        });

        // note: don't dispose this (or let it be disposed) or some of the stats, like those related
        // to the thread pool won't work
        DotNetRuntimeStatsHolder.Value = DotNetRuntimeStatsBuilder.Default().StartCollecting();
        services.AddSystemMetrics();

        services.AddDataProtection()
            .PersistKeysToFileSystem(new DirectoryInfo(Path.Combine(dataDirectory, "misc", ".DataProtection-Keys")));

        // LOW-02: SHA256-hash the configured key so the signing key is always 32 raw bytes of key material
        // regardless of the string's encoding width, avoiding weak keys from short UTF-8 strings.
        var jwtSigningKey = new SymmetricSecurityKey(
            System.Security.Cryptography.SHA256.HashData(Encoding.UTF8.GetBytes(optionsAtStartup.Web.Authentication.Jwt.Key)));

        // JwtOptions.Key defaults to a freshly generated random value when unset in config, so we
        // can't distinguish "configured" from "ephemeral" by inspecting the Options object itself.
        // Check the raw configuration tree instead — the warning only fires when no value was
        // actually provided by the user.
        var jwtKeyConfigured = !string.IsNullOrWhiteSpace(configuration["slskd:web:authentication:jwt:key"])
            || !string.IsNullOrWhiteSpace(configuration["web:authentication:jwt:key"])
            || !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable($"{environmentVariablePrefix}JWT_KEY"));

        if (!jwtKeyConfigured)
        {
            Log.Warning("JWT signing key is ephemeral (auto-generated per-process start). All sessions will be invalidated on restart. Set web.authentication.jwt.key in configuration to persist sessions.");
        }

        services.AddSingleton(jwtSigningKey);
        services.AddSingleton(new JwtRevocationStore(Path.Combine(dataDirectory, "security", "jwt-revocations.json")));
        services.AddSingleton<ISecurityService, SecurityService>();
        services.AddSingleton<Common.Security.ISoulseekSafetyLimiter, Common.Security.SoulseekSafetyLimiter>();

        // T-MCP01: Register Moderation / Control Plane services
        services.AddSingleton<Common.Moderation.IModerationProvider>(sp =>
        {
            var opts = sp.GetRequiredService<IOptionsMonitor<slskd.Options>>();
            var logger = sp.GetRequiredService<ILogger<Common.Moderation.CompositeModerationProvider>>();

            if (!opts.CurrentValue.Moderation.Enabled)
            {
                return new Common.Moderation.NoopModerationProvider();
            }

            // T-MCP03: Inject share repository for content ID checking
            var shareRepository = sp.GetService<Shares.IShareRepository>();

            // For now, use CompositeModerationProvider with no sub-providers
            // T-MCP02+ will add actual implementations
            // We need to wrap the Options.Moderation in an IOptionsMonitor
            var moderationOptions = Microsoft.Extensions.Options.Options.Create(opts.CurrentValue.Moderation);
            var moderationOptionsMonitor = new Common.Moderation.WrappedOptionsMonitor<Common.Moderation.ModerationOptions>(moderationOptions);

            return new Common.Moderation.CompositeModerationProvider(
                moderationOptionsMonitor,
                logger,
                hashBlocklist: null,
                peerReputation: null,
                externalClient: null,
                shareRepository: shareRepository); // T-MCP03
        });

        // T-FED01: Register Social Federation services
        if (optionsAtStartup.SocialFederation.Enabled)
        {
            services.AddSocialFederation();
        }

        if (!optionsAtStartup.Web.Authentication.Disabled)
        {
            services.AddAuthorization(options =>
            {
                options.AddPolicy(AuthPolicy.JwtOnly, policy =>
                {
                    policy.AuthenticationSchemes.Add(JwtBearerDefaults.AuthenticationScheme);
                    policy.RequireAuthenticatedUser();
                });

                options.AddPolicy(AuthPolicy.ApiKeyOnly, policy =>
                {
                    policy.AuthenticationSchemes.Add(ApiKeyAuthentication.AuthenticationScheme);
                    policy.RequireAuthenticatedUser();
                });

                options.AddPolicy(AuthPolicy.Any, policy =>
                {
                    policy.AuthenticationSchemes.Add(ApiKeyAuthentication.AuthenticationScheme);
                    policy.AuthenticationSchemes.Add(JwtBearerDefaults.AuthenticationScheme);
                    policy.RequireAuthenticatedUser();
                });
            });

            services.AddAuthentication(options =>
                {
                    options.DefaultAuthenticateScheme = ApiKeyOrJwtAuthenticationScheme;
                    options.DefaultChallengeScheme = ApiKeyOrJwtAuthenticationScheme;
                    options.DefaultScheme = ApiKeyOrJwtAuthenticationScheme;
                })
                .AddPolicyScheme(
                    ApiKeyOrJwtAuthenticationScheme,
                    ApiKeyOrJwtAuthenticationScheme,
                    options => options.ForwardDefaultSelector = SelectAuthenticationScheme)
                .AddJwtBearer(options =>
                {
                    options.TokenValidationParameters = new TokenValidationParameters
                    {
                        ClockSkew = SecurityService.JwtClockSkew,
                        RequireSignedTokens = true,
                        RequireExpirationTime = true,
                        ValidateLifetime = true,
                        ValidIssuer = appName,
                        ValidateIssuer = true,
                        ValidateAudience = true,
                        ValidAudiences = new[] { appName },
                        IssuerSigningKey = jwtSigningKey,
                        ValidateIssuerSigningKey = true,
                    };

                    options.Events = new JwtBearerEvents
                    {
                        OnTokenValidated = context =>
                        {
                            // HIGH-04: check jti deny-list to support token revocation (e.g. logout)
                            var jti = context.Principal?.FindFirst(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Jti)?.Value;
                            if (!string.IsNullOrEmpty(jti))
                            {
                                var security = context.HttpContext.RequestServices.GetService<ISecurityService>();
                                if (security?.IsTokenRevoked(jti) == true)
                                {
                                    context.Fail("Token has been revoked");
                                }
                            }

                            return Task.CompletedTask;
                        },
                        OnMessageReceived = context =>
                        {
                            // signalr authentication is stupid
                            if (context.Request.Path.StartsWithSegments("/hub"))
                            {
                                // assign the request token from the access_token query parameter if one is present
                                // this typically means that the calling signalr client is running in a browser. this takes
                                // precedent over the Authorization header value (if one is present)
                                // https://docs.microsoft.com/en-us/aspnet/core/signalr/authn-and-authz?view=aspnetcore-5.0
                                if (context.Request.Query.TryGetValue("access_token", out var accessToken))
                                {
                                    var token = accessToken.ToString();

                                    try
                                    {
                                        context.Token = PromoteApiKeyToJwt(context.HttpContext, token);
                                    }
                                    catch
                                    {
                                        // The token may already be a JWT. Let JWT bearer validation handle it.
                                        context.Token = token;
                                    }
                                }
                                else if (context.Request.Headers.ContainsKey("Authorization")
                                    && context.Request.Headers.TryGetValue("Authorization", out var authorization)
                                    && authorization.ToString().StartsWith("Bearer ", StringComparison.InvariantCultureIgnoreCase))
                                {
                                    // extract the bearer token. this value might be an API key, a JWT, or some garbage value
                                    var token = authorization.ToString().Split(' ').LastOrDefault();

                                    try
                                    {
                                        // check to see if the provided value is a valid API key
                                        context.Token = PromoteApiKeyToJwt(context.HttpContext, token ?? string.Empty);
                                    }
                                    catch
                                    {
                                        // the token either isn't a valid API key. use the provided value and let the
                                        // rest of the auth middleware figure out whether it is valid
                                        context.Token = token;
                                    }
                                }
                            }

                            return Task.CompletedTask;
                        },
                    };
                })
                .AddScheme<ApiKeyAuthenticationOptions, ApiKeyAuthenticationHandler>(ApiKeyAuthentication.AuthenticationScheme, (_) => { });
        }
        else
        {
            Log.Warning("Authentication of web requests is DISABLED");

            services.AddAuthorization(options =>
            {
                options.AddPolicy(AuthPolicy.Any, policy =>
                {
                    policy.AuthenticationSchemes.Add(PassthroughAuthentication.AuthenticationScheme);
                    policy.RequireAuthenticatedUser();
                });

                options.AddPolicy(AuthPolicy.ApiKeyOnly, policy =>
                {
                    policy.AuthenticationSchemes.Add(PassthroughAuthentication.AuthenticationScheme);
                    policy.RequireAuthenticatedUser();
                });

                options.AddPolicy(AuthPolicy.JwtOnly, policy =>
                {
                    policy.AuthenticationSchemes.Add(PassthroughAuthentication.AuthenticationScheme);
                    policy.RequireAuthenticatedUser();
                });
            });

            services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = PassthroughAuthentication.AuthenticationScheme;
                options.DefaultChallengeScheme = PassthroughAuthentication.AuthenticationScheme;
                options.DefaultScheme = PassthroughAuthentication.AuthenticationScheme;
            })
                .AddScheme<PassthroughAuthenticationOptions, PassthroughAuthenticationHandler>(PassthroughAuthentication.AuthenticationScheme, options =>
                {
                    options.Username = "Anonymous";
                    options.Role = Role.Administrator;
                    options.AllowRemoteNoAuth = optionsAtStartup.Web.AllowRemoteNoAuth;
                    options.AllowedCidrs = optionsAtStartup.Web.Authentication.Passthrough?.AllowedCidrs;
                });
        }

        services.AddMemoryCache(); // Required by ShardCache and others

        // CSRF Protection (only applies to cookie-based authentication, not JWT/API keys)
        services.AddAntiforgery(options =>
        {
            // Multi-instance (E2E) runs multiple nodes on the same host with different ports.
            // Cookies are host-scoped (not port-scoped), so both the antiforgery cookie token and the
            // JS-readable request-token cookie need stable per-port names that do not collide with each other.
            options.Cookie.Name = $"XSRF-COOKIE-{optionsAtStartup.Web.Port}";
            options.HeaderName = "X-CSRF-TOKEN";
            options.Cookie.SameSite = SameSiteMode.Strict;

            // Keep the antiforgery cookie secure whenever HTTPS is enabled. Browsers scope cookies by
            // host, not port or scheme, so an HTTP response must not replace the HTTPS cookie.
            options.Cookie.SecurePolicy = optionsAtStartup.Web.Https.Disabled
                ? CookieSecurePolicy.SameAsRequest
                : CookieSecurePolicy.Always;
            options.Cookie.HttpOnly = true;

            // IMPORTANT: Don't auto-validate - we use custom ValidateCsrfForCookiesOnlyAttribute
            // This ensures GET requests are never validated automatically
            options.SuppressXFrameOptionsHeader = false; // Keep X-Frame-Options for security

            // Session-based tokens (30 days with sliding expiration)
            // Tokens don't expire independently - they're tied to the session
        });

        services.AddRouting(options => options.LowercaseUrls = true);
        services.AddProblemDetails();

        services.AddControllers(options =>
            {
                options.Filters.Add(new AuthorizeFilter(AuthPolicy.Any));
                options.Filters.Add<ScopedApiKeyDenyByDefaultFilter>();
            })
            .ConfigureApplicationPartManager(manager =>
            {
                // Replace the default ControllerFeatureProvider with a resilient one that
                // handles Assembly.GetTypes() failures from optional or build-adjacent
                // dependencies before controller discovery can inspect individual types.
                var existing = manager.FeatureProviders
                    .OfType<IApplicationFeatureProvider<ControllerFeature>>().ToList();
                foreach (var p in existing)
                {
                    manager.FeatureProviders.Remove(p);
                }

                manager.FeatureProviders.Add(new slskd.Common.CodeQuality.SafeControllerFeatureProvider());
            })
            .ConfigureApiBehaviorOptions(options =>
            {
                options.SuppressInferBindingSourcesForParameters = true; // explicit [FromRoute], etc
                options.SuppressMapClientErrors = true; // disables automatic ProblemDetails for 4xx

                // PR-07: when EnforceSecurity, enable automatic 400 for invalid model (ValidationProblemDetails)
                options.SuppressModelStateInvalidFilter = false;
                options.DisableImplicitFromServicesParameters = true; // explicit [FromServices]

                // PR-05, PR-07: custom ValidationProblemDetails; in Production do not leak internal property paths or structure.
                options.InvalidModelStateResponseFactory = actionContext =>
                {
                    var env = actionContext.HttpContext.RequestServices.GetService<Microsoft.AspNetCore.Hosting.IWebHostEnvironment>();
                    var isDev = env?.IsDevelopment() == true;
                    var problem = new ValidationProblemDetails(actionContext.ModelState)
                    {
                        Status = 400,
                        Title = "One or more validation errors occurred.",
                    };
                    if (!isDev)
                    {
                        problem.Detail = "The request is invalid.";
                        problem.Errors.Clear();
                    }

                    return new BadRequestObjectResult(problem);
                };
            })
            .AddJsonOptions(options =>
            {
                options.JsonSerializerOptions.Converters.Add(new IPAddressConverter());
                options.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter());
                options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
            });

        services
            .AddSignalR(options =>
            {
                // https://github.com/SignalR/SignalR/issues/1149#issuecomment-973887222
                options.MaximumParallelInvocationsPerClient = 2;
                options.AddFilter<ScopedApiKeyHubFilter>();
            })
            .AddJsonProtocol(options =>
            {
                options.PayloadSerializerOptions.Converters.Add(new IPAddressConverter());
                options.PayloadSerializerOptions.Converters.Add(new JsonStringEnumConverter());
            });

        services.AddHealthChecks()
            .AddSecurityHealthCheck()
            .AddMeshHealthCheck(
                name: "mesh",
                failureStatus: Microsoft.Extensions.Diagnostics.HealthChecks.HealthStatus.Degraded, // Don't fail entire health endpoint if mesh isn't ready
                tags: new[] { "mesh", "network", "dht" },
                timeout: TimeSpan.FromSeconds(5)); // 5 second timeout to prevent hanging

        services.AddApiVersioning(options =>
            {
                options.ReportApiVersions = true;
            })
            .AddMvc()
            .AddApiExplorer(options =>
            {
                options.GroupNameFormat = "'v'VVV";
                options.SubstituteApiVersionInUrl = true;
            });

        // PR-09: HTTP rate limiting – Api (generous), FederationInbox (tighter), MeshGateway (tighter). Per-IP partitions.
        if (optionsAtStartup.Web.RateLimiting.Enabled)
        {
            var rl = optionsAtStartup.Web.RateLimiting;
            var apiPermit = rl.ApiPermitLimit;
            var apiWindow = TimeSpan.FromSeconds(rl.ApiWindowSeconds <= 0 ? 60 : rl.ApiWindowSeconds);
            var fedPermit = rl.FederationPermitLimit;
            var fedWindow = TimeSpan.FromSeconds(rl.FederationWindowSeconds <= 0 ? 60 : rl.FederationWindowSeconds);
            var meshPermit = rl.MeshGatewayPermitLimit;
            var meshWindow = TimeSpan.FromSeconds(rl.MeshGatewayWindowSeconds <= 0 ? 60 : rl.MeshGatewayWindowSeconds);

            services.AddRateLimiter(options =>
            {
                options.RejectionStatusCode = 429;
                options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
                {
                    var path = context.Request.Path.Value ?? string.Empty;
                    var ip = context.Connection.RemoteIpAddress?.ToString() ?? "unknown";
                    if (path.StartsWith("/mesh/", StringComparison.OrdinalIgnoreCase))
                    {
                        return RateLimitPartition.GetFixedWindowLimiter("mesh:" + ip, _ => new FixedWindowRateLimiterOptions { PermitLimit = meshPermit, Window = meshWindow });
                    }

                    if (path.Contains("/inbox", StringComparison.OrdinalIgnoreCase) && string.Equals(context.Request.Method, "POST", StringComparison.OrdinalIgnoreCase))
                    {
                        return RateLimitPartition.GetFixedWindowLimiter("fed:" + ip, _ => new FixedWindowRateLimiterOptions { PermitLimit = fedPermit, Window = fedWindow });
                    }

                    if (path.StartsWith("/api/", StringComparison.OrdinalIgnoreCase)
                        && path.Contains("/events/", StringComparison.OrdinalIgnoreCase)
                        && string.Equals(context.Request.Method, "POST", StringComparison.OrdinalIgnoreCase))
                    {
                        return RateLimitPartition.GetFixedWindowLimiter(
                            "event-injection:" + ip,
                            _ => new FixedWindowRateLimiterOptions
                            {
                                PermitLimit = Math.Min(apiPermit, 10),
                                Window = TimeSpan.FromMinutes(1),
                            });
                    }

                    if (path.StartsWith("/api/", StringComparison.OrdinalIgnoreCase)
                        && path.Contains("/warm-cache/hints", StringComparison.OrdinalIgnoreCase)
                        && string.Equals(context.Request.Method, "POST", StringComparison.OrdinalIgnoreCase))
                    {
                        var caller = context.User?.Identity?.Name ?? ip;
                        return RateLimitPartition.GetFixedWindowLimiter(
                            "warm-cache:" + caller + ":" + ip,
                            _ => new FixedWindowRateLimiterOptions
                            {
                                PermitLimit = Math.Min(apiPermit, 10),
                                Window = TimeSpan.FromMinutes(1),
                            });
                    }

                    if (context.User?.Identity?.IsAuthenticated == true)
                    {
                        return RateLimitPartition.GetNoLimiter("authenticated");
                    }

                    if (!path.StartsWith("/api/", StringComparison.OrdinalIgnoreCase))
                    {
                        return RateLimitPartition.GetNoLimiter("web");
                    }

                    return RateLimitPartition.GetFixedWindowLimiter("api:" + ip, _ => new FixedWindowRateLimiterOptions { PermitLimit = apiPermit, Window = apiWindow });
                });
            });
        }

        if (optionsAtStartup.Feature.Swagger)
        {
            services.AddSwaggerGen(options =>
            {
                options.DescribeAllParametersInCamelCase();

                // Use fully-qualified type name as schema ID to prevent conflicts between
                // types with the same short name in different namespaces (e.g. slskd.Search.File
                // vs Soulseek.File both map to "File" by default, crashing Swagger generation).
                options.CustomSchemaIds(type => type.FullName?.Replace("+", "."));
                options.ResolveConflictingActions(apiDescriptions => apiDescriptions.First());
                options.SwaggerDoc("v0", new OpenApiInfo
                {
                    Version = "v0",
                    Title = "slskdN API",
                    Description = "slskdN is an unofficial fork of slskd for the Soulseek community service network",
                    Contact = new OpenApiContact
                    {
                        Name = "slskdN on GitHub",
                        Url = new Uri("https://github.com/snapetech/slskdn"),
                    },
                    License = new OpenApiLicense
                    {
                        Name = "AGPL-3.0 license",
                        Url = new Uri("https://github.com/snapetech/slskdn/blob/main/LICENSE"),
                    },
                });

                // allow endpoints marked with multiple content types in [Produces] to generate properly
                options.OperationFilter<ContentNegotiationOperationFilter>();

                if (File.Exists(xmlDocumentationFile))
                {
                    options.IncludeXmlComments(xmlDocumentationFile);
                }
                else
                {
                    Log.Warning($"Unable to find XML documentation in {xmlDocumentationFile}, Swagger will not include metadata");
                }
            });
        }

        return services;
    }

    internal static string PromoteApiKeyToJwt(HttpContext context, string token)
    {
        var service = context.RequestServices.GetRequiredService<ISecurityService>();
        var remoteIpAddress = context.Connection.RemoteIpAddress;
        if (string.IsNullOrWhiteSpace(token) || remoteIpAddress == null)
        {
            throw new InvalidOperationException("API key token or caller IP address was unavailable.");
        }

        var (name, role, scopes) = service.AuthenticateWithApiKey(token, callerIpAddress: remoteIpAddress);

        // The API key is valid. Create a short-lived JWT while preserving its scopes.
        return service.GenerateJwt(name, role, ttl: 1000, scopes: scopes).Serialize();
    }

    internal static string SelectAuthenticationScheme(HttpContext context)
    {
        return context.Request.Headers.ContainsKey("X-API-Key")
            ? ApiKeyAuthentication.AuthenticationScheme
            : JwtBearerDefaults.AuthenticationScheme;
    }
}
