// <copyright file="WebServiceCollectionExtensionsTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Bootstrap;

using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.Tokens;
using Moq;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Net;
using slskd.Authentication;
using slskd.Bootstrap;
using Xunit;

public class WebServiceCollectionExtensionsTests
{
    [Theory]
    [InlineData("/library")]
    [InlineData("/library?next=/settings")]
    [InlineData("/")]
    public void IsSafeLocalRedirectUrl_accepts_local_paths(string url)
    {
        Assert.True(WebServiceCollectionExtensions.IsSafeLocalRedirectUrl(url));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("relative/path")]
    [InlineData("https://attacker.example")]
    [InlineData("//attacker.example")]
    [InlineData("/\\\\attacker.example")]
    [InlineData("/safe\\\\..\\\\attacker.example")]
    [InlineData("/safe\r\nLocation: https://attacker.example")]
    public void IsSafeLocalRedirectUrl_rejects_external_or_malformed_paths(string? url)
    {
        Assert.False(WebServiceCollectionExtensions.IsSafeLocalRedirectUrl(url));
    }

    [Fact]
    public void SelectAuthenticationScheme_uses_api_key_scheme_for_api_key_header()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers["X-API-Key"] = "configured-key";

        var scheme = WebServiceCollectionExtensions.SelectAuthenticationScheme(context);

        Assert.Equal(ApiKeyAuthentication.AuthenticationScheme, scheme);
    }

    [Fact]
    public void SelectAuthenticationScheme_uses_jwt_scheme_without_api_key_header()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers.Authorization = "Bearer token";

        var scheme = WebServiceCollectionExtensions.SelectAuthenticationScheme(context);

        Assert.Equal(JwtBearerDefaults.AuthenticationScheme, scheme);
    }

    [Fact]
    public void PromoteApiKeyToJwt_UsesApiKeyIdentityForSignalRQueryTokens()
    {
        var security = new Mock<ISecurityService>();
        var jwt = new JwtSecurityToken(
            issuer: "issuer",
            audience: "audience",
            claims: new[] { new Claim(ClaimTypes.Name, "operator") },
            notBefore: DateTime.UtcNow,
            expires: DateTime.UtcNow.AddMinutes(1),
            signingCredentials: new SigningCredentials(
                new SymmetricSecurityKey(new byte[32]),
                SecurityAlgorithms.HmacSha256));
        security
            .Setup(service => service.AuthenticateWithApiKey("configured-key", It.IsAny<IPAddress>()))
            .Returns(("operator", Role.Administrator, new[] { SlskdClaims.ScopeAll }));
        security
            .Setup(service => service.GenerateJwt("operator", Role.Administrator, 1000, It.IsAny<string[]>()))
            .Returns(jwt);

        var services = new ServiceCollection();
        services.AddSingleton(security.Object);
        var context = new DefaultHttpContext
        {
            RequestServices = services.BuildServiceProvider(),
        };
        context.Connection.RemoteIpAddress = IPAddress.Loopback;

        var promoted = WebServiceCollectionExtensions.PromoteApiKeyToJwt(context, "configured-key");

        Assert.Equal(jwt.Serialize(), promoted);
        security.Verify(service => service.AuthenticateWithApiKey("configured-key", IPAddress.Loopback), Times.Once);
    }
}
