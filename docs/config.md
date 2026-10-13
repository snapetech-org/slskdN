# Configuration 

The application is highly configurable while coming out of the box with sensible defaults.

The defaults that have been chosen should cover the vast majority of users. Still, deployments on low spec hardware (such as a single-board computer or a shared system) should monitor resource usage and adjust as necessary.

Credentials (username and password) for the Soulseek network are the only required configuration, but it is advised to also change the credentials for the Web UI.

# Sources

The application supports several different configuration sources to make it easy for users to deploy the application in various situations.

The configuration options used by the application derive from the values specified by each of the sources, with sources higher in the hierarchy overwriting or expanding the configuration set earlier. The hierarchy is:

```
Default Values < Environment Variables < YAML Configuration File < Command Line Arguments
```

Some options can be specified as lists. In these cases, when combining configurations from multiple sources, care should be taken. .NET framework not only appends but also overwrites values. If a list of `one;two;three` is defined in an environment variable for an option, and the YAML configuration specifies a list of `foo` and `bar`, the resulting configuration will be a list containing `foo, bar, three`.

## Default Values

Default values for each option (unless the default is `null`) are specified in `Options.cs`.  Upon startup, these values are copied into the configuration first.

## Environment Variables

Environment variables are loaded after defaults. Each environment variable name is prefixed with `SLSKD_`.

Environment variables are ideal for use cases involving Docker where configuration is expected to be changed neither often nor remotely.

An environment variable that is present with an empty value, such as
`SLSKD_HEADLESS=`, is treated as unset. This is intentional for container
templates that expose optional settings as blank fields: the YAML value or
built-in default remains in effect. Set a non-empty value such as `true` or
`false` when you want an environment variable to override a Boolean option.

The same rule applies to empty numeric, path, array, and secret overrides.
Required host bind mounts are different: Docker/Unraid templates must provide
a valid host path before the container can start. In the Unraid template,
`/downloads` is deliberately a required user-selected path rather than a
guessed host share.

Some options are backed by arrays or lists and allow multiple options to be set via a single environment variable. To achieve this, separate each list item by a semicolon `;` in the value:

```
SLSKD_SOME_OPTION=1;2;3
```

## YAML Configuration File

Configuration is loaded from the YAML file located at `<application directory>/slskd.yml` after environment variables. The location can be changed by specifying the path in the `SLSKD_CONFIG` environment variable or `--config` command-line argument.

The application watches for changes in the YAML file and will reload the configuration when they are detected. Options will be updated in real-time and transmitted to the web UI. If a server reconnect or application restart is required for changes to take effect fully, a flag will be set indicating so.

The YAML file can be read and written at run time via API calls or edited on disk.

If no such configuration file exists at startup, the example file `/config/slskd.example.yml` is copied to this location for convenience.

YAML configuration should be used in most cases.

## Command Line Arguments

Command-line arguments are loaded last, override all other configuration options, and are immutable at run time.

Command-line arguments are helpful for security options, such as remote configuration, HTTPS JWT secret, and certificate. Choosing this source for sensitive options can prevent a remote attacker from gaining full control over the application.

Some options are backed by arrays or lists and allow multiple options to be set via the command line. To achieve this, repeat the command line argument:

```
--some-option 1 --some-option 2 --some-option 3
```

# Remote Configuration

The application contains APIs for retrieving and updating the YAML configuration file. By default, this option is disabled. Applications run within untrusted networks, especially those where the application is internet-facing, should consider the risks of enabling this option.

If an attacker were to gain access to the application and retrieve the YAML file, any secrets contained within it will be exposed.

| Command-Line             | Environment Variable         | Description                                                   |
| ------------------------ | -----------------------------| ------------------------------------------------------------- |
| `--remote-configuration` | `SLSKD_REMOTE_CONFIGURATION` | Determines whether the remote configuration of options is allowed |

#### **YAML**
```yaml
remote_configuration: false
```

# Headless Mode

Users that want extra security and don't intend to use the application's web UI can disable it.  This setting is ideal in
situations where slskd will be controlled by another application via the API (like when run as a Relay agent).

| Command-Line             | Environment Variable         | Description                                                                |
| ------------------------ | -----------------------------| -------------------------------------------------------------------------- |
| `--headless`             | `SLSKD_HEADLESS`             | Determines whether the application should run in headless (no web UI) mode |

#### **YAML**
```yaml
headless: false
```

# Permissions

