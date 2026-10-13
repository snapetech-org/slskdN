// <copyright file="IShareRepository.cs" company="slskd Team">
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

// <copyright file="IShareRepository.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Shares
{
    using System;
    using System.Collections.Generic;
    using Soulseek;

    /// <summary>
    ///     Persistent storage of shared files and metadata.
    /// </summary>
    public interface IShareRepository : IDisposable
    {
        /// <summary>
        ///     Gets the connection string for this repository.
        /// </summary>
        string ConnectionString { get; }

        /// <summary>
        ///     Backs the current database up to the database at the specified <paramref name="repository"/>.
        /// </summary>
        /// <param name="repository">The destination repository.</param>
        void BackupTo(IShareRepository repository);

        /// <summary>
        ///     Counts the number of directories in the database.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for counting subdirectories.</param>
        /// <returns>The number of directories.</returns>
        int CountDirectories(string? parentDirectory = null);

        /// <summary>
        ///     Counts the number of files in the database.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for counting files in a subdirectory.</param>
        /// <returns>The number of files.</returns>
        int CountFiles(string? parentDirectory = null);

        /// <summary>
        ///     Creates a new database.
        /// </summary>
        /// <remarks>
        ///     Creates tables using 'IF NOT EXISTS', so this is idempotent unless 'discardExisting` is specified, in which case
        ///     tables are explicitly dropped prior to creation.
        /// </remarks>
        /// <param name="discardExisting">An optional value that determines whether the existing database should be discarded.</param>
        void Create(bool discardExisting = false);

        /// <summary>
        ///     Dumps the contents of the database to a file.
        /// </summary>
        /// <param name="filename">The destination file.</param>
        void DumpTo(string filename);

        /// <summary>
        ///     Enable connection keepalive.
        /// </summary>
        /// <param name="enable">A value indicating whether the keepalive logic should be executed.</param>
        void EnableKeepalive(bool enable);

        /// <summary>
        ///     Finds the filename and length of the file matching the specified <paramref name="maskedFilename"/>.
        /// </summary>
        /// <param name="maskedFilename">The fully qualified remote path of the file.</param>
        /// <returns>The filename, if found.</returns>
        (string Filename, long Size) FindFileInfo(string maskedFilename);

        /// <summary>
        ///     Finds and returns the most recent scan record.
        /// </summary>
        /// <returns>The most recent scan record, or default if no scan was found.</returns>
        Scan? FindLatestScan();

        /// <summary>
        ///     Flags the latest scan as suspect, indicating that the cached contents may have diverged from physical storage.
        /// </summary>
        void FlagLatestScanAsSuspect();

        /// <summary>
        ///     Flags the scan with the specified <paramref name="timestamp"/> as suspect.
        /// </summary>
        /// <param name="timestamp">The start timestamp identifying the scan.</param>
        void FlagScanAsSuspect(long timestamp);

        /// <summary>
        ///     Inserts a directory.
        /// </summary>
        /// <param name="name">The fully qualified local name of the directory.</param>
        /// <param name="timestamp">The timestamp to assign to the record.</param>
        void InsertDirectory(string name, long timestamp);

        /// <summary>
        ///     Inserts a file.
        /// </summary>
        /// <param name="maskedFilename">The fully qualified remote path of the file.</param>
        /// <param name="originalFilename">The fully qualified local path of the file.</param>
        /// <param name="touchedAt">The timestamp at which the file was last modified, according to the host OS.</param>
        /// <param name="file">The Soulseek.File instance representing the file.</param>
        /// <param name="timestamp">The timestamp to assign to the record.</param>
        /// <param name="isBlocked">Whether the file is blocked by MCP.</param>
        /// <param name="isQuarantined">Whether the file is quarantined by MCP.</param>
        /// <param name="moderationReason">The moderation reason, if any.</param>
        void InsertFile(
            string maskedFilename,
            string originalFilename,
            DateTime touchedAt,
            File file,
            long timestamp,
            bool isBlocked = false,
            bool isQuarantined = false,
            string? moderationReason = null);

        /// <summary>
        ///     Inserts a scan record at the specified <paramref name="timestamp"/>.
        /// </summary>
        /// <param name="timestamp">The timestamp associated with the scan.</param>
        /// <param name="options">The options snapshot at the start of the scan.</param>
        void InsertScan(long timestamp, Options.SharesOptions options);

        /// <summary>
        ///     Lists all directories.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for listing subdirectories.</param>
        /// <returns>The list of directories.</returns>
        IEnumerable<string> ListDirectories(string? parentDirectory = null);

        /// <summary>
        ///     Streams directory names in database order without materializing the result set.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for listing subdirectories.</param>
        /// <returns>An ordered sequence of directory names.</returns>
        IEnumerable<string> EnumerateDirectories(string? parentDirectory = null);

        /// <summary>
        ///     Lists all files.
        /// </summary>
        /// <param name="parentDirectory">The optional parent directory.</param>
        /// <param name="includeFullPath">A value indicating whether the fully qualified path should be returned.</param>
        /// <returns>The list of files.</returns>
        IEnumerable<File> ListFiles(string? parentDirectory = null, bool includeFullPath = false);

        /// <summary>
        ///     Streams files in database order without materializing the result set.
        /// </summary>
        /// <param name="parentDirectory">The optional parent directory.</param>
        /// <param name="includeFullPath">Whether to return fully qualified remote paths.</param>
        /// <returns>An ordered sequence of files.</returns>
        IEnumerable<File> EnumerateFiles(string? parentDirectory = null, bool includeFullPath = false);

        /// <summary>
        ///     Lists local (original) file paths and sizes for all shared files.
        ///     Used by <see cref="Mesh.IFlacKeyToPathResolver"/> to serve proof-of-possession chunk requests (T-1434).
        /// </summary>
        /// <param name="parentDirectory">Optional. When set, filters by maskedFilename LIKE parentDirectory || '%'.</param>
        /// <returns>Sequence of (LocalPath, Size).</returns>
        IEnumerable<(string LocalPath, long Size)> ListLocalPathsAndSizes(string? parentDirectory = null);

        /// <summary>
        ///     Returns the list of all <see cref="Scan"/> started at or after the specified <paramref name="startedAtOrAfter"/>
        ///     unix timestamp.
        /// </summary>
        /// <param name="startedAtOrAfter">A unix timestamp that serves as the lower bound of the time-based listing.</param>
        /// <returns>The operation context, including the list of found scans.</returns>
        IEnumerable<Scan> ListScans(long startedAtOrAfter = 0);

        /// <summary>
        ///     Deletes directory records with a timestamp prior to the specified <paramref name="olderThanTimestamp"/>.
        /// </summary>
        /// <param name="olderThanTimestamp">The timestamp before which to delete directories.</param>
        /// <returns>The number of records deleted.</returns>
        long PruneDirectories(long olderThanTimestamp);

        /// <summary>
        ///     Deletes file records with a timestamp prior to the specified <paramref name="olderThanTimestamp"/>.
        /// </summary>
        /// <param name="olderThanTimestamp">The timestamp before which to delete files.</param>
        /// <returns>The number of records deleted.</returns>
        long PruneFiles(long olderThanTimestamp);

        /// <summary>
        ///     Rebuilds the filename index table using the data in the files table.
        /// </summary>
        void RebuildFilenameIndex();

        /// <summary>
        ///     Restores the current database from the database at the specified <paramref name="repository"/>.
        /// </summary>
        /// <param name="repository">The destination repository.</param>
        void RestoreFrom(IShareRepository repository);

        /// <summary>
        ///     Searches the database for files matching the specified <paramref name="query"/>.
        /// </summary>
        /// <param name="query">The search query.</param>
        /// <param name="limit">An optional row limit.</param>
        /// <returns>The list of matching files.</returns>
        IEnumerable<File> Search(SearchQuery query, int? limit = null);

        /// <summary>
        ///     Attempts to validate the backing database.
        /// </summary>
        /// <returns>A value indicating whether the database is valid.</returns>
        bool TryValidate();

        /// <summary>
        ///     Attempts to validate the backing database.
        /// </summary>
        /// <param name="problems">The list of problems, if the database is invalid.</param>
        /// <returns>A value indicating whether the database is valid.</returns>
        bool TryValidate(out IEnumerable<string> problems);

        /// <summary>
        ///     Updates the scan started at the specified <paramref name="timestamp"/> to set the <paramref name="end"/>.
        /// </summary>
        /// <param name="timestamp">The timestamp associated with the scan.</param>
        /// <param name="end">The timestamp at the conclusion of the scan.</param>
        void UpdateScan(long timestamp, long end);

        /// <summary>
        ///     Reclaims unused space.
        /// </summary>
        void Vacuum();

        /// <summary>
        ///     Checkpoints the write-ahead log to the database file.
        /// </summary>
        /// <returns>A value indicating whether the complete checkpoint succeeded.</returns>
        bool Checkpoint();

        // T-MCP03: Content item management for VirtualSoulfind advertisable gating

        /// <summary>
        ///     Inserts or updates a content item mapping.
        /// </summary>
        /// <param name="contentId">The unique content identifier.</param>
        /// <param name="domain">The content domain (Music, GenericFile, etc.).</param>
        /// <param name="workId">The optional parent work identifier.</param>
        /// <param name="maskedFilename">The file this content maps to.</param>
        /// <param name="isAdvertisable">Whether this content can be advertised.</param>
        /// <param name="moderationReason">The moderation reason, if any.</param>
        /// <param name="checkedAt">The timestamp when this was checked.</param>
        void UpsertContentItem(
            string contentId,
            string domain,
            string workId,
            string maskedFilename,
            bool isAdvertisable,
            string? moderationReason,
            long checkedAt);

        /// <summary>
        ///     Finds a content item by content ID.
        /// </summary>
        /// <param name="contentId">The content identifier.</param>
        /// <returns>The content item info, or null if not found.</returns>
        (string Domain, string WorkId, string MaskedFilename, bool IsAdvertisable, string ModerationReason, long CheckedAt)? FindContentItem(string contentId);

        /// <summary>
        ///     Lists all content items associated with a file.
        /// </summary>
        /// <param name="maskedFilename">The file to look up.</param>
        /// <returns>The list of content items for this file.</returns>
        IEnumerable<(string ContentId, string Domain, string WorkId, bool IsAdvertisable, string ModerationReason)> ListContentItemsForFile(string maskedFilename);

        /// <summary>
        ///     Lists advertisable content IDs whose files are not blocked or quarantined.
        /// </summary>
        IEnumerable<string> ListAdvertisableContentIds();

        /// <summary>
        ///     Counts advertisable content items.
        /// </summary>
        /// <returns>The number of advertisable items.</returns>
        int CountAdvertisableItems();
    }
}
