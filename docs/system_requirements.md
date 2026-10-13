# System Requirements

Designed to run on a minimum of a Raspberry Pi 2 (or equivalent), or any system with:

* x86, x86_64, amd64, or ARMv7+ processor
* at least 512mb RAM
* enough disk space for the application package and its runtime dependencies

Users concerned about optimal performance should consider something faster.

## Storage and filesystems

The application package size varies by platform and install method. Allow
additional space for the application database, retained logs, transfer history,
incomplete and completed downloads, and shared files. The amount depends on
your library, transfer activity, and retention settings.

Keep the writable application data directory on persistent storage with
reliable file locking. slskdN uses SQLite databases with write-ahead logging,
so network filesystems can affect database locking and recovery. For Docker,
persist `/app` as the application data directory; see the
[Docker guide](docker.md) for the container layout.

Download and shared-file directories can be mounted separately from
application data. Make sure those mounts stay available and grant the service
the required read or write access. Network-storage interruptions or permission
changes can interrupt scans and transfers; see
[Docker download permissions](docker-download-permissions.md) for mount and
NAS guidance.
