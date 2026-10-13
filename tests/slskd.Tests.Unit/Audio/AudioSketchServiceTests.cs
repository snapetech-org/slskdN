// <copyright file="AudioSketchServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Audio
{
    using System;
    using System.IO;
    using System.Threading.Tasks;
    using Microsoft.Extensions.Options;
    using Moq;
    using slskd.Audio;
    using Xunit;

    public class AudioSketchServiceTests
    {
        [Fact]
        public void ResolveExecutablePath_WhenCommandIsOnPath_ReturnsResolvedFile()
        {
            var originalPath = Environment.GetEnvironmentVariable("PATH");
            var tempDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-audiosketch-{Guid.NewGuid():N}");
            Directory.CreateDirectory(tempDirectory);

            try
            {
                var executableName = OperatingSystem.IsWindows() ? "ffmpeg.exe" : "ffmpeg";
                var executablePath = Path.Combine(tempDirectory, executableName);
                File.WriteAllText(executablePath, string.Empty);
                Environment.SetEnvironmentVariable("PATH", tempDirectory);

                var resolved = AudioSketchService.ResolveExecutablePath("ffmpeg");

                Assert.Equal(
                    executablePath,
                    resolved,
                    OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);
            }
            finally
            {
                Environment.SetEnvironmentVariable("PATH", originalPath);
                Directory.Delete(tempDirectory, recursive: true);
            }
        }

        [Fact]
        public void ResolveExecutablePath_WhenExplicitPathMissing_ReturnsNull()
        {
            var missingPath = Path.Combine(Path.GetTempPath(), $"missing-ffmpeg-{Guid.NewGuid():N}");

            var resolved = AudioSketchService.ResolveExecutablePath(missingPath);

            Assert.Null(resolved);
        }

        [Theory]
        [InlineData("cover.jpg", false)]
        [InlineData("booklet.png", false)]
        [InlineData("track.flac", true)]
        [InlineData("track.MP3", true)]
        [InlineData("track.opus", true)]
        public void IsSupportedAudioFile_ReturnsTrueOnlyForAudioExtensions(string filePath, bool expected)
        {
            var result = AudioSketchService.IsSupportedAudioFile(filePath);

            Assert.Equal(expected, result);
        }

        [Fact]
        public async Task ComputeSketchHash_DrainsLargeStandardErrorWhileReadingPcm()
        {
            if (OperatingSystem.IsWindows() || !File.Exists("/usr/bin/timeout"))
            {
                return;
            }

            var directory = Path.Combine(Path.GetTempPath(), $"slskdn-audiosketch-process-{Guid.NewGuid():N}");
            Directory.CreateDirectory(directory);
            var inputPath = Path.Combine(directory, "track.flac");
            var childPath = Path.Combine(directory, "fake-ffmpeg-child.sh");
            var wrapperPath = Path.Combine(directory, "fake-ffmpeg.sh");
            var markerPath = Path.Combine(directory, "finished");
            File.WriteAllText(inputPath, "audio fixture");
            File.WriteAllText(
                childPath,
                "#!/bin/sh\ni=0\nwhile [ \"$i\" -lt 4096 ]; do printf 'pcm output %s\n' \"$i\"; printf 'diagnostic output %s\n' \"$i\" >&2; i=$((i + 1)); done\nprintf finished > '" + markerPath + "'\n");
            File.WriteAllText(wrapperPath, "#!/bin/sh\nexec /usr/bin/timeout -k 1 3s '" + childPath + "'\n");
            File.SetUnixFileMode(childPath, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            File.SetUnixFileMode(wrapperPath, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);

            var options = new slskd.Options
            {
                Integration = new slskd.Options.IntegrationOptions
                {
                    Chromaprint = new slskd.Options.IntegrationOptions.ChromaprintOptions
                    {
                        FfmpegPath = wrapperPath,
                    },
                },
            };
            var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
            optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(options);

            try
            {
                var sketch = await Task.Run(() => new AudioSketchService(optionsMonitor.Object).ComputeSketchHash(inputPath))
                    .WaitAsync(TimeSpan.FromSeconds(8));

                Assert.False(string.IsNullOrWhiteSpace(sketch));
                Assert.True(File.Exists(markerPath));
            }
            finally
            {
                Directory.Delete(directory, recursive: true);
            }
        }
    }
}