On [Unix-like](https://en.wikipedia.org/wiki/Unix-like) operating systems, slskd creates downloaded files with permissions dictated by the [umask](https://en.wikipedia.org/wiki/Umask) of the process, usually 022, which translates to a file mode of 644; read/write for the owner and read for the group and all others.

Users wishing to create files with different permissions can change the umask value before launching the application (e.g. `umask 000 & ./slskd`), and the file mode will be changed accordingly.

When running within a docker container the environment variable `SLSKD_UMASK` can be used to change the umask for the process within the container, and this will in turn change the resulting file mode on a mounted volume.

Users can optionally configure alternative permissions for files by setting the file permission mode option.  It's not possible to supersede the configured umask value; setting a mode of 777, for example, will have no effect with a umask of 022.

These options have no effect on Windows.

| Command-Line             | Environment Variable         | Description                                                                      |
| ------------------------ | -----------------------------| -------------------------------------------------------------------------------- |
| n/a                      | `SLSKD_UMASK`                | When running within the slskd Docker container, the umask for the process        |
| `--file-permission-mode` | `SLSKD_FILE_PERMISSION_MODE` | The permissions to apply to newly created files (chmod syntax, non-Windows only) |

#### **YAML**
```yaml
permissions:
  file:
    mode: 644 # not for Windows, chmod syntax, e.g. 644, 777. can't escalate beyond umask
```

# Application Directory Configuration

The application directory configuration option determines the location of the YAML file, the default locations of the download and incomplete directories, and the location of application working data, such as logs and SQLite databases.

Because the location of the YAML file derived from this value, it can't be specified within the YAML file and must instead be set with the `APP_DIR` environment variable or `--app-dir` command-line argument.

If no value is specified, the location defaults to either `~/.local/share/slskd` (on Linux and macOS) or `%localappdata%/slskd` (on Windows).

This value is set to `/app` within the official Docker image.

# Other Directory Configuration

## Incomplete and Downloads

By default, incomplete and downloaded files are saved in `APP_DIR/incomplete` and `APP_DIR/downloads` directories, respectively. The application will create these directories on startup if they don't exist.

Alternative locations can be specified for each directory. Directories must exist and be writable by the application; the application will not attempt to create them.

When Docker bind-mounts these paths, the host directory must also be writable
by the container's runtime UID/GID. See [Docker Download Permissions](docker-download-permissions.md)
for multiple destinations, Compose `PUID`/`PGID` setup, and NAS/ACL
troubleshooting.

| Command-Line      | Environment Variable       | Description                                   |
| ----------------- | ---------------------------| --------------------------------------------- |
| `-o\|--downloads` | `SLSKD_DOWNLOADS_DIR`      | The path where downloaded files are saved     |
| `--incomplete`    | `SLSKD_INCOMPLETE_DIR`     | The path where incomplete downloads are saved |

#### **YAML**
```yaml
directories:
  incomplete: ~
  downloads: ~
```

## Remote File Management

The application offers APIs for listing and deleting files within the 'Incomplete' and 'Downloads' directories.  Listing is always allowed, while the ability
to delete is disabled by default.  Deletions can be enabled by enabling the remote file management option.

| Command-Line               | Environment Variable           | Description                                                                               |
| -------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------- |
| `--remote-file-management` | `SLSKD_REMOTE_FILE_MANAGEMENT` | Determines whether the remote management of 'Incomplete' and 'Downloads' files is allowed |

#### **YAML**
```yaml
remote_file_management: false
```

# Shares

## Directories

Any number of shared directories can be configured.

Paths must be absolute, meaning they must begin with `/`, `X:\`, or `\\`, depending on the system. Relative paths, such as `~/directory` or `../directory`, are not supported. Sharing a root mount on a unix-like OS (`/`) is also not supported.

Shares can be excluded by prefixing them with `-` or `!`. This is useful in situations where sharing a subdirectory of a share isn't desired, for example, if a user wants to share their entire music library but not their personal recordings:

```yaml
shares:
  directories:
    - 'D:\Music'
    - '!D:\Music\Personal Recordings'
```

Shares can be aliased to improve privacy (for example, if a username is present in the path). A share alias can be specified by prefixing the share with the alias in square brackets, for example:

```yaml
shares:
  directories:
    - '[Music]\users\John Doe\Music'
```

If no alias is specified, the name of the shared folder is used (e.g. `D:\Music` is aliased to `Music`). To a remote user, any files within the aliased path will appear as though they are shared from a directory named as the alias.

Aliases:
* Must be unique
* Must be at least one character in length
* Must not contain path separators (`\` or `/`)

| Command-Line   | Environment Variable       | Description                       |
| -------------- | -------------------------- | --------------------------------- |
| `-s\|--shared` | `SLSKD_SHARED_DIR`         | The list of paths to shared files |

## Collection share endpoints

Cross-node collection shares include an owner URL so recipients can stream
items or use **Backfill All**. Set `sharing.externalEndpoint` to the base URL
other peers can reach, including a reverse-proxy path when used. The default is
empty; without it, newly announced shares do not advertise an HTTP endpoint.
Use a public HTTPS URL where available.

Public owner URLs continue to use the outbound public-address guard. For an
owner reachable only on a private LAN or loopback network, a recipient operator
can allow one exact IP origin with `sharing.trustedPrivateOwnerOrigins`. This
setting accepts only private, unique-local, or loopback IP literals with an
optional port; it does not accept hostnames, link-local or reserved addresses.
Redirects remain disabled. Add the origin only when you trust that service.

```yaml
sharing:
  externalEndpoint: "https://shares.example.net/slskd"
  trustedPrivateOwnerOrigins:
    - "http://192.168.1.40:5030"
```

Each recipient configures its own trusted private origins. Public Internet
endpoints need no allowlist entry.

## Filters

Share filters can be used to prevent certain types of files from being shared.  This option is an array that can take any number of filters.  Filters must be a valid regular expression; a few examples are included below and in the example configuration included with the application, but the list is empty by default.

Filter expressions are case insensitive by default.

| Command Line              | Environment Variable          | Description                                                           |
| ------------------------- | ----------------------------- | --------------------------------------------------------------------- |
| `--share-filter`          | `SLSKD_SHARE_FILTER`          | A list of regular expressions used to filter files from shares        |

#### **YAML**
```yaml
shares:
  filters:
    - \.ini$
    - Thumbs.db$
    - \.DS_Store$
```

## Cache

The contents of shares are cached following a share scan, and users can choose how the cache is stored; in memory, or on disk.

Storing the cache in memory results in faster lookups and lower CPU and disk activity while the application is running, but increases the amount of memory used.  Systems that don't have a lot of memory might have an issue with large shares.

Storing the cache on disk uses quite a bit less memory and allows the application to run without issue for large shares, but lookups are slower, use more CPU, and cause more disk activity.

The cache is stored in memory by default.  If you find that the application uses too much memory or crashes with an `Out of Memory` exception, change this option to store the cache on disk.

Scanning shares is an I/O intensive operation; all of the files and directories in each share have to be listed, and by default audio files are probed for metadata like length, bitrate, and sample rate. To speed things up, multiple 'workers'
are used to allow metadata to be read from several files concurrently. The scan generally gets faster as additional workers are added, but each worker also adds additional I/O pressure and increases CPU and memory usage. At some number of workers
performance will start to get worse as more are added.  The optimal number of workers will vary from system to system, so if scan performance is important to you it will be a good idea to experiment to see what the optimal number is for your system.

The default number of workers is intentionally conservative: `1` worker on 1-2 core hosts, otherwise half of the detected cores capped at `4`. If your machine can comfortably handle more scan pressure, increase the value explicitly. If initial scans cause high load, reduce it to `1`, `2`, or `4`.

If shares live on slow or remote storage, set `shares.probe_media_attributes` to `false` to skip TagLib audio probing during the share scan. Files remain shared, but Soulseek browse metadata may omit bitrate, length, sample rate, and bit depth until probing is enabled again.

Shares can be configured to be automatically re-scanned at a regular interval by setting the retention limit for the cache.  This value is empty by default, and shares will not be re-scanned automatically.  The interval is set in minutes.

| Command Line                 | Environment Variable             | Description                                               |
| ---------------------------- | -------------------------------- | --------------------------------------------------------- |
| `--share-cache-storage-mode` | `SLSKD_SHARE_CACHE_STORAGE_MODE` | The type of storage to use for the cache (Memory, Disk)   |
| `--share-cache-workers`      | `SLSKD_SHARE_CACHE_WORKERS`      | The number of workers to use while scanning shares        |
| `--share-cache-retention`    | `SLSKD_SHARE_CACHE_RETENTION`    | The interval on which the cache is re-scanned, in minutes |
| `--shares-probe-media-attributes` | `SLSKD_SHARES_PROBE_MEDIA_ATTRIBUTES` | Whether to probe shared audio files for bitrate/length/sample metadata |

#### **YAML**
```yaml
shares:
  probe_media_attributes: true # set false on slow/remote storage to skip TagLib audio probing
  cache:
    storage_mode: memory
    workers: 4 # default is conservative; lower this on weaker hosts, raise it carefully if scans are too slow
    retention: 10080 # 1 week
```

# Relay

Two (or more) instances of the application can be connected, allowing files shared by one instance to be "relayed" to another while only one of the instances is connected to the Soulseek network.  This allows users to share files from several different systems as the same Soulseek user, or to run an instance in the cloud and avoid needing to expose their home network to internet traffic.

The Relay consists of two operation modes: 'Controller', which is the copy that connects to the Soulseek network, and 'Agent', which relays files to the controller.  Only one controller can be configured, while any number of agents can be connected.

## Controller

Controllers must have at least one API key configured.  For increased security it is a good idea to use a different API key for each agent, and to specify a CIDR for each key that limits access to the known IP address range the agent will be connecting from.

The relay mode for the controller must be set to `controller`, and the relay must be enabled.

For each agent, the agent must be specified in the `agents` map, including an `instance_name` that corresponds to the top-level `instance_name` configured for the agent, and a different secret value between 16-255 characters should be specified for each agent.

It is strongly suggested that controllers be configured to force HTTPS.  This makes the traffic between the controller and agents completely private, and prevents API keys and agent secrets from being exposed.

```yaml
relay:
  enabled: true
  mode: controller
  agents:
    some_instance:
      instance_name: some_instance
      secret: <a secret value between 16 and 255 characters>
    a_different_instance:
      instance_name: different_instance
      secret: <a different secret value between 16 and 255 characters>
```

| Command-Line       | Environment Variable | Description                               |
| ------------------ | ---------------------| ------------------------------------------|
| `-r\|--relay`      | `SLSKD_RELAY`        | Enable the Relay feature                  |
| `-m\|--relay-mode` | `SLSKD_RELAY_MODE`   | The Relay mode (Controller, Agent, Debug) |

## Agents

The relay mode for agents must be set to `agent`, the relay must be enabled, and each agent must have a unique instance name that corresponds to the `instance_name` of an agent configured in the controller.

Agents need to specify the HTTP or HTTPS address of their controller, the API key for the controller, and the secret that corresponds to the value configured in the controller for the agent.

If using HTTPS; most users won't have a valid certificate (the self-signed certificates that slskd generates at startup are not 'valid' because they are self-signed), and in those cases the `ignore_certificate_errors` option should be set to `true`.

Agents can optionally receive completed downloads from the controller by enabling the `downloads` option.  With this option enabled, agents will automatically download new files from the controller and save them to the configured local downloads directory.

| Command-Line                             | Environment Variable                         | Description                                     |
| ---------------------------------------- | -------------------------------------------- | ------------------------------------------------|
| `-r\|--relay`                            | `SLSKD_RELAY`                                | Enable the Relay feature                        |
| `-m\|--relay-mode`                       | `SLSKD_RELAY_MODE`                           | The Relay mode (Controller, Agent, Debug)       |
| `--controller-address`                   | `SLSKD_CONTROLLER_ADDRESS`                   | The address of the controller                   |
| `--controller-ignore-certificate-errors` | `SLSKD_CONTROLLER_IGNORE_CERTIFICATE_ERRORS` | Ignore certificate errors                       |
| `--controller-api-key`                   | `SLSKD_CONTROLLER_API_KEY`                   | An API key for the controller                   |
| `--controller-secret`                    | `SLSKD_CONTROLLER_SECRET`                    | The shared secret for this agent                |
| `--controller-downloads`                 | `SLSKD_CONTROLLER_DOWNLOADS`                 | Receive completed downloads from the controller |

```yaml
instance_name: some_instance
relay:
  enabled: true
  mode: agent
  controller:
    address: https://my_cloud_server.example.com:5031
    ignore_certificate_errors: true
    api_key: <a valid API key for the controller instance>
    secret: <a secret value that matches the controller for this instance>
    downloads: false
```

# Limits and User Groups

## Global Slot and Speed Limits

Global slot and speed behave as a hard limit, additive across all groups. These values should be set as high as practical for the application's environment; more granular controls should be defined at the group level.

A change to slot limits requires an application restart to take effect, while speed limits can be adjusted at runtime.

| Command-Line             | Environment Variable         | Description                                      |
| ------------------------ | ---------------------------- | ------------------------------------------------ |
| `--upload-slots`         | `SLSKD_UPLOAD_SLOTS`         | The limit for the total number of upload slots   |
| `--upload-speed-limit`   | `SLSKD_UPLOAD_SPEED_LIMIT`   | The total upload speed limit, in kibibytes       |
| `--download-slots`       | `SLSKD_DOWNLOAD_SLOTS`       | The limit for the total number of download slots |
| `--download-speed-limit` | `SLSKD_DOWNLOAD_SPEED_LIMIT` | The total download speed limit, in kibibytes     |
| `--download-completed-layout` | `SLSKD_DOWNLOAD_COMPLETED_LAYOUT` | Completed download folder layout. Default: `remote_folder` to preserve source folder/file names. Other values: `uploader_folder`, `batch_id`, or `flat` |
| `--download-completed-path-template` | `SLSKD_DOWNLOAD_COMPLETED_PATH_TEMPLATE` | Optional path template that overrides `--download-completed-layout`. Tokens: `{uploader}`, `{remote_folder}`, `{remote_parent}`, `{remote_filename}`, `{batch_id}`, `{request_name}`, `{date}` / `{date:yyyy-MM}`. Example: `{uploader}/{remote_folder}` |
| `--download-retry-incomplete` | `SLSKD_DOWNLOAD_RETRY_INCOMPLETE` | How to handle partial files between direct download attempts: `resume` or `overwrite` |
| `--download-retry-attempts` | `SLSKD_DOWNLOAD_RETRY_ATTEMPTS` | Maximum direct download attempts (1–20) |
| `--download-retry-delay` | `SLSKD_DOWNLOAD_RETRY_DELAY` | Initial delay between direct download attempts, in milliseconds |
| `--download-retry-max-delay` | `SLSKD_DOWNLOAD_RETRY_MAX_DELAY` | Maximum delay between direct download attempts, in milliseconds |

#### **YAML**
```yaml
transfers:
  upload:
    slots: 20
    speed_limit: 1000 # kibibytes
  download:
    slots: 500
    speed_limit: 1000
    completed_layout: remote_folder
    # When set, completed_path_template overrides completed_layout.
    # completed_path_template: '{uploader}/{remote_folder}'
    retry:
      incomplete: resume # resume or overwrite
      attempts: 1
      delay: 5000 # milliseconds
      max_delay: 60000 # milliseconds
    auto_retry:
      enabled: true
      retry_delay_seconds: 1800
      check_interval_seconds: 300
      max_attempts: 5
      max_files_per_cycle: 10
      max_files_per_peer_per_cycle: 1
      peer_cooldown_seconds: 900
      alternate_sources_enabled: true
      max_alternate_source_searches_per_cycle: 1
      alternate_source_size_tolerance_percent: 5
```

The older `global` key is still accepted so existing deployments can upgrade without an immediate edit. New configuration should use `transfers`.

Download auto-retry is enabled by default, and `max_attempts: 5` bounds retry
churn per persisted download request across process restarts. Existing legacy
transfers without a request identity fall back to the process-lifetime guard.
Set `max_attempts: 0` only when you explicitly want unlimited automatic retries. The loop is
intentionally conservative for Soulseek network health: retries are delayed
after a failure, scans are bounded globally, and each scan only contacts a small
number of files per peer with a peer cooldown between attempts. When alternate
sources are enabled, auto-retry first tries cooled-down local HashDb inventory
candidates, then uses at most the configured number of bounded alternative-source
searches per scan before falling back to the original
peer. Mesh/swarm retry policies can be more aggressive because those paths use
slskdN-controlled transport budgets; direct Soulseek retry should stay
respectful of remote client queue, file, and megabyte limits.

#### Auto-replace stuck downloads

```yaml
auto_replace:
  interval_seconds: 300
  size_threshold_percent: 0 # exact-size alternatives; raise this to allow a difference
  max_retries: 3 # persisted replacement attempts per download request; 0 = unlimited
```

Auto-replace is a separate background feature from download auto-retry. It
searches for an alternative source for terminal timeout/error/rejection states,
then preserves the stable download-request identity when it swaps sources. The
retry budget is persisted with the transfer history, and failed rows remain
available for manual review. The legacy `transfers.download.auto_replace_*`
aliases remain accepted for existing configurations.

## Global Upload Limits

Global upload limits define the number of queued, daily, and weekly uploads on a _per user_ basis.  These limits behave as defaults and are applied if limits for a user's group have not been set.

Limits are evaluated when a user attempts to enqueue a file.  Queued limits behave exactly as those in other clients; if a limit would be exceeded if the requested file were accepted the request is rejected with the standard messages `Too many files` or `Too many megabytes`, depending on which limit was hit.  These messages are used by other clients to determine whether to retry the transfer later.

If a daily or weekly limit would be exceeded, the request is rejected with a message like `Too many files this week` or `Too many failures today`, depending on which limit is hit.  Transfers rejected with one of these messages should not be retried by other clients (at least, that's the goal!).

The transfers database for the application is used to calculate the statistics used to make limit decisions.  If this database is deleted, moved, cleared, or if the 'volatile' option is set (preventing the database from being persisted to disk), these limits won't work reliably.  Because of the asynchronous nature of the application it's possible for limits to be exceeded if the requests are 'in flight' while data is being persisted, but the number of excess transfers should never be significant.

Note that while it's possible to set the `failures` option for `queued`, it has no effect.

#### **YAML**
```yaml
transfers:
  upload:
    limits:
      queued:
        files: 500
        megabytes: 5000
      daily:
        files: 1000
        megabytes: 10000
        failures: 200
      weekly:
        files: 5000
        megabytes: 50000
        failures: 1000
```

The older `transfers.limits` and `global.limits` layouts are still accepted for
existing deployments. New configuration should keep upload limits under
`transfers.upload.limits`.

## Groups

User groups are used to control upload slots, speed limits, and queue behavior on a per-user basis.

Each group has a priority, starting from 1, determining the order in which groups are prioritized in the upload queue. A lower number translates to higher priority, and Upload slots are granted to higher priority groups before lower priority groups.

Groups have a queue strategy, either `FirstInFirstOut` or `RoundRobin`. This setting determines how uploads from multiple users in the same group are processed; `FirstInFirstOut` processes uploads in the order in which they were enqueued, while `RoundRobin` processes uploads in the order in which the user was ready to receive the upload.

[Upload slots and speed limits](#global-slot-and-speed-limits) configured at the group level can be used to create constraints in addition to global settings. If group-level limits exceed global settings, global settings become the constraint. Slots and speed limit settings default to `int.MaxValue`, effectively deferring to the global limits.

[Upload limits](#global-upload-limits) can be configured at the group level to override the global defaults.  If neither global defaults nor group limits are set, uploads are unlimited.  If global defaults are set and unlimited uploads for a group are desired, set values to `int.MaxValue` or `2147483647`.  While not technically unlimited, this number translates to over 2 petabytes, which would be an impressive amount of data to move peer to peer in a week.

For compatibility, slskdN still accepts `limits` as a sibling of `upload` inside each group. New configuration should nest group limits under `upload`.

The general configuration for a group is as follows:

#### **YAML**
```yaml
upload:
  priority: 500 # 1 to 2147483647
  strategy: roundrobin # roundrobin or firstinfirstout
  slots: 10 # 1 to 2147483647
  speed_limit: 100 # in KiB/s, 1 to 2147483647
  limits:
    queued:
      files: 500 # 1 to 2147483647
      megabytes: 5000 # 1 to 2147483647
    daily:
      files: 1000
      megabytes: 10000
      failures: 200 # 1 to 2147483647
    weekly:
      files: 5000
      megabytes: 50000
      failures: 1000
```

## Built-In Groups

The `default` built-in group contains all users who have not been explicitly added to a user-defined group, are not privileged, and haven't been identified as leechers.

The `leechers` built-in group contains users that have not been explicitly added to a user-defined group, are not privileged, and have shared file and/or directory counts less than the configured `thresholds` for the group. By default, users must share at least one directory with one file to avoid being identified as leechers.

The `privileged` built-in is used to prioritize users who have purchased privileges on the Soulseek network. This groups is not configurable, has a priority of 0 (the highest), a strategy of `FirstInFirstOut`, and can use any number of slots up to the global limit.  Users in this group are also not subject to any limits; they can enqueue any number of files they wish.

It is impossible to explicitly assign users to these built-in groups, but the priority, number of slots, speed, and queue strategy can be adjusted (excluding `privileged`).

Group configuration is accepted either at top level as `groups` or under
`transfers.groups`. New configuration should use `transfers.groups`.

#### **YAML**
```yaml
transfers:
  groups:
    default:
      upload:
        priority: 1
        strategy: roundrobin
        slots: 10
        speed_limit: 50000 # kibibytes
        limits:
          queued:
            files: 150
            megabytes: 1500
          daily:
            files: 2147483647 # effectively unlimited, weekly still applies
            megabytes: 2147483647
          weekly:
            files: 1500
            megabytes: 15000
            failures: 150
    leechers:
      thresholds:
        files: 1
        directories: 1
      upload:
        priority: 99
        strategy: roundrobin
        slots: 1
        speed_limit: 100
        limits:
          queued:
            files: 15
            megabytes: 150
          daily:
            files: 30
            megabytes: 300
            failures: 10
          weekly:
            files: 150
            megabytes: 1500
            failures: 30
```

## User Blacklist

A fourth built-in group, `blacklisted`, is used to disallow other users from various activities.

Blacklisted users are prevented from:
- Receiving search results
- Browsing files
- Retrieving directory contents
- Enqueueing downloads

Private and chat room messages from blacklisted users are also ignored.

Users can be blacklisted by adding their username to the `members` list. Additionally, users can be blacklisted by IP address, or range of addresses by adding a CIDR entry to the `cidrs` list. Username regular expressions can be added to `patterns` for families of abusive or disposable usernames.

Users added to the blacklist will be blocked from enqueueing any new files.  Any existing active or queued transfers will need to be cancelled manually.

A managed blacklist file may also be used to achieve the same effects.  Read more about this in the [Managed Blacklist](#managed-blacklist) section below.

**YAML**
```yaml
transfers:
  groups:
    blacklisted:
      members:
        - <username to blacklist>
      cidrs:
        - <CIDR to blacklist, e.g. 255.255.255.255/32>
      patterns:
        - ^spammer_[0-9]+$
```

## User Defined Groups

In the group configuration, any number of user-defined groups can be added under the `user_defined` key.

User-defined groups use the same configuration as built-in groups and allow a list of `members` containing the usernames of users assigned to the group.

Users can be assigned to multiple groups, with their effective group being the highest priority (lowest-numbered) group. If a user has privileges on the network, any explicit group membership is superseded, and their effective group is the built-in `privileged` group. If users are explicitly assigned to a group, they will not be identified as leechers.

#### **YAML**
```yaml
transfers:
  groups:
    user_defined:
      my_custom_group_name:
        upload:
          priority: 500
          strategy: roundrobin
          slots: 10
          speed_limit: 100
          limits:
            queued:
              files: 1000 # override global default
        members:
          - bob
          - alice
```

## Example

In the following example:

* All leechers share one slot and can download at a maximum speed of 100 KiB/s.  Leechers can only download if fewer than 20 other uploads are in progress to other users.
* Users that aren't leechers and that aren't in the `my_buddies` group (`default` users) share 10 slots among them and can download at the global maximum speed of 1000 KiB/s, but only if fewer than 20 upload slots are being used by users in the `my_buddies` group.
* Users in the `my_buddies` group share 20 slots among them and can download at the global maximum speed. Ten upload slots are reserved for users in this group, and users `alice` and `bob` are members.

```yaml
transfers:
  upload:
    slots: 20
    speed_limit: 1000
  download:
    slots: 500
    speed_limit: 1000
  groups:
    default:
      upload:
        priority: 500
        strategy: roundrobin
        slots: 10
    leechers:
      upload:
        priority: 999
        strategy: roundrobin
        slots: 1
        speed_limit: 100
    user_defined:
      my_buddies:
        upload:
          priority: 250
          queue_strategy: firstinfirstout
          slots: 20
        members:
          - alice
          - bob
```

## Managed Blacklist

A managed blacklist (also called a blocklist) can be specified to disallow interaction with known undesirable actors.  Users whose IP address matches an entry on this list are functionally the same as users added to the [User Blacklist](#user-blacklist) described above and are disallowed any interactions with shares or files.

Blacklists/blocklists designed for use with other P2P applications (such as BitTorrent) are supported; specifically the P2P, DAT, and CIDR formats.

When enabled, the specified file is validated by reading the first few lines of the file to automatically detect the format.  If the file doesn't exist, can't be read, the format can't be detected, or if it contains any lines that don't match the format, the application will exit.  Similarly, if the file changes while the application is running and there's an issue, the application will exit.

Note that the contents of the blacklist are stored in memory to ensure performance, and this will increase the amount of memory used, potentially significantly if the blacklist is large.

| Command-Line         | Environment Variable       | Description                    |
| -------------------- | -------------------------- | ------------------------------ |
| `--enable-blacklist` | `SLSKD_BLACKLIST`          | Enable the managed blacklist   |
| `--blacklist-file`   | `SLSKD_BLACKLIST_FILE`     | The path to the blacklist file |

```yaml
blacklist:
  enabled: true
  file: <path to file containing CIDRs to blacklist>
```

# Chat Rooms and Private Messaging

## Auto-Joining Rooms

A configured list of chat rooms will now be automatically joined on connect.

The list can be specified via command line (e.g. --rooms <room1> --rooms <room2>), with the SLSKD_ROOMS environment variable (rooms separated by a semicolon).

Additionally, when the client is disconnected, any rooms that were joined at the time of the disconnect are rejoined upon reconnect, as long as the app hasn't been restarted in between.

| Command-Line  | Environment Variable | Description                             |
| ------------- | ---------------------| ----------------------------------------|
| `--rooms`     | `SLSKD_ROOMS`        | A list of chat rooms to join on startup |

#### **YAML**
```yaml
rooms:
  - <room 1>
  - <room 2>
```


# Soulseek Configuration

The Soulseek configuration determines how slskd interacts with the Soulseek network and the vendored [slskNet.Runtime](https://github.com/snapetech/slskNet.Runtime) library, which is derived from Soulseek.NET.

## Server Connection

By default the application connects to `vps.slsknet.org` on port `2271`.  This should work for nearly everyone, but it is possible to override both defaults if necessary.

| Command-Line     | Environment Variable | Description                        |
| ---------------- | ---------------------| -----------------------------------|
| `--slsk-address` | `SLSKD_SLSK_ADDRESS` | The address of the Soulseek server |
| `--slsk-port`    | `SLSKD_SLSK_PORT`    | The port of the Soulseek server    |

#### **YAML**
```yaml
soulseek:
  address: vps.slsknet.org
  port: 2271
```

## Username and Password

Credentials to log in to the Soulseek network.

Changing either of these values requires the server connection to be reset.

The password field is masked when serializing options to JSON or YAML to avoid inadvertently exposing the value.

| Command-Line      | Environment Variable       | Description                           |
| ----------------- | -------------------------- | ------------------------------------- |
| `--slsk-username` | `SLSKD_SLSK_USERNAME`      | The username for the Soulseek network |
| `--slsk-password` | `SLSKD_SLSK_PASSWORD`      | The password for the Soulseek network |

#### **YAML**
```yaml
soulseek:
  username: <username>
  password: <password>
```

## Native Interests

slskdN can publish configured native Soulseek liked and disliked interests after login. These values are public to Soulseek interest/recommendation features, so keep them intentional and concise.

| Command-Line              | Environment Variable           | Description                                             |
| ------------------------- | ------------------------------ | ------------------------------------------------------- |
| `--slsk-liked-interests`  | `SLSKD_SLSK_LIKED_INTERESTS`   | Native Soulseek interests to publish as likes after login |
| `--slsk-hated-interests`  | `SLSKD_SLSK_HATED_INTERESTS`   | Native Soulseek interests to publish as dislikes after login |

#### **YAML**
```yaml
soulseek:
  liked_interests:
    - jazz
    - lossless
  hated_interests:
    - low bitrate
```

## Distributed Network

Options for the Soulseek distributed network, which is how search requests are delivered.

The distributed network should only be disabled if no files are being shared.  

Child connections should generally only be disabled on low spec systems or situations where network bandwidth is scarce. Received search requests are re-broadcast to each child connection, and incoming requests are numerous. Consider increasing the child limit from the default of 25 on systems with CPU and memory headroom.

Depending on the current state, changing these values may require the server connection to be reset.

| Command-Line              | Environment Variable    | Description                                                                                                                                                                           |
| ------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--slsk-no-dnet`          | `SLSKD_SLSK_NO_DNET`          | Determines whether the distributed network is disabled. If disabled, the client will not obtain a parent or any child connections, and will not receive distributed search requests. |
| `--slsk-dnet-no-children` | `SLSKD_SLSK_DNET_NO_CHILDREN` | Determines whether to disallow distributed children                                                                                                                                   |
| `--slsk-dnet-children`    | `SLSKD_SLSK_DNET_CHILDREN`    | The maximum number of distributed children to accept                                                                                                                                  |
| `--slsk-dnet-logging`     | `SLSKD_SLSK_DNET_LOGGING`     | Determines whether to enable distributed network logging

#### **YAML**
```yaml
soulseek:
  distributed_network:
    disabled: false
    disable_children: false
    child_limit: 25
```

## Listen IP Address and Port

The local IP address and port on which the application listens for incoming connections.

As with any other Soulseek client, configuring the listen port and port forwarding ensures full connectivity with other clients, including those without a correctly configured a listening port.  

Symptoms of a misconfigured listen port include poor search results and the inability to browse or retrieve user information for some users.

The local IP address defaults to 0.0.0.0, and this should be correct for most people.  If you have multiple network adapters or are using a VPN you may want to set this value to ensure
incoming traffic is properly routed.

If your VPN provider assigns dynamic forwarded ports, use the
[slskdN VPN Agent](../src/slskdN.VpnAgent/README.md) rather than hard-coding a
stale listen port. The Web UI/API can usually remain local or LAN-bound while
Soulseek traffic uses VPN egress. When VPN integration is enabled, the agent
keeps the configured local `soulseek.listen_port` bound and advertises the
active provider mapping as the public Soulseek port. The public and local ports
may therefore differ, while plain/type-1 Soulseek and mesh TCP still share one
TCP forward by default.

For a home instance behind CGNAT, the
[self-hosted relay mode](../src/slskdN.VpnAgent/self-hosted-relay.md) uses a
private Tailscale or WireGuard control URL and requires
`integrations.vpn.self_hosted_relay: true` together with
`integrations.vpn.port_forwarding: true`. This explicit mode enables relay
diagnostics without probing optional relay endpoints on ordinary Gluetun
installations.

When Gluetun's control server uses an API key or Basic authentication, allow
the configured credentials to access `GET /v1/publicip/ip`. If
`integrations.vpn.port_forwarding` is enabled, also allow `GET /v1/portforward`.
Keep the control server on a private container or host network; do not expose it
to the public internet.

| Command-Line                | Environment Variable           | Description                                                      |
| --------------------------- | ------------------------------ | ---------------------------------------------------------------- |
| `--slsk-listen-ip-address`  | `SLSKD_SLSK_LISTEN_IP_ADDRESS` | The local IP address on which to listen for incoming connections |
| `--slsk-listen-port`        | `SLSKD_SLSK_LISTEN_PORT`       | The port on which to listen for incoming connections             |

#### **YAML**
```yaml
soulseek:
  listen_ip_address: 0.0.0.0
  listen_port: 50300
```

## Type-1 Peer, Distributed, and File Transfer Obfuscation

slskdN exposes Soulseek type-1 peer-message, distributed-message, and file-transfer obfuscation as a first-class feature option. It defaults to `enabled: true` in `compatibility` mode, which means regular Soulseek paths stay available and obfuscated reachability is added for compatible peers. The runtime advertises obfuscation metadata, accepts type-1 obfuscated peer-message, distributed-message, and file-transfer connections, and can prefer compatible outbound obfuscated dials.

This is obfuscation, not transport security. It should be treated as a compatibility and traffic-shaping posture, not encryption. Current runtime support covers peer-message (`P`), distributed-network message (`D`), and file-transfer (`F`) streams, with regular fallback retained for all three.

Modes:

| Mode | Intent |
| ---- | ------ |
| `compatibility` | Keep regular peer/distributed/transfer reachability available and add obfuscated reachability when runtime support exists. This is the default and safest broad-client posture. |
| `prefer` | Prefer type-1 obfuscated outbound peer/distributed/transfer dials when compatible peer metadata is available, while preserving regular fallback. |
| `only` | Reserved for obfuscated-only reachability. The current runtime rejects this mode because slskdN keeps regular fallback for legacy clients. |

| Command-Line                             | Environment Variable                         | Description |
| ---------------------------------------- | -------------------------------------------- | ----------- |
| `--slsk-obfuscation`                     | `SLSKD_SLSK_OBFUSCATION`                     | Enables the type-1 obfuscation feature option and status reporting |
| `--slsk-obfuscation-mode`                | `SLSKD_SLSK_OBFUSCATION_MODE`                | Obfuscation posture: `compatibility`, `prefer`, or `only` |
| `--slsk-obfuscation-listen-port`         | `SLSKD_SLSK_OBFUSCATION_LISTEN_PORT`         | Dedicated type-1 obfuscated peer/distributed/transfer listen port; `0` (default) shares `listen_port` instead, with plain and obfuscated connections distinguished per-connection |
| `--slsk-obfuscation-advertise-regular-port` | `SLSKD_SLSK_OBFUSCATION_ADVERTISE_REGULAR_PORT` | Advertises the regular listen port alongside obfuscation metadata |
| `--slsk-obfuscation-prefer-outbound`     | `SLSKD_SLSK_OBFUSCATION_PREFER_OUTBOUND`     | In `prefer` mode, prefers compatible type-1 obfuscated outbound peer/distributed/transfer dials |

#### **YAML**
```yaml
soulseek:
  listen_port: 50300
  obfuscation:
    enabled: true
    mode: compatibility
    listen_port: 0
    advertise_regular_port: true
    prefer_outbound: true  # only changes outbound priority when mode is prefer
```

With the default `obfuscation.listen_port: 0`, obfuscated peer/distributed/transfer connections are accepted on the same TCP socket as `soulseek.listen_port` -- there's nothing extra to forward. On each accepted connection, slskdN reads the first bytes and tests whether they form a plausible plain init frame; if not, it treats them as the start of an obfuscated frame. Set `obfuscation.listen_port` to an explicit nonzero value only if you need obfuscated connections to arrive on a dedicated port instead.

Mesh-DHT and overlay privacy uses the separate `security.adversarial` transport options. Those options can prefer Tor, I2P, WebSocket tunnel, HTTP tunnel, obfs4, or meek for slskdN mesh paths while falling back to normal mesh routing when private/obfuscated transports are unavailable. They do not wrap the official Soulseek server connection or change the separate public BitTorrent DHT rendezvous layer.

## Soulseek Mesh Rendezvous and Capability Handshakes

slskdN can use the native Soulseek interest graph as an explicit rendezvous path for finding other slskdN mesh peers. This is separate from DHT rendezvous and is disabled by default because enabling it publishes the recognizable `slskdn-mesh-v1` interest tag on the configured Soulseek account.

Runtime capability handshakes are separate from rendezvous interest publishing. When enabled, slskdN peers can exchange signed capability descriptors over Soulseek peer-message connections. Capability file discovery still falls back to `@@slskdn/__caps__.json` when a runtime descriptor is unavailable.

| YAML option | Default | Description |
| ----------- | ------- | ----------- |
| `mesh.enable_soulseek_capability_handshake` | `false` | Opts into slskdN peer capability descriptor exchange over Soulseek peer-message connections. |
| `mesh.enable_soulseek_rendezvous` | `false` | Allows System -> Mesh and API callers to publish/remove the public `slskdn-mesh-v1` rendezvous interest and query rendezvous candidates. |
| `mesh.probe_soulseek_rendezvous_capabilities` | `false` | Probes rendezvous candidates for runtime peer capability descriptors when running active rendezvous discovery. |

#### **YAML**
```yaml
mesh:
  enable_soulseek_capability_handshake: false
  enable_soulseek_rendezvous: false
  probe_soulseek_rendezvous_capabilities: false
```

## Other

Users can configure "profile" information for other users on the network to view, including a description and a photo.  Note that Soulseek NS doesn't support .PNG,
so formats .JPG/.JPEG, .GIF, and .BMP are advised.

| Command-Line         | Environment Variable       | Description                                   |
| -------------------- | -------------------------- | --------------------------------------------- |
| `--slsk-description` | `SLSKD_SLSK_DESCRIPTION`   | The user description for the Soulseek network |
| `--slsk-picture`     | `SLSKD_SLSK_PICTURE`       | The user picture for the Soulseek network     |

#### **YAML**
```yaml
soulseek:
  description: "A slskdN user. Unofficial fork of slskd: https://github.com/snapetech/slskdn"
  picture: path/to/slsk-profile-picture.jpg
```

## Connection Options

### Timeouts

Timeout options control how long the application waits for connections to connect, and how long connections can be inactive before they are disconnected.

Higher connect timeout values will help ensure that operations (browse, download requests, etc.) are successful the first time but decrease the responsiveness of commands that will ultimately fail.

Inactivity timeouts help the application determine when a distributed parent connection has stopped sending data and when connections that have delivered search results (and are unlikely to be used further) from remaining open longer than needed. Reducing this timeout can help low spec systems if port exhaustion is a concern but may result in the application "hunting" for a distributed parent connection needlessly. Values below one minute can also break slow peer browse responses and transfer acknowledgements.

Transfer connections use their own timeout value; other Soulseek clients regulate transfer speed by controlling how often data is sent (e.g. send full speed for 5 seconds, send nothing for 25 seconds),
and as such transfers can easily time out due to inactivity if using a lower value.  This setting must be at least 30 seconds.

| Command-Line                | Environment Variable            | Description                                      |
| --------------------------- | ------------------------------- | ------------------------------------------------ |
| `--slsk-connection-timeout` | `SLSKD_SLSK_CONNECTION_TIMEOUT` | The connection timeout value, in milliseconds    |
| `--slsk-inactivity-timeout` | `SLSKD_SLSK_INACTIVITY_TIMEOUT` | The connection inactivity value, in milliseconds |
| `--slsk-transfer-timeout`   | `SLSKD_SLSK_TRANSFER_TIMEOUT`   | The transfer connection timeout value, in milliseconds |

#### **YAML**
```yaml
soulseek:
  connection:
    timeout:
      connect: 10000
      inactivity: 60000
      transfer: 60000
```

### Server MTU

The optional `mtu` value caps the TCP segment size used for the Soulseek server connection. Leave it unset to use the operating system default. Systems with jumbo frames enabled can try `1500` if the server connection stalls; the setting applies to the server connection only.

| Command-Line | Environment Variable | Description |
| --- | --- | --- |
| `--slsk-connection-mtu` | `SLSKD_SLSK_CONNECTION_MTU` | Optional server TCP MTU cap; valid values are 1280 through 9000 |

#### **YAML**
```yaml
soulseek:
  connection:
    mtu: 1500 # optional; remove or use null for the operating system default
```

### Buffers

Buffer options control the application's internal buffer to batch socket reads and writes. The host Operating System controls actual socket buffer sizes (.NET is not great in this department currently, and the behavior is not consistent cross-platform).

Larger buffer sizes can improve performance, especially for file transfers, resulting in increased memory usage.

The transfer buffer size is used for file transfers (both read and write), and the read and write buffer sizes are used for all other connection types. The transfer buffer size directly correlates with transfer speed; setting this value much lower than the default will result in slow uploads (which may be good for low-spec hardware).

The write queue option is the hard limit for the number of concurrent writes for a connection. It generally only applies to distributed child connections and prevents a memory leak if the application continues to try and send data after a connection has gone "bad". This value can be set as low as five if memory is a constraint, though the default has been tested extensively and should be suitable for most scenarios, including low spec.

| Command-Line             | Environment Variable         | Description                                        |
| ------------------------ | ---------------------------- | -------------------------------------------------- |
| `--slsk-read-buffer`     | `SLSKD_SLSK_READ_BUFFER`     | The connection read buffer size, in bytes          |
| `--slsk-write-buffer`    | `SLSKD_SLSK_WRITE_BUFFER`    | The connection write buffer size, in bytes         |
| `--slsk-transfer-buffer` | `SLSKD_SLSK_TRANSFER_BUFFER` | The read/write buffer size for transfers, in bytes |
| `--slsk-write-queue`     | `SLSKD_SLSK_WRITE_QUEUE`     | The connection write buffer size, in bytes         |

#### **YAML**
```yaml
soulseek:
  connection:
    buffer:
      read: 16384
      write: 16384
      transfer: 262144
      write_queue: 250    
```

### Proxy

Connections can optionally use a SOCKS5 proxy, with or without username and password authentication.

An address and port must also be specified if the proxy is enabled.

| Command-Line            | Environment Variable        | Description                              |
| ----------------------- | --------------------------- | ---------------------------------------- |
| `--slsk-proxy`          | `SLSKD_SLSK_PROXY_ENABLED`  | Determines whether a proxy is to be used |
| `--slsk-proxy-address`  | `SLSKD_SLSK_PROXY_ADDRESS`  | The proxy address                        |
| `--slsk-proxy-port`     | `SLSKD_SLSK_PROXY_PORT`     | The proxy port                           |
| `--slsk-proxy-username` | `SLSKD_SLSK_PROXY_USERNAME` | The proxy username, if applicable        |
| `--slsk-proxy-password` | `SLSKD_SLSK_PROXY_PASSWORD` | The proxy password, if applicable        |

#### **YAML**
```yaml
soulseek:
  connection:
    proxy:
      enabled: false
      address: ~
      port: ~
      username: ~
      password: ~   
```

## Diagnostic Level

The diagnostic level option is passed to the vendored `slskNet.Runtime` configuration and determines the level of detail the library produces diagnostic messages. This option should generally be left to `Info` or `Warning` but can be set to `Debug` if more verbose logging is desired.

| Command-Line        | Environment Variable       | Description                                               |
| ------------------- | -------------------------- | --------------------------------------------------------- |
| `--slsk-diag-level` | `SLSKD_SLSK_DIAG_LEVEL`    | The minimum diagnostic level (None, Warning, Info, Debug) |

#### **YAML**
```yaml
soulseek:
  diagnostic_level: Info
```

# Web Configuration

## Basic

The default HTTP listen port is 5030, but can be anything between 1 and 65535.

A [unix domain socket](https://en.wikipedia.org/wiki/Unix_domain_socket) can be used on both unix-like operating systems and Windows. The specified socket file path must be absolute, and must point to a file that does not exist (slskd will manage it automatically).

The URL base option allows the application to operate behind a reverse proxy. Setting a base of "slskd" would make the web UI accessible at `http://<host>:<port>/slskd`.

The content path can be used to force the application to serve static web content from a location other than the default (`wwwroot`). The application is designed to decouple the Web UI from the rest of the application to be replaceable.

Logging of HTTP requests is disabled by default.

| Command-Line      | Environment Variable       | Description                                       |
| ----------------- | -------------------------- | ------------------------------------------------- |
| `-l\|--http-port` | `SLSKD_HTTP_PORT`          | The HTTP listen port                              |
| `--http-socket`   | `SLSKD_HTTP_SOCKET`        | The HTTP listen unix domain socket (UDS) path     |
| `--url-base`      | `SLSKD_URL_BASE`           | The base url for web requests                     |
| `--content-path`  | `SLSKD_CONTENT_PATH`       | The path to static web content                    |
| `--http-logging`  | `SLSKD_HTTP_LOGGING`       | Determines whether HTTP requests are to be logged |

#### **YAML**
```yaml
web:
  port: 5030
  socket: ~
  url_base: /
  content_path: wwwroot
  logging: false
```

## HTTPS

The default HTTPS port is 5031, but can be anything between 1 and 65535.

By default, the application generates a new, self-signed X509 certificate at each startup. If, for whatever reason, a self-signed certificate isn't sufficient, or if the certificate needs to be shared among systems or applications, a certificate `.pfx` and password can be defined.

The application can produce a self-signed `.pfx` file and random password using the `--generate-cert` command.

| Command-Line            | Environment Variable        | Description                                                    |
| ----------------------- | --------------------------- | -------------------------------------------------------------- |
| `-L\|--https-port`      | `SLSKD_HTTPS_PORT`          | The HTTPS listen port                                          |
| `-f\|--force-https`     | `SLSKD_HTTPS_FORCE`         | Determines whether HTTP requests are to be redirected to HTTPS |
| `--https-cert-pfx`      | `SLSKD_HTTPS_CERT_PFX`      | The path to the X509 certificate .pfx file                     |
| `--https-cert-password` | `SLSKD_HTTPS_CERT_PASSWORD` | The password for the X509 certificate                          |
| `--no-https`            | `SLSKD_NO_HTTPS`            | Determines whether HTTPS is to be disabled                     |

#### **YAML**
```yaml
web:
  https:
    disabled: false
    port: 5031
    force: false
    certificate:
      pfx: ~
      password: ~
```

## Authentication

Authentication for the web UI (and underlying API) is enabled by default, and the default username and password are both `slskd`. Changing both the username and password during the initial configuration is highly recommended.

When authentication is disabled (`web.authentication.disabled: true` or
`SLSKD_NO_AUTH=true`), unauthenticated access is limited to loopback by
default. To allow remote clients, set `web.allow_remote_no_auth: true` and
configure `web.authentication.passthrough.allowed_cidrs` with the specific
client IP ranges that may connect. The flag alone does not allow every remote
client. For example:

```yaml
web:
  allow_remote_no_auth: true
  authentication:
    disabled: true
    passthrough:
      allowed_cidrs: 192.168.1.0/24
```

If requests pass through a reverse proxy, the application checks the address
of that proxy connection; apply any client-range restriction at the ingress
when appropriate. A 401 in passthrough mode is reported to the request caller
without clearing passthrough state or reloading the whole Web UI.

By default, a random JWT secret key is generated at each start. It is convenient and secure, but restarting the application will invalidate any issued JWTs, causing users to sign in again. To avoid this, supply a custom secret at least 16 characters in length. Note that the secret can be used to generate valid JWTs for the application, so keep this value secret.

The JWT TTL option determines how long issued JWTs are valid, defaulting to 7 days.

API keys can be configured to allow for secure communication without requiring the caller to obtain a JWT by signing in with a username and password. Each key must be given a name and a key with a length between 16 and 255 characters (inclusive). Callers may then supply one of the configured keys in the `X-API-Key` header when making web requests. Remember that API keys are secrets, so keep them safe.

Browser SignalR connections also support API-key authentication. The web UI
passes the configured API key as a short-lived SignalR `access_token`; the
server promotes it to a scoped JWT before hub authorization. This keeps live
search, transfer, application-state, and log updates working for API-key-only
operators without requiring a browser password login.

You can generate a random, 32 bit API key by starting the application with `-k` or `--generate-secret` at the command line.

An optional comma separated list of [CIDRs](https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing) can be defined for each key, which will restrict usage of the key to callers with a remote IP address that falls within one of the defined CIDRs.  The default CIDR list for each key is `0.0.0.0/0,::0`, which applies to any IP address (IPv4 or IPv6).

A common use case for CIDR filtering might be to restrict API access to clients within your home network. Assuming your network uses the common `192.168.1.x` addressing, you could specify a `cidr` of `192.168.1.0/24`, which would apply to any IP between `192.168.1.1` and `192.168.1.254`, inclusive.

Note that CIDR filtering may not work as expected behind a reverse proxy, ingress controller, or load balancer, because the remote IP address will be that of the device that's handling ingress.  This application doesn't support the `X-Forwarded-For` header (or anything like it) because a bad actor can easily fake it.  If you wish to use CIDR filtering in this scenario, you'll need to do it at the point of ingress to your network.

Please also note that using API key authentication without HTTPS is **NOT RECOMMENDED**.  API keys are sent in HTTP headers (and in the case of SignalR, in query parameters) and will be easily accessible to anyone eavesdropping on the network.  This is a risk with JWTs as well, but JWTs expire and API keys don't.  If you choose to use API keys over plain HTTP, seriously consider using CIDR filtering.

| Command-Line     | Environment Variable       | Description                                         |
| ---------------- | -------------------------- | --------------------------------------------------- |
| `-X\|--no-auth`  | `SLSKD_NO_AUTH`            | Determines whether authentication is to be disabled |
| `-u\|--username` | `SLSKD_USERNAME`           | The username for the web UI                         |
| `-p\|--password` | `SLSKD_PASSWORD`           | The password for the web UI                         |
| `--jwt-key`      | `SLSKD_JWT_KEY`            | The secret key used to sign JWTs                    |
| `--jwt-ttl`      | `SLSKD_JWT_TTL`            | The TTL (duration) of JWTs, in milliseconds         |

#### **YAML**
```yaml
web:
  authentication:
    disabled: false
    username: slskd
    password: slskd
    jwt:
      key: ~
      ttl: 604800000
    api_keys:
      my_api_key:
        key: <some example string between 16 and 255 characters>
        cidr: 0.0.0.0/0,::/0
```

# Filters

A number of filters can be configured to control various aspects of how the application interacts with the Soulseek network.

## Search Filters

Search filters can be used to prevent certain types of search requests from being performed against your shares.  This option is an array that can take any number of filters.  Filters must be a valid regular expression; a few examples are included below and in the example configuration included with the application, but the list is empty by default.

Filter expressions are case insensitive by default.

| Command Line              | Environment Variable          | Description                                                           |
| ------------------------- | ----------------------------- | --------------------------------------------------------------------- |
| `--search-request-filter` | `SLSKD_SEARCH_REQUEST_FILTER` | A list of regular expressions used to filter incoming search requests |

#### **YAML**
```yaml
filters:
  search:
    request:
      - ^.{1,2}$ # discard any requests shorter than 3 characters
      - ^(\.?pdf|\.?docx|\.?xlsx)$ # discard any requests that might be looking for sensitive documents
```

## Download Exclusions

Download exclusions prevent outbound transfers when a literal term appears in
the remote filename or path. Matching is case-insensitive and covers the
normal download queue, retries, wishlist automation, auto-replacements,
search-action downloads, peer-preview streams, pod downloads, multi-source
transfers, and direct probe/bridge paths. A policy update also cancels active
transfers that become blocked.

These are literal substring matches, not regular expressions, and the policy
does not inspect audio tags or infer the contents of a file. Add one term per
entry; use a phrase such as `a cappella` when the spaces are part of the match.
For day-to-day changes, open **Download filters** in the Downloads header. The
same setting is also available in **System -> Policies** for advanced YAML
administration.

| Command Line                  | Environment Variable              | Description |
| ----------------------------- | ---------------------------------- | ----------- |
| `--download-filter-exclude`   | `SLSKD_DOWNLOAD_FILTER_EXCLUDE`   | Literal terms that block outbound downloads when present in a remote filename or path; separate environment-variable entries with semicolons |

#### **YAML**
```yaml
filters:
  download:
    exclude:
      - acapella
      - instrumental
      - a cappella
```

# Data Retention

By default, most things created by the application are retained indefinitely; they have to be removed manually by the user.  Users can optionally configure certain things to be removed or deleted automatically after a period of time.

Completed searches can be configured to be removed from the UI and 'hard' deleted from the database.  It's a good idea to set this to something relatively short, as old searches have diminishing value as they age and the records contain a lot of data.

Transfers can be configured to be removed from the UI after they are complete by specifying retention periods for uploads and downloads separately, and by transfer state; succeeded, errored, and cancelled.

Files (on disk) can be configured to be deleted after the age of their last access time exceeds the configured time.  Completed and incomplete files can be configured separately.

Application logs are removed after 14 days by default. Configure at least 2 days of retention; Serilog's daily rollover needs more than one day to keep the active file safely.

Search retention may be left unset (`null`) to keep completed searches regardless
of age. Event retention is in days. Transfer, removed-transfer, and file
retention periods are in minutes; log retention is in days. The event count
limit is separate from age retention, and `0` disables that count limit.

#### **YAML**
```yaml
retention:
  search: 1440 # 1 day
  events: 30 # days
  events_max_count: 10000 # 0 disables the count limit
  transfers:
    removed: 10080 # 7 days; null keeps removed rows indefinitely
    upload:
      succeeded: 1440 # 1 day
      errored: 30
      cancelled: 5
    download:
      succeeded: 1440 # 1 day
      errored: 20160 # 2 weeks 
      cancelled: 5
  files:
    complete: 20160 # 2 weeks
    incomplete: 43200 # 30 days
  logs: 14 # days (minimum 2)
```

| Command-Line | Environment Variable | Description |
| ------------ | -------------------- | ----------- |
| `--retention-search` | `SLSKD_RETENTION_SEARCH` | Age limit for completed searches, in minutes; unset or `null` keeps them regardless of age |
| `--retention-events` | `SLSKD_RETENTION_EVENTS` | Age limit for event records, in days |
| `--retention-events-max-count` | `SLSKD_RETENTION_EVENTS_MAX_COUNT` | Maximum retained event records; `0` disables the count limit |
| `--retention-transfers-removed` | `SLSKD_RETENTION_TRANSFERS_REMOVED` | Age limit for soft-removed completed transfers, in minutes; `null` keeps them indefinitely |
| `--retention-transfers-upload-succeeded` | `SLSKD_RETENTION_TRANSFERS_UPLOAD_SUCCEEDED` | Age limit for successful uploads, in minutes |
| `--retention-transfers-upload-errored` | `SLSKD_RETENTION_TRANSFERS_UPLOAD_ERRORED` | Age limit for errored uploads, in minutes |
| `--retention-transfers-upload-cancelled` | `SLSKD_RETENTION_TRANSFERS_UPLOAD_CANCELLED` | Age limit for cancelled uploads, in minutes |
| `--retention-transfers-download-succeeded` | `SLSKD_RETENTION_TRANSFERS_DOWNLOAD_SUCCEEDED` | Age limit for successful downloads, in minutes |
| `--retention-transfers-download-errored` | `SLSKD_RETENTION_TRANSFERS_DOWNLOAD_ERRORED` | Age limit for errored downloads, in minutes |
| `--retention-transfers-download-cancelled` | `SLSKD_RETENTION_TRANSFERS_DOWNLOAD_CANCELLED` | Age limit for cancelled downloads, in minutes |
| `--retention-files-complete` | `SLSKD_RETENTION_FILES_COMPLETE` | Age limit for completed files on disk, in minutes |
| `--retention-files-incomplete` | `SLSKD_RETENTION_FILES_INCOMPLETE` | Age limit for incomplete files on disk, in minutes |
| `--retention-logs` | `SLSKD_RETENTION_LOGS` | Age limit for application logs, in days (minimum 2) |

# Integrations

## User-Defined

User-defined integrations allow users to configure external applications to receive data from slskd as things happen internally.  slskd uses an internal [event bus](https://www.akamai.com/glossary/what-is-an-event-bus) over which event data is sent from application logic to whatever destination(s) users choose.

The number and type of events will change as the application matures, but each event should have some minimal properties:

|Name|Description|
|-|-|
|Id|The unique ID for the event.  Events may be delivered to external consumers more than once; use this property to de-duplicate them.|
|Timestamp|The time (UTC) at which the event was raised.  Events can arrive out of chronological order; use this property to determine if that has taken place.|
|Version|The event version, used to disambiguate event shapes if a breaking change is made to the data in the future.|
|Type|The event type.  Use this to determine what other data will be included.  See: [Events.cs](https://github.com/slskd/slskd/blob/master/src/slskd/Events/Types/Events.cs).|

Here's an example of what a `DownloadFileComplete` event (at the time of this writing; review Events.cs!) looks like:

```json
{
    "type": "DownloadFileComplete",
    "version": 0,
    "localFilename": "asdfasfdasfdlocal.file",
    "remoteFilename": "asdfasfdasfdremote.file",
    "transfer": {
        "id": "00000000-0000-0000-0000-000000000000",
        "direction": "Download",
        "size": 0,
        "startOffset": 0,
        "state": "None",
        "requestedAt": "0001-01-01T00:00:00",
        "bytesTransferred": 0,
        "averageSpeed": 0,
        "bytesRemaining": 0,
        "percentComplete": 0
    },
    "id": "973bed18-8516-4b7d-ab24-e13888385237",
    "timestamp": "2024-11-28T00:54:13.8939864Z"
}
```

Users developing integrations can use the internal `RaiseEvent` HTTP endpoint to create sample events and put them on the bus.  This will help test integrations end to end without having to take action within the application, but be aware; using this endpoint after testing is complete is not a good idea!

Here's an example cURL command for the endpoint:

```bash
curl --location 'localhost:5030/api/v0/events/downloadfilecomplete' \
  --header 'Content-Type: application/json' \
  --header 'X-API-Key: <an API key from your config>' \
  --data '"asdfasfdasfd"'
```

The data passed is a 'disambiguator' that's prepended to sample data.  This helps differentiate between different event instances.

### Webhooks

Webhooks (outbound HTTP requests) can be configured to be called when application events are raised.  Webhooks are given a name (useful for troubleshooting!), a list of triggering events, a `call` configuration that defines the HTTP request to be made, and timeout and retry configuration.

Webhook HTTP requests are always a `POST`, and will always include the event data in the body, serialized as JSON.  Users define a fully-qualified endpoint address, an optional collection of headers, and an optional flag to ignore HTTPS errors caused by invalid (e.g. self signed) certificates.

If unconfigured, the default timeout for requests is 5 seconds, and each request will be attempted only once per event.

#### **YAML**
```yaml
integrations:
  webhooks:
    my_basic_webhook_using_defaults:
      on:
        - All
      call:
        url: http://localhost:4224
    my_webhook_using_detailed_config:
      on:
        - DownloadFileComplete
      call:
        url: https://192.168.1.42:8080/slskd_webhook
        headers:
          - name: X-API-Key # if using API key style authentication
            value: foobar1234
          - name: Authorization # if using JWT authentication
            value: Bearer eyJ...ssw5c
          - name: User-Agent # can be useful!
            value: slskd/0.0
        ignore_certificate_errors: true # defaults to false
      timeout: 5000 # in milliseconds
      retry:
        attempts: 3
```

The older singular `integration` key remains readable for existing files. New configuration should use `integrations`.

### Scripts

User-defined scripts can be configured to run when application events are raised.  Scripts are given a name (useful for troubleshooting!), a list of triggering events, and a `run` configuration that's used to execute the script.

The `run` configuration can take a few different forms (see examples below), but in all cases a new process is started using either the `executable` you specify or, if you don't specify one, the executable set in your system's `$SHELL` environment variable, or `cmd.exe` on Windows.

Processes are started in the `/scripts` directory (meaning the working directory), and stdout and stderr are redirected to slskd for logging purposes.  Depending on the `run` configuration your defined command will be passed as either a single argument or list of arguments, with the latter being easier to properly quote and escape.

The data associated with the event that's invoking your script is stringified to JSON and set as the value of the `SLSKD_SCRIPT_DATA` environment variable.  Whatever command or script you specify will need to read this value and handle the data.

> [!CAUTION]
> **Remote Code Execution Risk**: The event data in `$SLSKD_SCRIPT_DATA` originates from the Soulseek network and may contain malicious content. Passing this data as command-line arguments could allow attackers to inject shell commands through specially crafted filenames, usernames, or other fields. For example, a filename like `song"; rm -rf /; echo "` could delete your entire filesystem if passed unsafely to a shell command.
> 
> **Best practices:**
> - ✅ Read `$SLSKD_SCRIPT_DATA` as an environment variable
> - ✅ Parse the JSON and validate/sanitize individual fields before use
> - ✅ Use programming languages with proper JSON parsing (Python, Node.js, etc.)
> - ❌ Avoid using `$SLSKD_SCRIPT_DATA` in shell command substitution like `$(echo $SLSKD_SCRIPT_DATA)`
> - ❌ Avoid passing the raw data as arguments: `my_script.sh "$SLSKD_SCRIPT_DATA"`

#### **YAML**
```yaml
integrations:
  scripts:
    my_post_download_script:
      on:
        - DownloadFileComplete
        - DownloadDirectoryComplete
      run:
        command: "echo "new event!" >> event_log.txt # command is run with system $SHELL/cmd.exe on Windows
    my_logging_script:
      on:
        - All
      run:
        executable: /bin/sh # explicitly setting executable; if omitted, $SHELL/cmd.exe is used
        args: '-c "echo "new event!" >> event_log.txt"'
    another_script:
      on:
        - All
      run:
        executable: /bin/sh # as above, can omit to use $SHELL/cmd.exe
        arglist: # easier to properly quote
          - /c
          - 'echo "new event!" >> event_log.txt'
```

## System-Defined

System-defined integrations are part of the application logic.  Users can configure settings, but don't have any control over behavior.

### Chromaprint and AcoustID

Chromaprint fingerprinting is opt-in. When enabled, completed audio downloads
are decoded with the configured `ffmpeg` executable, fingerprinted with the
native `chromaprint` library, and stored in HashDb. AcoustID lookup is a
separate opt-in step that uses the resulting fingerprint and requires an
AcoustID client ID.

```yaml
integrations:
  chromaprint:
    enabled: true
    ffmpeg_path: ffmpeg
    sample_rate: 44100
    channels: 2
    duration_seconds: 120
  acoustid:
    enabled: true
    client_id: "your-acoustid-client-id"
```

The `ffmpeg_path` value may be a command available on `PATH` or an absolute
path. In Docker, the standard image includes `ffmpeg` and the native
Chromaprint library. The System -> Integrations metadata-processing panel
shows each fingerprint attempt and preserves the failure detail, including
ffmpeg's diagnostic output when decoding fails.

When both the built-in HTTP and HTTPS listeners are enabled, slskdN marks
antiforgery cookies as `Secure` on HTTPS and does not mint them from HTTP.
Browsers scope cookies by host rather than port or scheme; this prevents an HTTP
response from trying to replace the HTTPS cookie and producing Firefox/LibreWolf errors such as
`Cookie XSRF-COOKIE-5030 has been rejected because there is an existing secure
cookie`. Authenticated UI requests use the JWT returned by login, so this does
not prevent the optional HTTP listener from being used. When HTTPS is disabled,
the HTTP-only deployment continues to use non-secure antiforgery cookies.

Auto-replace does not act on user-cancelled downloads. It only considers
timeouts, transfer errors, and peer rejections. Disabling Auto-replace also
cancels an active replacement cycle. Wishlist automatic directory downloads
are bounded at 50 unique track names; duplicate suffixes such as `(1)` and
`(2)` are treated as the same track, and larger candidates are left for manual
review.

### Lidarr

Lidarr is a first-class slskdN integration for music acquisition. slskdN uses
Lidarr's supported HTTP API to read Wanted/Missing albums, apply per-entry
quality-profile filters, create album or missing-track Wishlist searches,
optionally auto-download those searches, and safely submit completed directories
back to Lidarr for import. No Lidarr plugin is required.

The safest rollout is to enable Lidarr, verify `/status`, preview
`/wanted/missing`, run a small one-time `/wanted/sync`, then enable scheduled
sync and auto-download/import after the paths are confirmed.

| Command-Line                         | Environment Variable                  | Description                                                        |
| ------------------------------------ | ------------------------------------- | ------------------------------------------------------------------ |
| `--lidarr`                           | `LIDARR`                              | Determines whether Lidarr integration is enabled                   |
| `--lidarr-url`                       | `LIDARR_URL`                          | Lidarr base URL, such as `http://lidarr:8686`                      |
| `--lidarr-api-key`                   | `LIDARR_API_KEY`                      | Lidarr API key from Settings, General, Security                    |
| `--lidarr-timeout`                   | `LIDARR_TIMEOUT`                      | HTTP timeout for Lidarr requests, in seconds                       |
| `--lidarr-sync-wanted`               | `LIDARR_SYNC_WANTED`                  | Sync Lidarr Wanted/Missing albums and tracks into slskdN Wishlist  |
| `--lidarr-sync-interval`             | `LIDARR_SYNC_INTERVAL`                | Interval between wanted syncs, in seconds                          |
| `--lidarr-sync-max-items`            | `LIDARR_SYNC_MAX_ITEMS`               | Maximum wanted albums to sync per run                              |
| `--lidarr-auto-download`             | `LIDARR_AUTO_DOWNLOAD`                | Auto-download Wishlist items created from Lidarr wanted albums     |
| `--lidarr-wishlist-filter`           | `LIDARR_WISHLIST_FILTER`              | Fallback filter when no recognizable Lidarr quality mapping exists  |
| `--lidarr-wishlist-max-results`      | `LIDARR_WISHLIST_MAX_RESULTS`         | Maximum search results retained by Lidarr-created Wishlist items   |
| `--lidarr-edition-match-mode`        | `LIDARR_EDITION_MATCH_MODE`           | Handling for candidates that don't match Lidarr's monitored release's track count/duration/edition: `exclude`, `prefer`, or `off` |
| `--lidarr-auto-import-completed`     | `LIDARR_AUTO_IMPORT_COMPLETED`        | Submit completed slskdN download directories to Lidarr for import  |
| `--lidarr-import-delay`              | `LIDARR_IMPORT_DELAY`                 | Delay before the first automatic import attempt, in seconds; lets a path-mapped or network-shared destination become visible to Lidarr first. Only applies to auto-triggered imports |
| `--lidarr-import-retry-max-attempts` | `LIDARR_IMPORT_RETRY_MAX_ATTEMPTS`    | Additional automatic retries when a manual-import call fails transiently (non-2xx response or timeout); `0` disables auto-retry |
| `--lidarr-import-retry-delay`        | `LIDARR_IMPORT_RETRY_DELAY`           | Base delay between automatic retries, in seconds; doubles after each failed attempt |
| `--lidarr-import-path-from`          | `LIDARR_IMPORT_PATH_FROM`             | Local slskdN completed path prefix to rewrite before calling Lidarr |
| `--lidarr-import-path-to`            | `LIDARR_IMPORT_PATH_TO`               | Lidarr-visible completed path prefix                               |
| `--lidarr-import-mode`               | `LIDARR_IMPORT_MODE`                  | Lidarr import mode: `move` or `copy`                               |
| `--lidarr-import-replace-existing`   | `LIDARR_IMPORT_REPLACE_EXISTING`      | Allow Lidarr import to replace existing files                      |
| `--lidarr-skip-already-owned-albums` | `LIDARR_SKIP_ALREADY_OWNED_ALBUMS`    | Skip auto-import, without calling Lidarr, when the identified album is already fully owned; ignored when `--lidarr-import-replace-existing` is set |

#### **YAML**
```yaml
integrations:
  lidarr:
    enabled: false
    url: "http://127.0.0.1:8686"
    api_key: ""
    timeout_seconds: 20
    sync_wanted_to_wishlist: false
    sync_interval_seconds: 3600
    max_items_per_sync: 100
    auto_download: false
    wishlist_filter: "" # fallback; a recognizable Lidarr quality profile takes precedence per entry
    wishlist_max_results: 100
    edition_match_mode: "exclude" # exclude, prefer, or off
    auto_import_completed: false
    import_delay_seconds: 0 # only applies to auto-triggered imports, not manual ones
    import_retry_max_attempts: 2 # 0 disables auto-retry
    import_retry_delay_seconds: 30 # doubles after each attempt
    import_path_from: ""
    import_path_to: ""
    import_mode: "move"
    import_replace_existing_files: false
    skip_already_owned_albums: true
```

A Lidarr manual-import call can fail transiently right after a download
completes — for example if the destination hasn't become visible to Lidarr
yet across a network share or path-mapped mount. When that happens, slskdN
automatically retries up to `import_retry_max_attempts` additional times,
doubling `import_retry_delay_seconds` between attempts, before giving up and
recording the failure in the Lidarr import history (retryable manually from
there). Set `import_delay_seconds` to wait before the very first automatic
attempt if the destination consistently needs a moment to become visible.
Failures that aren't transient (Lidarr disabled, bad credentials, a
permanently missing path) are not retried automatically.

Separately, some Lidarr versions throw an internal error scanning a download
folder that duplicates an album already fully present in the library (a
re-download or a second search hitting the same release), rather than
returning a normal "no changes" result. When `skip_already_owned_albums` is
enabled (the default), slskdN identifies the release via Lidarr's `/parse`
endpoint before scanning it and, if every track of the matched album already
has a file in Lidarr, skips the import outright instead of calling the
manual-import endpoint at all. This check is skipped when
`import_replace_existing_files` is enabled, since that setting means
existing files should intentionally be replaced.

If slskdN and Lidarr see completed downloads at different paths, set both
`import_path_from` and `import_path_to`. `import_path_from` must match the path
inside the slskdN process; it does not change `directories.downloads`. For
example, Docker slskdN can rewrite `/music/downloaded` to
`D:\downloaded` for a native Windows Lidarr instance. Write the YAML value with
single quotes (`import_path_to: 'D:\downloaded'`) so its backslash remains
literal. If both
applications see the same Windows directory, leave the mapping empty and set
`directories.downloads` to that Windows path.

See [Lidarr Integration](lidarr-integration.md) for setup, Docker volume
examples, operator API calls, and import safety rules.

### FTP

Files can be uploaded to a remote FTP server upon completion. Files are uploaded to the server and remote path specified using the directory and filename with which they were downloaded; the FTP will match the layout of the local disk.

Uploads are attempted up to the maximum configured retry count and then discarded.

| Command-Line                      | Environment Variable                  | Description                                              |
| --------------------------------- | ------------------------------------- | -------------------------------------------------------- |
| `--ftp`                           | `SLSKD_FTP`                           | Determines whether FTP integration is enabled            |
| `--ftp-address`                   | `SLSKD_FTP_ADDRESS`                   | The FTP address                                          |
| `--ftp-port`                      | `SLSKD_FTP_PORT`                      | The FTP port                                             |
| `--ftp-username`                  | `SLSKD_FTP_USERNAME`                  | The FTP username                                         |
| `--ftp-password`                  | `SLSKD_FTP_PASSWORD`                  | The FTP password                                         |
| `--ftp-remote-path`               | `SLSKD_FTP_REMOTE_PATH`               | The remote path for uploads                              |
| `--ftp-encryption-mode`           | `SLSKD_FTP_ENCRYPTION_MODE`           | The FTP encryption mode (none, implicit, explicit, auto) |
| `--ftp-ignore-certificate-errors` | `SLSKD_FTP_IGNORE_CERTIFICATE_ERRORS` | Determines whether to ignore FTP certificate errors      |
| `--ftp-overwrite-existing`        | `SLSKD_FTP_OVERWRITE_EXISTING`        | Determines whether existing files should be overwritten  |
| `--ftp-connection-timeout`        | `SLSKD_FTP_CONNECTION_TIMEOUT`        | The connection timeout value, in milliseconds            |
| `--ftp-retry-attempts`            | `SLSKD_FTP_RETRY_ATTEMPTS`            | The number of times failing uploads will be retried      |

#### **YAML**
```yaml
integrations:
  ftp:
    enabled: false
    address: ~
    port: ~
    username: ~
    password: ~
    remote_path: /
    encryption_mode: auto
    ignore_certificate_errors: false
    overwrite_existing: true
    connection_timeout: 5000
    retry_attempts: 3
```

### Pushbullet

Pushbullet notifications can be sent when a private message is sent, or the current user's username is mentioned in a chat room. Notifications are prefixed with a user-definable string to differentiate these notifications from others.  

A Pushbullet account must be created, and users must create an API key within the Pushbullet application and configure it through options. Complete documentation for the Pushbullet API, including the latest instructions for obtaining an API key or "Access Token" can be found [here](https://docs.pushbullet.com/).

The Pushbullet integration is one-way, meaning the application cannot know whether a user is active or receiving notifications. To prevent an inappropriate number of notifications from being sent, for example, if a user is carrying on an active conversation, a "cooldown" option is provided to ensure that notifications are sent only after the cooldown has expired. By default, this is every 15 minutes.

Notification API calls are made up to the maximum configured retry count and then discarded.

| Command-Line                          | Environment Variable                         | Description                                                                                        |
| ------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `--pushbullet`                        | `SLSKD_PUSHBULLET`                           | Determines whether Pushbullet integration is enabled                                               |
| `--pushbullet-token`                  | `SLSKD_PUSHBULLET_ACCESS_TOKEN`              | The Pushbullet API access token                                                                    |
| `--pushbullet-prefix`                 | `SLSKD_PUSHBULLET_NOTIFICATION_PREFIX`      | The prefix for notification titles                                                                 |
| `--pushbullet-notify-on-pm`           | `SLSKD_PUSHBULLET_NOTIFY_ON_PRIVATE_MESSAGE` | Determines whether to send a notification when a private message is received                       |
| `--pushbullet-notify-on-room-mention` | `SLSKD_PUSHBULLET_NOTIFY_ON_ROOM_MENTION`    | Determines whether to send a notification when the current user's name is mentioned in a chat room |
| `--pushbullet-retry-attempts`         | `SLSKD_PUSHBULLET_RETRY_ATTEMPTS`            | The number of times failing API calls will be retried                                              |
| `--pushbullet-cooldown`               | `SLSKD_PUSHBULLET_COOLDOWN_TIME`             | The cooldown time for notifications, in milliseconds                                               |

#### **YAML**
```yaml
integrations:
  pushbullet:
    enabled: false
    access_token: ~
    notification_prefix: "From slskdN:"
    notify_on_private_message: true
    notify_on_room_mention: true
    retry_attempts: 3
    cooldown_time: 900000
```

# Other Configuration

## Instance Name

The instance name uniquely identifies the running instance of the application. It is primarily helpful for structured logging in cases where multiple instances are logging to the same remote source.

| Command-Line          | Environment Variable       | Description                              |
| --------------------- | -------------------------- | ---------------------------------------- |
| `-i\|--instance-name` | `SLSKD_INSTANCE_NAME`      | The unique name for the running instance |

#### **YAML**
```yaml
instance_name: default
```

## Logging Options and Configurable Loggers

By default, the application logs to console with colors enabled and writes a rolling log file under `/logs` in the application directory. Disk logs are retained for 30 days. Set `logger.disk` to `false` to disable them, or change `retention.logs` to adjust how many days are kept.

Console colors can be disabled via typical application configuration described below, or by setting the environment variable `NO_COLOR` in accordance with https://no-color.org/.

| Command Line       | Environment Variable           | Description                        |
| ------------------ | ------------------------------ | ---------------------------------- |
| `--disk-logger`    | `SLSKD_DISK_LOGGER`            | Enable logging to disk (enabled by default; set `false` to disable) |
| `--no-color`       | `SLSKD_NO_COLOR` or `NO_COLOR` | Disable console log colors         |

Logs can optionally be forwarded to external services, and the targets can be expanded to any service supported by a [Serilog Sink](https://github.com/serilog/serilog/wiki/Provided-Sinks). Support for targets is added on an as-needed basis and within reason.

The current list of available targets is:

| Command Line       | Environment Variable       | Description                        |
| ------------------ | -------------------------- | ---------------------------------- |
| `--loki`           | `SLSKD_LOKI`               | The URL to a Grafana Loki instance |

#### **YAML**
```yaml
logger:
  loki: ~
  disk: true
  no_color: false
```

## Metrics

The application captures metrics internally and can optionally expose these metrics to be consumed by an instance of Prometheus.  This is a good option for those wanting to tune performance characteristics of the application.

Metrics are disabled by default, and enabling them will make them available at `/metrics`. Authentication is enabled by default, but the password must be set explicitly before the endpoint will start serving authenticated requests.

If the application will be exposed to the internet, it's a good idea to leave this disabled or to set credentials other than the defaults.  Elements of the system configuration, like operating system, architecture, and drive configuration are included and can this can make it easier for an attacker to exploit a vulnerability in your system.

`slskd_enqueue_queue_limit_snapshot_rejections` counts requests rejected from a recent per-user queue snapshot. It helps distinguish repeated queue-limit denials from requests that needed a fresh transfer-history query; it carries no peer labels.


| Command Line         | Environment Variable       | Description                                               |
| -------------------- | -------------------------- | --------------------------------------------------------- |
| `--metrics`          | `SLSKD_METRICS`            | Determines whether the metrics endpoint should be enabled |
| `--metrics-url`      | `SLSKD_METRICS_URL`        | The URL of the metrics endpoint                           |
| `--metrics-no-auth`  | `SLSKD_METRICS_NO_AUTH`    | Disables authentication for the metrics endpoint          |
| `--metrics-username` | `SLSKD_METRICS_USERNAME`   | The username for the metrics endpoint                     |
| `--metrics-password` | `SLSKD_METRICS_PASSWORD`   | The password for the metrics endpoint                     |

#### **YAML**

```yaml
metrics:
  enabled: false
  url: /metrics
  authentication:
    disabled: false
    username: slskd
    password: "" # set a non-empty password before enabling metrics auth
```

## Features

### slskdN experimental feature flags

The slskdN-specific `feature.Mesh`, `feature.Dht`, `feature.Pods`,
`feature.SocialFederation`, `feature.VirtualSoulfind`, and
`feature.MultiSourceDownloads` values gate their controllers/APIs and related
hosted-service activation. `feature.IdentityFriends` gates Identity/Friends
APIs. These networked experimental flags default to true and can be disabled
independently. Automatic LAN advertising has its own default-off setting,
separate from the Identity/Friends API gate:

```yaml
lan_discovery:
  advertise: false # Set true to advertise the local profile over mDNS at startup
```

Nearby-peer browsing remains user-triggered. Metrics and OpenTelemetry tracing
also remain disabled by default. When the metrics endpoint is enabled,
authentication stays on by default; `metrics.authentication.disabled: true`
is an explicit unauthenticated override.

There is no `mesh.enabled` option. Use the actual independent settings such as
`mesh.enable_dht`, `mesh.enable_overlay`, `dht.enabled`, `overlay.enable`, and
`overlay_data.enable`. `feature.Pods: false` prevents Gold Star pod creation,
publication, and enrollment. Gold Star is independently strictly opt-in:
creation, publication, and automatic enrollment require the daemon environment
variable `SLSKDN_POD_GOLD_STAR_CLUB_AUTOJOIN=true` exactly. Missing, malformed,
or non-`true` values leave it dormant.
See [Runtime Feature Gates and Network Defaults](runtime-feature-gating.md) for
the current lifecycle boundary, enabled defaults, and explicit reduction examples.

These settings expose separate layers: public BitTorrent DHT rendezvous finds
mesh overlay endpoints, the slskdN mesh DHT stores bounded metadata, and the
mesh overlay carries control messages and file bytes. See [DHT and Mesh
Architecture](DHT_MESH_ARCHITECTURE.md) for the complete boundary.

### VirtualSoulfind v2 BitTorrent

Torrent acquisition is off by default. To enable it, set
`virtualSoulfindV2.backends.torrent.enabled: true`. The default
`private_only: true` mode removes tracker and web-seed URLs from magnets,
disables BitTorrent DHT and PEX, and admits only peers from the configured
source policy. `allowed_peer_sources` accepts `overlay`, `invite_list`, or
`both`; `invite_list` entries use `host:port`. The standalone resolver fetch
uses invite-list peers because its source records do not carry overlay peer
endpoints. Cross-peer Swarm fallback is currently rejected until sender-side
activation and job cancellation are connected; it does not start a torrent
manager. `private_only` also disables local peer discovery engine-wide, which
affects public-mode torrent transfers in the same process.

```yaml
virtualSoulfindV2:
  backends:
    torrent:
      enabled: false
      min_seeders: 3
      private_only: true
      disable_dht: true
      disable_pex: true
      allowed_peer_sources: both
      invite_list: []
```

Several features have been added that aid in the application's development, debugging, and operation but are generally not valuable for most users.

The application can publish Prometheus metrics to `/metrics` using [prometheus-net](https://github.com/prometheus-net/prometheus-net).  This is especially useful for anyone attempting to tune performance characteristics.

The application can publish a Swagger (OpenAPI) definition and host SwaggerUI at `/swagger` using [Swashbuckle](https://github.com/domaindrivendev/Swashbuckle.AspNetCore).  This is useful for anyone developing against the application API and/or creating a new web interface.

| Command-Line   | Environment Variable       | Description                                                                               |
| -------------- | -------------------------- | ----------------------------------------------------------------------------------------- |
| `--swagger`    | `SLSKD_SWAGGER`            | Determines whether Swagger (OpenAPI) definitions and UI should be available at `/swagger` |

#### **YAML**
```yaml
feature:
  swagger: false
```

## Development Flags

Several additional feature flags are provided to change the application's runtime behavior, which is helpful during development. Available feature flags are:

| Flag                             | Environment Variable                 | Description                                                      |
| -------------------------------- | ------------------------------------ | ---------------------------------------------------------------- |
| `-d\|--debug`                    | `SLSKD_DEBUG`                        | Run the application in debug mode.  Produces verbose log output. |
| `--experimental`                 | `SLSKD_EXPERIMENTAL`                 | Run the application in experimental mode.  YMMV.                 |
| `-n\|--no-logo`                  | `SLSKD_NO_LOGO`                      | Don't show the application logo on startup                       |
| `-x\|--no-start`                 | `SLSKD_NO_START`                     | Bootstrap the application, but don't start                       |
| `--no-config-watch`              | `SLSKD_NO_CONFIG_WATCH`              | Don't watch the configuration file for changes                   |
| `--no-connect`                   | `SLSKD_NO_CONNECT`                   | Start the application, but don't connect to the server           |
| `--no-share-scan`                | `SLSKD_NO_SHARE_SCAN`                | Don't perform a scan of shared directories on startup            |
| `--force-share-scan`             | `SLSKD_FORCE_SHARE_SCAN`             | Force a scan of shared directories on startup                    |
| `--force-migrations`             | `SLSKD_FORCE_MIGRATIONS`             | Force database migrations to be applied on startup               |
| `--no-version-check`             | `SLSKD_NO_VERSION_CHECK`             | Don't perform a version check on startup                         |
| `--log-sql`                      | `SLSKD_LOG_SQL`                      | Log SQL queries generated by Entity Framework                    |
| `--log-unobserved-exceptions`    | `SLSKD_LOG_UNOBSERVED_EXCEPTIONS`    | Log unobserved Exceptions (caution: verbose)                     |
| `--volatile`                     | `SLSKD_VOLATILE`                     | Use volatile data storage (all data will be lost at shutdown)    |
| `--case-sensitive-regex`         | `SLSKD_CASE_SENSITIVE_REGEX`         | User-defined regular expressions are case sensitive              |
| `--legacy-windows-tcp-keepalive` | `SLSKD_LEGACY_WINDOWS_TCP_KEEPALIVE` | Use a legacy TCP keepalive strategy for older Windows versions   |

#### **YAML**
```yaml
debug: false
flags:
  no_logo: false
  no_start: false
  no_config_watch: false
  no_connect: false
  no_share_scan: false
  force_share_scan: false
  force_migrations: false
  no_version_check: false
  log_sql: false
  experimental: false
  volatile: false
  case_sensitive_reg_ex: false
  legacy_windows_tcp_keepalive: false
```

# Commands

The application can be run in "command mode", causing it to execute a command and quit immediately. Available commands are:

| Command                          | Description                                         |
| -------------------------------- | --------------------------------------------------- |
| `-v\|--version`                  | Display the current application version             |
| `-h\|--help`                     | Display available command-line arguments            |
| `-e\|--envars`                   | Display available environment variables             |
| `-g\|--generate-cert`            | Generate an X509 certificate and password for HTTPS |
| `-k\|--generate-secret <length>` | Generate a random secret of the specified length    |

### Legacy Virtual Soulfind bridge

The optional `virtualSoulfind.bridge` listener binds to `127.0.0.1` and requires
authentication by default. Set `bindAddress` to a non-loopback IP only when
`requireAuth` is `true` and `password` contains a strong secret; insecure
non-loopback configurations are rejected at startup. `maxRequestsPerMinute`
and `maxTransfersPerSession` bound work initiated by each legacy connection.
