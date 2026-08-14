---
description: Open a pull request for the current branch, writing the description from the work actually done.
argument-hint: '[target-branch] [review]'
---

Create a GitHub pull request for the current branch, writing the title and description from the actual work done in this session — not reconstructed from the diff.

## Why this command exists

A description written from the diff alone can't know _why_ a change was made, so it tends to describe things that aren't true. **You author it here, where the full context is available.**

This is a **RoboSystems integration**: a scheduled job that speaks to the platform through its public API with an API key. Everything runs through `uv run`; branches come from `just create-feature <type> <name>`.

## Instructions

### 1. Preflight

```bash
CURRENT=$(git branch --show-current)
TARGET=${1:-main}
```

- **Never PR from `main`.** **Source ≠ target.** Stop if either holds.
- **Uncommitted changes**: surface them and ask whether to commit (never on `main`, stage by name, no `git add -A`).
- **Existing PR**: `gh pr list --head "$CURRENT" --base "$TARGET" --json url,number` — offer `gh pr edit` rather than duplicating.
- **Push**: `git push -u origin "$CURRENT"`.

### 2. Gather the real change context

Use this session as the primary source, corroborate with `git log`, `git diff --stat`, and the full `git diff`. **No confabulation** — every claim must be supported by the diff.

### 3. Compose the PR

- **Title** — conventional-commit style with a scope, matching `git log`.
- **Body** — **match the headings in `.github/PULL_REQUEST_TEMPLATE.md`**, since `--body-file` bypasses template prefill and silently drops omitted sections:
  - **Summary** — 1–3 sentences.
  - **Changes** — grouped by stage: collect, transform, emit, config, scheduling.
  - **Run Impact** — see below. "None" if a scheduled run behaves identically.
  - **Testing** — the gate is `just test-all` (`test` → `format` → `lint` → `typecheck`). Say explicitly whether anything was run **against the live API**, and if so, against which graph. If nothing was run, say "Not run".

  Put `Closes #123` as the last line of the Summary — the template has no Related Issues section.

- **Run Impact is the judgment that matters.** This runs unattended on a schedule:
  - Does it change **what gets emitted** — new events, a changed `external_id`, a different period key, a new metric concept? An `external_id` change means the next run re-emits everything it already sent.
  - Does it change **how much** gets collected — a widened time window or removed limit can make the next scheduled run enormous.
  - Is it still **idempotent**? Lane 1 dedupes on `(source, external_id)`; Lane 2 replaces per period.
  - Does it need a **new secret or variable** set before the next scheduled run? Say so — the schedule won't wait for someone to notice.

- **Never put an API key or a real graph id in the body.**
- **Attribution** — attribute to the user only; no Claude footer or trailer unless explicitly asked.

### 4. Create the PR

```bash
gh pr create --base "$TARGET" --head "$CURRENT" --title "<title>" --body-file /tmp/pr-body.md
```

### 5. Optional Claude review

Only if the user asks (`review` / `--review`): `gh pr comment <number> --body "@claude please review this PR"`.

## Output

1. PR URL. 2. Title. 3. Target ← source. 4. Run Impact, including anything needed before the next scheduled run. 5. Whether a review was requested.

$ARGUMENTS
