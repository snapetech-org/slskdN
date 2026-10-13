// <copyright file="FilesController.cs" company="slskd Team">
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

// <copyright file="FilesController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Files.API
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel.DataAnnotations;
    using System.IO;
    using System.Linq;
    using System.Security;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using OneOf;
    using Serilog;
    using slskd.Common.Security;
    using slskd.Core.Security;

    /// <summary>
    ///     Files.
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class FilesController : ControllerBase
    {
        public FilesController(
            FileService fileService,
            IOptionsSnapshot<Options> optionsSnapshot)
        {
            Files = fileService;
            OptionsSnapshot = optionsSnapshot;
        }

        private FileService Files { get; }
        private IOptionsSnapshot<Options> OptionsSnapshot { get; }
        private ILogger Log { get; set; } = Serilog.Log.ForContext<FilesController>();

        /// <summary>
        ///     Lists the contents of the downloads directory.
        /// </summary>
        /// <param name="recursive">An optional value indicating whether to recursively list subdirectories and files.</param>
        /// <param name="includeDirectorySizes">An optional value indicating whether to total file sizes below each listed directory.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        [HttpGet("downloads/directories")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(FilesystemDirectory), 200)]
        [ProducesResponseType(401)]
        public Task<IActionResult> GetDownloadContentsAsync(
            [FromQuery] bool recursive = false,
            [FromQuery] bool includeDirectorySizes = false)
                    => ListDirectoryAsync(OptionsSnapshot.Value.Directories.Downloads, null, recursive, includeDirectorySizes);

        /// <summary>
        ///     Lists the contents of the specified subdirectory within the downloads directory.
        /// </summary>
        /// <param name="base64SubdirectoryName">The relative, base 64 encoded, name of the subdirectory to list.</param>
        /// <param name="recursive">An optional value indicating whether to recursively list subdirectories and files.</param>
        /// <param name="includeDirectorySizes">An optional value indicating whether to total file sizes below each listed directory.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        /// <response code="403">Access to the specified subdirectory was denied.</response>
        /// <response code="404">The specified subdirectory does not exist.</response>
        [HttpGet("downloads/directories/{base64SubdirectoryName}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(FilesystemDirectory), 200)]
        [ProducesResponseType(401)]
        [ProducesResponseType(403)]
        [ProducesResponseType(404)]
        public Task<IActionResult> GetDownloadSubdirectoryContentsAsync(
            [FromRoute] string base64SubdirectoryName,
            [FromQuery] bool recursive = false,
            [FromQuery] bool includeDirectorySizes = false)
                    => ListDirectoryAsync(OptionsSnapshot.Value.Directories.Downloads, base64SubdirectoryName, recursive, includeDirectorySizes);

        /// <summary>
        ///     Deletes the specified subdirectory within the downloads directory.
        /// </summary>
        /// <param name="base64SubdirectoryName">The relative, base 64 encoded, name of the subdirectory to delete.</param>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        /// <response code="403">Access to the specified subdirectory was denied.</response>
        /// <response code="404">The specified subdirectory does not exist.</response>
        [HttpDelete("downloads/directories/{base64SubdirectoryName}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public Task<IActionResult> DeleteDownloadSubdirectoryAsync([FromRoute] string base64SubdirectoryName)
                    => DeleteSubdirectoryAsync(rootDirectory: OptionsSnapshot.Value.Directories.Downloads, base64SubdirectoryName);

        /// <summary>
        ///     Deletes the specified file within the downloads directory.
        /// </summary>
        /// <param name="base64FileName">The relative, base 64 encoded, name of the file to delete.</param>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        /// <response code="403">Access to the specified subdirectory was denied.</response>
        /// <response code="404">The specified subdirectory does not exist.</response>
        [HttpDelete("downloads/files/{base64FileName}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public Task<IActionResult> DeleteDownloadFileAsync([FromRoute] string base64FileName)
                    => DeleteFileAsync(rootDirectory: OptionsSnapshot.Value.Directories.Downloads, base64FileName);

        /// <summary>
        ///     Deletes a set of files and directories below the downloads directory.
        /// </summary>
        /// <param name="request">The relative paths and item types to delete.</param>
        /// <returns>One result for each requested item.</returns>
        /// <response code="200">Every requested item was deleted.</response>
        /// <response code="207">Some requested items could not be deleted.</response>
        /// <response code="400">The request contains an invalid or overlapping path.</response>
        /// <response code="403">Remote file management is disabled or a path is forbidden.</response>
        [HttpDelete("downloads/items")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(DeleteItemsResponse), 200)]
        [ProducesResponseType(typeof(DeleteItemsResponse), 207)]
        public Task<IActionResult> DeleteDownloadItemsAsync([FromBody] DeleteItemsRequest request)
            => DeleteItemsAsync(OptionsSnapshot.Value.Directories.Downloads, request);

        /// <summary>
        ///     Lists the contents of the downloads directory.
        /// </summary>
        /// <param name="recursive">An optional value indicating whether to recursively list subdirectories and files.</param>
        /// <param name="includeDirectorySizes">An optional value indicating whether to total file sizes below each listed directory.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        [HttpGet("incomplete/directories")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(FilesystemDirectory), 200)]
        public Task<IActionResult> GetIncompleteContentsAsync(
            [FromQuery] bool recursive = false,
            [FromQuery] bool includeDirectorySizes = false)
                    => ListDirectoryAsync(OptionsSnapshot.Value.Directories.Incomplete, null, recursive, includeDirectorySizes);

        /// <summary>
        ///     Lists the contents of the specified subdirectory within the incomplete directory.
        /// </summary>
        /// <param name="base64SubdirectoryName">The relative, base 64 encoded, name of the subdirectory to list.</param>
        /// <param name="recursive">An optional value indicating whether to recursively list subdirectories and files.</param>
        /// <param name="includeDirectorySizes">An optional value indicating whether to total file sizes below each listed directory.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        /// <response code="403">Access to the specified subdirectory was denied.</response>
        /// <response code="404">The specified subdirectory does not exist.</response>
        [HttpGet("incomplete/directories/{base64SubdirectoryName}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(FilesystemDirectory), 200)]
        public Task<IActionResult> GetIncompleteSubdirectoryContentsAsync(
            [FromRoute, Required] string base64SubdirectoryName,
            [FromQuery] bool recursive = false,
            [FromQuery] bool includeDirectorySizes = false)
                    => ListDirectoryAsync(OptionsSnapshot.Value.Directories.Incomplete, base64SubdirectoryName, recursive, includeDirectorySizes);

        /// <summary>
        ///     Deletes the specified subdirectory within the downloads directory.
        /// </summary>
        /// <param name="base64SubdirectoryName">The relative, base 64 encoded, name of the subdirectory to delete.</param>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        /// <response code="403">Access to the specified subdirectory was denied.</response>
        /// <response code="404">The specified subdirectory does not exist.</response>
        [HttpDelete("incomplete/directories/{base64SubdirectoryName}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public Task<IActionResult> DeleteIncompleteSubdirectoryAsync([FromRoute] string base64SubdirectoryName)
                    => DeleteSubdirectoryAsync(rootDirectory: OptionsSnapshot.Value.Directories.Incomplete, base64SubdirectoryName);

        /// <summary>
        ///     Deletes the specified file within the downloads directory.
        /// </summary>
        /// <param name="base64FileName">The relative, base 64 encoded, name of the file to delete.</param>
        /// <returns></returns>
        /// <response code="204">The request completed successfully.</response>
        /// <response code="401">Authentication failed.</response>
        /// <response code="403">Access to the specified subdirectory was denied.</response>
        /// <response code="404">The specified subdirectory does not exist.</response>
        [HttpDelete("incomplete/files/{base64FileName}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public Task<IActionResult> DeleteIncompleteFileAsync([FromRoute] string base64FileName)
                    => DeleteFileAsync(rootDirectory: OptionsSnapshot.Value.Directories.Incomplete, base64FileName);

        /// <summary>
        ///     Deletes a set of files and directories below the incomplete directory.
        /// </summary>
        /// <param name="request">The relative paths and item types to delete.</param>
        /// <returns>One result for each requested item.</returns>
        /// <response code="200">Every requested item was deleted.</response>
        /// <response code="207">Some requested items could not be deleted.</response>
        /// <response code="400">The request contains an invalid or overlapping path.</response>
        /// <response code="403">Remote file management is disabled or a path is forbidden.</response>
        [HttpDelete("incomplete/items")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(DeleteItemsResponse), 200)]
        [ProducesResponseType(typeof(DeleteItemsResponse), 207)]
        public Task<IActionResult> DeleteIncompleteItemsAsync([FromBody] DeleteItemsRequest request)
            => DeleteItemsAsync(OptionsSnapshot.Value.Directories.Incomplete, request);

        private async Task<IActionResult> ListDirectoryAsync(
            string rootDirectory,
            string? base64SubdirectoryName = null,
            bool recursive = false,
            bool includeDirectorySizes = false)
        {
            if (!TryDecodeRelativePath(base64SubdirectoryName, out var relativeDirectory))
            {
                return BadRequest("Invalid directory path");
            }

            var requestedDir = PathGuard.NormalizeAndValidate(
                string.IsNullOrWhiteSpace(relativeDirectory) ? "." : relativeDirectory,
                rootDirectory);
            if (requestedDir == null)
            {
                return BadRequest("Invalid directory path");
            }

            Log.Debug("Listing directory '{Directory}'", requestedDir);

            try
            {
                var response = await Files.ListContentsAsync(
                    directory: requestedDir,
                    enumerationOptions: new EnumerationOptions
                    {
                        AttributesToSkip = FileAttributes.System | FileAttributes.ReparsePoint,
                        RecurseSubdirectories = recursive,
                    },
                    includeDirectorySizes: includeDirectorySizes);

                return Ok(response);
            }
            catch (SecurityException)
            {
                Log.Warning("Directory listing of '{Directory}' forbidden", requestedDir);
                return Forbid();
            }
            catch (NotFoundException)
            {
                Log.Debug("Directory '{Directory}' not found", requestedDir);
                return NotFound();
            }
        }

        private async Task<IActionResult> DeleteItemsAsync(string rootDirectory, DeleteItemsRequest request)
        {
            if (!OptionsSnapshot.Value.RemoteFileManagement)
            {
                return Forbid();
            }

            var items = request?.Items?.ToArray() ?? Array.Empty<DeleteItemRequest>();
            if (items.Length == 0 || items.Length > 10_000)
            {
                return BadRequest("The request must contain between 1 and 10000 items");
            }

            var normalizedRoot = PathGuard.NormalizeAndValidate(".", rootDirectory);
            if (normalizedRoot is null)
            {
                return BadRequest("Invalid files root");
            }

            var fullRoot = Path.TrimEndingDirectorySeparator(normalizedRoot);
            var pathComparer = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
            var seen = new HashSet<string>(pathComparer);
            var normalizedItems = new List<(DeleteItemRequest Item, string FullPath, string Kind)>(items.Length);

            foreach (var item in items)
            {
                if (item is null)
                {
                    return BadRequest("Every item must have a relative path and a type of file or directory");
                }

                var kind = item.Type?.Trim();
                var path = item.Path?.Trim();
                if (string.IsNullOrWhiteSpace(path) || string.IsNullOrWhiteSpace(kind) ||
                    (!kind.Equals("file", StringComparison.OrdinalIgnoreCase) &&
                        !kind.Equals("directory", StringComparison.OrdinalIgnoreCase)))
                {
                    return BadRequest("Every item must have a relative path and a type of file or directory");
                }

                var fullPath = PathGuard.NormalizeAndValidate(path, rootDirectory);
                if (fullPath is null || pathComparer.Equals(fullPath, fullRoot))
                {
                    return BadRequest("Invalid item path");
                }

                if (!seen.Add(fullPath))
                {
                    return BadRequest("The request contains duplicate item paths");
                }

                normalizedItems.Add((item, fullPath, kind!));
            }

            foreach (var parent in normalizedItems.Where(item => item.Kind.Equals("directory", StringComparison.OrdinalIgnoreCase)))
            {
                if (normalizedItems.Any(child =>
                    !pathComparer.Equals(parent.FullPath, child.FullPath) &&
                    IsDescendantPath(parent.FullPath, child.FullPath)))
                {
                    return BadRequest("A selected directory cannot overlap another selected item");
                }
            }

            var directoryItems = normalizedItems
                .Where(item => item.Kind.Equals("directory", StringComparison.OrdinalIgnoreCase))
                .ToArray();
            var fileItems = normalizedItems
                .Where(item => item.Kind.Equals("file", StringComparison.OrdinalIgnoreCase))
                .ToArray();

            var directoryResults = directoryItems.Length == 0
                ? new Dictionary<string, OneOf<bool, Exception>>()
                : await Files.DeleteDirectoriesAsync(directoryItems.Select(item => item.FullPath).ToArray());
            var fileResults = fileItems.Length == 0
                ? new Dictionary<string, OneOf<bool, Exception>>()
                : await Files.DeleteFilesAsync(fileItems.Select(item => item.FullPath).ToArray());

            var results = normalizedItems.Select(item =>
            {
                var operationResults = item.Kind.Equals("directory", StringComparison.OrdinalIgnoreCase)
                    ? directoryResults
                    : fileResults;
                var result = operationResults[item.FullPath];
                return result.Match(
                    _ => new DeleteItemResult(item.Item.Path, item.Kind.ToLowerInvariant(), true, null),
                    exception => new DeleteItemResult(
                        item.Item.Path,
                        item.Kind.ToLowerInvariant(),
                        false,
                        GetSafeDeleteError(exception)));
            }).ToArray();

            var response = new DeleteItemsResponse { Results = results };
            return results.All(result => result.Succeeded)
                ? Ok(response)
                : StatusCode(207, response);
        }

        private static bool IsDescendantPath(string parent, string path)
        {
            var relative = Path.GetRelativePath(parent, path);
            return relative != "." &&
                relative != ".." &&
                !relative.StartsWith($"..{Path.DirectorySeparatorChar}", StringComparison.Ordinal) &&
                !relative.StartsWith($"..{Path.AltDirectorySeparatorChar}", StringComparison.Ordinal) &&
                !Path.IsPathRooted(relative);
        }

        private static string GetSafeDeleteError(Exception exception)
        {
            if (exception is NotFoundException || exception is FileNotFoundException || exception is DirectoryNotFoundException)
            {
                return "not-found";
            }

            if (exception is UnauthorizedException || exception is UnauthorizedAccessException || exception is SecurityException)
            {
                return "access-denied";
            }

            return "delete-failed";
        }

        private async Task<IActionResult> DeleteSubdirectoryAsync(string rootDirectory, string base64SubdirectoryName)
        {
            if (!OptionsSnapshot.Value.RemoteFileManagement)
            {
                return Forbid();
            }

            if (!TryDecodeRelativePath(base64SubdirectoryName, out var decodedDirectory) || string.IsNullOrWhiteSpace(decodedDirectory))
            {
                return BadRequest("Invalid directory path");
            }

            var requestedDir = PathGuard.NormalizeAndValidate(decodedDirectory, rootDirectory);
            if (requestedDir == null)
            {
                return BadRequest("Invalid directory path");
            }

            Log.Information("Deleting directory '{Directory}'", requestedDir);

            try
            {
                var results = await Files.DeleteDirectoriesAsync(requestedDir);

                return results[requestedDir].Match(
                    success => NoContent(),
                    failure => throw failure);
            }
            catch (SecurityException)
            {
                Log.Warning("Directory deletion of '{Directory}' forbidden", requestedDir);
                return Forbid();
            }
            catch (NotFoundException)
            {
                Log.Information("Directory '{Directory}' not found", requestedDir);
                return NotFound();
            }
        }

        private async Task<IActionResult> DeleteFileAsync(string rootDirectory, string base64FileName)
        {
            if (!OptionsSnapshot.Value.RemoteFileManagement)
            {
                return Forbid();
            }

            if (!TryDecodeRelativePath(base64FileName, out var decodedFilename) || string.IsNullOrWhiteSpace(decodedFilename))
            {
                return BadRequest("Invalid file path");
            }

            var requestedFilename = PathGuard.NormalizeAndValidate(decodedFilename, rootDirectory);
            if (requestedFilename == null)
            {
                return BadRequest("Invalid file path");
            }

            Log.Information("Deleting file '{File}'", requestedFilename);

            try
            {
                var results = await Files.DeleteFilesAsync(requestedFilename);

                return results[requestedFilename].Match(
                    success => NoContent(),
                    failure => throw failure);
            }
            catch (SecurityException)
            {
                Log.Warning("File deletion of '{File}' forbidden", requestedFilename);
                return Forbid();
            }
            catch (UnauthorizedException)
            {
                Log.Warning("File deletion of '{File}' forbidden", requestedFilename);
                return Forbid();
            }
            catch (NotFoundException)
            {
                Log.Information("File '{File}' not found", requestedFilename);
                return NotFound();
            }
        }

        private static bool TryDecodeRelativePath(string? encodedPath, out string decodedPath)
        {
            decodedPath = string.Empty;

            encodedPath = encodedPath?.Trim() ?? string.Empty;
            if (string.IsNullOrEmpty(encodedPath))
            {
                return true;
            }

            try
            {
                decodedPath = encodedPath.FromBase64();
                decodedPath = decodedPath?.Trim() ?? string.Empty;
                return true;
            }
            catch (FormatException)
            {
                return false;
            }
            catch (ArgumentException)
            {
                return false;
            }
        }
    }
}
