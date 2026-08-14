"""YOUR transform — shape raw source data for the lane you emit on.

Lane 1 (ledger): map source records to event payloads — event type,
amounts in cents, counterparty, and a stable ``external_id`` from the
source system (invoice id, transaction id) for idempotency.

Lane 2 (semantic facts): roll raw observations up to your reporting
cadence (e.g. daily snapshots → monthly values) keyed by concept qname.

Lane 3 (raw graph): write parquet/CSV files matching your graph's
table schemas.
"""

from __future__ import annotations

from typing import Any


def transform(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
  """Turn raw source records into lane-ready payloads.

  Replace with your mapping logic.
  """
  raise NotImplementedError("implement your transform here")
