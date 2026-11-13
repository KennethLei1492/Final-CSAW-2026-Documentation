# Project Scribe for OpenClaw

An installable local package that observes multiple Claude Code and Codex sessions, records normalized events in SQLite, checks Git worktrees, asks a dedicated OpenClaw agent for evidence-cited documentation, and maintains a marked section of a Google Doc.

Built against official documentation checked **November 12, 2026**. See `SOURCES.md` for command verification and `VERIFICATION.md` for the tests actually run. No API keys, account tokens, project paths, or document IDs are bundled.

## How it works

```text
Claude Code hooks ─┐
Codex hooks ───────┼─> local SQLite events.db ─┐
Test wrapper ─────┘                          │
Git status / diffs / commits / source files ─┼─> controller ─> OpenClaw synthesis
                                           │                    │
                                           └────────────────────┴─> local reports
                                                                   │
                                                              Google Docs API
```

The controller owns collection and publishing. OpenClaw receives a bounded, redacted evidence packet and returns a validated JSON digest with evidence citations. The agent's tools are denied; it cannot run project commands or choose a different publishing destination. The package pins its model to OpenClaw's embedded runtime using the current model-scoped configuration. Coding sessions remain independent.

The included files are:

| File | Purpose |
|---|---|
| `config.example.json` | All paths, IDs, capture controls, model and cadence |
| `workspace/AGENTS.md`, `SOUL.md`, `IDENTITY.md` | Agent role and behavior |
| `workspace/skills/project-documentation/SKILL.md` | Evidence rules and structured response contract |
| `scribe.mjs` and `lib/` | Event database, Git observer, report controller, Google publisher, installer |
| `scripts/setup.sh`, `scripts/setup.ps1` | Setup entry points for Unix/WSL and Windows |
| `test/scribe.test.mjs` | Local integration and failure-recovery tests |
| `REQUIRED-VALUES.md` | Fill-in checklist with credential instructions |

## 1. Install prerequisites and choose one host

Use **Node.js 24.16+ on the 24.x line, or 26.1+** and Git. The current OpenClaw getting-started guide recommends newer patched Node versions; follow its current installation guidance. This package uses Node's built-in SQLite and has **no npm dependencies**. Do not run `npm install` for this package.

