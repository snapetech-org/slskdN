// <copyright file="WebApplicationPipelineExtensions.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Bootstrap;

using System;
using slskd.Relay;
using slskd.ListeningParty;
using slskd.Common.Security;
using Asp.Versioning.ApiExplorer;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Options;
using Prometheus;
using Serilog;
using slskd.Authentication;
using slskd.Core.API;
using slskd.Core.Features;
using slskd.Search.API;
using slskd.Signals;
using slskd.Telemetry;

public static class WebApplicationPipelineExtensions
{
    public static WebApplication UseSlskdWebPipeline(this WebApplication app, OptionsAtStartup optionsAtStartup)
    {
        // STEP 1: Verify middleware is in the built pipeline by inspecting the ApplicationBuilder
        // STEP 2: Check for exceptions during pipeline construction
        // STEP 3: Use a custom middleware class instead of inline delegate
        Serilog.Log.Debug("[Pipeline] Starting ConfigureAspDotNetPipeline...");

        // PR-05: RFC 7807 ProblemDetails; in Production do not leak exception message; always include traceId
        app.UseExceptionHandler(a => a.Run(async context =>
        {
            var feature = context.Features.Get<IExceptionHandlerPathFeature>();
            if (feature?.Error != null)
            {
                var ex = feature.Error;
                var path = LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Path.Value);
                var traceId = context.TraceIdentifier;
                Serilog.Log.Error("[ExceptionHandler] Unhandled exception for {Method} {Path} traceId={TraceId}: {Exception}",
                    LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Method),
                    path,
                    traceId,
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!context.Response.HasStarted)
                {
                    int status;
                    string title;
                    string detail;
                    if (ex is FeatureNotImplementedException fe)
                    {
                        // §11: Incomplete features → 501 Not Implemented
                        status = 501;
                        title = "Not Implemented";
                        detail = fe.Message;
                    }
                    else if (ex is BadHttpRequestException { StatusCode: StatusCodes.Status413PayloadTooLarge })
                    {
                        status = StatusCodes.Status413PayloadTooLarge;
                        title = "Payload Too Large";
                        detail = "Request body too large.";
                    }
                    else
                    {
                        var env = context.RequestServices.GetService<Microsoft.AspNetCore.Hosting.IWebHostEnvironment>();
                        var isDev = env?.IsDevelopment() == true;
                        status = 500;
                        title = "Internal Server Error";
                        detail = isDev ? ex.ToString() : "An unexpected error occurred.";
                    }

                    var problem = new ProblemDetails { Status = status, Title = title, Detail = detail };
                    problem.Extensions["traceId"] = traceId;
                    context.Response.StatusCode = status;
                    context.Response.ContentType = "application/problem+json";
                    await context.Response.Body.WriteAsync(System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(problem));
                }
                else
                {
                    Serilog.Log.Warning("[ExceptionHandler] Response already started, cannot write error body for {Method} {Path} traceId={TraceId}",
                        context.Request.Method, path, traceId);
                }
            }
        }));

        if (optionsAtStartup.Web.Cors.Enabled && optionsAtStartup.Web.Cors.AllowedOrigins != null && optionsAtStartup.Web.Cors.AllowedOrigins.Length > 0)
        {
            app.UseCors("ConfiguredCors");
        }

        if (optionsAtStartup.Web.Https.Force)
        {
            app.UseHttpsRedirection();
            app.UseHsts();

            Serilog.Log.Information($"Forcing HTTP requests to HTTPS");
        }

        // Security middleware (rate limiting, violation tracking, etc.)
        // MUST be FIRST in pipeline (before UsePathBase) to catch path traversal and other attacks
        // This ensures we check the raw request path before any path rewriting occurs
        Serilog.Log.Debug("[Pipeline] About to call UseSlskdnSecurity (FIRST in pipeline)...");
        app.UseSlskdnSecurity();
        Serilog.Log.Debug("[Pipeline] UseSlskdnSecurity completed");

        // allow users to specify a custom path base, for use behind a reverse proxy
        var urlBase = optionsAtStartup.Web.UrlBase;
        urlBase = urlBase.StartsWith("/") ? urlBase : "/" + urlBase;

        // use urlBase. this effectively just removes urlBase from the path.
        // inject urlBase into any html files we serve, and rewrite links to ./static or /static to
        // prepend the url base.
        app.UsePathBase(urlBase);
        foreach (var (pattern, replacement) in WebHtmlRewriteRules.Create(urlBase))
        {
            app.UseHTMLRewrite(pattern, replacement);
        }

        // The main fix is making HTTP_ADDRESS configurable for proper binding
        app.UseHTMLInjection($"<script>window.urlBase=\"{urlBase}\";window.port={optionsAtStartup.Web.Port}</script>", excludedRoutes: new[] { "/api", "/swagger" });
        app.UseAuthentication();

        // CSRF token middleware - generates tokens for cookie-based auth
        // This must run after path-base rewriting and after authentication so tokens are bound to the
        // principal that will later be used for validation on state-changing requests.
        app.Use(async (context, next) =>
        {
            // Log all requests to MediaCore endpoints for debugging
            var path = context.Request.Path.Value ?? string.Empty;
            if (path.Contains("mediacore", StringComparison.OrdinalIgnoreCase))
            {
                Serilog.Log.Debug("[CSRF Middleware] Processing MediaCore request: {Method} {Path}",
                    context.Request.Method, LoggingSanitizer.SanitizeExternalIdentifier(path));
            }

            if (HttpMethods.IsGet(context.Request.Method) ||
                HttpMethods.IsHead(context.Request.Method) ||
                HttpMethods.IsOptions(context.Request.Method) ||
                HttpMethods.IsTrace(context.Request.Method))
            {
                try
                {
                    var antiforgery = context.RequestServices.GetRequiredService<Microsoft.AspNetCore.Antiforgery.IAntiforgery>();

                    if (Core.Security.AntiforgeryCookieRecovery.StripKnownCookiesFromRequest(context, optionsAtStartup.Web.Port))
                    {
                        Core.Security.AntiforgeryCookieRecovery.ClearKnownCookies(context, optionsAtStartup.Web.Port);
                    }

                    // When HTTPS is enabled, do not mint cookies from the optional HTTP listener. Browsers
                    // may reject Secure cookies set over HTTP, and the JWT-based UI does not need CSRF tokens there.
                    if (!context.Request.IsHttps && !optionsAtStartup.Web.Https.Disabled)
                    {
                        await next();
                        return;
                    }

                    // Only mint/store tokens on safe requests. Rotating them on the same unsafe request that
                    // later validates them can invalidate the frontend's header/cookie pair mid-flight.
                    var tokens = Core.Security.AntiforgeryCookieRecovery.TryGetAndStoreTokens(
                        context,
                        antiforgery,
                        optionsAtStartup.Web.Port,
                        path => Log.Warning("[CSRF Middleware] Cleared stale antiforgery cookies for {Path} after key-ring mismatch",
                            LoggingSanitizer.SanitizeExternalIdentifier(path)));

                    // ASP.NET stores the antiforgery cookie token using the configured Cookie.Name.
                    // Only publish the JavaScript-readable request token here.
                    if (tokens?.RequestToken != null)
                    {
                        context.Response.Cookies.Append($"XSRF-TOKEN-{optionsAtStartup.Web.Port}", tokens.RequestToken,
                            new CookieOptions
                            {
                                HttpOnly = false,  // JavaScript needs to read this
                                Secure = context.Request.IsHttps,
                                SameSite = SameSiteMode.Strict,
                                Path = "/",
                            });
                    }

                    // Clear the legacy request-token cookie so mixed old/new cookie sets cannot confuse the web client.
                    context.Response.Cookies.Delete("XSRF-TOKEN", new CookieOptions
                    {
                        Path = "/",
                        Secure = context.Request.IsHttps,
                        SameSite = SameSiteMode.Strict,
                    });
                }
                catch (Microsoft.AspNetCore.Antiforgery.AntiforgeryValidationException ex)
                {
                    // This is expected for some requests - log at debug level only
                    Serilog.Log.Debug("[CSRF Middleware] Antiforgery validation exception for {Method} {Path} (this is normal for some requests): {Exception}",
                        LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Method),
                        LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Path.Value),
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
                catch (Exception ex)
                {
                    // Log other exceptions but don't fail - GetAndStoreTokens can fail for some requests
                    Serilog.Log.Warning("[CSRF Middleware] Exception getting/storing tokens for {Method} {Path}: {Exception}",
                        LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Method),
                        LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Path.Value),
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }

            await next();
        });
        Serilog.Log.Information("Using base url {UrlBase}", urlBase);

        // serve static content from the configured path
        FileServerOptions? fileServerOptions = null;
        var contentPath = Path.Combine(AppContext.BaseDirectory, optionsAtStartup.Web.ContentPath);

        fileServerOptions = new FileServerOptions
        {
            FileProvider = StartupFileSystem.CreateOwnedPhysicalFileProvider(contentPath),
            RequestPath = string.Empty,
            EnableDirectoryBrowsing = false,
            EnableDefaultFiles = true,
        };

        // CRITICAL: Block suspicious paths at the file server level
        // This is the last line of defense before files are served
        fileServerOptions.StaticFileOptions.OnPrepareResponse = (context) =>
        {
            var path = context.Context.Request.Path.Value ?? string.Empty;
            var rawTarget = context.Context.Features.Get<Microsoft.AspNetCore.Http.Features.IHttpRequestFeature>()?.RawTarget ?? string.Empty;

            // Log static file requests for debugging
            Serilog.Log.Debug("[FILE_SERVER] Serving static file: {Path}, Status: {Status}",
                LoggingSanitizer.SanitizeExternalIdentifier(path), context.Context.Response.StatusCode);

            if (path.Contains("/etc/passwd") || path.Contains("/etc/") ||
                rawTarget.Contains("/etc/passwd") || rawTarget.Contains("/etc/") ||
                path.StartsWith("/etc", StringComparison.OrdinalIgnoreCase))
            {
                Serilog.Log.Warning("[FILE_SERVER_BLOCK] Blocking suspicious path: {Path}",
                    LoggingSanitizer.SanitizeExternalIdentifier(path));
                context.Context.Response.StatusCode = 400;
                context.Context.Response.ContentLength = 0;
            }
        };

        // Mesh gateway auth middleware (must be before UseRouting to catch /mesh paths)
        // This middleware blocks /mesh/* paths when gateway is disabled
        app.UseMiddleware<Mesh.ServiceFabric.MeshGatewayAuthMiddleware>();

        // PR-14: Capture POST /actors/.../inbox body for HTTP Signature verification (Digest) before model binding.
        // §8: Bounded read to prevent DoS; reject over MaxRemotePayloadSize with 413.
        app.UseWhen(
            ctx => string.Equals(ctx.Request.Method, "POST", StringComparison.OrdinalIgnoreCase)
                && ctx.Request.Path.StartsWithSegments("/actors", StringComparison.OrdinalIgnoreCase)
                && (ctx.Request.Path.Value ?? string.Empty).Contains("/inbox", StringComparison.OrdinalIgnoreCase),
            branch => branch.Use(async (ctx, next) =>
            {
                ctx.Request.EnableBuffering();
                var limit = ctx.RequestServices.GetService<IOptions<Mesh.MeshOptions>>()?.Value?.Security?.GetEffectiveMaxPayloadSize()
                    ?? slskd.Mesh.Transport.SecurityUtils.MaxRemotePayloadSize;
                if (ctx.Request.ContentLength.HasValue && ctx.Request.ContentLength.Value > limit)
                {
                    ctx.Response.StatusCode = 413;
                    return;
                }

                var buf = new byte[8192];
                int total = 0;
                using var ms = new MemoryStream();
                int n;
                while ((n = await ctx.Request.Body.ReadAsync(buf)) > 0)
                {
                    total += n;
                    if (total > limit)
                    {
                        ctx.Response.StatusCode = 413;
                        return;
                    }

                    ms.Write(buf, 0, n);
                }

                var b = ms.ToArray();
                ctx.Request.Body.Position = 0;
                ctx.Items["ActivityPubInboxBody"] = b;
                await next(ctx);
            }));

        app.UseRouting();
        if (optionsAtStartup.Web.RateLimiting.Enabled)
        {
            app.UseRateLimiter();
        }

        app.UseAuthorization();

        if (optionsAtStartup.Web.Logging)
        {
            app.UseSerilogRequestLogging(options =>
            {
                // Browser media elements and SignalR WebSocket clients cannot set an Authorization
                // header, so a handful of endpoints accept auth material in the query string
                // (?access_token=, ?token=, ?ticket=). Serilog's default request log records only
                // the path, but we enrich the diagnostic context with the query string here so it is
                // useful for debugging - and we MUST redact those secret values before they land in
                // our logs (and, from there, in any log-shipping or aggregation sink). Do not remove
                // the redaction without removing the query enrichment as well.
                options.EnrichDiagnosticContext = (diagnosticContext, httpContext) =>
                {
                    var query = httpContext.Request.QueryString;
                    if (query.HasValue)
                    {
                        diagnosticContext.Set("QueryString", RedactSensitiveQuery(query.Value));
                    }
                };
            });
        }

        // starting with .NET 7 the framework *really* wants you to use top level endpoint mapping
        // for whatever reason this breaks everything, and i just can't bring myself to care unless
        // UseEndpoints is going to be deprecated or if there's some material benefit
