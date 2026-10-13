// <copyright file="DirectoryExistsAttributeTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Common.Validation;

using System.ComponentModel.DataAnnotations;
using System.IO;
using slskd.Validation;
using Xunit;

public sealed class DirectoryExistsAttributeTests
{
    [Theory]
    [InlineData("..")]
    [InlineData("../outside")]
    [InlineData("nested/../../outside")]
    public void RelativeDirectory_RejectsCanonicalPathOutsideApplicationDirectory(string path)
    {
        var attribute = new DirectoryExistsAttribute(relativeToApplicationDirectory: true);
        var context = new ValidationContext(new object()) { DisplayName = "content path" };

        var result = attribute.GetValidationResult(path, context);

        Assert.NotNull(result);
        Assert.Contains("outside the application directory", result!.ErrorMessage);
    }

    [Fact]
    public void RelativeDirectory_AllowsApplicationDirectoryItself()
    {
        var attribute = new DirectoryExistsAttribute(relativeToApplicationDirectory: true);
        var context = new ValidationContext(new object()) { DisplayName = "content path" };

        var result = attribute.GetValidationResult(".", context);

        Assert.Null(result);
    }

    [Fact]
    public void RelativeDirectory_RejectsSymlinkTargetOutsideApplicationDirectory()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var outside = Path.Combine(Path.GetTempPath(), $"slskdn-content-{Guid.NewGuid():N}");
        var link = Path.Combine(AppContext.BaseDirectory, $"slskdn-content-link-{Guid.NewGuid():N}");
        Directory.CreateDirectory(outside);

        try
        {
            Directory.CreateSymbolicLink(link, outside);
            var relativeLink = Path.GetRelativePath(AppContext.BaseDirectory, link);
            var attribute = new DirectoryExistsAttribute(relativeToApplicationDirectory: true);
            var context = new ValidationContext(new object()) { DisplayName = "content path" };

            var result = attribute.GetValidationResult(relativeLink, context);

            Assert.NotNull(result);
            Assert.Contains("outside the application directory", result!.ErrorMessage);
        }
        finally
        {
            if (Directory.Exists(link))
            {
                Directory.Delete(link);
            }

            Directory.Delete(outside, recursive: true);
        }
    }
}
