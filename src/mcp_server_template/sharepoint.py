"""SharePoint document access via Microsoft Graph API.

Reads configuration from env vars (see .env.example):
  SHAREPOINT_SITE_URL        Full URL of the SharePoint site
  SHAREPOINT_POLICIES_FOLDER Folder path relative to the Shared Documents drive root

Tokens come from auth.get_sharepoint_token() — see auth.py for AUTH_MODE options.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import httpx

from mcp_server_template import auth

_GRAPH = "https://graph.microsoft.com/v1.0"

_SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "")
_POLICIES_FOLDER = os.environ.get("SHAREPOINT_POLICIES_FOLDER", "")

# Graph fields requested on every item listing.
_ITEM_SELECT = ",".join([
    "id",
    "name",
    "size",
    "lastModifiedDateTime",
    "eTag",
    "@microsoft.graph.downloadUrl",
    "webUrl",
    "file",
    "deleted",
])

# Cached site ID — resolved once on first request, shared across all calls.
_site_id: str | None = None
_site_id_lock = asyncio.Lock()


class SharePointError(Exception):
    pass


@dataclass
class PolicyFile:
    id: str                 # Graph drive item ID — store in Milvus for later re-fetch
    name: str
    size: int               # bytes
    last_modified: datetime # UTC
    etag: str               # use for conditional re-fetch (If-None-Match)
    download_url: str       # pre-auth URL (~1h TTL) — use for file content
    web_url: str            # SharePoint browser URL — include in answers as source citation
    mime_type: str | None


@dataclass
class DeltaResult:
    changed: list[PolicyFile]   # new or modified files
    deleted_ids: list[str]      # item IDs removed from the folder
    delta_link: str             # opaque URL — pass back to get_delta() on next call


async def list_policy_files() -> list[PolicyFile]:
    """Return all files currently in the configured policy folder."""
    site_id = await _get_site_id()
    folder = _folder_path()
    url = f"{_GRAPH}/sites/{site_id}/drive/root:/{folder}:/children"

    files: list[PolicyFile] = []
    params: dict | None = {"$select": _ITEM_SELECT}

    while url:
        data = await _get(url, params=params)
        params = None  # nextLink already carries params
        for item in data.get("value", []):
            if "file" in item:  # skip subfolders
                files.append(_parse_item(item))
        url = data.get("@odata.nextLink")

    return files


async def download_file(item_id: str) -> bytes:
    """Download the raw content of a drive item by ID.

    Always fetches fresh metadata first to get a current pre-auth download URL.
    The caller's SSO credentials gate this call via auth.get_sharepoint_token().
    """
    site_id = await _get_site_id()
    meta = await _get(
        f"{_GRAPH}/sites/{site_id}/drive/items/{item_id}",
        params={"$select": "@microsoft.graph.downloadUrl"},
    )

    download_url = meta.get("@microsoft.graph.downloadUrl")
    if not download_url:
        raise SharePointError(f"No download URL for item {item_id!r} — check permissions")

    # Pre-auth URL needs no Authorization header
    async with httpx.AsyncClient() as client:
        resp = await client.get(download_url, follow_redirects=True)
        _raise_for_status(resp)
        return resp.content


async def get_delta(delta_link: str | None = None) -> DeltaResult:
    """Detect changes in the policy folder.

    First call (delta_link=None): returns all files + an initial delta_link.
    Subsequent calls: pass the delta_link from the previous result to get only
    files added, modified, or deleted since that checkpoint.

    Store delta_link in persistent storage (e.g. a file or Milvus metadata)
    between ingestion runs.
    """
    if delta_link:
        # Use the full URL from the previous call — it encodes the sync state.
        url: str | None = delta_link
        params: dict | None = None
    else:
        site_id = await _get_site_id()
        folder = _folder_path()
        url = f"{_GRAPH}/sites/{site_id}/drive/root:/{folder}:/delta"
        params = {"$select": _ITEM_SELECT}

    changed: list[PolicyFile] = []
    deleted_ids: list[str] = []
    final_delta_link = ""

    while url:
        data = await _get(url, params=params)
        params = None

        for item in data.get("value", []):
            if "deleted" in item:
                deleted_ids.append(item["id"])
            elif "file" in item:
                changed.append(_parse_item(item))

        if "@odata.deltaLink" in data:
            final_delta_link = data["@odata.deltaLink"]
            url = None
        else:
            url = data.get("@odata.nextLink")

    return DeltaResult(changed=changed, deleted_ids=deleted_ids, delta_link=final_delta_link)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_site_id() -> str:
    global _site_id
    if _site_id:
        return _site_id

    async with _site_id_lock:
        if _site_id:  # another coroutine resolved it while we waited
            return _site_id

        if not _SITE_URL:
            raise SharePointError("SHAREPOINT_SITE_URL is not configured")

        parsed = urlparse(_SITE_URL)
        host = parsed.hostname
        path = parsed.path.rstrip("/")

        data = await _get(f"{_GRAPH}/sites/{host}:{path}")
        _site_id = data["id"]
        return _site_id


async def _get(url: str, params: dict | None = None) -> dict:
    # MSAL token acquisition is synchronous; run in a thread to avoid blocking.
    token = await asyncio.to_thread(auth.get_sharepoint_token)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        _raise_for_status(resp)

    return resp.json()


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        err = resp.json().get("error", {})
        msg = err.get("message") or resp.text
        code = err.get("code", str(resp.status_code))
    except Exception:
        msg, code = resp.text, str(resp.status_code)

    if resp.status_code == 401:
        raise auth.AuthError(f"SharePoint auth rejected: {msg}")
    if resp.status_code == 403:
        raise SharePointError(f"Access denied (check Sites.Read.All permission): {msg}")
    if resp.status_code == 404:
        raise SharePointError(f"Not found ({code}): {msg}")
    raise SharePointError(f"Graph API error {code}: {msg}")


def _parse_item(item: dict) -> PolicyFile:
    return PolicyFile(
        id=item["id"],
        name=item["name"],
        size=item.get("size", 0),
        last_modified=datetime.fromisoformat(item["lastModifiedDateTime"]),
        etag=item.get("eTag", ""),
        download_url=item.get("@microsoft.graph.downloadUrl", ""),
        web_url=item.get("webUrl", ""),
        mime_type=item.get("file", {}).get("mimeType"),
    )


def _folder_path() -> str:
    if not _POLICIES_FOLDER:
        raise SharePointError("SHAREPOINT_POLICIES_FOLDER is not configured")
    return _POLICIES_FOLDER.strip("/")
