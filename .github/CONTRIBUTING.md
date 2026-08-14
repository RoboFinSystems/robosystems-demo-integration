# Contributing to the RoboSystems Integration Template

This template is the scaffold for building custom integrations against the [RoboSystems](https://github.com/RoboFinSystems/robosystems) public API. Contributions that improve the scaffold itself — emitter ergonomics, docs, CI — are welcome.

## Community

- **[Discussions](https://github.com/orgs/RoboFinSystems/discussions)** - Questions, ideas, and general conversation
- **[Wiki](https://github.com/RoboFinSystems/robosystems/wiki)** - Architecture docs and guides

## Development Setup

```bash
git clone https://github.com/RoboFinSystems/robosystems-integration-template.git
cd robosystems-integration-template
just venv          # create the environment + install dependencies + hooks
just test-all      # tests + format + lint + typecheck
```

Daily commands (mirrors the other RoboSystems Python repos):

| Command | What it does |
| --- | --- |
| `just test` | Run the test suite |
| `just test-all` | Tests + format + lint + typecheck (the CI gate) |
| `just lint` / `just format` | Ruff check / format |
| `just typecheck` | basedpyright |
| `just run` | Run the integration locally |
| `just create-feature <type> <name>` | Create a feature branch from `origin/main` |

## Development Process

1. Create a branch with `just create-feature feature my-change` (never commit on `main` — the `.githooks/pre-push` hook blocks direct pushes to protected branches).
2. Make your change; keep the scaffold thin — the template deliberately ships no infrastructure.
3. `just test-all` must be green (the pre-commit hook runs the same gate).
4. Open a PR against `main`.

## Building your own integration

Don't PR your integration here — click **Use this template** and build it in your own repository. This repo is the scaffold, not a home for integrations.
