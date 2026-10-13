# Transfer Operations

This guide covers completed-download destinations, collision behavior, path
tokens, request retention, UTC timestamps, and paging through search and
transfer history.

## Completed download destinations

Completed files are saved beneath the selected downloads root. Destination
selection follows this order:

1. A destination explicitly selected for the request.
2. `transfers.download.destination.subdirectory`, when configured.
3. The legacy `completed_path_template` or `completed_layout` setting, when
   configured and no canonical subdirectory is set.
4. The source directory name, by default.

An empty `subdirectory` saves directly in the selected root. The global
subdirectory is relative; absolute paths and `..` components are rejected.
After token expansion, the application resolves the final path under the
configured download roots. A path that escapes those roots, including through
an existing symlink, is rejected before the file is moved.

```yaml
transfers:
  download:
    destination:
      subdirectory: '${SOURCE_USERNAME}/${SOURCE_PATH}'
      exists: rename
      permissions:
        mode: '0644'
```

`destination.subdirectory` accepts the following tokens:

| Token | Value |
| --- | --- |
| `${SOURCE_USERNAME}` | Peer that supplied the file |
| `${SOURCE_PATH}` | Sanitized remote parent path, preserving its folder hierarchy |
| `${SOURCE_DIRECTORY}` | Final folder in the remote parent path; `_singles` for a file with no parent folder |
| `${BATCH_ID}` | Batch UUID, or `unknown_batch_id` if the request has no batch |
| `${BATCH_EXTERNAL_ID}` | Caller-provided batch label, or `unknown_batch_external_id` |
| `${SEARCH_ID}` | Originating search UUID, or `unknown_search_id` |
| `${SEARCH_TEXT}` | Originating query, or `unknown_search_text` |

Peer names, query text, and caller-provided batch labels are reduced to safe
single path components. Separators in those values become underscores; only
`${SOURCE_PATH}` intentionally expands to multiple components. Long components
are shortened with a stable hash suffix so distinct long values remain
distinct.

When a search result is queued from the Web UI, its search ID and query are
captured with the request. API clients can pass the same metadata per file:

```json
[
  {
    "filename": "Music/Album/Track.flac",
    "size": 24823104,
    "batchId": "c681ca67-a187-4d7f-8e6d-13699f468ad7",
    "batchExternalId": "lidarr-album-481",
    "searchId": "7b82c49b-39d7-4ac4-a61d-97144f7336bc",
    "searchText": "Artist Album"
  }
]
```

These fields are optional and existing clients may omit them. The request
metadata is persisted, so retries and restarts retain the original values.

## Existing filenames

`transfers.download.destination.exists` controls a completed file whose name
already exists at the destination:

- `rename` keeps the existing file and writes the new download under a unique
  suffixed name. This is the default.
- `overwrite` replaces the existing file.

The setting applies to global layouts and explicit request destinations.

## File and directory permissions

`transfers.download.destination.permissions.mode` accepts a three- or
four-digit chmod-style octal mode and applies on non-Windows systems. When set,
it takes precedence over `permissions.file.mode` for completed files. If it is
omitted, completed files keep using the global file mode.

New directories receive the configured read and write bits plus execute bits
corresponding to each read bit, so the application can enter directories it
creates. The requested mode is applied after creation to avoid losing bits to
the process umask. Existing directories are left unchanged. Windows ignores
Unix mode settings.

## Download request history

The `retention.transfers.removed` setting controls permanent removal of
soft-removed completed download attempts. After those rows are removed, a
terminal download request is also removed once its completion time is older
than the configured age. If it has no completion time, its creation time is
used. Active requests and terminal requests with any remaining download
attempt stay available. If removed-transfer retention is unset, request history
is retained.

An API client that looks up a request should treat a `404` as the record no
longer being available; retention can remove it after its attempt history has
expired.

## API timestamp format

Transfer timestamps persisted in the database are returned as UTC ISO 8601
values with a `Z` suffix. Clients can compare them as UTC instants and convert
them for display in the user's local time zone.

## Browsing long lists

The Web UI starts search history from the live hub's capped snapshot of up to
500 rows. It then fetches API pages of 250. The search-list API keeps its array
response and accepts `limit`, `offset`, and an optional source filter. The Web
UI continues with the last row's `startedAt` and `id`, so new live searches do
not shift older page boundaries. Selecting **Load more searches** appends
another page; existing loaded rows, selected searches, and live updates remain
in the list.

The transfer view initially fetches up to 100 active or unsuccessful records
per direction. **Load more transfers** requests the next server page without
loading the entire active list. Each page keeps its original snapshot and uses
request time plus transfer ID as its continuation position. Updates that
arrive after that snapshot continue through the live feed and incremental API
changes. Successful history uses its own stable page of 250 rows.

Filters, retries, cancels, and per-row removals apply to loaded rows. The UI
shows how many rows are loaded and explains this scope. Clearing completed
rows uses the server-side bulk action and covers the matching completed rows
even when older history pages are not loaded.

## CLI and environment variables

The download destination settings have matching YAML, CLI, and environment
bindings:

| YAML | CLI | Environment |
| --- | --- | --- |
| `transfers.download.destination.subdirectory` | `--download-destination-subdirectory` | `SLSKD_DOWNLOAD_DESTINATION_SUBDIRECTORY` |
| `transfers.download.destination.exists` | `--download-destination-exists` | `SLSKD_DOWNLOAD_DESTINATION_EXISTS` |
| `transfers.download.destination.permissions.mode` | `--download-destination-permissions-mode` | `SLSKD_DOWNLOAD_DESTINATION_PERMISSIONS_MODE` |

Legacy `completed_layout` and `completed_path_template` remain accepted when
`destination.subdirectory` is omitted. New configuration should use the
`destination` object. See the [configuration reference](config.md) and
[API reference](api-documentation.md) for the full option and request shape.
