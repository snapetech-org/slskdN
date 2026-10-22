// <copyright file="StartupFileSystem.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Bootstrap;

using System;
using System.IO;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.FileProviders.Physical;
using System.Security.Cryptography.X509Certificates;
using Serilog;
using slskd.Common.Security;
using slskd.Common.IO;
using slskd.Cryptography;

public static class StartupFileSystem
{
    public static void VerifyDirectory(string directory, bool createIfMissing = true, bool verifyWriteable = true)
    {
        if (!Directory.Exists(directory))
        {
            if (createIfMissing)
            {
                try
                {
                    Directory.CreateDirectory(directory);
                }
                catch (Exception ex)
                {
                    throw new IOException($"Directory {directory} does not exist, and could not be created: {ex.Message}", ex);
                }
            }
            else
            {
                throw new IOException($"Directory {directory} does not exist");
            }
        }

        if (verifyWriteable)
        {
            try
            {
                var file = Guid.NewGuid().ToString();
                var probe = Path.Combine(directory, file);
                // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- probe name is a generated GUID; the directory is the configured, operator-owned app path.
                File.WriteAllText(probe, string.Empty);
                File.Delete(probe);
            }
            catch (Exception ex)
            {
                throw new IOException($"Directory {directory} is not writeable: {ex.Message}", ex);
            }
        }
    }

    public static void RecreateConfigurationFileIfMissing(
        string configurationFile,
        string appName,
        string baseDirectory,
        ILogger log)
    {
        if (File.Exists(configurationFile))
        {
            return;
        }

        try
        {
            log.Warning(
                "Configuration file {ConfigurationFile} does not exist; creating from example",
                LoggingSanitizer.SanitizeFilePath(configurationFile));
            var source = Path.Combine(baseDirectory, "config", $"{appName}.example.yml");
            File.Copy(source, configurationFile);
        }
        catch (Exception ex)
        {
            log.Error(
                "Failed to create configuration file {ConfigurationFile}: {Exception}",
                LoggingSanitizer.SanitizeFilePath(configurationFile),
                LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
        }
    }

    public static (string Filename, string Password) GenerateX509Certificate(
        string appName,
        string baseDirectory,
        string password,
        string filename,
        ILogger log)
    {
        if (string.IsNullOrWhiteSpace(filename)
            || Path.IsPathRooted(filename)
            || !string.Equals(filename, Path.GetFileName(filename), StringComparison.Ordinal)
            || filename.Contains('/')
            || filename.Contains('\\'))
        {
            throw new ArgumentException("Certificate filename must be a single path segment.", nameof(filename));
        }

        var canonicalBaseDirectory = Path.GetFullPath(baseDirectory);
        filename = Path.GetFullPath(Path.Combine(canonicalBaseDirectory, filename));
        var baseDirectoryPrefix = canonicalBaseDirectory.EndsWith(Path.DirectorySeparatorChar)
            ? canonicalBaseDirectory
            : canonicalBaseDirectory + Path.DirectorySeparatorChar;
        if (!filename.StartsWith(baseDirectoryPrefix, OperatingSystem.IsWindows()
                ? StringComparison.OrdinalIgnoreCase
                : StringComparison.Ordinal))
        {
            throw new ArgumentException("Certificate path must remain inside the application directory.", nameof(filename));
        }

        using var cert = X509.Generate(subject: appName, password, X509KeyStorageFlags.Exportable);
        AtomicFileWriter.WriteAllBytes(
            filename,
            cert.Export(X509ContentType.Pkcs12, password),
            UnixFileMode.UserRead | UnixFileMode.UserWrite);

        return (filename, password);
    }

    public static PhysicalFileProvider CreateOwnedPhysicalFileProvider(string root, ExclusionFilters exclusionFilters = ExclusionFilters.Sensitive)
        => new(root, exclusionFilters);
}
