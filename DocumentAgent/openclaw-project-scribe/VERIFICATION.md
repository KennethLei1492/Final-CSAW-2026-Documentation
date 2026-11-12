# Verification record

Build date: **November 12, 2026**.

**Result: 28 tests passed; 0 failures; 0 skipped.**

Executed on native Windows using Node.js **v24.16.0**, Git, and Node's built-in test runner. The final test run took approximately 27 seconds. The command was:

```text
node --no-warnings --test test/*.test.mjs
```

The CLI `help` command, JavaScript syntax checks, and PowerShell setup-script parsing also passed. This package has no third-party npm dependencies.

## Exercised behavior

- Project filtering, session/subagent attribution, secret redaction, and available exit statuses.
- Deduplication using stable callback IDs while retaining distinct callbacks without such IDs.
- Eight simultaneous capture processes writing to one SQLite database.
- Staged, unstaged, untracked and committed Git changes; unborn repositories; detached HEAD; explicit linked worktrees.
- Secret-path exclusions, source-path traversal rejection, bounded source excerpts and patches.
- Event batching, explicit backlog counts, and preview without advancing the checkpoint.
- Model output schema/citation validation and refusal of unknown response formats.
- Google managed-block initialization, human text outside the block, UTF-16 indexing, nested tabs, duplicate-marker refusal, and non-text-content refusal.
- Simulated Google permission failures, revision conflicts, and a successful write whose network acknowledgment was lost.
- Pending publication retention, cursor recovery, synthesis reuse on retry, and destination-change refusal.
- Skipping unchanged report runs, preserving existing hooks, and idempotent hook merging.
- Actual native Windows Codex hook wrapper execution with JSON stdin and paths containing spaces.
- Nonblocking handling of malformed hook input, explicit test-command failure recording, and overlap locks.
- A complete package CLI flow against a **simulated OpenClaw executable**: setup, generated configuration, capability checks, model request arguments, report generation, and schedule creation.
- Invalid configuration booleans and unknown CLI option refusal.

## Not represented as live verification

OpenClaw was not installed on the build host. Its current official command/configuration documentation was checked, and the generated package checks its target installation's help flags and configuration acceptance during setup. The simulated executable test validates our argument construction and integration flow, not the actual OpenClaw service.

No real model provider call, Google OAuth grant, service-account exchange, or Google Docs write was performed. These require the user's paths, selected model, credentials and document access. Google publishing behavior was tested with controlled document/API fixtures. The first authenticated `google-inspect` and `run` are the live installation checks.

No actual user project repository, coding-agent settings, OpenClaw installation, automation, or Google document was modified to build this package. Only temporary fixture repositories and the deliverable package were used.
