#!/usr/bin/env python3
"""Seal application, delivery, and complete W77 evidence bundle checksums."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def write_sums(folder, name):
    path = folder / name
    entries = []
    for item in sorted(folder.rglob('*')):
        if item.is_file() and item != path:
            rel = item.relative_to(folder).as_posix()
            entries.append(f'{hashlib.sha256(item.read_bytes()).hexdigest()}  {rel}')
    path.write_text('\n'.join(entries) + '\n', encoding='utf-8')


write_sums(ROOT / 'application', 'SHA256SUMS.txt')
write_sums(ROOT / 'delivery', 'SHA256SUMS.txt')
write_sums(ROOT, 'SHA256SUMS.txt')
print('Sealed application, delivery, and full W77 evidence bundle.')
