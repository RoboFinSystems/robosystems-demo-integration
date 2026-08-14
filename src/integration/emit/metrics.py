"""Lane 2 — semantic fact series: vocabulary + asserted observations.

Two steps, done at very different cadences:

1. **Author the vocabulary once** (``create-taxonomy-block``): your
   concepts, display names, and presentation order, as a
   ``block_type='metric'`` structure with no Derive rules. Re-run only
   when the catalog changes.
2. **Assert observations per period** (``assert-metrics``): observed
   values keyed by concept qname. Re-asserting a period replaces its
   values, so the call is safe to re-run — and backfill is one loop
   over your raw history.

The platform renders the series everywhere (envelopes, charts, fact
grids, GraphQL, MCP) with no further work.
"""

from __future__ import annotations

from datetime import date

from robosystems_client.api.extensions_robo_ledger import (
  assert_metrics as _assert_metrics,
)
from robosystems_client.api.extensions_robo_ledger import (
  create_taxonomy_block as _create_taxonomy_block,
)
from robosystems_client.models import AssertMetricsRequest, CreateTaxonomyBlockRequest
from robosystems_client.types import UNSET

from integration.client import IntegrationClient


def author_metric_structure(
  client: IntegrationClient,
  *,
  name: str,
  parent_taxonomy_id: str,
  abstract_qname: str,
  concepts: list[dict],
  description: str | None = None,
) -> dict:
  """Create the metric vocabulary + structure (run once).

  ``concepts``: ``[{"qname", "name", "period_type"}]`` — use
  ``period_type='instant'`` for point-in-time counts (followers at
  month end) and ``'duration'`` for windowed totals (downloads per
  month). Find ``parent_taxonomy_id`` via GraphQL:
  ``{ taxonomies(taxonomyType: "reporting_standard") { taxonomies { id standard } } }``.
  """
  payload = {
    "name": f"{name} Extension",
    "taxonomy_type": "reporting_extension",
    "parent_taxonomy_id": parent_taxonomy_id,
    "description": description,
    "elements": [
      {
        "qname": abstract_qname,
        "name": name,
        "element_type": "abstract",
        "period_type": "duration",
        "is_monetary": False,
      },
      *(
        {
          "qname": c["qname"],
          "name": c["name"],
          "element_type": "concept",
          "period_type": c.get("period_type", "instant"),
          "is_monetary": c.get("is_monetary", False),
          "balance_type": c.get("balance_type", "debit"),
        }
        for c in concepts
      ),
    ],
    "structures": [
      {
        "name": name,
        "description": description,
        "block_type": "metric",
        "concept_arrangement": "arithmetic",
      }
    ],
    "associations": [
      {
        "structure_ref": name,
        "from_ref": abstract_qname,
        "to_ref": c["qname"],
        "association_type": "presentation",
        "order_value": float(i + 1),
      }
      for i, c in enumerate(concepts)
    ],
  }
  response = _create_taxonomy_block.sync_detailed(
    client.config.graph_id,
    client=client.sdk,
    body=CreateTaxonomyBlockRequest.from_dict(payload),
  )
  return client.unwrap(response)


def assert_metrics(
  client: IntegrationClient,
  *,
  structure_id: str,
  period_end: date,
  observations: dict[str, float],
  period_start: date | None = None,
  basis_note: str | None = None,
  idempotency_key: str | None = None,
) -> dict:
  """Assert one period's observed values (``{qname: value}``).

  Replace-per-period: re-asserting the same period overwrites it —
  never duplicates. ``source_system`` is stamped from your configured
  source name.
  """
  payload = {
    "structure_id": structure_id,
    "period_end": period_end.isoformat(),
    "period_start": period_start.isoformat() if period_start else None,
    "source_system": client.config.source_name,
    "basis_note": basis_note,
    "observations": [
      {"qname": qname, "value": value} for qname, value in observations.items()
    ],
  }
  response = _assert_metrics.sync_detailed(
    client.config.graph_id,
    client=client.sdk,
    body=AssertMetricsRequest.from_dict(payload),
    idempotency_key=idempotency_key if idempotency_key is not None else UNSET,
  )
  return client.unwrap(response)
