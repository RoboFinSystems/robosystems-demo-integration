"""Environment-driven settings.

Reads process env vars, with `.env` as a convenience fallback for local
development. Runtime secrets (the API key, your source system's
credentials) belong in your runtime's secret store — never in the repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
  """Minimal .env loader — process env always wins."""
  if not path.is_file():
    return
  for line in path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    key, _, value = line.partition("=")
    os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Config:
  api_url: str
  api_key: str
  graph_id: str
  source_name: str


def load_config() -> Config:
  _load_dotenv(Path(".env"))
  missing = [
    name
    for name in ("ROBOSYSTEMS_API_KEY", "ROBOSYSTEMS_GRAPH_ID")
    if not os.environ.get(name)
  ]
  if missing:
    raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
  return Config(
    api_url=os.environ.get("ROBOSYSTEMS_API_URL", "https://api.robosystems.ai").rstrip(
      "/"
    ),
    api_key=os.environ["ROBOSYSTEMS_API_KEY"],
    graph_id=os.environ["ROBOSYSTEMS_GRAPH_ID"],
    source_name=os.environ.get("INTEGRATION_SOURCE_NAME", "myintegration"),
  )
