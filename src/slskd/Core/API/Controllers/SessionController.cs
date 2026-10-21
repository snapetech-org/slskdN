// <copyright file="SessionController.cs" company="slskd Team">
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

// <copyright file="SessionController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Core.API
{
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authentication;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Serilog;
    using slskd.Authentication;
    using slskd.Core.Security;

    /// <summary>
    ///     Session.
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class SessionController : ControllerBase
    {
        private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, (int Failures, DateTimeOffset LastFailure, DateTimeOffset? LockoutUntil)> _loginAttempts = new();
        private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, (int Failures, DateTimeOffset LastFailure, DateTimeOffset? LockoutUntil)> _credentialLoginAttempts = new(StringComparer.OrdinalIgnoreCase);
        private const int MaxFailures = 5;
        private const int MaxTrackedLoginAttempts = 10000;
        private static readonly TimeSpan LockoutDuration = TimeSpan.FromMinutes(5);
        private static readonly TimeSpan WindowDuration = TimeSpan.FromMinutes(10);

        public SessionController(
            ISecurityService securityService,
            IOptionsSnapshot<Options> optionsSnapshot,
            OptionsAtStartup optionsAtStartup)
        {
            Security = securityService;
            OptionsSnapshot = optionsSnapshot;
            OptionsAtStartup = optionsAtStartup;
        }

        private IOptionsSnapshot<Options> OptionsSnapshot { get; set; }
        private OptionsAtStartup OptionsAtStartup { get; set; }
        private ISecurityService Security { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<SessionController>();

        /// <summary>
        ///     Checks whether the provided authentication is valid.
        /// </summary>
        /// <remarks>This is a no-op provided so that the application can test for an expired token on load.</remarks>
        /// <returns></returns>
        /// <response code="200">The authentication is valid.</response>
        /// <response code="403">The authentication is is invalid.</response>
        [HttpGet]
        [Route("")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        [ProducesResponseType(401)]
        public IActionResult Check()
        {
            return Ok();
        }

        /// <summary>
        ///     Checks whether security is enabled.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">True if security is enabled, false otherwise.</response>
        [HttpGet]
        [Route("enabled")]
        [AllowAnonymous]
        [ProducesResponseType(typeof(bool), 200)]
        public IActionResult Enabled()
        {
            return Ok(!OptionsAtStartup.Web.Authentication.Disabled);
        }

        /// <summary>
        ///     Checks whether OIDC browser sign-in is configured.
        /// </summary>
        [HttpGet]
        [Route("oidc/enabled")]
        [AllowAnonymous]
        [ProducesResponseType(typeof(object), 200)]
        public IActionResult OidcEnabled()
        {
            var oidc = OptionsAtStartup.Web.Authentication.Oidc;
            var enabled = !OptionsAtStartup.Headless && !OptionsAtStartup.Web.Authentication.Disabled &&
                !string.IsNullOrWhiteSpace(oidc.IssuerUrl) &&
                !string.IsNullOrWhiteSpace(oidc.ClientId) &&
                !string.IsNullOrWhiteSpace(oidc.ClientSecret) &&
                !string.IsNullOrWhiteSpace(oidc.RedirectUri);
            return Ok(new { enabled, provider = oidc.Provider });
        }

        /// <summary>
        ///     Starts the OpenID Connect authorization-code sign-in flow.
        /// </summary>
        [HttpGet]
        [Route("oidc")]
        [AllowAnonymous]
        [ProducesResponseType(302)]
        public IActionResult OidcLogin([FromQuery] string? returnUrl = null)
        {
            var oidc = OptionsAtStartup.Web.Authentication.Oidc;
            if (OptionsAtStartup.Headless || OptionsAtStartup.Web.Authentication.Disabled ||
                string.IsNullOrWhiteSpace(oidc.IssuerUrl) ||
                string.IsNullOrWhiteSpace(oidc.ClientId) ||
                string.IsNullOrWhiteSpace(oidc.ClientSecret) ||
                string.IsNullOrWhiteSpace(oidc.RedirectUri))
            {
                return NotFound();
            }

            var pathBase = Request.PathBase.Value ?? string.Empty;
            var fallback = $"{pathBase}/";
            var candidate = returnUrl?.Trim();
            var isLocalPath = !string.IsNullOrWhiteSpace(candidate) &&
                              candidate.StartsWith("/", StringComparison.Ordinal) &&
                              !candidate.StartsWith("//", StringComparison.Ordinal) &&
                              Url.IsLocalUrl(candidate);
            var isWithinPathBase = string.IsNullOrEmpty(pathBase) ||
                                   candidate == pathBase ||
                                   candidate?.StartsWith(pathBase + "/", StringComparison.Ordinal) == true;
            var safeReturnUrl = isLocalPath && isWithinPathBase ? candidate! : fallback;

            return Challenge(
                new AuthenticationProperties { RedirectUri = safeReturnUrl },
                slskd.Bootstrap.WebServiceCollectionExtensions.OidcAuthenticationScheme);
        }

        /// <summary>
        ///     Logs out, revoking the current JWT.
        /// </summary>
        /// <returns></returns>
        /// <response code="204">Logout successful.</response>
        // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- DELETE is non-simple; cookie auth is covered by ValidateCsrfForCookiesOnly.
        [HttpDelete]
        [Route("")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public IActionResult Logout()
        {
            var jti = User.FindFirst(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Jti)?.Value;
            var exp = User.FindFirst(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Exp)?.Value;
            if (!string.IsNullOrEmpty(jti)
                && long.TryParse(exp, System.Globalization.NumberStyles.None, System.Globalization.CultureInfo.InvariantCulture, out var expiresAtUnixSeconds))
            {
                Security.RevokeToken(
                    jti,
                    DateTimeOffset.FromUnixTimeSeconds(expiresAtUnixSeconds).Add(SecurityService.JwtClockSkew));
            }

            return NoContent();
        }

        /// <summary>
        ///     Logs in.
        /// </summary>
        /// <param name="login"></param>
        /// <returns></returns>
        /// <response code="200">Login was successful.</response>
        /// <response code="400">Bad request.</response>
        /// <response code="401">Login failed.</response>
        // nosemgrep: csharp.dotnet.security.mvc-missing-antiforgery.mvc-missing-antiforgery -- Controller-level Consumes(application/json) and ValidateCsrfForCookiesOnly block simple cross-site form login.
        [HttpPost]
        [Route("")]
        [AllowAnonymous]
        [ProducesResponseType(typeof(TokenResponse), 200)]
        [ProducesResponseType(400)]
        [ProducesResponseType(401)]
        [ProducesResponseType(typeof(string), 500)]
        public IActionResult Login([FromBody] LoginRequest login)
        {
            if (login == default)
            {
                return BadRequest();
            }

            login.Username = login.Username?.Trim() ?? string.Empty;
            login.Password ??= string.Empty;

            if (OptionsAtStartup.Headless)
            {
                Log.Warning("Login from {User} rejected; web UI is DISABLED when running in headless mode", login.Username);
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(login.Username) || string.IsNullOrWhiteSpace(login.Password))
            {
                return BadRequest("Username and/or Password missing or invalid");
            }

            var normalizedUsername = login.Username;
            var normalizedPassword = login.Password;
            var remoteIp = HttpContext?.Connection?.RemoteIpAddress?.ToString() ?? "unknown";
            var credentialAttemptKey = $"{normalizedUsername}\n{remoteIp}";
            PruneLoginAttempts();

            // Check for active lockout by IP (defends single-source spam)
            if (_loginAttempts.TryGetValue(remoteIp, out var existing) && existing.LockoutUntil.HasValue && existing.LockoutUntil.Value > DateTimeOffset.UtcNow)
            {
                Log.Warning("Login from {RemoteIp} rejected; IP is locked out until {LockoutUntil}", remoteIp, existing.LockoutUntil.Value);
                return StatusCode(429, "Too many failed login attempts. Try again later.");
            }

            // Never create a global username reservation from unauthenticated traffic.
            // Credential throttling is scoped to the normalized username and request source.
            if (_credentialLoginAttempts.TryGetValue(credentialAttemptKey, out var credentialExisting) && credentialExisting.LockoutUntil.HasValue && credentialExisting.LockoutUntil.Value > DateTimeOffset.UtcNow)
            {
                Log.Warning("Login for {User} from {RemoteIp} rejected until {LockoutUntil}", normalizedUsername, remoteIp, credentialExisting.LockoutUntil.Value);
                return StatusCode(429, "Too many failed login attempts. Try again later.");
            }

            if (Security.AuthenticateAdminCredentials(normalizedUsername, normalizedPassword))
            {
                // Successful login: clear both source-IP and source-scoped credential counters.
                _loginAttempts.TryRemove(remoteIp, out _);
                _credentialLoginAttempts.TryRemove(credentialAttemptKey, out _);
                return Ok(new TokenResponse(Security.GenerateJwt(normalizedUsername, Role.Administrator)));
            }

            // Failed login: increment IP counter and potentially lock out
            _loginAttempts.AddOrUpdate(
                remoteIp,
                _ => (1, DateTimeOffset.UtcNow, null),
                (_, prev) =>
                {
                    // Reset window if last failure was outside the window
                    var failures = (DateTimeOffset.UtcNow - prev.LastFailure) > WindowDuration ? 1 : prev.Failures + 1;
                    DateTimeOffset? lockout = failures >= MaxFailures ? DateTimeOffset.UtcNow.Add(LockoutDuration) : null;
                    return (failures, DateTimeOffset.UtcNow, lockout);
                });

            // Failed login: increment only the source-scoped credential bucket.
            _credentialLoginAttempts.AddOrUpdate(
                credentialAttemptKey,
                _ => (1, DateTimeOffset.UtcNow, null),
                (_, prev) =>
                {
                    var failures = (DateTimeOffset.UtcNow - prev.LastFailure) > WindowDuration ? 1 : prev.Failures + 1;
                    DateTimeOffset? lockout = failures >= MaxFailures ? DateTimeOffset.UtcNow.Add(LockoutDuration) : null;
                    return (failures, DateTimeOffset.UtcNow, lockout);
                });

            return Unauthorized();
        }

        private static void PruneLoginAttempts()
        {
            Prune(_loginAttempts);
            Prune(_credentialLoginAttempts);
        }

        private static void Prune(System.Collections.Concurrent.ConcurrentDictionary<string, (int Failures, DateTimeOffset LastFailure, DateTimeOffset? LockoutUntil)> attempts)
        {
            var now = DateTimeOffset.UtcNow;
            foreach (var item in attempts)
            {
                if ((!item.Value.LockoutUntil.HasValue && now - item.Value.LastFailure > WindowDuration) ||
                    (item.Value.LockoutUntil.HasValue && item.Value.LockoutUntil.Value <= now))
                {
                    attempts.TryRemove(item.Key, out _);
                }
            }

            if (attempts.Count <= MaxTrackedLoginAttempts)
            {
                return;
            }

            foreach (var item in attempts.OrderBy(x => x.Value.LastFailure).Take(attempts.Count - MaxTrackedLoginAttempts))
            {
                attempts.TryRemove(item.Key, out _);
            }
        }
    }
}