Install and onboard OpenClaw using the [official getting-started guide](https://docs.openclaw.ai/start/getting-started). Its Gateway and model credentials must work before setup. Commands to inspect readiness:

```text
node --version
git --version
openclaw --version
openclaw onboard
openclaw gateway status
openclaw models list
```

Run onboarding only if needed. Use an actual `provider/model` ID available to your account; the package does not choose a paid model for you. Provider authentication stays in OpenClaw, not in this package.

Keep the package, SQLite database, hooks, Git, and Gateway on **one machine and one OS environment**. WSL2 is a convenient Windows deployment option when your coding CLIs also run there. Native Windows is supported by the package; its capture wrapper and tests were exercised on Windows. Do not have Windows and WSL concurrently write the same SQLite file, or place it on a network share or sync folder. Remote machines need a separate transport/database adapter; this package does not provide one.

Extract the ZIP into a permanent folder outside your project, for example `~/tools/openclaw-project-scribe`. Do not move it after installing hooks: generated hooks use absolute paths.

## 2. Fill the configuration

Copy `config.example.json` to `config.json`, then replace the `FILL_...` values. JSON paths on Windows can use forward slashes, such as `C:/Users/you/projects/challenge`.

At minimum fill:

- `project.name` and `project.roots`: the absolute **Git worktree roots**, including every separate worktree you want observed. A challenge subfolder is not a Git root; use the enclosing clone root. Roots are explicitly allowlisted, including linked worktrees.
- `stateDir`: a private local directory for SQLite, retries, prompt input, and locks.
- `outputDir`: local Markdown and JSON reports.
- `workspaceDir`: a new, dedicated OpenClaw workspace.
- `openclaw.model`: the actual provider/model identifier.
- Google document, tab, and authentication values from `REQUIRED-VALUES.md` when you are ready to publish.

Keep `google.enabled: false` until Google access is set up. Google placeholders can remain during local setup. `stateDir`, `outputDir`, and `workspaceDir` must be outside all observed repositories. A single config represents one project with one Google destination.

**Native Windows OpenClaw command:** Node cannot directly spawn an npm `.cmd` shim. If OpenClaw is installed through npm, use `npm.cmd root -g` to locate its module directory and verify that `openclaw/openclaw.mjs` exists there. Set the command to the actual files on your machine:

```json
"command": ["C:/Program Files/nodejs/node.exe", "C:/Users/YOU/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs"]
```

The example location is not assumed by the installer. For another installation layout use its actual executable or Node entry point. On Linux/WSL, `["openclaw"]` works when the Gateway service also has that executable on PATH; absolute paths are more reliable. A named profile can be expressed as `["/absolute/openclaw", "--profile", "YOUR_PROFILE"]` and must identify the same local Gateway used for setup and scheduling.

## 3. Prepare and register the documentation agent

Run from the extracted package directory:

```text
node --no-warnings scribe.mjs setup --config /ABSOLUTE/config.json
node --no-warnings scribe.mjs setup --config /ABSOLUTE/config.json --apply
```

The first command copies workspace files and creates `generated/openclaw.patch.json`, `generated/claude-hooks.json`, and `generated/codex-hooks.json`. It refuses to overwrite different workspace files. Review those generated files if desired.

The second command verifies installed OpenClaw help flags, checks the agent roster, creates this agent when needed, validates the configuration patch, applies it, and runs OpenClaw config validation. It changes only the selected agent entry. Existing agents and channel bindings are preserved. A running local Gateway is required. If a command returns an uncertain result, inspect `openclaw agents list` before retrying.

Equivalent setup wrappers:

```bash
bash scripts/setup.sh --config /ABSOLUTE/config.json --apply
```

```powershell
.\scripts\setup.ps1 -Config 'C:\ABSOLUTE\config.json' -Apply
```

There is no global `agents.list` replacement or legacy `HEARTBEAT.md` setup. The package uses the current `agents.entries` map and a scheduled **command job**. For this agent, automatic workspace-context injection is disabled; the controller explicitly includes the installed AGENTS.md, SOUL.md, and full skill contract in each request. This keeps generic first-run onboarding files out of scheduled synthesis and works without read tools. Start reports through the package commands rather than an ordinary chat with this specialized agent.

## 4. Connect Claude Code and Codex hooks

These commands merge hooks into the exact file you name and save a backup. Use **one scope per CLI**, not both user and project scope, to avoid duplicate callbacks. Review existing hooks first if your configuration is managed by your organization.

Linux/WSL user-level examples:

```bash
node --no-warnings scribe.mjs hooks --config "$PWD/config.json" --provider claude --target "$HOME/.claude/settings.json"
node --no-warnings scribe.mjs hooks --config "$PWD/config.json" --provider codex --target "$HOME/.codex/hooks.json"
```

Native Windows examples, replacing `YOUR_USER` and the package path:

```powershell
node --no-warnings .\scribe.mjs hooks --config 'C:/ABSOLUTE/config.json' --provider claude --target 'C:/Users/YOUR_USER/.claude/settings.json'
node --no-warnings .\scribe.mjs hooks --config 'C:/ABSOLUTE/config.json' --provider codex --target 'C:/Users/YOUR_USER/.codex/hooks.json'
```

For project-local installation use `<root>/.claude/settings.local.json` and `<root>/.codex/hooks.json`; configure every worktree where necessary. A custom `CODEX_HOME` changes the appropriate user hook target. Restart existing coding sessions after installation. **In Codex run `/hooks`, review the exact generated commands, and trust them.** Hook trust is not bypassed.

Claude hooks use its current direct executable plus `args` form. Codex uses a quoted command and a Windows-specific encoded PowerShell wrapper generated from local absolute paths. Hooks return `{}` and exit successfully even if observation fails, so they never block a coding turn. Failures appear in the coding CLI's hook diagnostics. SQLite lock contention can spool a normalized event to a private file; the next report run replays it.

Events include provider, session, subagent, available model/turn/tool IDs, root, HEAD, event type, selected message, and available exit status. There is no guessed model inference. Raw user prompts, transcript contents, and hidden reasoning are not read. `PostToolUseFailure` is configured for Claude only; Codex reports supported tool failures through `PostToolUse`.

This observes **future callbacks**, not historical sessions. Claude/Codex transcript directory paths are **not required**. Sessions where these hooks cannot run—such as another host or an unavailable desktop runtime—are not silently discovered. Check that real events appear after doing one harmless coding turn in each CLI:

```text
node --no-warnings scribe.mjs status --config /ABSOLUTE/config.json
node --no-warnings scribe.mjs preview --config /ABSOLUTE/config.json
```

`preview` produces `preview.md` and `preview-evidence.json`, makes no model or Google calls, and advances no report checkpoint.

## 5. Add project context and test evidence

By default Git supplies status, staged and unstaged change statistics, recent commits, committed change statistics since the previous successful report, branch and HEAD. It does not prove authorship or correctness. Each registered worktree is tracked separately; changing history is identified through ancestry checks. Initial history and later commit lists are bounded by `git.maxCommits`.

For useful architecture documentation, explicitly allow a few relevant text files. Indices refer to `project.roots`:

```json
"sourceFiles": [
  {"root": 0, "path": "README.md"},
  {"root": 0, "path": "finals/challenge_3/README.md"}
]
```

These are examples: list only files that exist in your repository. Each must be under its root, nonbinary, under 1 MiB, and not excluded; excerpts are capped at 12,000 characters. Set `git.includePatches: true` if you want redacted patch excerpts included in model input and reports. Secret paths are excluded; built-in and optional custom regex redaction is best-effort. Review a preview before enabling publishing. Report data is sent to the configured model provider, and to Google when publishing is enabled.

Agent text such as “tests passed” is labeled a claim. To record an actual command exit, explicitly run your test command through the wrapper:

```text
node --no-warnings scribe.mjs record-test --config /ABSOLUTE/config.json --root /ABSOLUTE/PROJECT --session testbench -- python3 -m pytest
```

The wrapper executes exactly the argument vector after `--`, with no shell, records exit status and a redacted output excerpt, hashes the output, and records HEAD and tracked-state stability. Test commands can change files; choose the command yourself. Windows `.cmd` test runners need their underlying executable or Node script. A nonzero exit returns failure; a timeout is recorded as an incomplete command. It does not infer coverage or claim an independently audited result.

## 6. Connect Google Docs

Create a Google Cloud project, enable the **Google Docs API**, and create a Google Doc with a blank tab reserved for this report. The script never creates a document, changes its sharing, or needs a Drive folder ID.

Choose one authentication mode:

**Desktop OAuth:** configure the consent screen and a **Desktop app** OAuth client; if the app is in Testing, include your Google account as a test user. Download the client JSON outside the repository. Set `authMode: "oauth"`, `oauthClientFile`, and a private writable `tokenFile`. Run:

```text
node --no-warnings scribe.mjs google-auth --config /ABSOLUTE/config.json
```

Open the printed Google authorization link on the same computer. The flow uses a temporary loopback listener, PKCE, a state check, and offline access. The refresh token stays on disk; never paste it into the workspace or chat. A browser on another machine needs explicit loopback forwarding; use service-account authentication for a headless server if appropriate. Testing-mode grants can expire; reauthorize if Google rejects the refresh credential. The requested scope is `https://www.googleapis.com/auth/documents`, which is broader than this one document. The implementation uses only the configured ID.

**Service account:** set `authMode: "service_account"` and `serviceAccountFile` to a private service-account JSON key. Share the destination Google Doc with that account's `client_email` as **Editor**. A service-account key alone does not grant access to your files. Domain-wide delegation is neither used nor needed. Your organization's sharing and key policies must permit this arrangement.

Fill `google.documentId` from the `/document/d/ID/edit` URL. Discover tab IDs with a read-only call:

```text
node --no-warnings scribe.mjs google-inspect --config /ABSOLUTE/config.json
```

Copy the intended tab's ID into `google.tabId`; then set `google.enabled: true`.

The first publish initializes a blank tab. For an existing nonempty tab, manually place the following exact markers on separate ordinary paragraphs, using your configured agent ID:

```text
[[PROJECT_SCRIBE_BEGIN:project-scribe]]
[[PROJECT_SCRIBE_END:project-scribe]]
```

Only the contents between these markers are owned by the package. Human notes outside them are preserved. Human edits inside the block are replaced on the next successful publish. Use plain text paragraphs inside the block: tables, objects, duplicate markers, and missing markers cause a refusal. The report is published as readable **Markdown text**, not converted to native Google heading or table styles. It uses an explicit tab ID, UTF-16 text positions, and required revision checks to avoid overwriting a concurrent unrelated edit.

## 7. Run once, then schedule

```text
node --no-warnings scribe.mjs run --config /ABSOLUTE/config.json
```

This calls the configured model and may incur its usual cost. It creates a historical Markdown/JSON pair, publishes when enabled, then updates `latest.md`, `latest.json`, and the processing checkpoint. Schema errors and invented evidence references stop publication. Google failures leave `pending-report.json`; the next run retries the **same report** without another model call. Successful retries are idempotent even after an ambiguous network response.

After a successful manual run:

```text
node --no-warnings scribe.mjs schedule --config /ABSOLUTE/config.json
node --no-warnings scribe.mjs schedule --config /ABSOLUTE/config.json --apply
```

The first command prints the exact argument array. The second checks support and registers an OpenClaw recurring command job at `schedule.every` (default `15m`). It uses `--command-argv`, `--command-cwd`, and `--no-deliver`; no chat channel is needed. The command job calls the controller, which then calls the synthesis agent. It is not an agent exec recursion. Scheduling requires a running local Gateway with administrator authority and access to these absolute paths and Git/OpenClaw executables. The Gateway must remain running for future updates.

Save the job ID in the schedule receipt. Inspect and manage it through:

```text
openclaw automations list
openclaw automations run JOB_ID
openclaw automations disable JOB_ID
openclaw automations remove JOB_ID
```

Do not create a second job just because a receipt was lost: inspect the list first. `schedule --apply` refuses when its local receipt already exists. Interval scheduling needs no timezone; it does not use a daily wall-clock schedule. Unchanged repositories with no new events skip the paid model call.

## Operations and limits

- `status` shows event count, checkpoint, pending publication, and spool count. `export --out /ABSOLUTE/events.jsonl` exports all normalized database records. Reports and event history are retained without automatic pruning.
- Reports process the oldest unprocessed events in bounded batches. Backlog counts are explicit. Historical reports retain older work; the Google block is the latest batch and Git snapshot, not a guaranteed all-time design specification. The session summary includes at most 200 recently observed sessions.
- One local run lock prevents overlapping report cycles. After a crash, inspect `stateDir/run.lock`, confirm its process has stopped, and remove only that lock file. Do not unlock a running report.
- If a failed publish is pending and you change config, the package refuses to mix destinations or evidence policies. Restore the prior config to retry, or archive the pending JSON to another filename and rerun; the unchanged cursor regenerates that batch.
- For a consistent SQLite backup, stop report jobs and coding clients first, then copy `stateDir` with any SQLite WAL files. Keep reports and credentials private. Unix files are created with restrictive modes; on Windows apply appropriate folder ACLs. No encryption-at-rest or remote collector is included.
- Git reads can race with simultaneous edits. Agent IDs establish callback attribution, not authorship of every changed line. An unchanged working tree can still have changing untracked file bytes. The package does not crawl every source file or parse historical transcripts.
- This is generic documentation infrastructure. It does not establish CSAW Challenge 3 compliance or reconstruct mandatory AI logs that were never captured. Supply your project requirements as explicitly configured source files if you want the report to discuss them.

## Troubleshooting and removal

Run `node --no-warnings scribe.mjs verify --config /ABSOLUTE/config.json` after an OpenClaw upgrade. It checks help surfaces rather than guessing unsupported flags. A configured model must work through the embedded OpenClaw runtime, not only through a CLI-only harness credential. If authentication fails, configure a compatible provider in OpenClaw.

No events: check the coding CLI's hook diagnostics, trust state, exact OS paths, selected worktree roots, and whether the session was restarted. Capture failures are intentionally nonblocking. Native Windows: check the Node/OpenClaw entry paths. Linux service: check its PATH or use absolute command paths. Google 403: verify the Docs API is enabled and the authenticated identity has edit access. Google 400: inspect markers and concurrent revisions. Persistent model JSON errors: try a model that follows the supplied JSON contract; no malformed report is published.

To remove: disable/remove the OpenClaw job first; remove only these hook entries from each named settings file (or carefully merge from its backup); then remove the dedicated agent with `openclaw agents delete AGENT_ID` if desired. That command affects its workspace/state, so keep your package reports and database backup first. The package does not modify your repository or delete your Google Doc during removal.
