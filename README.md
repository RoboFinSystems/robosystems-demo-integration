# RoboSystems Demo Integration

The demo tenant loop, built on the [integration template](https://github.com/RoboFinSystems/robosystems-integration-template): provision a throwaway company on a deployed RoboSystems environment, load a showcase episode from the public repo's `examples/`, hand back the graph's MCP URL for Claude to sign into, and tear the whole thing down when the demo ends.

```bash
just demo-up coffee-roaster    # provision + load Driftline + MCP URL
just demo-up saas-startup      # Cadence Labs
just demo-up roboinvestor      # Meridian fund + cross-graph handshake (loads Cadence first)
just demo-status               # what the loop currently holds
just demo-down coffee-roaster  # tear one tenant down (~10 min server-side)
just demo-down all             # tear everything down
```

Configuration is `.env`: `ROBOSYSTEMS_API_KEY` must belong to the **invoice-billed demo account** — that is what lets `POST /v1/graphs` provision with no Stripe round-trip — and `ROBOSYSTEMS_REF` pins which ref of the public robosystems repo the episodes run from (cloned into `.robosystems/`, a tool-owned cache). Loop state lives in `.local/demo-state.json`. Every step is ordinary API traffic; the loop holds no database access of any kind.

### Connecting the demo to Claude

`demo-up` prints the tenant's per-graph MCP URL — `…/v1/graphs/{graph_id}/mcp`. That URL **is** the handoff:

1. Claude → Settings → Connectors → Add custom connector (or `claude mcp add --transport http demo <url>`).
2. Sign in as the demo account. The graph is named by the URL, so consent shows this tenant rather than a picker, and the grant is bound to this one resource.

The URL is not a credential — safe to paste in chat, a run summary, or a slide. The retired `?token=` connector URL *was* a credential; the API stopped honoring it when OAuth landed.

The loop's own `ROBOSYSTEMS_API_KEY` is unrelated to any of this: OAuth covers MCP clients only, while provisioning, loading and teardown are ordinary REST that takes `X-API-Key`. It stays.

For a viewer who **can't** sign in as the demo account, `demo-up <episode> --connector-key` mints a graph-scoped key to send as an `X-API-Key` header (Claude's "Additional request headers" field, or a Cursor/VS Code `mcp.json`). Off by default, printed once, revoked on teardown, and never valid in a URL.

---

The template scaffold this repo was cut from is documented below.

