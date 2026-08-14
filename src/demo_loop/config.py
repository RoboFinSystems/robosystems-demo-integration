"""Environment-driven settings for the demo loop.

Reads process env vars, with `.env` as a convenience fallback for local
development — the same contract as the integration template's own config.
The API key belongs to the invoice-billed demo account, never a live
customer account.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from integration.config import _load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DemoConfig:
  api_url: str
  api_key: str
  repo_url: str
  repo_ref: str
  checkout_dir: Path
  state_file: Path

  @property
  def host_slug(self) -> str:
    """The API host, dashed — names the per-target credentials file."""
    return (urlparse(self.api_url).hostname or "remote").replace(".", "-")

  @property
  def checkout_credentials_file(self) -> Path:
    """Where the demo runners inside the checkout read credentials from."""
    return self.checkout_dir / ".local" / f"config.{self.host_slug}.json"


def load_config() -> DemoConfig:
  _load_dotenv(REPO_ROOT / ".env")
  api_key = os.environ.get("ROBOSYSTEMS_API_KEY", "")
  if not api_key:
    raise SystemExit(
      "Missing ROBOSYSTEMS_API_KEY — the demo account's API key. "
      "Set it in .env or the process environment."
    )
  return DemoConfig(
    api_url=os.environ.get("ROBOSYSTEMS_API_URL", "https://api.robosystems.ai").rstrip(
      "/"
    ),
    api_key=api_key,
    repo_url=os.environ.get(
      "ROBOSYSTEMS_REPO_URL", "https://github.com/RoboFinSystems/robosystems.git"
    ),
    repo_ref=os.environ.get("ROBOSYSTEMS_REF", "main"),
    checkout_dir=REPO_ROOT / ".robosystems",
    state_file=REPO_ROOT / ".local" / "demo-state.json",
  )
