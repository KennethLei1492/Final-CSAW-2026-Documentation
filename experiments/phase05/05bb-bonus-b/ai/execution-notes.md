# Execution and provenance notes

The user's complete task remains in the active Codex conversation. New code was
AI-authored by the root and delegated RTL agent; audit and documentation agents
reviewed separate files. This note is an execution summary, not a transcript.

The laboratory declares the synthetic message explicitly in inputs/message.txt.
The original candidates were inspected read-only; the source commit is pinned
before worktree creation. The current runtime is Codex/GPT-6, not the requested
Claude role label. No private transcript stores were opened or published.

One housekeeping Python `-c` invocation failed because Windows PowerShell
stripped embedded quotes, producing a SyntaxError before any code executed.
The test log was subsequently generated through the Python packaging script
with argument-vector execution and recorded exit status. This was not an RTL,
decoder, or build failure. Early discovery probes also found absent paths and
matched no wildcard manifest; discovery continued with the actual local paths.

Corruption and truncation are intentional software negative controls. Their
non-bit-exact results are retained and do not represent physical board tests.
No hardware execution was attempted: the enumerated serial ports were Bluetooth.
No known implementation or build failure remains after available verification.
The complete interaction transcript and historical provenance sufficiency are
still unverified; export the full relevant conversations locally for submission.
