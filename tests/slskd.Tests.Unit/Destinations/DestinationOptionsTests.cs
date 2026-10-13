// <copyright file="DestinationOptionsTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Destinations;

using System.ComponentModel.DataAnnotations;
using Xunit;

public class DestinationOptionsTests
{
    [Fact]
    public void Validate_WithOneAbsoluteDefault_Succeeds()
    {
        var options = CreateOptions((Path.Combine(Path.GetTempPath(), "downloads", "music"), true));

        Assert.Empty(options.Validate(new ValidationContext(options)));
    }

    [Fact]
    public void Validate_WithMultipleDefaults_ReturnsValidationError()
    {
        var options = CreateOptions(
            (Path.Combine(Path.GetTempPath(), "downloads", "music"), true),
            (Path.Combine(Path.GetTempPath(), "downloads", "audiobooks"), true));

        var result = Assert.Single(options.Validate(new ValidationContext(options)));

        Assert.Equal("Only one download destination can be marked as default", result.ErrorMessage);
    }

    [Theory]
    [InlineData("")]
    [InlineData("relative/downloads")]
    public void Validate_WithInvalidPath_ReturnsValidationError(string path)
    {
        var options = CreateOptions((path, true));

        Assert.Single(options.Validate(new ValidationContext(options)));
    }

    private static slskd.Options.DestinationsOptions CreateOptions(
        params (string Path, bool Default)[] destinations)
    {
        return new slskd.Options.DestinationsOptions
        {
            Folders = destinations
                .Select((destination, index) => new slskd.Options.DestinationOption
                {
                    Name = $"Destination {index + 1}",
                    Path = destination.Path,
                    Default = destination.Default,
                })
                .ToList(),
        };
    }
}
