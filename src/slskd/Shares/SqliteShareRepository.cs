// <copyright file="SqliteShareRepository.cs" company="slskd Team">
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

// <copyright file="SqliteShareRepository.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Shares
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Timers;
    using Microsoft.Data.Sqlite;
    using Serilog;
    using slskd.Common.Security;
    using Soulseek;

    /// <summary>
    ///     Persistent storage of shared files and metadata.
    /// </summary>
    public class SqliteShareRepository : IShareRepository
    {
        private static readonly StringComparison PathComparison = OperatingSystem.IsWindows()
            ? StringComparison.OrdinalIgnoreCase
            : StringComparison.Ordinal;

        /// <summary>
        ///     Initializes a new instance of the <see cref="SqliteShareRepository"/> class.
        /// </summary>
        /// <param name="connectionString"></param>
        public SqliteShareRepository(string connectionString)
        {
            ConnectionString = NormalizeConnectionString(connectionString);

            // in-memory databases will be destroyed if at any point the number of connections reaches zero. to prevent this,
            // create a connection and hold it open for the duration of the application. SQLite will destroy this database when
            // the connection that created it closes. since this is the first connection, it *should* keep the db alive. it's
            // possible that this connection will be recycled somehow due to pooling; the app will crash if this happens so i'll
            // know to keep digging.
            KeepaliveConnection = GetConnection(ConnectionString);
            KeepaliveTimer = new Timer(1000)
            {
                AutoReset = true,
                Enabled = false, // enabled later
            };

            KeepaliveTimer.Elapsed += (_, _) => Keepalive();
        }

        /// <summary>
        ///     Gets the connection string for this repository.
        /// </summary>
        public string ConnectionString { get; }

        private bool Disposed { get; set; }
        private SqliteConnection KeepaliveConnection { get; }
        private Timer KeepaliveTimer { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<SqliteShareRepository>();

        /// <summary>
        ///     Backs the current database up to the database at the specified <paramref name="repository"/>.
        /// </summary>
        /// <param name="repository">The destination repository.</param>
        public void BackupTo(IShareRepository repository)
        {
            using var sourceConn = GetConnection(ConnectionString);
            using var backupConn = GetConnection(repository.ConnectionString);
            sourceConn.BackupDatabase(backupConn);

            Log.Debug("Vacuuming backup");
            using var cmd = new SqliteCommand("VACUUM", backupConn);
            cmd.ExecuteNonQuery();
            Log.Debug("Backup vacuumed successfully");

            if (!Checkpoint(backupConn))
            {
                Log.Warning("Share database backup WAL checkpoint was blocked by an active reader");
            }
        }

        /// <summary>
        ///     Counts the number of directories in the database.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for counting subdirectories.</param>
        /// <returns>The number of directories.</returns>
        public int CountDirectories(string? parentDirectory = null)
        {
            using var conn = GetConnection();

            SqliteCommand? cmd = null;

            try
            {
                if (string.IsNullOrEmpty(parentDirectory))
                {
                    cmd = new SqliteCommand("SELECT COUNT(*) FROM directories;", conn);
                }
                else
                {
                    cmd = new SqliteCommand("SELECT COUNT(*) FROM directories WHERE name LIKE @prefix || '%'", conn);
                    cmd.Parameters.AddWithValue("prefix", parentDirectory);
                }

                return Convert.ToInt32(cmd.ExecuteScalar());
            }
            finally
            {
                cmd?.Dispose();
            }
        }

        /// <summary>
        ///     Counts the number of files in the database.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for counting files in a subdirectory.</param>
        /// <returns>The number of files.</returns>
        public int CountFiles(string? parentDirectory = null)
        {
            using var conn = GetConnection();

            SqliteCommand? cmd = null;

            try
            {
                if (string.IsNullOrEmpty(parentDirectory))
                {
                    cmd = new SqliteCommand("SELECT COUNT(*) FROM files;", conn);
                }
                else
                {
                    cmd = new SqliteCommand("SELECT COUNT(*) FROM files WHERE maskedFilename LIKE @prefix || '%'", conn);
                    cmd.Parameters.AddWithValue("prefix", parentDirectory);
                }

                return Convert.ToInt32(cmd.ExecuteScalar());
            }
            finally
            {
                cmd?.Dispose();
            }
        }

        /// <summary>
        ///     Creates a new database.
        /// </summary>
        /// <remarks>
        ///     Creates tables using 'IF NOT EXISTS', so this is idempotent unless 'discardExisting` is specified, in which case
        ///     tables are explicitly dropped prior to creation.
        /// </remarks>
        /// <param name="discardExisting">An optional value that determines whether the existing database should be discarded.</param>
        public void Create(bool discardExisting = false)
        {
            using var conn = GetConnection();

            // warning: with synchronous=0, an operating system crash can leave the database corrupted.
            // if this occurs we should generate a new one, so this is _probably_ ok
            conn.ExecuteNonQuery("PRAGMA journal_mode=WAL; PRAGMA synchronous=0;");

            if (discardExisting)
            {
                conn.ExecuteNonQuery("DROP TABLE IF EXISTS content_items; DROP TABLE IF EXISTS version; DROP TABLE IF EXISTS scans; DROP TABLE IF EXISTS directories; DROP TABLE IF EXISTS filenames; DROP TABLE IF EXISTS files;");
            }

            conn.ExecuteNonQuery("CREATE TABLE IF NOT EXISTS version (a INTEGER PRIMARY KEY)");

            conn.ExecuteNonQuery("CREATE TABLE IF NOT EXISTS scans (timestamp INTEGER PRIMARY KEY, options TEXT NOT NULL, end INTEGER DEFAULT NULL, suspect INTEGER DEFAULT 0);");

            conn.ExecuteNonQuery("CREATE TABLE IF NOT EXISTS directories (name TEXT PRIMARY KEY, timestamp INTEGER NOT NULL);");

            conn.ExecuteNonQuery("CREATE VIRTUAL TABLE IF NOT EXISTS filenames USING fts5(maskedFilename);");

            conn.ExecuteNonQuery("CREATE TABLE IF NOT EXISTS files " +
                "(maskedFilename TEXT PRIMARY KEY, originalFilename TEXT NOT NULL, size BIGINT NOT NULL, touchedAt TEXT NOT NULL, code INTEGER DEFAULT 1 NOT NULL, " +
                "extension TEXT, attributeJson TEXT NOT NULL, timestamp INTEGER NOT NULL, " +
                "isBlocked INTEGER DEFAULT 0 NOT NULL, isQuarantined INTEGER DEFAULT 0 NOT NULL, moderationReason TEXT);");

            // T-MCP03: Content items table for VirtualSoulfind advertisable gating
            // Maps ContentId → file(s), tracks IsAdvertisable state per content item
            conn.ExecuteNonQuery("CREATE TABLE IF NOT EXISTS content_items " +
                "(contentId TEXT PRIMARY KEY, " +
                "domain TEXT NOT NULL, " +
                "workId TEXT, " +
                "maskedFilename TEXT NOT NULL, " +
                "isAdvertisable INTEGER DEFAULT 0 NOT NULL, " +
                "moderationReason TEXT, " +
                "checkedAt INTEGER NOT NULL, " +
                "FOREIGN KEY(maskedFilename) REFERENCES files(maskedFilename) ON DELETE CASCADE);");

            conn.ExecuteNonQuery("CREATE INDEX IF NOT EXISTS idx_content_items_filename ON content_items(maskedFilename);");
            conn.ExecuteNonQuery("CREATE INDEX IF NOT EXISTS idx_content_items_advertisable ON content_items(isAdvertisable);");
        }

        /// <summary>
        ///     Disposes this object.
        /// </summary>
        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        ///     Dumps the contents of the database to a file.
        /// </summary>
        /// <param name="filename">The destination file.</param>
        public void DumpTo(string filename)
        {
            using var sourceConn = GetConnection(ConnectionString);

            // very important! don't use pooling for the backup connection or the file will remain locked
            using var backupConn = GetConnection($"Data Source={filename};Pooling=False");
            sourceConn.BackupDatabase(backupConn);
        }

        /// <summary>
        ///     Enable connection keepalive.
        /// </summary>
        /// <param name="enable">A value indicating whether the keepalive logic should be executed.</param>
        public void EnableKeepalive(bool enable) => KeepaliveTimer.Enabled = enable;

        /// <summary>
        ///     Finds the filename of the file matching the specified <paramref name="maskedFilename"/>.
        /// </summary>
        /// <param name="maskedFilename">The fully qualified remote path of the file.</param>
        /// <returns>The filename, if found.</returns>
        public (string Filename, long Size) FindFileInfo(string maskedFilename)
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand("SELECT originalFilename, size FROM files WHERE maskedFilename = @maskedFilename;", conn);
            cmd.Parameters.AddWithValue("maskedFilename", maskedFilename);

            using var reader = cmd.ExecuteReader();

            if (!reader.Read())
            {
                Log.Debug("Failed to resolve shared file {Filename}", maskedFilename);
                return default;
            }

            var filename = (string)reader["originalFilename"];
            var size = (long)reader["size"];
            Log.Debug($"Resolved requested shared file {maskedFilename} to {filename} ({size} bytes)");
            return (filename, size);
        }

        /// <summary>
        ///     Finds and returns the most recent scan record.
        /// </summary>
        /// <returns>The most recent scan record, or default if no scan was found.</returns>
        public Scan? FindLatestScan()
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand("SELECT timestamp, options, COALESCE(end, -1), suspect FROM scans ORDER BY timestamp DESC LIMIT 1", conn);

            using var reader = cmd.ExecuteReader();

            if (!reader.Read())
            {
                return default;
            }

            var timestamp = reader.GetInt64(0);
            var optionsJson = reader.GetString(1);

            var endRaw = reader.GetInt64(2);
            long? end = endRaw == -1 ? null : endRaw;

            var suspect = reader.GetInt32(3) > 0;

            return new Scan { StartedAt = timestamp, OptionsJson = optionsJson, EndedAt = end, Suspect = suspect };
        }

        /// <summary>
        ///     Flags the latest scan as suspect, indicating that the cached contents may have diverged from physical storage.
        /// </summary>
        public void FlagLatestScanAsSuspect()
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand("UPDATE scans SET suspect = 1 WHERE timestamp = (SELECT timestamp FROM scans ORDER BY timestamp DESC LIMIT 1)", conn);

            cmd.ExecuteNonQuery();
        }

        /// <inheritdoc/>
        public void FlagScanAsSuspect(long timestamp)
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand("UPDATE scans SET suspect = 1 WHERE timestamp = @timestamp", conn);
            cmd.Parameters.AddWithValue("timestamp", timestamp);
            cmd.ExecuteNonQuery();
        }

        /// <summary>
        ///     Inserts a directory.
        /// </summary>
        /// <param name="name">The fully qualified local name of the directory.</param>
        /// <param name="timestamp">The timestamp to assign to the record.</param>
        public void InsertDirectory(string name, long timestamp)
        {
            using var conn = GetConnection();

            conn.ExecuteNonQuery("INSERT INTO directories VALUES(@name, @timestamp) ON CONFLICT DO UPDATE SET timestamp = excluded.timestamp;", cmd =>
            {
                cmd.Parameters.AddWithValue("name", name);
                cmd.Parameters.AddWithValue("timestamp", timestamp);
            });
        }

        /// <summary>
        ///     Inserts a file.
        /// </summary>
        /// <param name="maskedFilename">The fully qualified remote path of the file.</param>
        /// <param name="originalFilename">The fully qualified local path of the file.</param>
        /// <param name="touchedAt">The timestamp at which the file was last modified, according to the host OS.</param>
        /// <param name="file">The Soulseek.File instance representing the file.</param>
        /// <param name="timestamp">The timestamp to assign to the record.</param>
        /// <param name="isBlocked">Whether the file is blocked by MCP (T-MCP02).</param>
        /// <param name="isQuarantined">Whether the file is quarantined by MCP (T-MCP02).</param>
        /// <param name="moderationReason">The moderation reason, if any (T-MCP02).</param>
        public void InsertFile(
            string maskedFilename,
            string originalFilename,
            DateTime touchedAt,
            Soulseek.File file,
            long timestamp,
            bool isBlocked = false,
            bool isQuarantined = false,
            string? moderationReason = null)
        {
            using var conn = GetConnection();

            conn.ExecuteNonQuery("INSERT INTO files (maskedFilename, originalFilename, size, touchedAt, code, extension, attributeJson, timestamp, isBlocked, isQuarantined, moderationReason) " +
                "VALUES(@maskedFilename, @originalFilename, @size, @touchedAt, @code, @extension, @attributeJson, @timestamp, @isBlocked, @isQuarantined, @moderationReason) " +
                "ON CONFLICT DO UPDATE SET originalFilename = excluded.originalFilename, size = excluded.size, touchedAt = excluded.touchedAt, " +
                "code = excluded.code, extension = excluded.extension, attributeJson = excluded.attributeJson, timestamp = excluded.timestamp, " +
                "isBlocked = excluded.isBlocked, isQuarantined = excluded.isQuarantined, moderationReason = excluded.moderationReason;", cmd =>
                {
                    cmd.Parameters.AddWithValue("maskedFilename", maskedFilename);
                    cmd.Parameters.AddWithValue("originalFilename", originalFilename);
                    cmd.Parameters.AddWithValue("size", file.Size);
                    cmd.Parameters.AddWithValue("touchedAt", touchedAt.ToLongDateString());
                    cmd.Parameters.AddWithValue("code", file.Code);
                    cmd.Parameters.AddWithValue("extension", file.Extension);
                    cmd.Parameters.AddWithValue("attributeJson", file.Attributes.ToJson());
                    cmd.Parameters.AddWithValue("timestamp", timestamp);
                    cmd.Parameters.AddWithValue("isBlocked", isBlocked ? 1 : 0);
                    cmd.Parameters.AddWithValue("isQuarantined", isQuarantined ? 1 : 0);
                    cmd.Parameters.AddWithValue("moderationReason", moderationReason ?? (object)DBNull.Value);
                });
        }

        /// <summary>
        ///     Inserts a scan record at the specified <paramref name="timestamp"/>.
        /// </summary>
        /// <param name="timestamp">The timestamp associated with the scan.</param>
        /// <param name="options">The options snapshot at the start of the scan.</param>
        public void InsertScan(long timestamp, Options.SharesOptions options)
        {
            using var conn = GetConnection();

            conn.ExecuteNonQuery("INSERT INTO scans (timestamp, options) VALUES(@timestamp, @options)", cmd =>
            {
                cmd.Parameters.AddWithValue("timestamp", timestamp);
                cmd.Parameters.AddWithValue("options", options.ToJson());
            });
        }

        /// <summary>
        ///     Lists all directories.
        /// </summary>
        /// <param name="parentDirectory">The optional directory prefix used for listing subdirectories.</param>
        /// <returns>The list of directories.</returns>
        public IEnumerable<string> ListDirectories(string? parentDirectory = null) => EnumerateDirectories(parentDirectory).ToList();

        /// <inheritdoc />
        public IEnumerable<string> EnumerateDirectories(string? parentDirectory = null)
        {
            using var conn = GetConnection();
            using var cmd = string.IsNullOrEmpty(parentDirectory)
                ? new SqliteCommand("SELECT name FROM directories ORDER BY name ASC;", conn)
                : new SqliteCommand("SELECT name from directories WHERE name LIKE @prefix || '%' ORDER BY name ASC;", conn);

            if (!string.IsNullOrEmpty(parentDirectory))
            {
                cmd.Parameters.AddWithValue("prefix", parentDirectory);
            }

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                yield return reader.GetString(0);
            }
        }

        /// <summary>
        ///     Lists all files.
        /// </summary>
        /// <param name="parentDirectory">The optional parent directory.</param>
        /// <param name="includeFullPath">A value indicating whether the fully qualified path should be returned.</param>
        /// <returns>The list of files.</returns>
        public IEnumerable<Soulseek.File> ListFiles(string? parentDirectory = null, bool includeFullPath = false) => EnumerateFiles(parentDirectory, includeFullPath).ToList();

        /// <inheritdoc />
        public IEnumerable<Soulseek.File> EnumerateFiles(string? parentDirectory = null, bool includeFullPath = false)
        {
            using var conn = GetConnection();
            using var cmd = string.IsNullOrEmpty(parentDirectory)
                ? new SqliteCommand(
                    "SELECT maskedFilename, code, size, extension, attributeJson FROM files " +
                    "WHERE isBlocked = 0 AND isQuarantined = 0 " +
                    "ORDER BY maskedFilename ASC;",
                    conn)
                : new SqliteCommand(
                    "SELECT maskedFilename, code, size, extension, attributeJson FROM files " +
                    "WHERE maskedFilename LIKE @match AND isBlocked = 0 AND isQuarantined = 0 " +
                    "ORDER BY maskedFilename ASC;",
                    conn);

            if (!string.IsNullOrEmpty(parentDirectory))
            {
                cmd.Parameters.AddWithValue("match", parentDirectory + '%');
            }

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var filename = reader.GetString(0);
                var code = reader.GetInt32(1);
                var size = reader.GetInt64(2);
                var extension = reader.GetString(3);
                var attributeJson = reader.GetString(4);
                var attributeList = attributeJson.FromJson<List<FileAttribute>>();

                filename = includeFullPath ? filename : filename.GetNormalizedFileName();
                yield return new Soulseek.File(code, filename, size, extension, attributeList);
            }
        }

        /// <inheritdoc/>
        public IEnumerable<(string LocalPath, long Size)> ListLocalPathsAndSizes(string? parentDirectory = null)
        {
            var results = new List<(string, long)>();
            using var conn = GetConnection();
            SqliteCommand cmd;
            if (string.IsNullOrEmpty(parentDirectory))
            {
                cmd = new SqliteCommand(
                    "SELECT originalFilename, size FROM files WHERE isBlocked = 0 AND isQuarantined = 0;",
                    conn);
            }
            else
            {
                cmd = new SqliteCommand(
                    "SELECT originalFilename, size FROM files WHERE isBlocked = 0 AND isQuarantined = 0 AND maskedFilename LIKE @prefix || '%';",
                    conn);
                cmd.Parameters.AddWithValue("prefix", parentDirectory);
            }

            using (cmd)
            {
                using var reader = cmd.ExecuteReader();
                while (reader.Read())
                {
                    var path = reader.GetString(0);
                    var size = reader.GetInt64(1);
                    results.Add((path, size));
                }
            }

            return results;
        }

        /// <summary>
        ///     Returns the list of all <see cref="Scan"/> started at or after the specified <paramref name="startedAtOrAfter"/>
        ///     unix timestamp.
        /// </summary>
        /// <param name="startedAtOrAfter">A unix timestamp that serves as the lower bound of the time-based listing.</param>
        /// <returns>The operation context, including the list of found scans.</returns>
        public IEnumerable<Scan> ListScans(long startedAtOrAfter = 0)
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand($"SELECT timestamp, options, COALESCE(end, -1), suspect FROM scans WHERE timestamp >= {startedAtOrAfter}", conn);

            using var reader = cmd.ExecuteReader();
            var scans = new List<Scan>();

            while (reader.Read())
            {
                var timestamp = reader.GetInt64(0);
                var optionsJson = reader.GetString(1);

                var endRaw = reader.GetInt64(2);
                long? end = endRaw == -1 ? null : endRaw;

                var suspect = reader.GetInt32(3) > 0;

                scans.Add(new Scan { StartedAt = timestamp, OptionsJson = optionsJson, EndedAt = end, Suspect = suspect });
            }

            return scans;
        }

        /// <summary>
        ///     Deletes directory records with a timestamp prior to the specified <paramref name="olderThanTimestamp"/>.
        /// </summary>
        /// <param name="olderThanTimestamp">The timestamp before which to delete directories.</param>
        /// <returns>The number of records deleted.</returns>
        public long PruneDirectories(long olderThanTimestamp)
        {
            using var conn = GetConnection();

            using var cmd = new SqliteCommand("DELETE FROM directories WHERE timestamp < @timestamp; SELECT changes()", conn);
            cmd.Parameters.AddWithValue("timestamp", olderThanTimestamp);

            using var reader = cmd.ExecuteReader();
            reader.Read();

            return reader.GetInt64(0);
        }

        /// <summary>
        ///     Deletes file records with a timestamp prior to the specified <paramref name="olderThanTimestamp"/>.
        /// </summary>
        /// <param name="olderThanTimestamp">The timestamp before which to delete files.</param>
        /// <returns>The number of records deleted.</returns>
        public long PruneFiles(long olderThanTimestamp)
        {
            using var conn = GetConnection();

            using var cmd = new SqliteCommand("DELETE FROM files WHERE timestamp < @timestamp; SELECT changes()", conn);
            cmd.Parameters.AddWithValue("timestamp", olderThanTimestamp);

            using var reader = cmd.ExecuteReader();
            reader.Read();

            return reader.GetInt64(0);
        }

        /// <summary>
        ///     Rebuilds the filename index table using the data in the files table.
        /// </summary>
        public void RebuildFilenameIndex()
        {
            using var conn = GetConnection();

            conn.ExecuteNonQuery("DELETE from filenames; INSERT INTO filenames SELECT maskedFilename FROM files;");
        }

        /// <summary>
        ///     Restores the current database from the database at the specified <paramref name="repository"/>.
        /// </summary>
        /// <param name="repository">The destination repository.</param>
        public void RestoreFrom(IShareRepository repository)
        {
            using var sourceConn = GetConnection(repository.ConnectionString);
            using var restoreConn = GetConnection();
            sourceConn.BackupDatabase(restoreConn);
        }

        /// <summary>
        ///     Searches the database for files matching the specified <paramref name="query"/>.
        /// </summary>
        /// <param name="query">The search query.</param>
        /// <param name="limit">An optional row limit.</param>
        /// <returns>The list of matching files.</returns>
        public IEnumerable<Soulseek.File> Search(SearchQuery query, int? limit = null)
        {
            string Clean(string str) => str.Replace("/", " ")
                .Replace("\\", " ")
                .Replace(":", " ")
                .Replace("\"", " ")
                .Replace("'", "''");

            var match = string.Join(" AND ", query.Terms.Select(token => $"\"{Clean(token)}\""));
            var exclusions = string.Join(" OR ", query.Exclusions.Select(exclusion => $"\"{Clean(exclusion)}\""));

            var ftsQuery = $"({match}) {(query.Exclusions.Any() ? $"NOT ({exclusions})" : string.Empty)}";
            var sql = "SELECT files.maskedFilename, files.code, files.size, files.extension, files.attributeJson FROM filenames " +
                "INNER JOIN files ON filenames.maskedFilename = files.maskedFilename " +
                "WHERE filenames MATCH @match " +
                $"ORDER BY filenames.maskedFilename ASC {(limit.HasValue ? $"LIMIT {limit.Value}" : string.Empty)};";

            var results = new List<Soulseek.File>();

            try
            {
                using var conn = GetConnection();
                using var cmd = new SqliteCommand(sql, conn);
                cmd.Parameters.AddWithValue("@match", ftsQuery);
                using var reader = cmd.ExecuteReader();

                while (reader.Read())
                {
                    var filename = reader.GetString(0);

                    // SQLite takes care of matching on tokens, but unfortunately doesn't work in cases where an exclusion appears as a substring.
                    // example: the token matching works to exclude the result "foo bar baz" given a "bar" exclusion, but does not exclude "foo xbarx baz"
                    // for this reason we must iterate over the exclusion list and ensure none appear as substrings
                    // **CAUTION** performance of this will degrade exponentially as the list of exclusions grows
                    if (query.Exclusions.Any(x => filename.Contains(x, StringComparison.OrdinalIgnoreCase)))
                    {
                        Log.Debug("Dropping excluded filename {File}", LoggingSanitizer.SanitizeFilePath(filename));
                        continue;
                    }

                    var code = reader.GetInt32(1);
                    var size = reader.GetInt64(2);
                    var extension = reader.GetString(3);
                    var attributeJson = reader.GetString(4);

                    var attributeList = attributeJson.FromJson<List<FileAttribute>>();

                    var file = new Soulseek.File(code, filename, size, extension, attributeList);
                    results.Add(file);
                }

                return results;
            }
            catch (Exception ex)
            {
                Log.Warning("Failed to execute shared file query '{Query}': {Exception}",
                    LoggingSanitizer.SanitizeQueryText(query.SearchText), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                return Enumerable.Empty<Soulseek.File>();
            }
        }

        /// <summary>
        ///     Attempts to validate the backing database.
        /// </summary>
        /// <returns>A value indicating whether the database is valid.</returns>
        public bool TryValidate()
        {
            return TryValidate(out _);
        }

        /// <summary>
        ///     Attempts to validate the backing database.
        /// </summary>
        /// <param name="problems">The list of problems, if the database is invalid.</param>
        /// <returns>A value indicating whether the database is valid.</returns>
        public bool TryValidate(out IEnumerable<string> problems)
        {
            var list = new List<string>();
            problems = list;

            // to update this schema map, run the following query against a valid, up-to-date database and paste the output below:
            // select '{ "' || name || '", "' || sql || '" },' from sqlite_master where type = 'table'
            var schema = new Dictionary<string, string>()
            {
                { "version", "CREATE TABLE version (a INTEGER PRIMARY KEY)" },
                { "scans", "CREATE TABLE scans (timestamp INTEGER PRIMARY KEY, options TEXT NOT NULL, end INTEGER DEFAULT NULL, suspect INTEGER DEFAULT 0)" },
                { "directories", "CREATE TABLE directories (name TEXT PRIMARY KEY, timestamp INTEGER NOT NULL)" },
                { "filenames", "CREATE VIRTUAL TABLE filenames USING fts5(maskedFilename)" },
                { "filenames_data", "CREATE TABLE 'filenames_data'(id INTEGER PRIMARY KEY, block BLOB)" },
                { "filenames_idx", "CREATE TABLE 'filenames_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID" },
                { "filenames_content", "CREATE TABLE 'filenames_content'(id INTEGER PRIMARY KEY, c0)" },
                { "filenames_docsize", "CREATE TABLE 'filenames_docsize'(id INTEGER PRIMARY KEY, sz BLOB)" },
                { "filenames_config", "CREATE TABLE 'filenames_config'(k PRIMARY KEY, v) WITHOUT ROWID" },
                { "files", "CREATE TABLE files (maskedFilename TEXT PRIMARY KEY, originalFilename TEXT NOT NULL, size BIGINT NOT NULL, touchedAt TEXT NOT NULL, code INTEGER DEFAULT 1 NOT NULL, extension TEXT, attributeJson TEXT NOT NULL, timestamp INTEGER NOT NULL, isBlocked INTEGER DEFAULT 0 NOT NULL, isQuarantined INTEGER DEFAULT 0 NOT NULL, moderationReason TEXT)" },
                { "content_items", "CREATE TABLE content_items (contentId TEXT PRIMARY KEY, domain TEXT NOT NULL, workId TEXT, maskedFilename TEXT NOT NULL, isAdvertisable INTEGER DEFAULT 0 NOT NULL, moderationReason TEXT, checkedAt INTEGER NOT NULL, FOREIGN KEY(maskedFilename) REFERENCES files(maskedFilename) ON DELETE CASCADE)" },
            };

            try
            {
                Log.Debug("Validating shares database with connection string {String}", ConnectionString);

                // Check if isBlocked and isQuarantined columns exist, add them if missing (migration)
                using var migrationConn = GetConnection();
                try
                {
                    migrationConn.ExecuteNonQuery("SELECT isBlocked FROM files LIMIT 1");
                }
                catch
                {
                    Log.Information("Adding isBlocked, isQuarantined, and moderationReason columns to files table (migration)");
                    migrationConn.ExecuteNonQuery("ALTER TABLE files ADD COLUMN isBlocked INTEGER DEFAULT 0 NOT NULL");
                    migrationConn.ExecuteNonQuery("ALTER TABLE files ADD COLUMN isQuarantined INTEGER DEFAULT 0 NOT NULL");
                    migrationConn.ExecuteNonQuery("ALTER TABLE files ADD COLUMN moderationReason TEXT");
                }

                try
                {
                    migrationConn.ExecuteNonQuery("SELECT 1 FROM content_items LIMIT 1");
                }
                catch
                {
                    Log.Information("Adding content_items table and indexes to shares database (migration)");
                    migrationConn.ExecuteNonQuery("CREATE TABLE IF NOT EXISTS content_items " +
                        "(contentId TEXT PRIMARY KEY, " +
                        "domain TEXT NOT NULL, " +
                        "workId TEXT, " +
                        "maskedFilename TEXT NOT NULL, " +
                        "isAdvertisable INTEGER DEFAULT 0 NOT NULL, " +
                        "moderationReason TEXT, " +
                        "checkedAt INTEGER NOT NULL, " +
                        "FOREIGN KEY(maskedFilename) REFERENCES files(maskedFilename) ON DELETE CASCADE);");
                    migrationConn.ExecuteNonQuery("CREATE INDEX IF NOT EXISTS idx_content_items_filename ON content_items(maskedFilename);");
                    migrationConn.ExecuteNonQuery("CREATE INDEX IF NOT EXISTS idx_content_items_advertisable ON content_items(isAdvertisable);");
                }

                using var conn = GetConnection();

                using var cmd = new SqliteCommand("SELECT name, sql from sqlite_master WHERE type = 'table';", conn);

                using var reader = cmd.ExecuteReader();
                var validatedTables = 0;

                while (reader.Read())
                {
                    var table = reader.GetString(0);
                    var expectedSql = reader.GetString(1);

                    if (!schema.TryGetValue(table, out var actualSql))
                    {
                        continue;
                    }

                    validatedTables++;

                    if (actualSql != expectedSql)
                    {
                        list.Add($"Expected {table} schema to be {expectedSql}, found {actualSql}");
                    }
                    else
                    {
                        Log.Debug("Shares database table {Table} is valid: {Actual}", table, actualSql);
                    }
                }

                if (validatedTables != schema.Count)
                {
                    list.Add($"Expected {schema.Count} tables, found {validatedTables}");
                }

                return !problems.Any();
            }
            catch (Exception ex)
            {
                Log.Debug(ex, $"Failed to validate database: {ex.Message}");
                list.Add("Failed to validate database");
                return false;
            }
        }

        /// <summary>
        ///     Updates the scan started at the specified <paramref name="timestamp"/> to set the <paramref name="end"/>.
        /// </summary>
        /// <param name="timestamp">The timestamp associated with the scan.</param>
        /// <param name="end">The timestamp at the conclusion of the scan.</param>
        public void UpdateScan(long timestamp, long end)
        {
            using var conn = GetConnection();

            conn.ExecuteNonQuery("UPDATE scans SET end = @end WHERE timestamp = @timestamp;", cmd =>
            {
                cmd.Parameters.AddWithValue("end", end);
                cmd.Parameters.AddWithValue("timestamp", timestamp);
            });
        }

        /// <summary>
        ///     Reclaims unused space.
        /// </summary>
        public void Vacuum()
        {
            using var conn = GetConnection();
            conn.ExecuteNonQuery("VACUUM;");
        }

        /// <summary>
        ///     Checkpoints the write-ahead log to the database file.
        /// </summary>
        /// <returns>A value indicating whether the complete checkpoint succeeded.</returns>
        public bool Checkpoint()
        {
            using var conn = GetConnection();
            return Checkpoint(conn);
        }

        private static bool Checkpoint(SqliteConnection connection)
        {
            using var cmd = new SqliteCommand("PRAGMA wal_checkpoint(TRUNCATE);", connection);
            using var reader = cmd.ExecuteReader();
            return reader.Read() && reader.GetInt32(0) == 0;
        }

        // T-MCP03: Content item management for VirtualSoulfind advertisable gating

        /// <summary>
        ///     Inserts or updates a content item mapping.
        /// </summary>
        public void UpsertContentItem(
            string contentId,
            string domain,
            string workId,
            string maskedFilename,
            bool isAdvertisable,
            string? moderationReason,
            long checkedAt)
        {
            using var conn = GetConnection();

            conn.ExecuteNonQuery(
                "INSERT OR REPLACE INTO content_items " +
                "(contentId, domain, workId, maskedFilename, isAdvertisable, moderationReason, checkedAt) " +
                "VALUES (@contentId, @domain, @workId, @maskedFilename, @isAdvertisable, @moderationReason, @checkedAt);",
                cmd =>
                {
                    cmd.Parameters.AddWithValue("contentId", contentId);
                    cmd.Parameters.AddWithValue("domain", domain);
                    cmd.Parameters.AddWithValue("workId", workId ?? (object)DBNull.Value);
                    cmd.Parameters.AddWithValue("maskedFilename", maskedFilename);
                    cmd.Parameters.AddWithValue("isAdvertisable", isAdvertisable ? 1 : 0);
                    cmd.Parameters.AddWithValue("moderationReason", moderationReason ?? (object)DBNull.Value);
                    cmd.Parameters.AddWithValue("checkedAt", checkedAt);
                });
        }

        /// <summary>
        ///     Finds a content item by content ID.
        /// </summary>
        public (string Domain, string WorkId, string MaskedFilename, bool IsAdvertisable, string ModerationReason, long CheckedAt)? FindContentItem(string contentId)
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand(
                "SELECT domain, workId, maskedFilename, isAdvertisable, moderationReason, checkedAt " +
                "FROM content_items WHERE contentId = @contentId;",
                conn);

            cmd.Parameters.AddWithValue("contentId", contentId);

            using var reader = cmd.ExecuteReader();

            if (reader.Read())
            {
                return (
                    Domain: reader.GetString(0),
                    WorkId: reader.IsDBNull(1) ? string.Empty : reader.GetString(1),
                    MaskedFilename: reader.GetString(2),
                    IsAdvertisable: reader.GetInt32(3) != 0,
                    ModerationReason: reader.IsDBNull(4) ? string.Empty : reader.GetString(4),
                    CheckedAt: reader.GetInt64(5)
                );
            }

            return null;
        }

        /// <summary>
        ///     Lists all content items associated with a file.
        /// </summary>
        public IEnumerable<(string ContentId, string Domain, string WorkId, bool IsAdvertisable, string ModerationReason)> ListContentItemsForFile(string maskedFilename)
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand(
                "SELECT contentId, domain, workId, isAdvertisable, moderationReason " +
                "FROM content_items WHERE maskedFilename = @maskedFilename;",
                conn);

            cmd.Parameters.AddWithValue("maskedFilename", maskedFilename);

            using var reader = cmd.ExecuteReader();

            while (reader.Read())
            {
                yield return (
                    ContentId: reader.GetString(0),
                    Domain: reader.GetString(1),
                    WorkId: reader.IsDBNull(2) ? string.Empty : reader.GetString(2),
                    IsAdvertisable: reader.GetInt32(3) != 0,
                    ModerationReason: reader.IsDBNull(4) ? string.Empty : reader.GetString(4)
                );
            }
        }

        /// <summary>
        ///     Lists advertisable content IDs for files eligible to appear in shares.
        /// </summary>
        public IEnumerable<string> ListAdvertisableContentIds()
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand(
                "SELECT c.contentId " +
                "FROM content_items c " +
                "JOIN files f ON f.maskedFilename = c.maskedFilename " +
                "WHERE c.isAdvertisable = 1 AND f.isBlocked = 0 AND f.isQuarantined = 0 " +
                "ORDER BY c.contentId ASC;",
                conn);
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
            {
                yield return reader.GetString(0);
            }
        }

        /// <summary>
        ///     Counts advertisable content items.
        /// </summary>
        public int CountAdvertisableItems()
        {
            using var conn = GetConnection();
            using var cmd = new SqliteCommand(
                "SELECT COUNT(*) FROM content_items WHERE isAdvertisable = 1;",
                conn);

            return Convert.ToInt32(cmd.ExecuteScalar());
        }

        /// <summary>
        ///     Disposes this object.
        /// </summary>
        /// <param name="disposing"></param>
        protected virtual void Dispose(bool disposing)
        {
            if (!Disposed)
            {
                if (disposing)
                {
                    Common.TimerDisposer.DisposeWithWait(KeepaliveTimer);
                    KeepaliveConnection.Dispose();
                }

                Disposed = true;
            }
        }

        private SqliteConnection GetConnection(string? connectionString = null)
        {
            connectionString = NormalizeConnectionString(connectionString ?? ConnectionString);

            var conn = new SqliteConnection(connectionString);
            conn.Open();
            return conn;
        }

        private static string NormalizeConnectionString(string connectionString)
        {
            if (string.IsNullOrWhiteSpace(connectionString))
            {
                throw new ArgumentException("Connection string cannot be null or empty", nameof(connectionString));
            }

            var parsed = new SqliteConnectionStringBuilder(connectionString);
            var dataSource = parsed.DataSource?.Trim();

            if (string.IsNullOrWhiteSpace(dataSource))
            {
                throw new ArgumentException("Connection string must include a data source", nameof(connectionString));
            }

            if (dataSource.StartsWith("file:", PathComparison))
            {
                if (!dataSource.Contains("?mode=memory", PathComparison))
                {
                    throw new ArgumentException("Only in-memory SQLite file URIs are supported", nameof(connectionString));
                }
            }
            else if (!Path.IsPathRooted(dataSource))
            {
                throw new ArgumentException("SQLite data source must be an absolute path", nameof(connectionString));
            }

            var normalized = new SqliteConnectionStringBuilder
            {
                DataSource = dataSource,
                Cache = parsed.Cache,
                Mode = parsed.Mode,
                Pooling = parsed.Pooling,
            };

            return normalized.ToString();
        }

        private void Keepalive()
        {
            try
            {
                // Check if the filenames table exists and is accessible
                // filenames is an FTS5 virtual table, so we check it differently than regular tables
                using var cmd = new SqliteCommand(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='filenames';",
                    KeepaliveConnection);

                var schemaPresent = Convert.ToInt32(cmd.ExecuteScalar()) == 1;

                if (!schemaPresent)
                {
                    var msg = "The internal share database has been corrupted or lost, and the application cannot continue to run. Please report this in a GitHub issue here: https://github.com/snapetech/slskdn/issues";
                    Log.Fatal(msg);
                    Environment.Exit(1);
                    throw new DataMisalignedException(msg);
                }

                // Additional check: verify we can query the filenames table.
                // FTS5 virtual tables require special handling, so presence alone is insufficient.
                using var verifyCmd = new SqliteCommand("SELECT COUNT(*) FROM filenames LIMIT 1;", KeepaliveConnection);

                verifyCmd.ExecuteScalar(); // If this throws, the table is corrupted
            }

            // SQLITE_ERROR means the table is missing or corrupted.
            catch (SqliteException ex) when (ex.SqliteErrorCode == 1)
            {
                // Table doesn't exist or is corrupted
                var msg = "The internal share database has been corrupted or lost, and the application cannot continue to run. Please report this in a GitHub issue here: https://github.com/snapetech/slskdn/issues";
                Log.Fatal(ex, msg);
                Environment.Exit(1);
                throw new DataMisalignedException(msg, ex);
            }
            catch (Exception ex)
            {
                // Log but don't exit on transient errors (e.g., database locked during backup)
                // Only exit on persistent corruption
                Log.Warning(ex, "Keepalive check encountered an error (may be transient): {Message}", ex.Message);
            }
        }
    }
}
