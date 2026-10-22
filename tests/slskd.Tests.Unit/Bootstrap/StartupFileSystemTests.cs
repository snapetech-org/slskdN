// <copyright file="StartupFileSystemTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Bootstrap;

using System.Security.Cryptography.X509Certificates;
using Serilog;
using slskd.Bootstrap;
using Xunit;

public sealed class StartupFileSystemTests : IDisposable
{
    private readonly string _tempDir = Path.Combine(Path.GetTempPath(), $"slskdn-startup-files-{Guid.NewGuid():N}");

    public StartupFileSystemTests()
    {
        Directory.CreateDirectory(_tempDir);
    }

    public void Dispose()
    {
        Directory.Delete(_tempDir, recursive: true);
    }

    [Fact]
    public void GenerateX509Certificate_WritesLoadableRestrictiveBundleAtomically()
    {
        const string password = "EXAMPLE_CERTIFICATE_PASSWORD";

        var result = StartupFileSystem.GenerateX509Certificate(
            "slskdn-test",
            _tempDir,
            password,
            "certificate.pfx",
            Log.Logger);

        using var certificate = X509CertificateLoader.LoadPkcs12FromFile(
            result.Filename,
            result.Password,
            X509KeyStorageFlags.EphemeralKeySet,
            new Pkcs12LoaderLimits());

        Assert.True(certificate.HasPrivateKey);
        Assert.Empty(Directory.EnumerateFiles(_tempDir, "certificate.pfx.*.tmp"));
        if (!OperatingSystem.IsWindows())
        {
            Assert.Equal(
                UnixFileMode.UserRead | UnixFileMode.UserWrite,
                File.GetUnixFileMode(result.Filename));
        }
    }

    [Theory]
    [InlineData("../outside.pfx")]
    [InlineData("nested/certificate.pfx")]
    [InlineData("nested\\certificate.pfx")]
    public void GenerateX509Certificate_RejectsPathsOutsideApplicationDirectory(string filename)
    {
        Assert.Throws<ArgumentException>(() => StartupFileSystem.GenerateX509Certificate(
            "slskdn-test",
            _tempDir,
            "EXAMPLE_CERTIFICATE_PASSWORD",
            filename,
            Log.Logger));
    }

    [Fact]
    public void GenerateX509Certificate_RejectsRootedOutputPath()
    {
        var rootedPath = Path.Combine(Path.GetTempPath(), "outside-certificate.pfx");

        Assert.Throws<ArgumentException>(() => StartupFileSystem.GenerateX509Certificate(
            "slskdn-test",
            _tempDir,
            "EXAMPLE_CERTIFICATE_PASSWORD",
            rootedPath,
            Log.Logger));
    }
}
