#!/usr/bin/env python3
"""Seal every W77 cross-audit packet file with a SHA-256 manifest."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMS = ROOT / 'SHA256SUMS.txt'

entries = []
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or path == SUMS:
        continue
    rel = path.relative_to(ROOT).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entries.append(f'{digest}  {rel}')
SUMS.write_text('\n'.join(entries) + '\n', encoding='utf-8')
print(f'Sealed {len(entries)} files in {SUMS}')
