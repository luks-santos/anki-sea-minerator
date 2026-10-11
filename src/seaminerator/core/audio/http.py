from __future__ import annotations

from typing import Any

import httpx

from .base import AudioError


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
    try:
        response = client.post(url, **kwargs)
    except httpx.TimeoutException as exc:
        raise AudioError(f"{source} did not answer in time", source_down=True) from exc
    except httpx.HTTPError as exc:
        raise AudioError(
            f"could not connect to {source} ({exc})", source_down=True
        ) from exc

    status = response.status_code
    if status < 400:
        return response
    if status in (401, 403):
        hint = "; check the API key in Sea Minerator settings" if key_hint else ""
        message = f"{source} refused the request (HTTP {status}){hint}"
    elif status == 429:
        message = f"{source} quota or rate limit exceeded (HTTP 429)"
    elif status >= 500:
        message = f"{source} is unavailable (HTTP {status})"
    else:
        message = (
            f"{source} rejected the request (HTTP {status}): {response.text[:200]}"
        )
    raise AudioError(message, source_down=True)
