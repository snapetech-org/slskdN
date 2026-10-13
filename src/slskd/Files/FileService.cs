// <copyright file="FileService.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="FileService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Files
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Linq;
    using System.Security;
    using System.Threading.Tasks;
    using slskd.Common.Security;
    using OneOf;
    using Serilog;

    /// <summary>
    ///     Manages files on disk.
    /// </summary>
    public class FileService
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="FileService"/> class.
        /// </summary>
        public FileService(
            IOptionsMonitor<Options> optionsMonitor)
        {
            OptionsMonitor = optionsMonitor;
        }

        private IEnumerable<string> AllowedDirectories => new[]
        {
            Path.GetFullPath(OptionsMonitor.CurrentValue.Directories.Downloads),
            Path.GetFullPath(OptionsMonitor.CurrentValue.Directories.Incomplete),
        };

        private ILogger Log { get; } = Serilog.Log.ForContext<FileService>();
        private IOptionsMonitor<Options> OptionsMonitor { get; }

        private bool IsAllowedPath(string path)
        {
            return PathGuard.NormalizeAbsolutePathWithinRoots(path, AllowedDirectories) != null;
        }

        /// <summary>
        ///     Computes the SHA256 hash of a file.
        /// </summary>
        /// <param name="filename">The fully qualified filename.</param>
        /// <param name="cancellationToken">Cancellation token.</param>
        /// <returns>The hex-encoded SHA256 hash.</returns>
        /// <remarks>
        ///     Added for T-MCP02 (moderation integration).
        ///     Uses SHA256 for content identification.
        /// </remarks>
        public virtual async Task<string> ComputeHashAsync(string filename, System.Threading.CancellationToken cancellationToken = default)
        {
            using var stream = File.OpenRead(filename);
            using var sha256 = System.Security.Cryptography.SHA256.Create();
            var hashBytes = await sha256.ComputeHashAsync(stream, cancellationToken);
            return Convert.ToHexString(hashBytes);
        }

        /// <summary>
        ///     Resolves an instance of <see cref="FileInfo"/> for the specified <paramref name="filename"/>, following
        ///     any symlinks that may be present to their final target. A non-null return value is guaranteed.
        /// </summary>
        /// <param name="filename">The fully qualified filename for which to resolve the FileInfo instance.</param>
        /// <returns>The resolved FileInfo instance.</returns>
        /// <exception cref="ArgumentException">Thrown if the specified filename is null or contains only whitespace.</exception>
        /// <exception cref="UnauthorizedException">Thrown if the specified or linked file is restricted.</exception>
        /// <exception cref="IOException">Thrown if the specified or linked file can't be resolved for some reason.</exception>
        public virtual FileInfo ResolveFileInfo(string filename)
        {
            ArgumentException.ThrowIfNullOrWhiteSpace(filename, nameof(filename));

            FileInfo info;

            try
            {
                info = new FileInfo(filename);
            }
            catch (Exception ex) when (ex is UnauthorizedAccessException || ex is SecurityException)
            {
                throw new UnauthorizedException($"Access to the file '{filename}' was denied: {ex.Message}", ex);
            }
            catch (Exception ex)
            {
                throw new IOException($"Failed to access file '{filename}': {ex.Message}", ex);
            }

            // if the above didn't throw we are guaranteed a valid instance of FileInfo regardless of whether
            // the file exists or if it is a symlink. if it doesn't exist it can't be a symlink, so just return it
            if (!info.Exists)
            {
                return info;
            }

            // LinkTarget is guaranteed to be null if the file isn't a symlink. docs:
            //  > Gets the target path of the link located in FullName, or null if this FileSystemInfo instance doesn't represent a link.
            if (info.LinkTarget is null)
            {
                return info;
            }

            // ResolveLinkTarget returns an instance of FileSystemInfo (which is being cast to FileInfo here) as long as
            // the link itself exists (which we've checked), and regardless of whether the link target itself exists.
            // we should only get this far if:
            //   1) the given file exists and
            //   2) it is a symlink, meaning this line _SHOULD_ be guaranteed to return an instance of FileInfo.
            try
            {
                var resolvedInfo = info.ResolveLinkTarget(returnFinalTarget: true);
                var linkTarget = info.LinkTarget ?? "<unknown>";
                info = resolvedInfo as FileInfo
                    ?? throw new IOException($"An unexpected error was encountered while resolving FileInfo for linked file '{filename}->{linkTarget}'");
            }
            catch (Exception ex) when (ex is UnauthorizedAccessException || ex is SecurityException)
            {
                throw new UnauthorizedException($"Access to the linked file '{filename}->{info.LinkTarget}' was denied: {ex.Message}", ex);
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to resolve FileInfo for linked file '{File}->{Link}': {Message}", filename, info.LinkTarget, ex.Message);
                throw new IOException($"Failed to resolve FileInfo for linked file '{filename}->{info.LinkTarget}': {ex.Message}", ex);
            }

            return info;
        }

        /// <summary>
        ///     Deletes the specified <paramref name="directories"/>.
        /// </summary>
        /// <remarks>
        ///     Returns a dictionary keyed on directory name and containing a result for each specified directory. Exceptions are
        ///     contained in the result, and are not thrown.
        /// </remarks>
        /// <param name="directories">The directories to delete.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentException">Thrown if any of the specified directories have a relative path.</exception>
        /// <exception cref="ArgumentException">
        ///     Thrown if any of the directories is an exact match for an application-controlled directory.
        /// </exception>
        /// <exception cref="NotFoundException">Thrown if a specified directory does not exist.</exception>
        /// <exception cref="UnauthorizedException">Thrown if a specified directory is restricted.</exception>
        public virtual async Task<Dictionary<string, OneOf<bool, Exception>>> DeleteDirectoriesAsync(params string[] directories)
        {
            if (directories.Any(directory => Path.GetFullPath(directory) != directory))
            {
                throw new ArgumentException("Only absolute paths may be specified", nameof(directories));
            }

            if (directories.Any(directory => AllowedDirectories.Contains(directory)))
            {
                throw new ArgumentException("Deletion of application-controlled directory roots is not supported");
            }

            // if any of the resolved directory paths aren't rooted in one of the allowed directories, forbid the entire request
            if (!directories.All(directory => IsAllowedPath(directory)))
            {
                throw new UnauthorizedException("Only application-controlled directories can be deleted");
            }

            await Task.Yield();

            Dictionary<string, OneOf<bool, Exception>> results = new();

            foreach (var directory in directories)
            {
                try
                {
                    Directory.Delete(directory, recursive: true);
                    results.Add(directory, true);

                    Log.Information("Deleted directory '{Directory}'", directory);
                }
                catch (DirectoryNotFoundException)
                {
                    results.Add(directory, new NotFoundException($"The directory '{directory}' does not exist"));
                }
                catch (UnauthorizedAccessException ex)
                {
                    results.Add(directory, new UnauthorizedException($"Deletion of the directory '{directory}' was denied: {ex.Message}", ex));
                }
                catch (Exception ex)
                {
                    results.Add(directory, ex);
                }
            }

            return results;
        }

        /// <summary>
        ///     Deletes the specified <paramref name="files"/>.
        /// </summary>
        /// <remarks>
        ///     Returns a dictionary keyed on directory name and containing a result for each specified directory. Exceptions are
        ///     contained in the result, and are not thrown.
        /// </remarks>
        /// <param name="files">The list of files to delete.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentException">Thrown if any of the specified files have a relative path.</exception>
        /// <exception cref="NotFoundException">Thrown if a specified file does not exist.</exception>
        /// <exception cref="UnauthorizedException">Thrown if a specified file is restricted.</exception>
        public virtual async Task<Dictionary<string, OneOf<bool, Exception>>> DeleteFilesAsync(params string[] files)
        {
            if (files.Any(file => Path.GetFullPath(file) != file))
            {
                throw new ArgumentException("Only absolute paths may be specified", nameof(files));
            }

            // if any of the resolved file paths aren't rooted in one of the allowed directories, forbid the entire request
            if (!files.All(file => IsAllowedPath(file)))
            {
                throw new UnauthorizedException("Only files in application-controlled directories can be deleted");
            }

            await Task.Yield();

            Dictionary<string, OneOf<bool, Exception>> results = new();

            foreach (var file in files)
            {
                try
                {
                    File.Delete(file);
                    results.Add(file, true);
                }
                catch (FileNotFoundException)
                {
                    results.Add(file, new NotFoundException($"The file '{file}' does not exist"));
                }
                catch (UnauthorizedAccessException ex)
                {
                    results.Add(file, new UnauthorizedException($"Deletion of the file '{file}' was denied: {ex.Message}", ex));
                }
                catch (Exception ex)
                {
                    results.Add(file, ex);
                }
            }

            return results;
        }

        /// <summary>
        ///     Lists the contents in the specified <paramref name="directory"/>, optionally applying the specified <paramref name="enumerationOptions"/>.
        /// </summary>
        /// <param name="directory">The directory from which to start the listing.</param>
        /// <param name="enumerationOptions">Optional enumeration options to apply.</param>
        /// <returns>The list of found contents.</returns>
        /// <exception cref="ArgumentException">Thrown if the specified directory has a relative path.</exception>
        /// <exception cref="NotFoundException">Thrown if the specified directory does not exist.</exception>
        /// <exception cref="UnauthorizedException">Thrown if the specified root directory is restricted.</exception>
        public virtual Task<FilesystemDirectory> ListContentsAsync(
            string directory,
            EnumerationOptions? enumerationOptions = null)
            => ListContentsAsync(directory, enumerationOptions, includeDirectorySizes: false);

        public virtual async Task<FilesystemDirectory> ListContentsAsync(
            string directory,
            EnumerationOptions? enumerationOptions,
            bool includeDirectorySizes)
        {
            if (Path.GetFullPath(directory) != directory)
            {
                throw new ArgumentException("Only absolute paths may be specified", nameof(directory));
            }

            if (!IsAllowedPath(directory))
            {
                throw new UnauthorizedException($"Only application-controlled directories can be listed");
            }

            if (!Directory.Exists(directory))
            {
                throw new NotFoundException($"The directory '{directory}' does not exist");
            }

            return await Task.Run(() =>
            {
                var dir = new DirectoryInfo(directory);

                try
                {
                    if (enumerationOptions?.RecurseSubdirectories == true)
                    {
                        enumerationOptions.AttributesToSkip |= FileAttributes.ReparsePoint;
                    }

                    var contents = enumerationOptions is null
                        ? dir.EnumerateFileSystemInfos("*")
                        : dir.EnumerateFileSystemInfos("*", enumerationOptions);
                    var files = new List<FilesystemFile>();
                    var dirs = new List<FilesystemDirectory>();
                    var directoryInfos = new List<DirectoryInfo>();

                    foreach (var content in contents)
                    {
                        if (content is FileInfo file)
                        {
                            files.Add(FilesystemFile.FromFileInfo(file) with
                            {
                                FullName = file.FullName.ReplaceFirst(directory, string.Empty).TrimStart('\\', '/'),
                            });
                        }
                        else if (content is DirectoryInfo subdirectory)
                        {
                            dirs.Add(FilesystemDirectory.FromDirectoryInfo(subdirectory) with
                            {
                                FullName = subdirectory.FullName.ReplaceFirst(directory, string.Empty).TrimStart('\\', '/'),
                            });
                            directoryInfos.Add(subdirectory);
                        }
                    }

                    if (includeDirectorySizes && directoryInfos.Count > 0)
                    {
                        var directorySizes = CalculateDirectorySizes(directoryInfos);
                        dirs = dirs.Select((subdirectory, index) => subdirectory with
                        {
                            Length = directorySizes[directoryInfos[index].FullName],
                        }).ToList();
                    }

                    var response = FilesystemDirectory.FromDirectoryInfo(dir) with
                    {
                        FullName = dir.FullName.ReplaceFirst(directory, string.Empty).TrimStart('\\', '/'),
                        Files = files,
                        Directories = dirs,
                    };

                    return response;
                }
                catch (UnauthorizedAccessException ex)
                {
                    throw new UnauthorizedException($"Access to directory '{directory}' was denied: {ex.Message}", ex);
                }
            });
        }

        private static Dictionary<string, long?> CalculateDirectorySizes(IEnumerable<DirectoryInfo> directories)
        {
            var pathComparer = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
            var sizes = new Dictionary<string, long?>(pathComparer);
            var pending = new Stack<(string Directory, string Root)>();

            foreach (var directory in directories)
            {
                sizes.Add(directory.FullName, 0);
                pending.Push((directory.FullName, directory.FullName));
            }

            while (pending.TryPop(out var current))
            {
                try
                {
                    foreach (var path in Directory.EnumerateFileSystemEntries(
                        current.Directory,
                        "*",
                        new EnumerationOptions
                        {
                            AttributesToSkip = FileAttributes.System | FileAttributes.ReparsePoint,
                            RecurseSubdirectories = false,
                        }))
                    {
                        var attributes = File.GetAttributes(path);
                        if ((attributes & (FileAttributes.System | FileAttributes.ReparsePoint)) != 0)
                        {
                            continue;
                        }

                        if ((attributes & FileAttributes.Directory) != 0)
                        {
                            pending.Push((path, current.Root));
                            continue;
                        }

                        var currentSize = sizes[current.Root];
                        if (currentSize.HasValue)
                        {
                            var fileLength = new FileInfo(path).Length;
                            sizes[current.Root] = fileLength > long.MaxValue - currentSize.Value
                                ? long.MaxValue
                                : currentSize.Value + fileLength;
                        }
                    }
                }
                catch (Exception exception) when (
                    exception is UnauthorizedAccessException ||
                    exception is IOException ||
                    exception is SecurityException)
                {
                    sizes[current.Root] = null;
                }
            }

            return sizes;
        }

        /// <summary>
        ///     Creates a new file with the specified fully qualified <paramref name="filename"/> and the optional <paramref name="options"/>,
        ///     returning a <see cref="Stream"/> with which the contents of the file can be written.
        /// </summary>
        /// <remarks>
        ///     Reasonable defaults, including the Unix permissions from app configuration, have been applied. Be sure to review the defaults
        ///     for each new use case and ensure they are appropriate.
        /// </remarks>
        /// <param name="filename">The fully qualified filename.</param>
        /// <param name="options">An optional patch for the underlying <see cref="FileStreamOptions"/>.</param>
        /// <returns>A Stream with which the contents of the file can be written.</returns>
        /// <exception cref="ArgumentNullException">Thrown if the specified filename is null or contains only whitespace.</exception>
        /// <exception cref="IOException">Thrown if the underlying file or Stream can't be created for some reason.</exception>
        public virtual Stream CreateFile(string filename, CreateFileOptions? options = null)
        {
            ArgumentNullException.ThrowIfNullOrWhiteSpace(filename, nameof(filename));

            var path = Path.GetDirectoryName(filename);
            if (string.IsNullOrWhiteSpace(path))
            {
                throw new IOException($"Failed to determine directory for file {filename}");
            }

            var configuredFileMode = OptionsMonitor.CurrentValue.Permissions.File.Mode;
            UnixFileMode? unixCreateMode = options?.UnixCreateMode
                ?? (!string.IsNullOrWhiteSpace(configuredFileMode) ? configuredFileMode.ToUnixFileMode() : null);

            EnsureDirectory(path, unixCreateMode);

            var streamOptions = new FileStreamOptions
            {
                Access = options?.Access ?? FileAccess.Write,
                BufferSize = options?.BufferSize ?? 4096, // framework default
                Mode = options?.Mode ?? FileMode.Create, // overwrite
                Options = options?.Options ?? FileOptions.None, // synchronous I/O
                PreallocationSize = options?.PreallocationSize ?? 0,
                Share = options?.Share ?? FileShare.None, // exclusive access
            };

            // attempting to use UnixCreateMode on Windows raises an Exception
            // we *MUST* check the OS and skip this on Windows
            // if we omit this on *nix systems, the application's UMASK is used
            if (!OperatingSystem.IsWindows() && unixCreateMode.HasValue)
            {
                streamOptions.UnixCreateMode = unixCreateMode;
                Log.Debug("Setting Unix file mode to {Mode}", streamOptions.UnixCreateMode);
            }

            try
            {
                return new FileStream(filename, streamOptions);
            }
            catch (DirectoryNotFoundException) when (!Directory.Exists(path))
            {
                EnsureDirectory(path, unixCreateMode);

                return new FileStream(filename, streamOptions);
            }
            catch (Exception ex)
            {
                // the operation above can throw quite a few exceptions, all granular variations of
                // IOException. to make handling downstream easier, wrap them all up and re-throw.
                throw new IOException($"Failed to create file {filename}: {ex.Message}", ex);
            }
        }

        /// <summary>
        ///     Creates a directory and applies the requested mode to directories created by this call.
        /// </summary>
        /// <param name="directory">The directory to create.</param>
        /// <param name="unixMode">An optional chmod-style base mode used on non-Windows systems.</param>
        public virtual void EnsureDirectory(string directory, UnixFileMode? unixMode = null)
        {
            ArgumentNullException.ThrowIfNullOrWhiteSpace(directory, nameof(directory));

            var fullPath = Path.GetFullPath(directory);
            if (Directory.Exists(fullPath))
            {
                return;
            }

            if (OperatingSystem.IsWindows() || !unixMode.HasValue)
            {
                Directory.CreateDirectory(fullPath);
                return;
            }

            var missingDirectories = new List<string>();
            var currentDirectory = fullPath;
            while (!Directory.Exists(currentDirectory))
            {
                missingDirectories.Add(currentDirectory);
                var parentDirectory = Path.GetDirectoryName(currentDirectory);
                if (string.IsNullOrEmpty(parentDirectory) || parentDirectory == currentDirectory)
                {
                    break;
                }

                currentDirectory = parentDirectory;
            }

            var directoryMode = unixMode.Value.WithExecuteFlagsForEachReadFlag();
            Directory.CreateDirectory(fullPath, directoryMode);

            // The create-mode overload still observes the process umask. Reapply the configured
            // mode only to paths that were absent when this operation began.
            foreach (var path in missingDirectories)
            {
                File.SetUnixFileMode(path, directoryMode);
            }
        }

        /// <summary>
        ///     Moves the specified fully qualified, localized, <paramref name="sourceFilename"/> to the specified fully qualified, localized,
        ///     <paramref name="destinationDirectory"/>.
        /// </summary>
        /// <remarks>
        ///     If the destination file already exists and the <paramref name="overwrite"/> option is not set, the destination filename will
        ///     be modified to include the current time to avoid the collision while preserving both files.
        /// </remarks>
        /// <param name="sourceFilename">The fully qualified filename of the file to move.</param>
        /// <param name="destinationDirectory">The fully qualified directory to which to move the source file.</param>
        /// <param name="unixFileMode">An optional Unix file mode to apply to the destination file.</param>
        /// <param name="overwrite">An optional value indicating whether the destination file should be overwritten if it already exists.</param>
        /// <param name="deleteSourceDirectoryIfEmptyAfterMove">
        ///     An optional value indicating whether the parent directory of the source file should be deleted if it is empty after the move.
        /// </param>
        /// <param name="unixDirectoryMode">An optional Unix mode to apply when creating destination directories.</param>
        /// <returns>The fully qualified filename of the resulting file.</returns>
        /// <exception cref="ArgumentNullException">Thrown if either of the specified file or directories are null or contain only whitespace.</exception>
        /// <exception cref="FileNotFoundException">Thrown if the specified <paramref name="sourceFilename"/> does not exist.</exception>
        /// <exception cref="IOException">Thrown if the file can't be moved, or the <paramref name="deleteSourceDirectoryIfEmptyAfterMove"/> option is set and the operation fails.</exception>
        public virtual string MoveFile(string sourceFilename, string destinationDirectory, UnixFileMode? unixFileMode = null, bool overwrite = false, bool deleteSourceDirectoryIfEmptyAfterMove = false, UnixFileMode? unixDirectoryMode = null)
        {
            ArgumentNullException.ThrowIfNullOrWhiteSpace(sourceFilename, nameof(sourceFilename));
            ArgumentNullException.ThrowIfNullOrWhiteSpace(destinationDirectory, nameof(destinationDirectory));

            if (!File.Exists(sourceFilename))
            {
                throw new FileNotFoundException($"The specified source file does not exist", fileName: sourceFilename);
            }

            var configuredFileMode = OptionsMonitor.CurrentValue.Permissions.File.Mode;
            UnixFileMode? unixCreateMode = unixFileMode
                ?? (!string.IsNullOrWhiteSpace(configuredFileMode) ? configuredFileMode.ToUnixFileMode() : null);

            EnsureDirectory(destinationDirectory, unixDirectoryMode ?? unixCreateMode);

            var destinationFilename = Path.Combine(destinationDirectory, Path.GetFileName(sourceFilename));

            Log.Debug("Attempting to move {Source} to {Destination}", sourceFilename, destinationFilename);

            if (!overwrite && File.Exists(destinationFilename))
            {
                Log.Debug("Destination file {Destination} exists, and overwrite option is not set; attempting to generate new filename", destinationFilename);

                var destinationPath = Path.GetDirectoryName(destinationFilename)
                    ?? throw new IOException($"Failed to determine destination directory for file {destinationFilename}");
                string extensionlessFilename = Path.Combine(destinationPath, Path.GetFileNameWithoutExtension(sourceFilename));
                string extension = Path.GetExtension(sourceFilename);

                while (File.Exists(destinationFilename))
                {
                    destinationFilename = $"{extensionlessFilename}_{DateTime.UtcNow.Ticks}{extension}";
                }
            }

            try
            {
                File.Move(sourceFilename, destinationFilename, overwrite: overwrite);

                Log.Debug("Successfully moved {Source} to {Destination}", sourceFilename, destinationFilename);

                // attempting to use UnixCreateMode on Windows raises an Exception
                // we *MUST* check the OS and skip this on Windows
                if (!OperatingSystem.IsWindows() && unixCreateMode.HasValue)
                {
                    File.SetUnixFileMode(destinationFilename, unixCreateMode.Value);
                    Log.Debug("Successfully set Unix file mode to {Mode}", unixCreateMode);
                }

                TryDeleteDirectoryIfEmpty(Path.GetDirectoryName(sourceFilename), deleteSourceDirectoryIfEmptyAfterMove);

                return destinationFilename;
            }
            catch (Exception ex)
            {
                // the operation above can throw quite a few exceptions, all granular variations of
                // IOException. to make handling downstream easier, wrap them all up and re-throw.
                throw new IOException($"Failed to move file {sourceFilename}: {ex.Message}", ex);
            }
        }

        private void TryDeleteDirectoryIfEmpty(string? directory, bool enabled)
        {
            if (!enabled || string.IsNullOrWhiteSpace(directory))
            {
                return;
            }

            var incompleteRoot = Path.GetFullPath(OptionsMonitor.CurrentValue.Directories.Incomplete);
            var safeRoot = PathGuard.NormalizeAbsolutePathWithinRoots(incompleteRoot, new[] { incompleteRoot });
            var currentDirectory = PathGuard.NormalizeAbsolutePathWithinRoots(directory, new[] { incompleteRoot });

            if (safeRoot is null || currentDirectory is null)
            {
                return;
            }

            var pathComparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;

            try
            {
                while (!string.Equals(currentDirectory, safeRoot, pathComparison))
                {
                    if (!Directory.Exists(currentDirectory) || Directory.EnumerateFileSystemEntries(currentDirectory).Any())
                    {
                        break;
                    }

                    Directory.Delete(currentDirectory);

                    var parent = Path.GetDirectoryName(currentDirectory);
                    if (string.IsNullOrWhiteSpace(parent) || string.Equals(parent, currentDirectory, pathComparison))
                    {
                        break;
                    }

                    currentDirectory = parent;
                }
            }
            catch (IOException ex)
            {
                Log.Debug(ex, "Skipped cleanup of incomplete download directory {Directory}", LoggingSanitizer.SanitizeFilePath(currentDirectory));
            }
            catch (UnauthorizedAccessException ex)
            {
                Log.Debug(ex, "Skipped cleanup of incomplete download directory {Directory}", LoggingSanitizer.SanitizeFilePath(currentDirectory));
            }
        }
    }
}
