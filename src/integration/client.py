"""Integration handle: the RoboSystems SDK client + this integration's identity.

The [`robosystems-client`](https://pypi.org/project/robosystems-client/)
SDK is the interface to the platform — typed request/response models and
one generated function per operation (`robosystems_client.api.*`). This
module wires it up with API-key auth and adds two small things the SDK
doesn't carry:

- ``raw_operation`` — call an operation the generated SDK doesn't have
  a function for *yet* (brand-new endpoints land in the SDK on its next
  regeneration; until then the same authenticated HTTP client reaches
  them directly).
- ``unwrap`` — turn a generated ``sync_detailed`` response into the
  operation-envelope dict, raising :class:`IntegrationAPIError` on HTTP
  or envelope errors.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from robosystems_client import AuthenticatedClient

from integration.config import Config


class IntegrationAPIError(RuntimeError):
  """An operation failed — HTTP error or an error in the envelope."""


class IntegrationClient:
  def __init__(self, config: Config, *, timeout: float = 60.0) -> None:
    self.config = config
    self.sdk = AuthenticatedClient(
      base_url=config.api_url,
      token=config.api_key,
      prefix="",
      auth_header_name="X-API-Key",
      timeout=httpx.Timeout(timeout),
    )

  # ── envelope plumbing ───────────────────────────────────────────────

  @staticmethod
  def unwrap(response: Any) -> dict:
    """Check a generated ``sync_detailed`` response; return the envelope dict."""
    status = int(response.status_code)
    if status >= 400:
      raise IntegrationAPIError(
        f"HTTP {status}: {response.content[:500].decode(errors='replace')}"
      )
    envelope: dict = json.loads(response.content or b"{}")
    if envelope.get("error"):
      raise IntegrationAPIError(str(envelope["error"]))
    return envelope

  def raw_operation(
    self, path: str, payload: dict, *, idempotency_key: str | None = None
  ) -> dict:
    """POST an operation not yet in the generated SDK, same auth + envelope."""
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    response = self.sdk.get_httpx_client().post(path, json=payload, headers=headers)
    if response.status_code >= 400:
      raise IntegrationAPIError(
        f"{path} -> HTTP {response.status_code}: {response.text[:500]}"
      )
    envelope: dict = response.json()
    if envelope.get("error"):
      raise IntegrationAPIError(f"{path} -> {envelope['error']}")
    return envelope

  def graphql(self, query: str, variables: dict | None = None) -> dict:
    """POST /extensions/{graph}/graphql — typed reads over what you wrote."""
    response = self.sdk.get_httpx_client().post(
      f"/extensions/{self.config.graph_id}/graphql",
      json={"query": query, "variables": variables or {}},
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
      raise IntegrationAPIError(f"GraphQL errors: {body['errors']}")
    return body.get("data") or {}

  def upload_presigned(self, url: str, content: bytes, content_type: str) -> None:
    """PUT file bytes to a presigned S3 URL (no API auth headers)."""
    response = httpx.put(
      url, content=content, headers={"Content-Type": content_type}, timeout=300.0
    )
    response.raise_for_status()

  def close(self) -> None:
    self.sdk.get_httpx_client().close()
