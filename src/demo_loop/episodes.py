"""The episode registry — which demos the loop can run, and how.

Each episode is a demo that lives in the public robosystems repo's
`examples/` and loads through the live API. The loop provisions the
graph(s) up front (the runners refuse to create graphs on remote targets
by design), hands the ids over positionally, and the episode does the
rest through the same SDK surface a customer integration uses.

Graph metadata (company name, URI, ticker, entity type) is read from the
episode's own data module inside the checkout, so the loop never
duplicates scenario content.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .config import DemoConfig


@dataclass(frozen=True)
class Episode:
  key: str
  module: str
  slot: str
  schema_extensions: list[str]
  metadata_snippet: str
  requires_issuer: str | None = None
  extra_args: list[str] = field(default_factory=list)


_SCENARIO_SNIPPET = """
import json
from examples.{pkg}.data import SCENARIO
print(json.dumps({{
    "graph_name": SCENARIO.company_name,
    "description": SCENARIO.description,
    "entity": {{
        "name": SCENARIO.company_name,
        "uri": SCENARIO.uri,
        "entity_type": SCENARIO.entity_type,
        "ticker": SCENARIO.ticker,
    }},
    "tags": ["demo", SCENARIO.slug],
}}))
"""

_FUND_SNIPPET = """
import json
from examples.roboinvestor_demo import data
print(json.dumps({
    "graph_name": data.FUND_NAME,
    "description": "Early-stage venture fund — private-markets portfolio",
    "entity": {
        "name": data.FUND_NAME,
        "uri": data.FUND_URI,
        "entity_type": "partnership",
        "ticker": data.FUND_TICKER,
    },
    "tags": ["demo", "roboinvestor"],
}))
"""

EPISODES: dict[str, Episode] = {
  "coffee-roaster": Episode(
    key="coffee-roaster",
    module="examples.coffee_roaster_demo.main",
    slot="coffee_roaster",
    schema_extensions=["roboledger"],
    metadata_snippet=_SCENARIO_SNIPPET.format(pkg="coffee_roaster_demo"),
    # Skip the post-filing serialization pass (bundles + SHACL/Arelle):
    # loop-run output files are dead weight — export from the report UI.
    # Harmlessly ignored by checkouts predating the flag.
    extra_args=["--no-artifacts"],
  ),
  "saas-startup": Episode(
    key="saas-startup",
    module="examples.saas_startup_demo.main",
    slot="saas_startup",
    schema_extensions=["roboledger"],
    metadata_snippet=_SCENARIO_SNIPPET.format(pkg="saas_startup_demo"),
    extra_args=["--no-artifacts"],
  ),
  "roboinvestor": Episode(
    key="roboinvestor",
    module="examples.roboinvestor_demo.main",
    slot="roboinvestor_demo",
    schema_extensions=["roboinvestor", "roboledger"],
    metadata_snippet=_FUND_SNIPPET,
    requires_issuer="saas-startup",
  ),
}


def get_episode(key: str) -> Episode:
  episode = EPISODES.get(key)
  if episode is None:
    raise SystemExit(
      f"Unknown episode {key!r}. Available: {', '.join(sorted(EPISODES))}"
    )
  return episode


def read_graph_metadata(cfg: DemoConfig, episode: Episode) -> dict[str, Any]:
  """Read the episode's graph-creation metadata out of the checkout.

  Runs a tiny snippet inside the checkout's own environment so the
  scenario content stays single-sourced in the robosystems repo.
  """
  result = subprocess.run(
    ["uv", "run", "python", "-c", episode.metadata_snippet],
    cwd=cfg.checkout_dir,
    capture_output=True,
    text=True,
    check=False,
  )
  if result.returncode != 0:
    raise SystemExit(
      f"Failed to read {episode.key} metadata from the checkout:\n{result.stderr}"
    )
  return json.loads(result.stdout.strip().splitlines()[-1])
