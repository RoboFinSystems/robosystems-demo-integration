"""The demo loop CLI.

    just demo-up coffee-roaster     # provision + load + connector URL
    just demo-down coffee-roaster   # tear that tenant down
    just demo-down all              # tear everything down
    just demo-status                # what the loop currently holds

State (which graphs the loop provisioned, which connector keys it
minted) lives in `.local/demo-state.json` — local, git-ignored, and only
ever describing throwaway tenants.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from . import api, checkout
from .config import DemoConfig, load_config
from .episodes import EPISODES, Episode, get_episode, read_graph_metadata


def _load_state(cfg: DemoConfig) -> dict[str, Any]:
  if cfg.state_file.exists():
    return json.loads(cfg.state_file.read_text())
  return {"episodes": {}}


def _save_state(cfg: DemoConfig, state: dict[str, Any]) -> None:
  cfg.state_file.parent.mkdir(parents=True, exist_ok=True)
  cfg.state_file.write_text(json.dumps(state, indent=2))


def _ensure_graph(cfg: DemoConfig, state: dict[str, Any], episode: Episode) -> str:
  """Provision the episode's graph unless the loop already holds one."""
  record = state["episodes"].get(episode.key)
  if record and record.get("graph_id"):
    print(f"Reusing {episode.key} graph: {record['graph_id']}")
    return record["graph_id"]
  metadata = read_graph_metadata(cfg, episode)
  graph_id = api.provision_graph(cfg, metadata, episode.schema_extensions)
  state["episodes"][episode.key] = {
    "graph_id": graph_id,
    "provisioned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  }
  _save_state(cfg, state)
  checkout.write_credentials(cfg, {episode.slot: graph_id})
  return graph_id


def cmd_up(cfg: DemoConfig, episode_key: str) -> None:
  episode = get_episode(episode_key)
  checkout.ensure_checkout(cfg)
  checkout.write_credentials(cfg, {})
  state = _load_state(cfg)

  issuer_args: list[str] = []
  if episode.requires_issuer:
    issuer = get_episode(episode.requires_issuer)
    issuer_record = state["episodes"].get(issuer.key) or {}
    if not issuer_record.get("loaded"):
      print(f"\n=== Issuer prerequisite: {issuer.key} ===")
      cmd_up(cfg, issuer.key)
      state = _load_state(cfg)
    issuer_args = ["--issuer", state["episodes"][issuer.key]["graph_id"]]

  graph_id = _ensure_graph(cfg, state, episode)
  record = state["episodes"][episode.key]

  if record.get("loaded"):
    print(f"{episode.key} is already loaded on {graph_id}")
  else:
    checkout.run_episode(
      cfg, episode.module, [*issuer_args, *episode.extra_args, graph_id]
    )
    record["loaded"] = True
    _save_state(cfg, state)

  if not record.get("connector_url"):
    key_id, connector_url = api.mint_connector_key(
      cfg, graph_id, f"demo-{episode.key}-connector"
    )
    record["connector_key_id"] = key_id
    record["connector_url"] = connector_url
    _save_state(cfg, state)

  print("\n" + "=" * 72)
  print(f"  Episode:       {episode.key}")
  print(f"  Graph:         {graph_id}")
  print(f"  Connector URL: {record['connector_url']}")
  print("  Paste the connector URL into Claude (Settings → Connectors) and")
  print("  ask about the books. Tear down with: just demo-down " + episode.key)
  print("=" * 72)


def cmd_down(cfg: DemoConfig, target: str) -> None:
  state = _load_state(cfg)
  if target == "all":
    keys = list(state["episodes"])
  elif target in state["episodes"]:
    keys = [target]
  else:
    matches = [k for k, v in state["episodes"].items() if v.get("graph_id") == target]
    if not matches:
      raise SystemExit(f"Nothing in demo state matches {target!r}")
    keys = matches

  if not keys:
    print("Nothing to tear down.")
    return

  for key in keys:
    record = state["episodes"][key]
    graph_id = record.get("graph_id")
    print(f"Tearing down {key} ({graph_id}) ...")
    if record.get("connector_key_id"):
      api.revoke_key(cfg, record["connector_key_id"])
    if graph_id:
      api.delete_graph(cfg, graph_id)
    del state["episodes"][key]
    _save_state(cfg, state)
  print("Done. Deprovisioning completes server-side in ~10 minutes.")


def cmd_status(cfg: DemoConfig) -> None:
  state = _load_state(cfg)
  if not state["episodes"]:
    print("No demo tenants held. Start one with: just demo-up coffee-roaster")
    return
  for key, record in state["episodes"].items():
    print(f"{key}:")
    for field in ("graph_id", "provisioned_at", "loaded", "connector_url"):
      if record.get(field) is not None:
        print(f"  {field}: {record[field]}")


def main() -> None:
  parser = argparse.ArgumentParser(prog="demo-loop", description=__doc__)
  sub = parser.add_subparsers(dest="command", required=True)

  up = sub.add_parser("up", help="Provision + load an episode, print the connector URL")
  up.add_argument("episode", choices=sorted(EPISODES))

  down = sub.add_parser(
    "down", help="Tear down a demo tenant (episode, graph id, or 'all')"
  )
  down.add_argument("target")

  sub.add_parser("status", help="Show what the loop currently holds")

  args = parser.parse_args()
  cfg = load_config()
  if args.command == "up":
    cmd_up(cfg, args.episode)
  elif args.command == "down":
    cmd_down(cfg, args.target)
  else:
    cmd_status(cfg)


if __name__ == "__main__":
  main()