**Living example**: [`robosystems-marketing-integration`](https://github.com/RoboFinSystems/robosystems-marketing-integration) — a real integration built from this template that collects RFS's own marketing/usage metrics (GitHub, npm, PyPI, Docker Hub) and asserts them as a monthly metric series.

An integration lives in its own repository — this one — and speaks to the platform exclusively through the public API with an API key. It never runs inside the platform, so it survives every platform release, works identically against the managed cloud or a self-hosted deployment, and is yours to run anywhere: a cron job, a Lambda, a container, a GitHub Actions schedule.

## The three lanes

Pick the lane that matches your data's nature (an integration can use more than one):

| Lane | What you send | What the platform enforces | Emitter |
|---|---|---|---|
| **1 — Ledger** | Business events → the general ledger | Double-entry balance, capture-then-approve, closed-period gate, `(source, external_id)` idempotency | `emit/events.py` |
| **2 — Semantic facts** | A custom vocabulary + observed metric series | Typed concepts, presentation structure, per-period replace, provenance | `emit/metrics.py` |
| **3 — Raw graph** | Parquet/CSV files → staging → graph | Per-graph schema, bulk ingestion pipeline | `emit/graph.py` |

- **Lane 1** is for data that *is* accounting: invoices, payments, payroll from a system the platform has no adapter for. Events land in an inbox (`captured`), an operator approves, handlers derive the GL entries.
- **Lane 2** is for data that is *facts but not bookkeeping*: marketing counts, usage numbers, operational KPIs. Author your vocabulary once (`create-taxonomy-block`), then assert observed values per period (`assert-metrics`). The platform renders the series everywhere — envelopes, charts, fact grids, GraphQL, MCP — with no further work.
- **Lane 3** is for graph-shaped domain data: upload files, stage, materialize. Combined with the per-graph schema operations you can stand up a complete custom knowledge graph.

## Quickstart

1. Click **Use this template** and create your integration repo (typically private).
2. Clone it, then:

```bash
just venv         # environment + dependencies + git hooks (.env provisioned from .env.example)
# fill in API key + graph id in .env
just run          # collect → transform → emit
```

3. Replace the stubs in `src/integration/collect.py` and `transform.py` with your source's extract/transform, and wire the emitter(s) for your lane in `main.py`.

Day-to-day commands mirror the other RoboSystems Python repos: `just test`, `just test-all` (tests + format + lint + typecheck — the CI gate), `just lint`, `just format`, `just typecheck`, `just create-feature <type> <name>`.

## Layout

```
src/integration/
  config.py       # env-driven settings (.env supported)
  client.py       # robosystems-client SDK wired with API-key auth,
                  # plus envelope unwrapping + a raw-op escape hatch
  collect.py      # YOUR extract — pull from your source system
  transform.py    # YOUR transform — shape raw data for the lane you use
  emit/
    events.py     # lane 1: create-event-block
    metrics.py    # lane 2: create-taxonomy-block + assert-metrics
    graph.py      # lane 3: create-file-upload → ingest-file → materialize
  main.py         # collect → transform → emit
```

The split is deliberate: **you own extract and transform** (they're specific to your source); **the platform owns validation and load** (the operations behind the API). Credentials for *your source system* stay on your side — the platform never holds them.

## Conventions that matter

- **Idempotency**: lane-1 events carry `(source, external_id)` — re-sending the same event is a no-op, so retries are always safe. Operations also accept an `Idempotency-Key` header (the client sends one when you pass it).
- **Raw history is yours**: keep your raw pulls (e.g. daily JSON snapshots) in your own storage; send the platform the rolled-up series at your reporting cadence. Backfill is one loop over your history.
- **One source name per integration**: your integration's registered source name is its identity stamp on everything it writes.

## Deploying

An integration is a small program that runs on a schedule — the contract is env vars in, API calls out — so the runtime is swappable. The ladder, in increasing weight:

1. **GitHub Actions (the default, included)**: `.github/workflows/run.yml` runs the integration on a cron with zero infrastructure. Set `secrets.ROBOSYSTEMS_API_KEY` plus `vars.ROBOSYSTEMS_GRAPH_ID` / `vars.INTEGRATION_SOURCE_NAME` in the repo settings and it's deployed. Standard runners give 4 vCPU / 16 GB and a 6-hour cap — ample for API-pull collectors.
2. **GitHub Actions, larger runner**: heavy backfills or transforms get real memory/CPU with a one-line `runs-on` change (e.g. `ubuntu-latest-8-cores`) — still zero infrastructure.
3. **ECS Fargate scheduled task**: full resource control and CloudWatch visibility when an integration outgrows runners — EventBridge Scheduler → `RunTask`, no service or load balancer, public subnet with egress only (the integration never needs to be inside a VPC; the API is the boundary). This template doesn't ship the CloudFormation for it — bring it when you graduate.

Secrets (API key, source credentials) belong in your runtime's secret store — repo secrets, or the task's secret manager — never in the repo.

## SDK

The [`robosystems-client`](https://pypi.org/project/robosystems-client/) Python SDK is how the emitters interface with the platform — typed request/response models and one generated function per operation (`robosystems_client.api.*`), regenerated from the live [OpenAPI spec](https://api.robosystems.ai/openapi.json). Brand-new operations occasionally land on the API before the SDK's next regeneration; `IntegrationClient.raw_operation` reaches those through the same authenticated client until the typed function exists.

### What the pin promises

`pyproject.toml` pins `robosystems-client>=1,<2`, and that range is safe because **this template defines the SDK's stable surface**. Every symbol the emitters import — `AuthenticatedClient`, `types.UNSET`, the emit operations (`create_file_upload`, `ingest_file`, `materialize`, `create_event_block`, `assert_metrics`, `create_taxonomy_block`) and their request models — is frozen for the life of `1.x`. Breaking any of it costs the SDK a major version.

The rest of `robosystems_client.api.*` carries no such promise. It tracks the API surface and moves with it on minor releases, so operations you reach for beyond the emitters above — including anything through `raw_operation` — can be renamed or removed without a major. If you build on one and want it frozen, the way to get that is to add it to this template's emitters, not to narrow the pin.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

MIT © 2026 RFS LLC

