#!/usr/bin/env python3
from __future__ import annotations
import json
import http.client
import ipaddress
import os
import socket
import ssl
import sys
import tempfile
import time
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "meta" / "manifest.json"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


class _PinnedHttpsConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: tuple, timeout: int) -> None:
        super().__init__(hostname, port=443, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection(self._address, self.timeout)
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _resolve_public_https(url: str) -> tuple[str, tuple, str]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("fixture URLs must use HTTPS without embedded credentials")
    if parsed.port not in (None, 443):
        raise ValueError("fixture URLs must use the standard HTTPS port")

    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("fixture host did not resolve")
    for address in addresses:
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError("fixture host resolves to a non-public address")

    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return parsed.hostname, addresses[0][4], path


def _safe_output_path(relative_path: str) -> Path:
    candidate = ROOT / relative_path
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or PureWindowsPath(relative_path).is_absolute()
        or "\\" in relative_path
        or any(part == ".." for part in relative.parts)
    ):
        raise ValueError("fixture path must remain inside the fixture directory")
    resolved = candidate.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() not in resolved.parents or candidate.is_symlink():
        raise ValueError("fixture path must remain inside the fixture directory")
    return resolved

def download(url: str, out_path: Path, retries: int = 3) -> None:
    try:
        relative_path = out_path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("fixture path must remain inside the fixture directory") from exc
    out_path = _safe_output_path(str(relative_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"OK: already present: {out_path.relative_to(ROOT)}")
        return
    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"DL: {url}")
            hostname, address, request_path = _resolve_public_https(url)
            connection = _PinnedHttpsConnection(hostname, address, timeout=60)
            temporary_path = None
            try:
                connection.request("GET", request_path, headers={"User-Agent": "slskdn-fixtures-fetch/1.0"})
                response = connection.getresponse()
                if response.status != 200:
                    raise OSError(f"fixture download returned HTTP {response.status}")
                if response.length is not None and response.length > MAX_DOWNLOAD_BYTES:
                    raise OSError("fixture download exceeds the size limit")

                with tempfile.NamedTemporaryFile(dir=out_path.parent, delete=False) as output:
                    temporary_path = Path(output.name)
                    total = 0
                    while chunk := response.read(min(1024 * 1024, MAX_DOWNLOAD_BYTES + 1 - total)):
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise OSError("fixture download exceeds the size limit")
                        output.write(chunk)
                os.replace(temporary_path, out_path)
            finally:
                connection.close()
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
            return
        except (OSError, TimeoutError, ValueError) as e:
            if attempt >= retries:
                raise
            wait = 2 * attempt
            print(f"WARN: download failed (attempt {attempt}/{retries}): {e}. Retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)

def main() -> int:
    mf = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for asset in mf.get("assets", []):
        for d in asset.get("download_via_script", []):
            url = d["url"]
            rel = d["path"]
            out = ROOT / rel
            download(url, out)
    print("OK: downloads complete. Run meta/write_checksums.py to (re)generate checksums.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

