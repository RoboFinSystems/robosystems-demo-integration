"""Platform API calls the loop makes directly: provision, connect, destroy.

Everything here is an ordinary authenticated call against the public API
with the demo account's key — the same surface a customer automation
would use. Graph creation succeeds without a Stripe round-trip because
the demo org is invoice-billed; that is the mechanism that makes the
loop repeatable.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from robosystems_client.client import AuthenticatedClient

from .config import DemoConfig


def make_client(cfg: DemoConfig) -> AuthenticatedClient:
  return AuthenticatedClient(
    base_url=cfg.api_url,
    token=cfg.api_key,
    prefix="",
    auth_header_name="X-API-Key",
  )


def _field(obj: Any, name: str, default: Any = None) -> Any:
  if isinstance(obj, dict):
    return obj.get(name, default)
  value = getattr(obj, name, default)
  if value is not None and "Unset" in type(value).__name__:
    return default
  return value


def provision_graph(
  cfg: DemoConfig, metadata: dict[str, Any], extensions: list[str]
) -> str:
  """Create a graph on the demo org and wait for it to come up.

  202 → operation poll → graph_id, the same primitive the drill proved.
  Provisioning a dedicated instance takes a few minutes.
  """
  from robosystems_client.api.graphs.create_graph import sync_detailed as create_graph
  from robosystems_client.api.operations.get_operation_status import (
    sync_detailed as get_operation_status,
  )
  from robosystems_client.models import CreateGraphRequest, GraphMetadata

  client = make_client(cfg)
  request = CreateGraphRequest(
    metadata=GraphMetadata(
      graph_name=metadata["graph_name"],
      description=metadata.get("description") or "",
      schema_extensions=extensions,
    ),
    initial_entity=metadata["entity"],
    tags=metadata.get("tags") or ["demo"],
  )
  print(f"Provisioning graph: {metadata['graph_name']}")
  response = create_graph(client=client, body=request)
  if response.status_code >= 400 or not response.parsed:
    body = response.content.decode() if response.content else "(no body)"
    raise SystemExit(f"Graph creation failed: HTTP {response.status_code}\n{body}")

  parsed = response.parsed
  graph_id = _field(parsed, "graph_id")
  operation_id = _field(parsed, "operation_id")

  if not graph_id and operation_id:
    print(f"  Queued (operation {operation_id}); waiting for provisioning ...")
    deadline = time.monotonic() + 15 * 60
    while time.monotonic() < deadline:
      time.sleep(5)
      status = get_operation_status(operation_id=operation_id, client=client)
      if not status.parsed:
        continue
      data = status.parsed
      props = getattr(data, "additional_properties", None)
      if isinstance(props, dict) and props:
        data = props
      state = _field(data, "status")
      result = _field(data, "result") or {}
      if state == "completed":
        graph_id = _field(result, "graph_id")
        break
      if state == "failed":
        raise SystemExit(f"Graph provisioning failed: {_field(result, 'error')}")

  if not graph_id:
    raise SystemExit("Timed out waiting for graph provisioning")
  print(f"  Graph ready: {graph_id}")
  return graph_id


def mint_connector_key(cfg: DemoConfig, graph_id: str, name: str) -> tuple[str, str]:
  """Mint a graph-scoped (rfsc) key and return (key_id, key).

  The key goes in an ``X-API-Key`` header for clients that cannot sign in;
  it never rides in a URL (the ``?token=`` connector URL was the bridge to
  OAuth and the API no longer honors it).

  The SDK's CreateAPIKeyRequest predates graph scoping, so this posts
  directly — the documented escape hatch for operations newer than the
  SDK regen.
  """
  response = httpx.post(
    f"{cfg.api_url}/v1/user/api-keys",
    headers={"X-API-Key": cfg.api_key, "Content-Type": "application/json"},
    json={
      "name": name,
      "description": f"MCP connector key for demo graph {graph_id}",
      "graph_id": graph_id,
    },
    timeout=30,
  )
  if response.status_code >= 400:
    raise SystemExit(
      f"Connector key mint failed: HTTP {response.status_code}\n{response.text}"
    )
  payload = response.json()
  return payload["api_key"]["id"], payload["key"]


def mcp_url(cfg: DemoConfig, graph_id: str) -> str:
  """The per-graph MCP endpoint — OAuth-capable clients add it and sign in."""
  return f"{cfg.api_url}/v1/graphs/{graph_id}/mcp"


def revoke_key(cfg: DemoConfig, key_id: str) -> None:
  response = httpx.delete(
    f"{cfg.api_url}/v1/user/api-keys/{key_id}",
    headers={"X-API-Key": cfg.api_key},
    timeout=30,
  )
  if response.status_code >= 400:
    print(f"  WARNING: key {key_id} revocation returned HTTP {response.status_code}")


def delete_graph(cfg: DemoConfig, graph_id: str) -> None:
  """Immediate teardown — the customer delete-graph operation.

  202-accepted; the platform's suspend → deprovision pipeline destroys
  the graph and its instance in ~10 minutes. Requires `confirm` to equal
  the graph id, which is the whole point.
  """
  from robosystems_client.api.graph_operations.delete_graph import (
    sync_detailed as delete_graph_op,
  )
  from robosystems_client.models import DeleteGraphOp

  client = make_client(cfg)
  response = delete_graph_op(
    graph_id=graph_id,
    client=client,
    body=DeleteGraphOp(confirm=graph_id),
  )
  if response.status_code >= 400:
    body = response.content.decode() if response.content else "(no body)"
    raise SystemExit(f"delete-graph failed: HTTP {response.status_code}\n{body}")
  print(f"  Teardown accepted for {graph_id} (deprovisions in ~10 min)")
