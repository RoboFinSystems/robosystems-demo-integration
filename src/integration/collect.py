"""YOUR extract — pull raw data from your source system.

This half is integration-specific and entirely yours: API pulls, file
drops, database reads, webhooks you receive. Two conventions worth
keeping:

- **Snapshot raw history into your own storage** (a ``data/`` directory
  locally, your own bucket in production). Some source data is
  perishable; your raw history is what makes backfill and re-processing
  possible without re-pulling.
- **Source credentials stay here**, in your runtime's secret store —
  the platform never holds them.
"""

from __future__ import annotations

from typing import Any

from integration.config import Config


def collect(config: Config) -> list[dict[str, Any]]:
  """Pull raw records from the source system.

  Replace with your extract. Return whatever raw shape suits your
  source — ``transform`` owns turning it into a lane payload.
  """
  raise NotImplementedError("implement your source extract here")
