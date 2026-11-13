"""Tool definitions and dispatch for the Claude agent.

These are the capabilities Claude is given so it can drive the whole
generate -> insert -> verify -> retry loop itself, rather than being called once
for a blob of text. Exposing insertion and verification *as tools the model
invokes* is what moves the pipeline from "prompt engineering" toward the
rubric's top band ("agentic loops with tool use ... AI authors the design,
insertion, and iteration").

Tools (all scoped to one challenge's working tree):
  * ``list_dir``      - see the recovered RTL, interface doc, and testbench.
  * ``read_file``     - read any of those (and the growing audit log).
  * ``write_rtl``     - write a candidate Verilog file into the work RTL dir.
  * ``run_verifier``  - simulate the candidate: normal-operation check + exploit
                        testbench; returns the structured verdict.
  * ``run_area_check``- optional yosys iCE40 area/stealth estimate.
  * ``submit``        - the agent declares a candidate final (the loop still
                        confirms with the verifier before accepting).

Every call and result is written to the audit log by the dispatcher, so the
transcript records exactly what the agent read, wrote, and observed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

from . import toolchain

MAX_READ_BYTES = 200_000
MAX_RESULT_CHARS = 20_000      # keep tool results from blowing the context window


def tool_schemas(area_check: bool = True) -> list[dict]:
    """Anthropic tool schema list advertised to the model."""
    schemas = [
        {
            "name": "list_dir",
            "description": "List files in a directory of the challenge working "
                           "tree (e.g. the recovered RTL, the interface doc, or "
                           "the testbench). Use this first to see what you have.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string",
                    "description": "Directory relative to the challenge root. "
                                   "Use '.' for the root."}},
                "required": ["path"],
            },
        },
        {
            "name": "read_file",
            "description": "Read a UTF-8 text file (recovered RTL, interface "
                           "documentation, exploit testbench, or the audit log) "
                           "from the challenge working tree.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string",
                    "description": "File path relative to the challenge root."}},
                "required": ["path"],
            },
        },
        {
            "name": "write_rtl",
            "description": "Write a candidate Verilog/SystemVerilog file into the "
                           "work RTL directory. This is how you insert your "
                           "Trojan: provide the COMPLETE file contents. Writing "
                           "the module that the testbench instantiates replaces "
                           "the current candidate for the next verification.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string",
                        "description": "Base filename only, e.g. 'crypto_top.v'. "
                                       "It is written into the work RTL dir."},
                    "content": {"type": "string",
                        "description": "The entire file contents (no markdown "
                                       "fences)."},
                },
                "required": ["filename", "content"],
            },
        },
        {
            "name": "run_verifier",
            "description": "Simulate the current candidate RTL. Runs the "
                           "normal-operation check (the design must still behave "
                           "correctly, Trojan dormant) and the exploit testbench "
                           "(the trigger must fire and the payload must be "
                           "observed). Returns a JSON verdict with normal_ok, "
                           "trigger_fires, and the full simulator log. Call this "
                           "after every write_rtl.",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]
    if area_check:
        schemas.append({
            "name": "run_area_check",
            "description": "Synthesise the current candidate for the iCE40-UP5K "
                           "with yosys and report cell/LUT usage, to judge how "
                           "stealthy (small) the Trojan is versus the clean "
                           "baseline. Optional.",
            "input_schema": {"type": "object", "properties": {}},
        })
    schemas.append({
        "name": "submit",
        "description": "Declare that the current candidate is your final Trojan. "
                       "Provide a short note on the trigger and payload. The loop "
                       "will run the verifier once more to confirm before "
                       "accepting; if it does not pass you should keep iterating.",
        "input_schema": {
            "type": "object",
            "properties": {"note": {"type": "string",
                "description": "One or two sentences: the trigger and the payload."}},
            "required": ["note"],
        },
    })
    return schemas


@dataclass
class ToolContext:
    """Everything the dispatcher needs, wired by a challenge's ``agent.py``."""
    challenge_root: str                 # absolute path, the sandbox boundary
    work_rtl_dir: str                   # where write_rtl lands (inside the root)
    candidate_filename: str             # the module the testbench instantiates
    verify: Callable[[], dict]          # returns {normal_ok, trigger_fires, raw, ...}
    is_success: Callable[[dict], bool]
    logger: object                      # AuditLogger
    area_check: Callable[[], str] | None = None
    last_verdict: dict | None = field(default=None)
    submitted_note: str | None = field(default=None)

    # -- path safety -------------------------------------------------------
    def _resolve(self, rel: str) -> str:
        p = os.path.realpath(os.path.join(self.challenge_root, rel))
        root = os.path.realpath(self.challenge_root)
        if p != root and not p.startswith(root + os.sep):
            raise ValueError(f"path {rel!r} escapes the challenge directory")
        return p


