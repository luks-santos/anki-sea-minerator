from __future__ import annotations

import time
from typing import Any

import httpx

from .base import AudioError

# A rate limit or a server hiccup often clears in seconds, so it gets two more
# tries; the server's own wait wins over the backoff when it names one.
_BACKOFF = (1.0, 2.0)
# Longer than this is a spent quota, not a hiccup: stop instead of waiting.
_MAX_WAIT = 30.0
_sleep = time.sleep


def post(
    client: httpx.Client,
    url: str,
    *,
    source: str,
    key_hint: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    # Every failure here would repeat for the next sentence, so all of them
    # are source failures: the run stops instead of waiting on each card.
    for attempt in range(len(_BACKOFF) + 1):
        response = _send(client, url, source, kwargs)
        status = response.status_code
        if status < 400:
            return response
        retryable = status == 429 or status >= 500
        if not retryable or attempt == len(_BACKOFF):
            break
        wait = _server_wait(response)
        if wait is None:
            wait = _BACKOFF[attempt]
        # Also refuses a negative or NaN wait, which `sleep` would raise on.
        if not 0 <= wait <= _MAX_WAIT:
            break
        _sleep(wait)
    raise AudioError(_failure(response, source, key_hint), source_down=True)


def _send(
    client: httpx.Client, url: str, source: str, kwargs: dict[str, Any]
) -> httpx.Response:
    try:
        return client.post(url, **kwargs)
    except httpx.TimeoutException as exc:
        raise AudioError(f"{source} did not answer in time", source_down=True) from exc
    except httpx.HTTPError as exc:
        raise AudioError(
            f"could not connect to {source} ({exc})", source_down=True
        ) from exc


def _failure(response: httpx.Response, source: str, key_hint: bool) -> str:
    status = response.status_code
    message = _server_message(response)
    said = f": {message}" if message else ""
    if status in (401, 403):
        hint = "; check the API key in Sea Minerator settings" if key_hint else ""
        return f"{source} refused the request (HTTP {status}){said}{hint}"
    if status == 429:
        return f"{source} quota or rate limit exceeded (HTTP 429){said}"
    if status >= 500:
        return f"{source} is unavailable (HTTP {status}){said}"
    return (
        f"{source} rejected the request (HTTP {status}): "
        f"{message or response.text[:200]}"
    )


def _error_body(response: httpx.Response) -> dict:
    # Gemini answers {"error": {"message": ..., "details": [...]}}; Google
    # Translate answers an HTML page, which has nothing worth showing.
    try:
        body = response.json()
    except ValueError:
        return {}
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, dict) else {}


def _server_message(response: httpx.Response) -> str:
    message = _error_body(response).get("message")
    # Without its period, so it reads inside a longer note.
    return message.strip().rstrip(".") if isinstance(message, str) else ""


def _server_wait(response: httpx.Response) -> float | None:
    """Seconds the server asked to wait before retrying, if it said."""
    header = response.headers.get("Retry-After", "")
    try:
        return float(header)
    except ValueError:
        pass
    details = _error_body(response).get("details")
    for detail in details if isinstance(details, list) else []:
        delay = detail.get("retryDelay") if isinstance(detail, dict) else None
        if isinstance(delay, str) and delay.endswith("s"):
            try:
                return float(delay[:-1])
            except ValueError:
                return None
    return None
