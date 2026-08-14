---
description: Create a GitHub issue for this integration, routed to the right repo.
argument-hint: '[what the issue is about]'
---

Create a GitHub issue for the current repository based on the user's input.

## Instructions

1. **Work out which repo owns it** - An integration talks to the RoboSystems platform exclusively through its public API. So:
   - **Belongs here**: the collect step, the transform, how the emitters are wired, configuration, scheduling.
   - **Belongs in `RoboFinSystems/robosystems`**: the API rejecting something it should accept, an operation behaving differently than documented, a platform-side guarantee not holding (double-entry balance, the closed-period gate, `(source, external_id)` idempotency, per-period replacement).
   - **Belongs in `RoboFinSystems/robosystems-python-client`** if you're using that SDK and its types or call surface are wrong.
   - **Belongs in `RoboFinSystems/robosystems-integration-template`** if the problem is in the scaffold itself and would affect every integration built from it — that's worth filing upstream rather than fixing only locally.

   Say which, and include the API response verbatim when the platform rejected something. "The emit failed" without the response body isn't actionable.

2. **Determine Issue Type** - Pick one: **Bug**, **Task**, **Feature**, **RFC**, **Spec**. Confirm what this repo offers — `ls .github/ISSUE_TEMPLATE/` and `gh issue create --help` — rather than assuming.

3. **Draft the Issue** - Read the matching template in `.github/ISSUE_TEMPLATE/` and mirror its structure; `gh issue create --title/--body` bypasses templates entirely, which is exactly why the body has to be hand-matched.

   For a pipeline bug, include: which **lane** (ledger events / semantic facts / raw graph), the stage that failed (collect, transform, emit), the API response if there was one, and whether it reproduces on a re-run — a bug that disappears on retry is an idempotency or ordering bug, which is a different fix.

4. **Sanitize** - Whatever this repo's visibility, an integration issue is unusually likely to carry secrets and customer data:
   - **Never** an API key. They appear in pasted `.env` fragments, curl reproductions, and tracebacks.
   - **Never** a real graph id, or real records from the source system. Invent them.
   - No internal cost/pricing detail.

5. **Create the Issue**:

   ```bash
   gh issue create --type <Type> --title "<title>" --body-file /tmp/issue-body.md
   ```

## Labels

```bash
gh label list --limit 100
```

This repo carries only GitHub's stock labels — it does **not** have the `area:*` / `priority:*` / `size:*` families the platform repos use, and `gh issue create` fails on a label that doesn't exist.

## Output Format

1. The issue URL
2. Brief summary of what was created
3. Issue type and any labels applied
4. Which repo you concluded owns it, and whether the scaffold upstream should get the same fix

$ARGUMENTS
