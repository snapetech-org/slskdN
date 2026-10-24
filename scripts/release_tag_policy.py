#!/usr/bin/env python3
"""Validate canonical v<SemVer> release tags and map package-specific tags."""

from __future__ import annotations

import re
import sys


_NUMBER = r"(?:0|[1-9][0-9]*)"
_PRERELEASE_ID = rf"(?:{_NUMBER}|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
TAG_RE = re.compile(
    rf"^(?=.{{1,128}}$)v{_NUMBER}\.{_NUMBER}\.{_NUMBER}"
    rf"(?:-{_PRERELEASE_ID}(?:\.{_PRERELEASE_ID})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
DATE_PACKAGE_TAG_RE = re.compile(
    r"^v([0-9]{8,10})\.0\.0\+slskdn\.([0-9]+)$"
)


def release_version(tag: str) -> str:
    """Return the package version for a strict SemVer release tag."""
    if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
        raise ValueError("release tags must be strict v<SemVer> tags")
    date_build = DATE_PACKAGE_TAG_RE.fullmatch(tag)
    if date_build:
        return f"{date_build.group(1)}-slskdn.{date_build.group(2)}"
    return tag[1:]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: release_tag_policy.py <tag>")
    try:
        print(release_version(sys.argv[1]))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
