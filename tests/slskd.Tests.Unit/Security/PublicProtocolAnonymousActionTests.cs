// <copyright file="PublicProtocolAnonymousActionTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Security;

using System;
using System.Linq;
using System.Reflection;
using Microsoft.AspNetCore.Authorization;
using slskd.Core.API;
using slskd.Core.Security;
using slskd.Identity.API;
using slskd.SocialFederation.API;
using slskd.Streaming;
using Xunit;

public class PublicProtocolAnonymousActionTests
{
    [Fact]
    public void SessionController_OnlyPublicBootstrapActions_AreAnonymous()
    {
        AssertAnonymousActions(
            typeof(SessionController),
            nameof(SessionController.Enabled),
            nameof(SessionController.Login),
            nameof(SessionController.OidcEnabled),
            nameof(SessionController.OidcLogin));
    }

    [Fact]
    public void ApplicationController_OnlyPublicBuildMetadata_IsAnonymous()
    {
        AssertAnonymousActions(
            typeof(ApplicationController),
            nameof(ApplicationController.GetBuild));
    }

    [Fact]
    public void ProfileController_OnlyPublicProfileLookup_IsAnonymous()
    {
        AssertAnonymousActions(
            typeof(ProfileController),
            nameof(ProfileController.GetProfile));
    }

    [Fact]
    public void StreamingController_RemainsAnonymousForTokenBackedTransport()
    {
        AssertControllerRequiresAuthenticationByDefault(typeof(StreamsController));
        AssertAnonymousActions(
            typeof(StreamsController),
            nameof(StreamsController.CreateShareTicket),
            nameof(StreamsController.Get),
            nameof(StreamsController.Transcode));
    }

    [Fact]
    public void FederationControllers_RemainAnonymousForProtocolDiscoveryAndDelivery()
    {
        AssertControllerRequiresAuthenticationByDefault(typeof(ActivityPubController));
        AssertAnonymousActions(
            typeof(ActivityPubController),
            nameof(ActivityPubController.GetActor),
            nameof(ActivityPubController.GetFollowers),
            nameof(ActivityPubController.GetFollowing),
            nameof(ActivityPubController.PostToInbox),
            nameof(ActivityPubController.GetOutbox));

        AssertAdministratorAction(typeof(ActivityPubController), nameof(ActivityPubController.GetInbox));

        AssertControllerRequiresAuthenticationByDefault(typeof(WebFingerController));
        AssertAnonymousActions(
            typeof(WebFingerController),
            nameof(WebFingerController.GetWebFinger));
    }

    private static void AssertControllerRequiresAuthenticationByDefault(Type controllerType)
    {
        var hasAllowAnonymous = controllerType
            .GetCustomAttributes(typeof(AllowAnonymousAttribute), inherit: true)
            .Any();
        var authorize = controllerType
            .GetCustomAttributes(typeof(AuthorizeAttribute), inherit: true)
            .Cast<AuthorizeAttribute>()
            .SingleOrDefault();

        Assert.False(hasAllowAnonymous, $"{controllerType.Name} should not allow anonymous access at controller scope.");
        Assert.NotNull(authorize);
        Assert.Equal(AuthPolicy.Any, authorize!.Policy);
    }

    private static void AssertAnonymousActions(Type controllerType, params string[] expectedAnonymousActionNames)
    {
        var publicInstanceActions = controllerType
            .GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly)
            .Where(method => method.IsPublic && !method.IsSpecialName)
            .Where(method => method.GetCustomAttributes().Any(attribute => attribute.GetType().Name.StartsWith("Http", StringComparison.Ordinal)))
            .ToArray();

        var actualAnonymousActionNames = publicInstanceActions
            .Where(method => method.GetCustomAttributes(typeof(AllowAnonymousAttribute), inherit: true).Any())
            .Select(method => method.Name)
            .OrderBy(name => name, StringComparer.Ordinal)
            .ToArray();

        var expected = expectedAnonymousActionNames
            .OrderBy(name => name, StringComparer.Ordinal)
            .ToArray();

        Assert.Equal(expected, actualAnonymousActionNames);
    }

    private static void AssertAdministratorAction(Type controllerType, string actionName)
    {
        var action = controllerType.GetMethod(actionName, BindingFlags.Instance | BindingFlags.Public)
            ?? throw new InvalidOperationException($"{controllerType.Name}.{actionName} was not found.");
        var authorize = action
            .GetCustomAttributes(typeof(AuthorizeAttribute), inherit: true)
            .Cast<AuthorizeAttribute>()
            .Single();

        Assert.Equal(AuthPolicy.Any, authorize.Policy);
        Assert.Equal(AuthRole.AdministratorOnly, authorize.Roles);
        Assert.Empty(action.GetCustomAttributes(typeof(AllowAnonymousAttribute), inherit: true));
    }
}