#pragma warning disable ASP0014 // Suggest using top level route registrations
        app.UseEndpoints(endpoints =>
        {
            endpoints.MapHub<ApplicationHub>("/hub/application");
            endpoints.MapHub<LogsHub>("/hub/logs");
            endpoints.MapHub<Transfers.API.TransfersHub>("/hub/transfers");
            var searchHub = endpoints.MapHub<SearchHub>("/hub/search");
            var songIdHub = endpoints.MapHub<slskd.SongID.API.SongIdHub>("/hub/songid");
            var listeningPartyHub = endpoints.MapHub<ListeningPartyHub>("/hub/listening-party");
            if (optionsAtStartup.Web.EnforceSecurity)
            {
                searchHub.RequireAuthorization(AuthPolicy.Any);
                songIdHub.RequireAuthorization(AuthPolicy.Any);
                listeningPartyHub.RequireAuthorization(AuthPolicy.Any);
            }

            var relayHub = endpoints.MapHub<RelayHub>("/hub/relay");
            if (optionsAtStartup.Web.EnforceSecurity)
            {
                relayHub.RequireAuthorization(AuthPolicy.Any);
            }

            endpoints.MapControllers();

            // Solid-OIDC Client ID document (must be anonymous and return application/ld+json)
            endpoints.MapGet("/solid/clientid.jsonld", async context =>
            {
                var opts = context.RequestServices.GetRequiredService<IOptionsMonitor<slskd.Options>>();
                if (!opts.CurrentValue.Feature.Solid)
                {
                    context.Response.StatusCode = StatusCodes.Status404NotFound;
                    return;
                }

                var svc = context.RequestServices.GetRequiredService<slskd.Solid.ISolidClientIdDocumentService>();
                context.Response.ContentType = "application/ld+json";
                await svc.WriteClientIdDocumentAsync(context, context.RequestAborted).ConfigureAwait(false);
            }).AllowAnonymous();

            // Make /health explicitly anonymous to avoid auth issues in E2E harness
            endpoints.MapHealthChecks("/health").AllowAnonymous();
            endpoints.MapHealthChecks("/health/mesh", new HealthCheckOptions
            {
                Predicate = check => check.Tags.Contains("mesh"),
            }).AllowAnonymous();

            // Simple readiness endpoint for E2E tests - just checks if server is listening
            // This bypasses complex health checks that might hang during startup
            endpoints.MapGet("/health/ready", async context =>
            {
                context.Response.StatusCode = 200;
                await context.Response.WriteAsync("ready");
            });

            // Test-only route listing endpoint for E2E diagnostics
            if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("SLSKDN_E2E_SHARE_ANNOUNCE")))
            {
                endpoints.MapGet("/__routes", async context =>
                {
                    var sources = context.RequestServices.GetRequiredService<IEnumerable<Microsoft.AspNetCore.Routing.EndpointDataSource>>();
                    var routes = sources
                        .SelectMany(s => s.Endpoints)
                        .OfType<Microsoft.AspNetCore.Routing.RouteEndpoint>()
                        .Select(e => new { Pattern = e.RoutePattern.RawText ?? e.RoutePattern.ToString(), e.DisplayName })
                        .OrderBy(r => r.Pattern)
                        .ToList();
                    context.Response.ContentType = "application/json";
                    await context.Response.WriteAsJsonAsync(routes);
                }).RequireAuthorization();
            }

            if (optionsAtStartup.Metrics.Enabled)
            {
                var options = optionsAtStartup.Metrics;
                var url = options.Url.StartsWith('/') ? options.Url : "/" + options.Url;

                Serilog.Log.Information("Publishing Prometheus metrics to {URL}", url);

                if (options.Authentication.Disabled)
                {
                    Serilog.Log.Warning("Authentication for the metrics endpoint is DISABLED");
                }
                else if (string.IsNullOrWhiteSpace(options.Authentication.Password))
                {
                    Serilog.Log.Warning("[LOW-05] Prometheus metrics endpoint password is empty. " +
                        "Set metrics.authentication.password to a strong value, or set metrics.authentication.disabled=true to opt out of auth explicitly.");
                }

                endpoints.MapGet(url, async context =>
                {
                    // at the time of writing, the prometheus library doesn't include a way to add authentication
                    // to the UseMetricServer() middleware. this is most likely a consequence of me mixing
                    // and matching minimal API stuff with controllers. if i ever straighten that out,
                    // this should be revisited.
                    if (!options.Authentication.Disabled)
                    {
                        static void Reject(HttpContext ctx)
                        {
                            ctx.Response.Headers.Append("WWW-Authenticate", "Basic realm=\"metrics\"");
                            ctx.Response.StatusCode = (int)HttpStatusCode.Unauthorized;
                        }

                        // LOW-05: refuse to authenticate when password is empty — forces explicit configuration
                        if (string.IsNullOrWhiteSpace(options.Authentication.Password))
                        {
                            context.Response.StatusCode = (int)HttpStatusCode.ServiceUnavailable;
                            await context.Response.WriteAsync("Metrics endpoint unavailable: authentication password is not configured.");
                            return;
                        }

                        var auth = context.Request.Headers["Authorization"].FirstOrDefault();
                        if (string.IsNullOrEmpty(auth) || !auth.StartsWith("Basic ", StringComparison.OrdinalIgnoreCase))
                        {
                            Reject(context);
                            return;
                        }

                        var providedBase64 = auth["Basic ".Length..].Trim();
                        if (string.IsNullOrEmpty(providedBase64))
                        {
                            Reject(context);
                            return;
                        }

                        byte[] providedBytes;
                        try
                        {
                            providedBytes = Convert.FromBase64String(providedBase64);
                        }
                        catch (FormatException)
                        {
                            Reject(context);
                            return;
                        }

                        var validBytes = Encoding.UTF8.GetBytes($"{options.Authentication.Username}:{options.Authentication.Password}");
                        if (!CryptographicOperations.FixedTimeEquals(providedBytes, validBytes))
                        {
                            Reject(context);
                            return;
                        }
                    }

                    List<Regex>? includeFilters;
                    List<Regex>? excludeFilters;
                    try
                    {
                        includeFilters = PrometheusMetricFilter.Compile(context.Request.Query["include"].ToArray(), "include");
                        excludeFilters = PrometheusMetricFilter.Compile(context.Request.Query["exclude"].ToArray(), "exclude");
                    }
                    catch (MetricsFilterValidationException exception)
                    {
                        context.Response.StatusCode = (int)HttpStatusCode.BadRequest;
                        await context.Response.WriteAsJsonAsync(new ProblemDetails
                        {
                            Status = (int)HttpStatusCode.BadRequest,
                            Title = "Invalid metrics filter",
                            Detail = exception.Message,
                        });
                        return;
                    }

                    var telemetryService = context.RequestServices.GetRequiredService<TelemetryService>();
                    string metricsAsText;
                    try
                    {
                        metricsAsText = await telemetryService.Prometheus.GetMetricsAsString(includeFilters, excludeFilters);
                    }
                    catch (RegexMatchTimeoutException)
                    {
                        context.Response.StatusCode = (int)HttpStatusCode.BadRequest;
                        await context.Response.WriteAsJsonAsync(new ProblemDetails
                        {
                            Status = (int)HttpStatusCode.BadRequest,
                            Title = "Metrics filter exceeded its evaluation time limit",
                            Detail = "Simplify the regular expression and try again.",
                        });
                        return;
                    }

                    context.Response.Headers.Append("Content-Type", "text/plain; version=0.0.4; charset=utf-8");
                    await context.Response.WriteAsync(metricsAsText);
                });
            }

            // SPA Fallback endpoint removed - using middleware instead (after file server)
            // This prevents the endpoint from intercepting static file requests
        });
