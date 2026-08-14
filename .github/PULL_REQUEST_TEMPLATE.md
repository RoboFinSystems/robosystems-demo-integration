## Summary

<!-- What this PR does and why. Ground it in the actual change, not the diff mechanics. -->

## Changes

<!-- Grouped by stage: collect, transform, emit, config, scheduling. -->

-

## Run Impact

<!-- Required judgment. This runs unattended on a schedule, so:
     - Does what gets EMITTED change? A new/changed external_id means the next run re-emits
       everything it already sent. A changed period key means Lane 2 replaces the wrong period.
     - Does how much gets COLLECTED change? A widened window or removed limit can make the next
       scheduled run enormous.
     - Is it still IDEMPOTENT? Lane 1 dedupes on (source, external_id); Lane 2 replaces per period.
     - Does a new secret or variable need setting BEFORE the next scheduled run? The schedule
       will not wait for someone to notice.
     Write "None" if a scheduled run behaves identically. -->

None

## Testing

<!-- Run `just test-all` (test -> format -> lint -> typecheck) before opening. Note `just format`
     auto-writes, so stage what it rewrote, and only the pytest stage emits a summary.

     Say explicitly whether anything ran against the LIVE API, and against which graph — `just run`
     executes the real pipeline and writes real data. "Not run" is a valid answer. -->
