from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from contextiq_ingestion.models import SourceSpec

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; ContextIQ-Ingestion/0.1; +https://github.com/contextiq; research/portfolio)"
)


class FetchError(RuntimeError):
    pass


def extension_for(source: SourceSpec) -> str:
    mapping = {
        "html": ".html",
        "markdown": ".md",
        "mdx": ".mdx",
        "pdf": ".pdf",
    }
    return mapping.get(source.format.value, ".bin")


def raw_path_for(raw_dir: Path, source: SourceSpec) -> Path:
    family = source.family or "misc"
    return raw_dir / family / f"{source.id}{extension_for(source)}"


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _download(url: str, timeout: float = 45.0) -> httpx.Response:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = client.get(url)
        if response.status_code == 404:
            raise FetchError(f"404 Not Found: {url}")
        if response.status_code >= 400:
            raise FetchError(f"HTTP {response.status_code} for {url}")
        return response


def fetch_source(
    source: SourceSpec,
    raw_dir: Path,
    *,
    force: bool = False,
) -> Path:
    """Download a source into the raw zone. Returns path to raw file."""
    dest = raw_path_for(raw_dir, source)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force and dest.stat().st_size > 0:
        logger.info("skip fetch (cached): %s", source.id)
        return dest

    url = source.download_url()
    logger.info("fetching %s ← %s", source.id, url)
    try:
        response = _download(url)
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f"Failed to fetch {source.id} from {url}: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    if source.format.value == "pdf" or "application/pdf" in content_type:
        dest.write_bytes(response.content)
    else:
        # Prefer decoded text; fall back to bytes decoded as utf-8
        text = response.text
        dest.write_text(text, encoding="utf-8")

    digest = hashlib.sha256(dest.read_bytes()).hexdigest()[:16]
    logger.info("wrote raw %s (%s bytes, sha256=%s)", dest, dest.stat().st_size, digest)
    return dest
