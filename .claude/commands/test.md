---
description: Run the full test and code-quality gate, fixing failures to green.
argument-hint: '[test-path]'
---

Run `just test-all` and systematically fix all failures to achieve 100% completion.

## Strategy

1. **Run the full gate first**, filtering for signal (below).
2. **Fix in the order it runs**: `just test` (pytest) → `just format` → `just lint` → `just typecheck`.
3. **Iterate on the failing layer only** — `uv run pytest path/to/test.py` for the fastest loop.
4. **Stop when green.** Don't re-run to "confirm."

## What `just test-all` runs

```
just test → just format → just lint → just typecheck
```

Only the first stage emits a pytest summary. A ruff or basedpyright failure surfaces as a recipe-failure line with no `failed` count — **a green pytest count alone is not proof the gate passed**.

`just format` is `ruff format` (auto-write), so the gate **mutates the working tree**. Check `git status` afterwards and stage what it rewrote; the pre-commit hook runs check-only variants and fails on exactly those files.

**Everything runs through `uv run`.** Bare `pytest`, `ruff`, or `python` use the wrong environment.

## Output Handling

```
just test-all 2>&1 | grep -E "passed|failed|error:|FAILED|warnings summary|^= " | tail -20
```

## Notes

- **Tests must not call the live API.** An integration's whole job is talking to a remote platform, so the temptation to "just run it" is strong — but a test that emits against a real graph writes real data. Stub `client.py` at the boundary and assert on what *would* be sent.
- **`just run` is not a test.** It executes the real collect → transform → emit pipeline against whatever `.env` points at. Treat it as a production action unless you have positively confirmed the target graph is a scratch one.
- **Idempotency is the property worth testing.** Lane 1 dedupes on `(source, external_id)` and Lane 2 replaces per period — so running twice should not double anything. A test that only covers the first run misses the bug that actually bites on a schedule.
- Assert on the *shape* of what the emitters send, not on platform behavior you can't see from here.

## Goal

100% pass on `just test-all` with no errors of any kind.

$ARGUMENTS
