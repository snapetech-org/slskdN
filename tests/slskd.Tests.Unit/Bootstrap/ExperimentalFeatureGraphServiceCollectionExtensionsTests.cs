// <copyright file="ExperimentalFeatureGraphServiceCollectionExtensionsTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Bootstrap;

using System.IO;
using System.Linq;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using slskd.Bootstrap;
using Xunit;

[Collection("ProgramAppDirectory")]
public sealed class ExperimentalFeatureGraphServiceCollectionExtensionsTests
{
    [Fact]
    public void AddSlskdExperimentalFeatureGraph_RegistersSingleOwnerServicesOnce()
    {
        var temporaryDirectory = Directory.CreateTempSubdirectory("slskdn-registration-").FullName;
        var appDirectoryProperty = typeof(Program).GetProperty(nameof(Program.AppDirectory))!;
        var setAppDirectory = appDirectoryProperty.GetSetMethod(nonPublic: true)!;
        var previousAppDirectory = Program.AppDirectory;

        try
        {
            setAppDirectory.Invoke(null, new object[] { temporaryDirectory });
            var services = new ServiceCollection();
            services.AddSlskdExperimentalFeatureGraph(
                new ConfigurationBuilder().Build(),
                new slskd.Options());

            Assert.Single(services, descriptor =>
                descriptor.ServiceType == typeof(slskd.Mesh.Transport.TransportPolicyManager));
            Assert.Single(services, descriptor =>
                descriptor.ServiceType == typeof(slskd.Mesh.Nat.INatTraversalService));
            Assert.Single(services, descriptor =>
                descriptor.ServiceType == typeof(slskd.MediaCore.IIpldMapper));
            Assert.Single(services, descriptor =>
                descriptor.ServiceType == typeof(slskd.MediaCore.IFuzzyMatcher));
        }
        finally
        {
            setAppDirectory.Invoke(null, new object[] { previousAppDirectory });
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(temporaryDirectory, "pods.db")}");
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(temporaryDirectory, "wishlist.db")}");
            Directory.Delete(temporaryDirectory, recursive: true);
        }
    }
}
