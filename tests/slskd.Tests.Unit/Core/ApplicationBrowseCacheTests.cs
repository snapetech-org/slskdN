// <copyright file="ApplicationBrowseCacheTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Core;

using System;
using System.IO;
using System.Text;
using Xunit;

public class ApplicationBrowseCacheTests
{
    [Fact]
    public void OpenBrowseCacheReadStream_AllowsReplacingCacheFileWhileReading()
    {
        var tempDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-browse-cache-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDirectory);

        try
        {
            var destination = Path.Combine(tempDirectory, "browse.cache");
            var replacement = Path.Combine(tempDirectory, "browse.cache.replacement");

            File.WriteAllText(destination, "old-cache", Encoding.UTF8);
            File.WriteAllText(replacement, "new-cache", Encoding.UTF8);

            using var stream = Application.OpenBrowseCacheReadStream(destination);

            Application.ReplaceBrowseCacheFile(replacement, destination);

            using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true, leaveOpen: false);
            var existingReaderContents = reader.ReadToEnd();
            var replacedContents = File.ReadAllText(destination, Encoding.UTF8);

            Assert.Contains("old-cache", existingReaderContents);
            Assert.Equal("new-cache", replacedContents);
        }
        finally
        {
            if (Directory.Exists(tempDirectory))
            {
                Directory.Delete(tempDirectory, recursive: true);
            }
        }
    }
}
