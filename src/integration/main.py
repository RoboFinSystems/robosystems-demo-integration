"""Entry point: collect → transform → emit.

Run locally with ``uv run python -m integration.main``. In production,
whatever invokes this on a schedule (cron, GitHub Actions, Lambda, ECS)
just needs the env vars from ``.env.example`` set.
"""

from __future__ import annotations

from integration.client import IntegrationClient
from integration.collect import collect
from integration.config import load_config
from integration.transform import transform


def run() -> None:
  config = load_config()
  client = IntegrationClient(config)
  try:
    raw = collect(config)
    records = transform(raw)  # noqa: F841 — handed to the emitter you wire below

    # Wire the emitter(s) for your lane:
    #
    # Lane 1 — ledger events:
    #   from integration.emit.events import emit_events
    #   emit_events(client, records)
    #
    # Lane 2 — metric series (vocabulary authored once, then per period):
    #   from integration.emit.metrics import assert_metrics
    #   assert_metrics(client, structure_id=..., period_end=...,
    #                  observations=records)
    #
    # Lane 3 — bulk graph content:
    #   from integration.emit.graph import materialize, upload_file
    #   for path in parquet_files: upload_file(client, path, table_name=...)
    #   materialize(client)
    raise NotImplementedError("wire your lane's emitter here")
  finally:
    client.close()


if __name__ == "__main__":
  run()
