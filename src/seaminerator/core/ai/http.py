from __future__ import annotations

from typing import Any

import httpx

from .base import OUTSIDE_FORMAT_MESSAGE, AIError


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    provider: str,
    base_url: str,
    headers: dict[str, str],
    body: dict | None = None,
) -> Any:
    # `Any` because provider bodies are only ever inspected inside
    # try/except blocks that turn a shape mismatch into AIError.
    try:
        response = client.request(method, url, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        # The server was reached (and may bill the tokens); it was just slow.
        raise AIError(
            f"{provider} did not answer in time; mine fewer words at a time "
            "or pick a faster model"
        ) from exc
    except httpx.HTTPError as exc:
        raise AIError(
            f"could not connect to {base_url}; for a local provider, check that "
            f"Ollama or LM Studio is running ({exc})"
        ) from exc

    if response.status_code >= 400:
        detail = _error_detail(response)
        if response.status_code in (401, 403):
            raise AIError(
                f"invalid or unauthorized API key for {provider}; check it in "
                f"Sea Minerator settings: {detail}"
            )
        if response.status_code == 429:
            raise AIError(f"{provider} quota or rate limit exceeded: {detail}")
        raise AIError(f"{provider} API error {response.status_code}: {detail}")

    try:
        return response.json()
    except ValueError as exc:
        raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc


def _error_detail(response: httpx.Response) -> str:
    # Gemini, OpenAI and Anthropic all document {"error": {"message": ...}}.
    # Anything else (non-JSON, a JSON list, a bare string under "error")
    # falls back to the raw body instead of raising from `.get`.
    detail = response.text[:200]
    try:
        body = response.json()
    except ValueError:
        return detail
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    return detail
