// <copyright file="PathGuardTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Security;

using System.IO;
using slskd.Common.Security;
using Xunit;

public class PathGuardTests
{
    private static readonly string TestRoot = Path.Combine(Path.GetTempPath(), "slskdn-path-guard-downloads");

    [Theory]
    [InlineData("music/album/track.flac", true)]
    [InlineData("artist - album/01 - track.mp3", true)]
    [InlineData("simple.txt", true)]
    [InlineData("nested/path/to/file.ogg", true)]
    public void NormalizeAndValidate_ValidPaths_ReturnsSafePath(string peerPath, bool expected)
    {
        var result = PathGuard.NormalizeAndValidate(peerPath, TestRoot);
        Assert.Equal(expected, result != null);
    }

    [Theory]
    [InlineData("../etc/passwd")]
    [InlineData("..\\windows\\system32")]
    [InlineData("music/../../../etc/passwd")]
    [InlineData("music/..\\..\\..\\etc\\passwd")]
    [InlineData("..")]
    [InlineData("../")]
    [InlineData("..\\")]
    public void NormalizeAndValidate_TraversalAttempts_ReturnsNull(string peerPath)
    {
        var result = PathGuard.NormalizeAndValidate(peerPath, TestRoot);
        Assert.Null(result);
    }

    [Theory]
    [InlineData("/etc/passwd")]
    [InlineData("C:\\Windows\\System32")]
    [InlineData("/home/other/file.txt")]
    public void NormalizeAndValidate_AbsolutePaths_ReturnsNull(string peerPath)
    {
        var result = PathGuard.NormalizeAndValidate(peerPath, TestRoot);
        Assert.Null(result);
    }

    [Theory]
    [InlineData("music%2f..%2f..%2fetc%2fpasswd")]
    [InlineData("music%2F..%2F..%2Fetc%2Fpasswd")]
    [InlineData("%2e%2e%2f")]
    public void NormalizeAndValidate_UrlEncodedTraversal_ReturnsNull(string peerPath)
    {
        var result = PathGuard.NormalizeAndValidate(peerPath, TestRoot);
        Assert.Null(result);
    }

    [Fact]
    public void NormalizeAndValidate_NullPath_ReturnsNull()
    {
        var result = PathGuard.NormalizeAndValidate(null, TestRoot);
        Assert.Null(result);
    }

    [Fact]
    public void NormalizeAndValidate_EmptyPath_ReturnsNull()
    {
        var result = PathGuard.NormalizeAndValidate("", TestRoot);
        Assert.Null(result);
    }

    [Fact]
    public void NormalizeAndValidate_PathWithNullByte_ReturnsNull()
    {
        var result = PathGuard.NormalizeAndValidate("music\0.txt", TestRoot);
        Assert.Null(result);
    }

    [Theory]
    [InlineData("../etc/passwd", true)]
    [InlineData("music/../../../etc", true)]
    [InlineData("..", true)]
    [InlineData("music/album", false)]
    [InlineData("valid/path/file.txt", false)]
    public void ContainsTraversal_DetectsTraversalPatterns(string path, bool expected)
    {
        var result = PathGuard.ContainsTraversal(path);
        Assert.Equal(expected, result);
    }

    [Theory]
    [InlineData("file.exe", true)]
    [InlineData("document.bat", true)]
    [InlineData("script.ps1", true)]
    [InlineData(" song.mp3 ", false)]
    [InlineData(" file.exe ", true)]
    [InlineData("music.flac", false)]
    [InlineData("song.mp3", false)]
    [InlineData("video.mkv", false)]
    public void HasDangerousExtension_DetectsDangerousExtensions(string filename, bool expected)
    {
        var result = PathGuard.HasDangerousExtension(filename);
        Assert.Equal(expected, result);
    }

    [Theory]
    [InlineData("music.flac", true)]
    [InlineData("song.mp3", true)]
    [InlineData(" song.mp3 ", true)]
    [InlineData("track.ogg", true)]
    [InlineData("audio.wav", true)]
    [InlineData("document.pdf", false)]
    [InlineData("program.exe", false)]
    public void HasSafeAudioExtension_DetectsSafeAudio(string filename, bool expected)
    {
        var result = PathGuard.HasSafeAudioExtension(filename);
        Assert.Equal(expected, result);
    }

    [Theory]
    [InlineData("valid<>file.txt", "valid__file.txt")]
    [InlineData("file:name.txt", "file_name.txt")]
    [InlineData("file|name.txt", "file_name.txt")]
    [InlineData("file?name.txt", "file_name.txt")]
    [InlineData("file*name.txt", "file_name.txt")]
    public void SanitizeFilename_RemovesForbiddenCharacters(string input, string expected)
    {
        var result = PathGuard.SanitizeFilename(input);
        Assert.Equal(expected, result);
    }

    [Fact]
    public void SanitizeFilename_NullInput_ReturnsUnnamed()
    {
        var result = PathGuard.SanitizeFilename(null);
        Assert.Equal("unnamed", result);
    }

    [Fact]
    public void SanitizeFilename_EmptyInput_ReturnsUnnamed()
    {
        var result = PathGuard.SanitizeFilename("");
        Assert.Equal("unnamed", result);
    }

    [Fact]
    public void SanitizeFilename_RemovesPathSeparators()
    {
        var result = PathGuard.SanitizeFilename("path/to/file.txt");
        Assert.DoesNotContain("/", result);
        Assert.DoesNotContain("\\", result);
    }