def _truncate(text: str) -> str:
    if len(text) <= MAX_RESULT_CHARS:
        return text
    head = text[: MAX_RESULT_CHARS // 2]
    tail = text[-MAX_RESULT_CHARS // 2:]
    return f"{head}\n...[{len(text) - MAX_RESULT_CHARS} chars elided]...\n{tail}"


def dispatch(ctx: ToolContext, name: str, tool_input: dict) -> tuple[str, bool]:
    """Execute one tool call. Returns ``(result_text, is_error)``."""
    try:
        if name == "list_dir":
            path = ctx._resolve(tool_input.get("path", "."))
            if not os.path.isdir(path):
                return f"Not a directory: {tool_input.get('path')!r}", True
            entries = []
            for e in sorted(os.listdir(path)):
                full = os.path.join(path, e)
                kind = "dir " if os.path.isdir(full) else "file"
                size = os.path.getsize(full) if os.path.isfile(full) else 0
                entries.append(f"  [{kind}] {e}" + (f" ({size} B)" if size else ""))
            return "\n".join(entries) or "(empty)", False

        if name == "read_file":
            path = ctx._resolve(tool_input["path"])
            if not os.path.isfile(path):
                return f"No such file: {tool_input['path']!r}", True
            with open(path, "rb") as fh:
                data = fh.read(MAX_READ_BYTES + 1)
            text = data[:MAX_READ_BYTES].decode("utf-8", errors="replace")
            if len(data) > MAX_READ_BYTES:
                text += f"\n...[truncated at {MAX_READ_BYTES} bytes]..."
            return text, False

        if name == "write_rtl":
            fname = os.path.basename(tool_input["filename"])
            if not fname:
                return "filename must be a non-empty base filename", True
            os.makedirs(ctx.work_rtl_dir, exist_ok=True)
            dest = os.path.join(ctx.work_rtl_dir, fname)
            content = tool_input.get("content", "")
            content = _strip_fences(content)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(content if content.endswith("\n") else content + "\n")
            return (f"Wrote {len(content)} bytes to work RTL as {fname}. "
                    f"Run run_verifier to test it."), False

        if name == "run_verifier":
            verdict = ctx.verify()
            ctx.last_verdict = verdict
            ctx.logger.verdict(attempt=-1, verdict=verdict)
            summary = {k: verdict.get(k) for k in
                       ("normal_ok", "trigger_fires", "area_ok")
                       if k in verdict}
            raw = verdict.get("raw", "")
            return (f"verdict: {summary}\n\n--- simulator log ---\n{_truncate(raw)}"), False

        if name == "run_area_check":
            if ctx.area_check is None:
                return "Area check is not configured for this challenge.", False
            return _truncate(ctx.area_check()), False

        if name == "submit":
            ctx.submitted_note = tool_input.get("note", "")
            verdict = ctx.verify()
            ctx.last_verdict = verdict
            ctx.logger.verdict(attempt=-1, verdict=verdict)
            if ctx.is_success(verdict):
                return "Confirmed: the verifier accepts this candidate. Done.", False
            summary = {k: verdict.get(k) for k in ("normal_ok", "trigger_fires")
                       if k in verdict}
            return (f"Not accepted yet: {summary}. Keep iterating.\n\n"
                    f"--- simulator log ---\n{_truncate(verdict.get('raw',''))}"), False

        return f"Unknown tool: {name!r}", True
    except Exception as exc:  # surfaced back to the model so it can adapt
        return f"Tool {name!r} raised: {type(exc).__name__}: {exc}", True


def _strip_fences(text: str) -> str:
    """Remove a leading/trailing markdown code fence if the model added one."""
    t = text.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        t = t[nl + 1:] if nl != -1 else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3].rstrip()
    return t
