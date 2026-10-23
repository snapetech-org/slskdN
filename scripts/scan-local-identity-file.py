#!/usr/bin/env python3
"""Scan one release-facing text file without printing matched content."""

import argparse
import re
import sys
from pathlib import Path


MAX_SCAN_BYTES = 16 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens-file", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--display-path", required=True)
    parser.add_argument("--whole-words", action="store_true")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()

    try:
        tokens = [token for token in args.tokens_file.read_text(encoding="utf-8").splitlines() if token]
        if args.file.is_symlink():
            raise OSError("symbolic links are not scanned")
        size = args.file.stat().st_size
        if size > MAX_SCAN_BYTES:
            raise OSError(f"file exceeds the {MAX_SCAN_BYTES}-byte scan limit")
        contents = args.file.read_bytes()
        if b"\0" in contents:
            raise OSError("binary file is outside the text scan contract")
        lines = contents.decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        print(f"{args.label}: {args.display_path}: unable to scan file ({error})", file=sys.stderr)
        return 2

    patterns = []
    for token in tokens:
        if args.whole_words:
            patterns.append(re.compile(r"(?<!\w)" + re.escape(token) + r"(?!\w)", re.IGNORECASE))
        else:
            patterns.append(token.casefold())

    matches = []
    for line_number, line in enumerate(lines, start=1):
        folded_line = line.casefold()
        if any(
            pattern.search(line) if args.whole_words else pattern in folded_line
            for pattern in patterns
        ):
            matches.append(line_number)

    for line_number in matches:
        print(f"{args.label}: {args.display_path}:{line_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
