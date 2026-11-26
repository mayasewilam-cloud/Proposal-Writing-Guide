"""
Lightweight Vercel Blob Storage adapter for BioWriter Studio.

Automatically activates when BLOB_READ_WRITE_TOKEN is configured in the
environment (e.g., on Vercel Serverless). Falls back cleanly to local/tmp
filesystem storage when running locally or in unit tests.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
import requests

BLOB_API_BASE = "https://blob.vercel-storage.com"
BLOB_API_VERSION = "12"
BLOB_NAMESPACE = "biowriter"
LAST_BLOB_DIAG: Dict[str, Any] = {}


def is_blob_enabled() -> bool:
    """Return True when Vercel Blob storage is configured via BLOB_READ_WRITE_TOKEN."""
    return bool(os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip())


def _auth_headers() -> Dict[str, str]:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
    return {
        "Authorization": f"Bearer {token}",
        "x-api-version": BLOB_API_VERSION,
    }


def _namespaced(pathname: str) -> str:
    clean = pathname.lstrip("/")
    if not clean.startswith(f"{BLOB_NAMESPACE}/"):
        return f"{BLOB_NAMESPACE}/{clean}"
    return clean


def blob_list_prefix(prefix: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
    """List blobs matching a prefix in Vercel Blob storage."""
    if not is_blob_enabled():
        return []
    full_prefix = _namespaced(prefix)
    try:
        resp = requests.get(
            BLOB_API_BASE,
            params={"prefix": full_prefix, "limit": 1000},
            headers=_auth_headers(),
            timeout=timeout,
        )
        if resp.ok:
            payload = resp.json()
            return payload.get("blobs", []) if isinstance(payload, dict) else []
        print(f"[blob_store] LIST failed ({resp.status_code}): {resp.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"[blob_store] LIST exception: {e}", file=sys.stderr)
    return []


def blob_get_json(pathname: str, timeout: float = 10.0) -> Optional[Any]:
    """Fetch and parse a JSON blob by exact pathname, or return None if missing."""
    if not is_blob_enabled():
        return None
    full_path = _namespaced(pathname)
    blobs = blob_list_prefix(full_path, timeout=timeout)
    matches = [b for b in blobs if b.get("pathname") == full_path]
    if not matches:
        return None
    matches.sort(key=lambda b: b.get("uploadedAt", ""), reverse=True)
    url = matches[0].get("url")
    if not url:
        return None
    sep = "&" if "?" in url else "?"
    fresh_url = f"{url}{sep}cb={int(time.time() * 1000)}"
    try:
        resp = requests.get(
            fresh_url,
            headers={**_auth_headers(), "Cache-Control": "no-cache"},
            timeout=timeout,
        )
        if not resp.ok:
            resp = requests.get(fresh_url, headers={"Cache-Control": "no-cache"}, timeout=timeout)
        LAST_BLOB_DIAG["get_status"] = resp.status_code
        if resp.ok:
            return resp.json()
        LAST_BLOB_DIAG["get_body"] = resp.text[:250]
        print(f"[blob_store] GET {full_path} failed ({resp.status_code}): {resp.text[:200]}", file=sys.stderr)
    except Exception as e:
        LAST_BLOB_DIAG["get_exception"] = str(e)
        print(f"[blob_store] GET {full_path} exception: {e}", file=sys.stderr)
    return None


def blob_put_json(pathname: str, data: Any, timeout: float = 15.0) -> bool:
    """Upload JSON data to Vercel Blob storage, overwriting if present."""
    if not is_blob_enabled():
        return False
    full_path = _namespaced(pathname)
    body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    url = f"{BLOB_API_BASE}/{full_path}"
    base_headers = {
        **_auth_headers(),
        "Content-Type": "application/json",
        "x-content-type": "application/json",
        "x-add-random-suffix": "0",
        "x-allow-overwrite": "1",
    }
    for extra in ({"x-vercel-blob-access": "private"}, {"x-vercel-blob-access": "public"}, {}):
        try:
            resp = requests.put(url, data=body, headers={**base_headers, **extra}, timeout=timeout)
            LAST_BLOB_DIAG["put_status"] = resp.status_code
            LAST_BLOB_DIAG["put_body"] = resp.text[:250]
            if resp.ok:
                return True
            print(f"[blob_store] PUT {full_path} ({extra or 'default'}) failed ({resp.status_code}): {resp.text[:200]}", file=sys.stderr)
        except Exception as e:
            LAST_BLOB_DIAG["put_exception"] = str(e)
            print(f"[blob_store] PUT {full_path} exception: {e}", file=sys.stderr)
    return False


def blob_delete(pathname: str, timeout: float = 10.0) -> bool:
    """Delete a blob by exact pathname if it exists."""
    if not is_blob_enabled():
        return False
    full_path = _namespaced(pathname)
    blobs = blob_list_prefix(full_path, timeout=timeout)
    urls = [b.get("url") for b in blobs if b.get("pathname") == full_path and b.get("url")]
    if not urls:
        return False
    try:
        resp = requests.post(
            f"{BLOB_API_BASE}/delete",
            json={"urls": urls},
            headers={**_auth_headers(), "Content-Type": "application/json"},
            timeout=timeout,
        )
        if not resp.ok:
            resp = requests.delete(
                BLOB_API_BASE,
                json={"urls": urls},
                headers={**_auth_headers(), "Content-Type": "application/json"},
                timeout=timeout,
            )
        return resp.ok
    except Exception as e:
        print(f"[blob_store] DELETE {full_path} exception: {e}", file=sys.stderr)
        return False
