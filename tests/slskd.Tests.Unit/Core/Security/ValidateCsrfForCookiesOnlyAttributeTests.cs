// <copyright file="ValidateCsrfForCookiesOnlyAttributeTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Core.Security;

using System;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Abstractions;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Moq;
using slskd.Core.Security;
using Xunit;

public class ValidateCsrfForCookiesOnlyAttributeTests
{
    [Fact]
    public async Task OnAuthorizationAsync_WithCookieAndQueryApiKey_StillValidatesAntiforgery()
    {
        var antiforgery = new Mock<IAntiforgery>();
        var services = new ServiceCollection()
            .AddSingleton(antiforgery.Object)
            .BuildServiceProvider();
        var httpContext = new DefaultHttpContext
        {
            RequestServices = services
        };
        httpContext.Request.Method = "POST";
        httpContext.Request.Path = "/api/v0/test";
        httpContext.Request.QueryString = new QueryString("?api_key=query-only");
        httpContext.Request.Headers.Cookie = "slskd-session=abc";

        var actionContext = new ActionContext(httpContext, new RouteData(), new ActionDescriptor());
        var filterContext = new AuthorizationFilterContext(actionContext, Array.Empty<IFilterMetadata>());

        await new ValidateCsrfForCookiesOnlyAttribute().OnAuthorizationAsync(filterContext);

        antiforgery.Verify(mock => mock.ValidateRequestAsync(httpContext), Times.Once);
        Assert.Null(filterContext.Result);
    }

    [Fact]
    public async Task OnAuthorizationAsync_WithBasicAuthorizationWithoutCookies_StillValidatesAntiforgery()
    {
        var antiforgery = new Mock<IAntiforgery>();
        antiforgery
            .Setup(mock => mock.ValidateRequestAsync(It.IsAny<HttpContext>()))
            .ThrowsAsync(new AntiforgeryValidationException("A request token is required."));
        var services = new ServiceCollection()
            .AddSingleton(antiforgery.Object)
            .BuildServiceProvider();
        var httpContext = new DefaultHttpContext
        {
            RequestServices = services
        };
        httpContext.Request.Method = "POST";
        httpContext.Request.Path = "/api/v0/test";
        httpContext.Request.Headers.Authorization = "Basic dXNlcjpwYXNz";

        var actionContext = new ActionContext(httpContext, new RouteData(), new ActionDescriptor());
        var filterContext = new AuthorizationFilterContext(actionContext, Array.Empty<IFilterMetadata>());

        await new ValidateCsrfForCookiesOnlyAttribute().OnAuthorizationAsync(filterContext);

        antiforgery.Verify(mock => mock.ValidateRequestAsync(httpContext), Times.Once);
        var result = Assert.IsType<BadRequestObjectResult>(filterContext.Result);
        Assert.Equal(StatusCodes.Status400BadRequest, result.StatusCode);
    }
}
