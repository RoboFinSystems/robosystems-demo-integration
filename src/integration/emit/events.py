"""Lane 1 — ledger events via the SDK's ``create-event-block``.

Send business events (invoices, payments, payroll) from a source the
platform has no adapter for. The platform enforces the accounting
discipline — double-entry balance, the closed-period gate,
capture-then-approve — so this emitter just delivers well-formed
events.

The idempotency convention: always set ``source`` (your registered
source name) and a stable ``external_id`` from the source system.
``(source, external_id)`` is unique on the platform, so re-sending an
event is a no-op and retries are always safe.
"""

from __future__ import annotations

from typing import Any

from robosystems_client.api.extensions_robo_ledger import (
  create_event_block as _create_event_block,
)
from robosystems_client.models import CreateEventBlockRequest
from robosystems_client.types import UNSET

from integration.client import IntegrationClient


def emit_event(
  client: IntegrationClient,
  payload: dict[str, Any],
  *,
  idempotency_key: str | None = None,
) -> dict:
  """Create one event. Payload keys (see ``CreateEventBlockRequest``):

  - ``event_type`` (required) — e.g. ``invoice_issued``, ``bank_transaction``
  - ``event_category`` (required) — e.g. ``sales``, ``purchase``, ``treasury``
  - ``occurred_at`` (required, ISO datetime)
  - ``source`` / ``external_id`` — source is stamped from config if absent
  - ``amount`` (cents, signed; inflows positive) + ``currency``
  - ``agent_id`` — counterparty, when known
  - ``metadata`` — handler-specific payload; use ``preview-event-block``
    to discover the expected shape without writing
  - ``apply_handlers`` — leave False to land in the inbox for operator
    approval (recommended for new integrations)
  """
  payload = {"source": client.config.source_name, **payload}
  if not payload.get("external_id"):
    raise ValueError(
      "external_id is required — a stable source-system id is what makes "
      "re-sends idempotent"
    )
  response = _create_event_block.sync_detailed(
    client.config.graph_id,
    client=client.sdk,
    body=CreateEventBlockRequest.from_dict(payload),
    idempotency_key=idempotency_key if idempotency_key is not None else UNSET,
  )
  return client.unwrap(response)


def emit_events(
  client: IntegrationClient, payloads: list[dict[str, Any]]
) -> list[dict]:
  """Create a batch of events, one call per event (the intended import
  path — per-event creation keeps handler validation and idempotency
  per record)."""
  return [emit_event(client, p) for p in payloads]
