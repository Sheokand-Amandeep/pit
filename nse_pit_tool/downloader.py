
"""Concurrent XBRL XML downloader with local caching."""

from __future__ import annotations
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import time
import requests

from config import XML_WORKERS, REQUEST_TIMEOUT, MAX_RETRIES, DEFAULT_HEADERS


def _filename(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest() + ".xml"


def download_one(session: requests.Session, url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return destination

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            destination.write_bytes(response.content)
            return destination
        except Exception as exc:
            last_error = exc
            time.sleep(attempt)

    raise RuntimeError(f"Failed to download XML: {last_error}")


def download_xml_files(records: list[dict], cache_dir: Path) -> dict[str, Path]:
    urls = list(dict.fromkeys(
        record.get("xmlFileName") for record in records if record.get("xmlFileName")
    ))
    result: dict[str, Path] = {}
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    def worker(url: str):
        return url, download_one(session, url, cache_dir / _filename(url))

    with ThreadPoolExecutor(max_workers=XML_WORKERS) as executor:
        futures = [executor.submit(worker, url) for url in urls]
        for future in as_completed(futures):
            url, path = future.result()
            result[url] = path

    return result
