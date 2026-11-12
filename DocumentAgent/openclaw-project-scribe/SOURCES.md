# Source and command verification

Official documentation checked on **2026-11-12**. These are documentation-verified interfaces. The package's local tests do not substitute for testing your installed OpenClaw version or your Google account. No OpenClaw executable was available in the build environment; setup and `verify` therefore include installed-CLI capability checks that you run on the target host.

| Source | Interface checked / package use |
|---|---|
| [OpenClaw getting started](https://docs.openclaw.ai/start/getting-started) | Installation, onboarding, Gateway prerequisites and supported Node lines. The package does not install or upgrade OpenClaw globally. |
| [OpenClaw agents CLI](https://docs.openclaw.ai/cli/agents) | `agents list --json`; `agents add NAME --workspace PATH --model MODEL --non-interactive`; workspace reuse and current Gateway state ownership. |
| [OpenClaw agent CLI](https://docs.openclaw.ai/cli/agent) | `agent --agent ID --session-id ID --message-file PATH --timeout SECONDS --json`; controller invokes a Gateway-backed turn with a unique session. JSON adapter accepts top-level payloads/final and the result-wrapped payload form; unknown shapes fail. |
| [OpenClaw configuration CLI](https://docs.openclaw.ai/cli/config) | `config get PATH --json`, `config patch --file PATH --dry-run`, patch application, `config validate`. Structured patch avoids shell quoting of nested config. |
| [OpenClaw agent entries](https://docs.openclaw.ai/gateway/config-agents/entries-and-multi-agent) | Uses the current `agents.entries` map, per-agent model, workspace, skills, tools and subagent restrictions. |
| [OpenClaw runtime configuration](https://docs.openclaw.ai/gateway/config-agents/runtime-and-cli-backends) | Pins `models[provider/model].agentRuntime.id` to `openclaw` within the selected agent entry. Avoids retired whole-agent runtime settings. |
| [OpenClaw tool policy](https://docs.openclaw.ai/gateway/config-tools/tool-policy) | Tool deny policy supports `*`; this agent receives a deny-all policy. Controller checks the authored policy before each synthesis. |
| [OpenClaw skills](https://docs.openclaw.ai/tools/skills) | Local agent skill lives at `<workspace>/skills/project-documentation/SKILL.md` with name/description frontmatter. The controller also includes its instructions directly in the prompt. |
| [OpenClaw workspace context](https://docs.openclaw.ai/gateway/config-agents/workspace-and-bootstrap) | Per-agent `contextInjection: "never"` avoids generic bootstrap injection. The controller explicitly supplies its installed role, personality and skill files. |
| [OpenClaw automations CLI](https://docs.openclaw.ai/cli/cron) | `automations` aliases `cron`; `create --every ... --command-argv ... --command-cwd ... --timeout-seconds ... --no-deliver`. Uses an operator command job, not an agent exec callback. A running Gateway and administrator authority are required. |
| [OpenClaw Gateway CLI](https://docs.openclaw.ai/cli/gateway) | Gateway status and service readiness diagnostics. |
| [OpenClaw models CLI](https://docs.openclaw.ai/cli/models) | Lists configured models; user supplies a compatible provider/model and credentials. |
| [Claude Code hook reference](https://code.claude.com/docs/en/hooks) | Direct executable plus `args`, JSON stdin, session/tool/stop/subagent events, separate `PostToolUseFailure`, timeout behavior. Captures selected fields only. |
| [Codex hooks, official OpenAI documentation](https://learn.chatgpt.com/docs/hooks) | `hooks.json` discovery, hook review through `/hooks`, `commandWindows`, session/tool/stop/subagent event schemas. Stop returns JSON. Tool failures are covered by PostToolUse; no invented Codex failure-hook name. |
| [Google Docs tabs](https://developers.google.com/workspace/docs/api/how-tos/tabs) | Reads document tabs explicitly and selects the configured tab, including nested tabs. |
| [Google Docs batchUpdate](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate) | Atomic request batch with `writeControl.requiredRevisionId`; concurrent edits require rereading. |
| [Google Docs requests](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request) and [document structures](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents) | `insertText`, `deleteContentRange`, text-run start indexes and tab-aware ranges. JavaScript string lengths preserve UTF-16 index semantics. |
| [Google OAuth desktop apps](https://developers.google.com/identity/protocols/oauth2/native-app) | Desktop client, loopback redirect, authorization code with PKCE, state validation and refresh credentials. |
| [Google service-account OAuth](https://developers.google.com/identity/protocols/oauth2/service-account) | Signed RS256 JWT token exchange for the Docs scope. The target document must separately be shared to the service account. |

## What is checked on installation

`setup --apply` asks the installed CLI for its version and help surfaces, confirms the flags it will use, validates the generated patch before applying it, and then validates the resulting configuration. `verify` also checks command-job scheduling flags. An incompatible CLI stops with an actionable error instead of silently falling back to an older syntax.

This verifies local command availability and config acceptance. The first real `run` checks provider authentication and actual JSON output. Google authorization and the first publish check account permissions and the live Docs API. Those live checks require your supplied values.

## Differences from the referenced chat's sketches

This is an implementation with tests, not the earlier illustrative Python snippets. It uses the current agent-entry schema, explicit command-job scheduling, a tool-free synthesis agent, bounded evidence batches, publication checkpoints, retry-safe managed sections, tab IDs, and built-in Node SQLite. It does not assume every CLI exposes identical hook events, that session log paths are required, or that agent claims establish successful tests.
