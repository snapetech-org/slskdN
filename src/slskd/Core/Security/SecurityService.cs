// <copyright file="SecurityService.cs" company="slskd Team">
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

// <copyright file="SecurityService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd
{
    using System;
    using System.Collections.Generic;
    using System.IdentityModel.Tokens.Jwt;
    using System.Linq;
    using System.Net;
    using System.Security.Claims;
    using Microsoft.IdentityModel.Tokens;
    using NetTools;
    using slskd.Authentication;

    public interface ISecurityService
    {
        JwtSecurityToken GenerateJwt(
            string username,
            Role role,
            int? ttl = null,
            string[]? scopes = null,
            IEnumerable<Claim>? additionalClaims = null);
        bool AuthenticateAdminCredentials(string username, string password);
        (string Name, Role Role, string[] Scopes) AuthenticateWithApiKey(string key, IPAddress callerIpAddress);
        void RevokeToken(string jti, DateTimeOffset expiresAt);
        bool IsTokenRevoked(string jti);
    }

    /// <summary>
    ///     Well-known claim types and scope values used by the authentication pipeline.
    /// </summary>
    /// <remarks>
    ///     HARDENING-2026-04-20 H13: scopes let an API key (or a JWT derived from one) be
    ///     restricted to specific endpoints — e.g., a Plex webhook key that can only POST to
    ///     <c>/api/v0/NowPlaying/webhook</c>.
    /// </remarks>
    public static class SlskdClaims
    {
        /// <summary>The JWT / claims key used to carry scope tags. Multi-valued.</summary>
        public const string ScopeClaim = "slskd:scope";

        /// <summary>Wildcard scope granting access to every scope-gated endpoint.</summary>
        public const string ScopeAll = "*";
    }

    public class SecurityService : ISecurityService
    {
        public static readonly TimeSpan JwtClockSkew = TimeSpan.FromMinutes(5);
        private readonly Core.Security.JwtRevocationStore _revocationStore;
        public SecurityService(
            SymmetricSecurityKey jwtSigningKey,
            OptionsAtStartup optionsAtStartup,
            IOptionsMonitor<Options> optionsMonitor,
            Core.Security.JwtRevocationStore revocationStore)
        {
            JwtSigningKey = jwtSigningKey;
            OptionsAtStartup = optionsAtStartup;
            OptionsMonitor = optionsMonitor;
            _revocationStore = revocationStore;
        }

        private SymmetricSecurityKey JwtSigningKey { get; }
        private OptionsAtStartup OptionsAtStartup { get; }
        private IOptionsMonitor<Options> OptionsMonitor { get; }

        public bool AuthenticateAdminCredentials(string username, string password)
        {
            var configuredUsername = OptionsMonitor.CurrentValue.Web.Authentication.Username?.Trim() ?? string.Empty;
            var configuredPassword = OptionsMonitor.CurrentValue.Web.Authentication.Password?.Trim() ?? string.Empty;

            return ConstantTimeEqual(configuredUsername, username) && ConstantTimeEqual(configuredPassword, password);
        }

        public (string Name, Role Role, string[] Scopes) AuthenticateWithApiKey(string key, IPAddress callerIpAddress)
        {
            callerIpAddress = callerIpAddress.NormalizeMappedIPv4();

            var inputKeyBytes = System.Text.Encoding.UTF8.GetBytes(key ?? string.Empty);
            var record = OptionsMonitor.CurrentValue.Web.Authentication.ApiKeys
                .FirstOrDefault(k =>
                {
                    var storedKeyBytes = System.Text.Encoding.UTF8.GetBytes(k.Value.Key ?? string.Empty);
                    var padLen = Math.Max(inputKeyBytes.Length, storedKeyBytes.Length);
                    var aPad = new byte[padLen];
                    var bPad = new byte[padLen];
                    inputKeyBytes.CopyTo(aPad, 0);
                    storedKeyBytes.CopyTo(bPad, 0);
                    return System.Security.Cryptography.CryptographicOperations.FixedTimeEquals(aPad, bPad);
                });

            if (record.Key == null)
            {
                throw new NotFoundException($"The provided API key does not match an existing key");
            }

            var isCallerInRange = false;

            foreach (var cidr in record.Value.Cidr.Split(','))
            {
                if (!string.IsNullOrWhiteSpace(cidr) && IPAddressRange.TryParse(cidr, out var range) && range.Contains(callerIpAddress))
                {
                    isCallerInRange = true;
                    break;
                }
            }

            if (!isCallerInRange)
            {
                throw new OutOfRangeException("The remote IP address is not within the range specified for the key");
            }

            var scopes = (record.Value.Scopes ?? SlskdClaims.ScopeAll)
                .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                .Where(s => !string.IsNullOrWhiteSpace(s))
                .ToArray();

            if (scopes.Length == 0)
            {
                scopes = new[] { SlskdClaims.ScopeAll };
            }

            return (record.Key, record.Value.Role.ToEnum<Role>(), scopes);
        }

        private static bool ConstantTimeEqual(string expected, string provided)
        {
            var expectedBytes = System.Text.Encoding.UTF8.GetBytes(expected ?? string.Empty);
            var providedBytes = System.Text.Encoding.UTF8.GetBytes(provided ?? string.Empty);
            var padLen = Math.Max(expectedBytes.Length, providedBytes.Length);
            var expectedPad = new byte[padLen];
            var providedPad = new byte[padLen];
            expectedBytes.CopyTo(expectedPad, 0);
            providedBytes.CopyTo(providedPad, 0);
            return System.Security.Cryptography.CryptographicOperations.FixedTimeEquals(expectedPad, providedPad);
        }

        public void RevokeToken(string jti, DateTimeOffset expiresAt)
        {
            _revocationStore.Revoke(jti, expiresAt);
        }

        public bool IsTokenRevoked(string jti)
        {
            return _revocationStore.IsRevoked(jti);
        }

        public JwtSecurityToken GenerateJwt(
            string username,
            Role role,
            int? ttl = null,
            string[]? scopes = null,
            IEnumerable<Claim>? additionalClaims = null)
        {
            var issuedUtc = DateTime.UtcNow;
            var expiresUtc = DateTime.UtcNow.AddMilliseconds(ttl ?? OptionsAtStartup.Web.Authentication.Jwt.Ttl);
            var jti = Guid.NewGuid().ToString("N");

            var claims = new List<Claim>()
            {
                new Claim(JwtRegisteredClaimNames.Jti, jti),
                new Claim(ClaimTypes.Name, username),
                new Claim(ClaimTypes.NameIdentifier, jti),
                new Claim(ClaimTypes.Role, role.ToString()),
                new Claim("name", username),
                new Claim("iat", ((DateTimeOffset)issuedUtc).ToUnixTimeSeconds().ToString()),
            };

            // HARDENING-2026-04-20 H13: persist scopes on the JWT so the API-key→short-JWT promotion
            // path in Program.cs doesn't accidentally upgrade a scope-limited key into full access.
            // Tokens with no explicit scopes (e.g. admin password login) are universal.
            var effectiveScopes = (scopes == null || scopes.Length == 0)
                ? new[] { SlskdClaims.ScopeAll }
                : scopes;
            foreach (var scope in effectiveScopes)
            {
                claims.Add(new Claim(SlskdClaims.ScopeClaim, scope));
            }

            if (additionalClaims != null)
            {
                claims.AddRange(additionalClaims);
            }

            var credentials = new SigningCredentials(JwtSigningKey, SecurityAlgorithms.HmacSha256);

            var token = new JwtSecurityToken(
                issuer: Program.AppName,
                audience: Program.AppName,
                claims: claims,
                notBefore: issuedUtc,
                expires: expiresUtc,
                signingCredentials: credentials);

            return token;
        }
    }
}