    [Fact]
    public void Validate_ReturnsDetailedError()
    {
        var result = PathGuard.Validate("../etc/passwd", TestRoot);

        Assert.False(result.IsValid);
        Assert.Equal(PathViolationType.DirectoryTraversal, result.ViolationType);
        Assert.NotNull(result.Error);
    }

    [Fact]
    public void Validate_ValidPath_ReturnsSuccess()
    {
        var result = PathGuard.Validate("music/track.flac", TestRoot);

        Assert.True(result.IsValid);
        Assert.NotNull(result.SafePath);
        Assert.Equal(PathViolationType.None, result.ViolationType);
    }

    [Fact]
    public void Validate_WhenPathNormalizationThrows_ReturnsSanitizedError()
    {
        var result = PathGuard.Validate("bad\0path", TestRoot);

        Assert.False(result.IsValid);
        Assert.Equal(PathViolationType.ControlCharacters, result.ViolationType);
        Assert.Equal("Path contains control characters", result.Error);
        Assert.DoesNotContain("null", result.Error ?? string.Empty, System.StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Validate_TrimsPaddedValidPath()
    {
        var result = PathGuard.Validate("  music/track.flac  ", TestRoot);

        Assert.True(result.IsValid);
        Assert.NotNull(result.SafePath);
        Assert.EndsWith("/music/track.flac", result.SafePath!.Replace('\\', '/'));
    }

    [Fact]
    public void NormalizeAbsolutePathWithinRoots_AllowsPathWithinConfiguredRoot()
    {
        var target = Path.Combine(TestRoot, "album", "track.flac");

        var result = PathGuard.NormalizeAbsolutePathWithinRoots(target, new[] { TestRoot });

        Assert.Equal(target, result);
    }

    [Fact]
    public void NormalizeAbsolutePathWithinRoots_TrimsPaddedPathAndRoot()
    {
        var target = Path.Combine(TestRoot, "album", "track.flac");

        var result = PathGuard.NormalizeAbsolutePathWithinRoots($"  {target}  ", new[] { $"  {TestRoot}  " });

        Assert.Equal(target, result);
    }

    [Fact]
    public void NormalizeAbsolutePathWithinRoots_RejectsPathOutsideConfiguredRoots()
    {
        var target = Path.Combine(Path.GetTempPath(), "slskdn-path-guard-other", "track.flac");

        var result = PathGuard.NormalizeAbsolutePathWithinRoots(target, new[] { TestRoot });

        Assert.Null(result);
    }

    [Fact]
    public void NormalizeAbsolutePathWithinRoots_RejectsTraversalBeforeNormalization()
    {
        var target = Path.Combine(TestRoot, "..", "other", "track.flac");

        var result = PathGuard.NormalizeAbsolutePathWithinRoots(target, new[] { TestRoot });

        Assert.Null(result);
    }

    [Fact]
    public void NormalizeAbsolutePathWithinRoots_RejectsDirectorySymlinkEscape()
    {
        using var temp = new TemporaryDirectory();
        var root = Path.Combine(temp.Path, "root");
        var outside = Path.Combine(temp.Path, "outside");
        Directory.CreateDirectory(root);
        Directory.CreateDirectory(outside);
        Directory.CreateSymbolicLink(Path.Combine(root, "escape"), outside);

        var result = PathGuard.NormalizeAbsolutePathWithinRoots(
            Path.Combine(root, "escape", "payload.bin"),
            new[] { root });

        Assert.Null(result);
    }

    [Fact]
    public void SecureFileWriter_CreatesNestedFileWithoutFollowingLinks()
    {
        using var temp = new TemporaryDirectory();
        var root = Path.Combine(temp.Path, "root");
        Directory.CreateDirectory(root);
        var output = Path.Combine(root, "nested", "payload.bin");

        using (var stream = SecureFileWriter.Open(output, root))
        {
            stream.WriteByte(42);
        }

        Assert.Equal(new byte[] { 42 }, File.ReadAllBytes(output));
    }

    [Fact]
    public void SecureFileWriter_RejectsFinalSymlink()
    {
        using var temp = new TemporaryDirectory();
        var root = Path.Combine(temp.Path, "root");
        var outside = Path.Combine(temp.Path, "outside.bin");
        Directory.CreateDirectory(root);
        File.WriteAllText(outside, "unchanged");
        var output = Path.Combine(root, "payload.bin");
        File.CreateSymbolicLink(output, outside);

        Assert.Throws<UnauthorizedAccessException>(() => SecureFileWriter.Open(output, root));
        Assert.Equal("unchanged", File.ReadAllText(outside));
    }

    [Fact]
    public void NormalizeAbsolutePathWithinRoots_UsesPlatformCaseSemantics()
    {
        using var temp = new TemporaryDirectory();
        var root = Path.Combine(temp.Path, "Approved");
        var differentCaseSibling = Path.Combine(temp.Path, "approved", "payload.bin");
        Directory.CreateDirectory(root);

        var result = PathGuard.NormalizeAbsolutePathWithinRoots(differentCaseSibling, new[] { root });

        if (OperatingSystem.IsWindows())
        {
            Assert.NotNull(result);
        }
        else
        {
            Assert.Null(result);
        }
    }

    private sealed class TemporaryDirectory : IDisposable
    {
        public TemporaryDirectory()
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-path-guard-{Guid.NewGuid():N}");
            Directory.CreateDirectory(Path);
        }

        public string Path { get; }

        public void Dispose() => Directory.Delete(Path, recursive: true);
    }
}