#pragma warning restore ASP0014 // Suggest using top level route registrations

        // RESPONSE BODY FINALIZER: Ensures 4xx API responses have bodies (AFTER endpoints)
        // This is a workaround to fix empty response bodies for BadRequest/ProblemDetails
        // It buffers API responses and ensures the body is written even if other middleware clears it
        // Placed after UseEndpoints to catch what endpoints write and any middleware that runs after
        app.Use(async (ctx, next) =>
        {
            // Only buffer API routes to reduce overhead
            if (!ctx.Request.Path.StartsWithSegments("/api"))
            {
                await next();
                return;
            }

            var originalBody = ctx.Response.Body;

            await using var buffer = new MemoryStream();
            ctx.Response.Body = buffer;

            await next();

            // Restore original body
            ctx.Response.Body = originalBody;
            buffer.Position = 0;

            var bufferLen = buffer.Length;
            var statusCode = ctx.Response.StatusCode;
            var contentType = ctx.Response.ContentType;
            var contentLengthHeader = ctx.Response.ContentLength;

            // Log diagnostic info for API routes with 4xx status codes
            if (statusCode >= 400 && statusCode < 500)
            {
                Serilog.Log.Warning("[BodyFinalizer] {Method} {Path} -> {StatusCode} bufferLen={BufferLen} contentType={ContentType} contentLengthHeader={ContentLength}",
                    ctx.Request.Method, LoggingSanitizer.SanitizeExternalIdentifier(ctx.Request.Path.Value), statusCode, bufferLen,
                    contentType ?? "null", contentLengthHeader?.ToString() ?? "null");
            }

            // For 400-499 status codes, ensure the body is written
            if (statusCode >= 400 && statusCode < 500)
            {
                if (bufferLen > 0)
                {
                    // Body was written - ensure it's copied to original stream
                    // If Content-Length was set to 0 by another middleware, fix it
                    if (ctx.Response.ContentLength == 0 || ctx.Response.ContentLength == null)
                    {
                        ctx.Response.ContentLength = bufferLen;
                    }

                    await buffer.CopyToAsync(originalBody);
                }
                else
                {
                    // Body is empty - already logged above with diagnostic info
                }
            }
            else
            {
                // For other status codes, just copy the buffer if it has content
                if (bufferLen > 0)
                {
                    await buffer.CopyToAsync(originalBody);
                }
            }
        });

        // if this is an /api route and no API controller was matched, give up and return a 404.
        app.Use(async (context, next) =>
        {
            if (context.Request.Path.StartsWithSegments("/api"))
            {
                // Log 404s for API routes to help debug route mismatches
                Serilog.Log.Warning("[API404] {Method} {Path} - No matching endpoint found", context.Request.Method,
                    LoggingSanitizer.SanitizeExternalIdentifier(context.Request.Path.Value));
                context.Response.StatusCode = 404;
                return;
            }

            await next();
        });

        if (optionsAtStartup.Feature.Swagger)
        {
            app.UseSwagger();
            var apiVersionDescriptions = app.DescribeApiVersions();
            app.UseSwaggerUI(options => apiVersionDescriptions.ToList()
                .ForEach(description => options.SwaggerEndpoint($"{(urlBase == "/" ? string.Empty : urlBase)}/swagger/{description.GroupName}/swagger.json", description.GroupName)));

            Serilog.Log.Information("Publishing Swagger documentation to {URL}", "/swagger");
        }

        // Old SPA fallback middleware removed - using fallback after file server instead

        // UseFileServer is placed AFTER UseEndpoints to ensure routing happens first, then static files.
        // This prevents static file middleware from short-circuiting requests before routing/security middleware runs.
        if (!optionsAtStartup.Headless)
        {
            // Revalidate HTML after deployments so clients pick up the current asset manifest.
            app.Use(async (context, next) =>
            {
                context.Response.OnStarting(() =>
                {
                    if (context.Response.StatusCode == StatusCodes.Status200OK &&
                        context.Response.ContentType?.StartsWith("text/html", StringComparison.OrdinalIgnoreCase) == true)
                    {
                        context.Response.Headers["Cache-Control"] = "no-cache";
                    }

                    return Task.CompletedTask;
                });

                await next();
            });

            app.UseFileServer(fileServerOptions);
            Serilog.Log.Information("Serving static content from {ContentPath}", contentPath);

            // SPA Fallback: Serve index.html for client-side routes AFTER file server
            // This runs AFTER file server so static files are served first, and only 404s get index.html
            var indexPath = Path.Combine(AppContext.BaseDirectory, optionsAtStartup.Web.ContentPath, "index.html");
            if (System.IO.File.Exists(indexPath))
            {
                app.Use(async (context, next) =>
                {
                    await next(); // Let file server try first

                    // If file server returned 404 and this is a client-side route, serve index.html
                    if (context.Response.StatusCode == 404 && !context.Response.HasStarted)
                    {
                        var path = context.Request.Path.Value ?? string.Empty;

                        // Only serve index.html for non-API, non-file, non-static paths
                        var isApi = path.StartsWith("/api", StringComparison.OrdinalIgnoreCase);
                        var isSwagger = path.StartsWith("/swagger", StringComparison.OrdinalIgnoreCase);
                        var isHub = path.StartsWith("/hub", StringComparison.OrdinalIgnoreCase);
                        var isHealth = path.StartsWith("/health", StringComparison.OrdinalIgnoreCase);
                        var isStatic = path.StartsWith("/static", StringComparison.OrdinalIgnoreCase);
                        var hasExtension = Path.GetExtension(path) != string.Empty;

                        if (!isApi && !isSwagger && !isHub && !isHealth && !isStatic && !hasExtension)
                        {
                            Serilog.Log.Debug("[SPA Fallback Middleware] Serving index.html for {Path} (file server returned 404)",
                                LoggingSanitizer.SanitizeExternalIdentifier(path));
                            context.Response.StatusCode = 200;
                            context.Response.ContentType = "text/html; charset=utf-8";
                            await context.Response.SendFileAsync(indexPath);
                        }
                    }
                });
                Serilog.Log.Information("[SPA] Registered fallback to index.html for client-side routing (after file server)");
            }
        }
        else
        {
            Serilog.Log.Warning("Running in headless mode; web UI is DISABLED");
        }

        return app;
    }

    // Query-string parameter names whose values are authentication/authorization material and must
    // never be written to logs. Compared case-insensitively.
    private static readonly HashSet<string> SensitiveQueryKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "access_token", "token", "ticket", "api_key", "apikey", "key", "password", "secret", "sig", "signature",
    };

    /// <summary>
    ///     Returns <paramref name="queryString"/> with the values of known secret parameters replaced by
    ///     <c>REDACTED</c>, so auth material passed in the query string (required by browser media elements
    ///     and SignalR clients that cannot set headers) never reaches the logs. Parameter names are kept so
    ///     the log still shows which auth mechanism was used.
    /// </summary>
    private static string RedactSensitiveQuery(string queryString)
    {
        if (string.IsNullOrEmpty(queryString))
        {
            return queryString;
        }

        var trimmed = queryString.StartsWith('?') ? queryString[1..] : queryString;
        var parts = trimmed.Split('&');
        for (var i = 0; i < parts.Length; i++)
        {
            var separator = parts[i].IndexOf('=');
            var name = separator >= 0 ? parts[i][..separator] : parts[i];
            if (SensitiveQueryKeys.Contains(Uri.UnescapeDataString(name)))
            {
                parts[i] = name + "=REDACTED";
            }
        }

        return "?" + string.Join('&', parts);
    }

}
