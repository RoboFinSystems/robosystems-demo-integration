"""Manage the robosystems checkout the episodes run from.

The public robosystems repo ships the showcase demos under `examples/`;
the loop clones it into `.robosystems/` (a tool-owned cache, never a
working copy), pins it to `ROBOSYSTEMS_REF`, and syncs its environment.
The demo runners are API-only against remote targets, so the checkout
needs nothing beyond its Python environment and a credentials file.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from .config import DemoConfig


def _run(args: list[str], cwd: str | None = None) -> None:
  result = subprocess.run(args, cwd=cwd, check=False)
  if result.returncode != 0:
    raise SystemExit(f"Command failed ({result.returncode}): {' '.join(args)}")


def ensure_checkout(cfg: DemoConfig) -> None:
  """Clone or update the robosystems checkout at the pinned ref."""
  checkout = cfg.checkout_dir
  if not (checkout / ".git").exists():
    print(f"Cloning {cfg.repo_url} @ {cfg.repo_ref} ...")
    checkout.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "clone", "--filter=blob:none", cfg.repo_url, str(checkout)])
  print(f"Pinning checkout to {cfg.repo_ref} ...")
  _run(["git", "fetch", "--quiet", "origin", cfg.repo_ref], cwd=str(checkout))
  _run(["git", "checkout", "--quiet", "FETCH_HEAD"], cwd=str(checkout))

  # The examples read env config the same way the repo's own tooling does.
  for template, target in (
    (".env.example", ".env"),
    (".env.local.example", ".env.local"),
  ):
    src, dst = checkout / template, checkout / target
    if src.exists() and not dst.exists():
      dst.write_text(src.read_text())

  print("Syncing checkout environment (uv sync) ...")
  _run(["uv", "sync", "--quiet"], cwd=str(checkout))


def write_credentials(cfg: DemoConfig, slots: dict[str, str]) -> None:
  """Write the per-target credentials file the demo runners read.

  Merges into an existing file so previously recorded graph slots
  survive. The slot map is how episodes find graphs the loop provisioned
  (`roboinvestor` looks its issuer up by slot).
  """
  path = cfg.checkout_credentials_file
  data: dict[str, Any] = {}
  if path.exists():
    data = json.loads(path.read_text())
  data["api_key"] = cfg.api_key
  graphs = data.setdefault("graphs", {})
  for slot, graph_id in slots.items():
    graphs[slot] = {"graph_id": graph_id, "graph_created_at": ""}
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2))


def run_episode(cfg: DemoConfig, module: str, args: list[str]) -> None:
  """Run one episode inside the checkout against the remote target."""
  import os

  env = dict(os.environ)
  env["DEMO_API_URL"] = cfg.api_url
  env["UV_ENV_FILE"] = ".env.local"
  cmd = ["uv", "run", "python", "-m", module, *args]
  print(f"\nRunning: {' '.join(cmd)}  (DEMO_API_URL={cfg.api_url})\n")
  result = subprocess.run(cmd, cwd=cfg.checkout_dir, env=env, check=False)
  if result.returncode != 0:
    raise SystemExit(f"Episode {module} exited with {result.returncode}")
