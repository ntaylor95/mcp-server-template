"""SharePoint authentication.

Three modes, selected by AUTH_MODE env var:

  obo          On-Behalf-Of flow (production). The SSE transport reads the
               caller's Bearer token from the Authorization header and stores
               it in a ContextVar. Each tool call exchanges it for a
               Graph-scoped token via Azure AD OBO. Requires
               AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET and
               an Azure app registration with Sites.Read.All (delegated).

  interactive  Browser-based MSAL flow (default for local dev). Opens a
               browser window on first call; subsequent calls use a cached
               token. Requires AZURE_TENANT_ID and AZURE_CLIENT_ID.

  device_code  Device code flow for headless dev environments (CI, SSH).
               Prints a URL + code; subsequent calls use the cached token.
               Requires AZURE_TENANT_ID and AZURE_CLIENT_ID.
"""

import contextvars
import os
from pathlib import Path

import msal

SCOPES = ["https://graph.microsoft.com/Sites.Read.All"]

_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
_AUTH_MODE = os.environ.get("AUTH_MODE", "interactive")

# Token cache path for dev flows (interactive / device_code).
# Contains serialized MSAL token cache — keep this file private.
_TOKEN_CACHE_PATH = Path.home() / ".mcp_policy_kb_tokens"

# Per-request context variable set by the SSE transport before each
# server.run() call. The OBO flow reads from here.
_user_token_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_token", default=None
)

# Module-level OBO app instance (created once, thread-safe for token exchange).
_obo_app: msal.ConfidentialClientApplication | None = None


class AuthError(Exception):
    pass


def set_user_token(token: str | None) -> None:
    """Called by the SSE transport to propagate the caller's Bearer token."""
    _user_token_var.set(token)


def get_sharepoint_token() -> str:
    """Return a Graph-scoped access token for the current request context."""
    match _AUTH_MODE:
        case "obo":
            return _obo_exchange()
        case "device_code":
            return _device_code()
        case _:
            return _interactive()


# ---------------------------------------------------------------------------
# Production: On-Behalf-Of
# ---------------------------------------------------------------------------

def _obo_exchange() -> str:
    """Exchange the caller's token for a Graph-scoped token via OBO."""
    user_token = _user_token_var.get()
    if not user_token:
        raise AuthError(
            "OBO mode requires a Bearer token in the Authorization header. "
            "Set AUTH_MODE=interactive for local dev."
        )
    app = _get_obo_app()
    result = app.acquire_token_on_behalf_of(
        user_assertion=user_token,
        scopes=SCOPES,
    )
    _raise_if_error(result, "OBO token exchange failed")
    return result["access_token"]


def _get_obo_app() -> msal.ConfidentialClientApplication:
    global _obo_app
    if _obo_app is None:
        _require_env("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
        _obo_app = msal.ConfidentialClientApplication(
            client_id=_CLIENT_ID,
            client_credential=_CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{_TENANT_ID}",
        )
    return _obo_app


# ---------------------------------------------------------------------------
# Dev: interactive browser
# ---------------------------------------------------------------------------

def _interactive() -> str:
    _require_env("AZURE_TENANT_ID", "AZURE_CLIENT_ID")
    cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id=_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{_TENANT_ID}",
        token_cache=cache,
    )
    result = _try_silent(app, cache)
    if result:
        return result

    result = app.acquire_token_interactive(scopes=SCOPES)
    _raise_if_error(result, "Interactive auth failed")
    _save_cache(cache)
    return result["access_token"]


# ---------------------------------------------------------------------------
# Dev: device code (headless)
# ---------------------------------------------------------------------------

def _device_code() -> str:
    _require_env("AZURE_TENANT_ID", "AZURE_CLIENT_ID")
    cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id=_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{_TENANT_ID}",
        token_cache=cache,
    )
    result = _try_silent(app, cache)
    if result:
        return result

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise AuthError(f"Device flow initiation failed: {flow.get('error_description')}")
    print(flow["message"])  # Prints the https://microsoft.com/devicelogin URL + code
    result = app.acquire_token_by_device_flow(flow)
    _raise_if_error(result, "Device code auth failed")
    _save_cache(cache)
    return result["access_token"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _try_silent(
    app: msal.PublicClientApplication,
    cache: msal.SerializableTokenCache,
) -> str | None:
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        _save_cache(cache)
        return result["access_token"]
    return None


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if _TOKEN_CACHE_PATH.exists():
        cache.deserialize(_TOKEN_CACHE_PATH.read_text())
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        _TOKEN_CACHE_PATH.write_text(cache.serialize())
        _TOKEN_CACHE_PATH.chmod(0o600)  # owner read/write only


def _require_env(*names: str) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise AuthError(f"Missing required env vars: {', '.join(missing)}")


def _raise_if_error(result: dict, context: str) -> None:
    if "access_token" not in result:
        detail = result.get("error_description") or result.get("error") or "unknown error"
        raise AuthError(f"{context}: {detail}")
