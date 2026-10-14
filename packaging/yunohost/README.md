# YunoHost packaging

The package tree lives in `packaging/yunohost/slskdn_ynh` and is mirrored in
[`YunoHost-Apps/slskdn_ynh`](https://github.com/YunoHost-Apps/slskdn_ynh).
That repository contains the YunoHost packaging files, not the slskdN
application source. Its manifest downloads checksum-pinned, self-contained
Linux release bundles from the [slskdN releases](https://github.com/snapetech-org/slskdN/releases).

YunoHost's catalog expects an app package to have its own repository. The
catalog tracks the `testing` branch while maintainers review and validate the
package; do not change its catalog entry to `main` until the package is ready
for regular use.

After installing the repository hooks with `./scripts/setup-git-hooks.sh`, a
push of `main` that changes the package tree syncs only that subtree to the
`testing` branch. To retry or sync it manually from the repository root, run:

    ./scripts/sync-yunohost-package.sh

Review package changes and run the YunoHost package linter before pushing them.
Full install, upgrade, backup, restore, and URL-change checks should run through
YunoHost package_check or the YunoHost app CI. The sync hook does not promote
the package to `main` or trigger CI; use the package repository PR workflow for
those steps.
