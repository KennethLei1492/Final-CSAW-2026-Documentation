"""Append-only JSONL audit logging for the CSAW 2026 AI Hardware Attack pipeline.

The competition rules are explicit: *"detailed logs need to be kept and included
in all submissions, detailing every interaction with AI. If a submission is made
without logs or the logs are missing key information, the submission may be
disqualified."*

This module records **all chat history** - every system prompt, user turn,
assistant turn (text, thinking, and tool-use blocks), tool result, verifier
verdict, and run-level event - as one JSON object per line in
``<challenge>/ai/agent_log.jsonl``. It is the direct successor of the CSAW25
``logger.py`` (which logged one record per generation attempt); here it is
widened to capture the full agentic conversation, because the 2026 pipeline runs
Claude as a tool-using agent rather than a single prompt/response.

Design goals:
  * append-only, one JSON object per line (grep/jq friendly, never rewritten);
  * never throw into the pipeline - a logging failure prints a warning and the
    run continues;
  * deterministic, serialisable records (Anthropic SDK blocks are normalised to
    plain dicts via ``normalise_content``);
  * a stable schema so judges (and ``summary.py``) can parse every entry.

Every record carries at least: ``ts`` (UTC ISO-8601), ``run_id`` (one agent
run), ``seq`` (monotonic within the run), and ``type``.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
import uuid
from typing import Any


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def normalise_content(content: Any) -> Any:
    """Turn Anthropic SDK content (blocks/objects) into JSON-serialisable data.

    Accepts a plain string, a list of block dicts, or a list of SDK block
    objects (which expose ``.model_dump()`` or ``.to_dict()``). Falls back to a
    best-effort ``repr`` so logging can never lose an interaction.
    """
    if content is None or isinstance(content, (str, int, float, bool)):
        return content
    if isinstance(content, dict):
        return {k: normalise_content(v) for k, v in content.items()}
    if isinstance(content, (list, tuple)):
        return [normalise_content(x) for x in content]
    for method in ("model_dump", "to_dict", "dict"):
        fn = getattr(content, method, None)
        if callable(fn):
            try:
                return normalise_content(fn())
            except Exception:  # pragma: no cover - defensive
                pass
    # Last resort: pull known block attributes off the object.
    out = {}
    for attr in ("type", "text", "thinking", "id", "name", "input",
                 "tool_use_id", "content", "is_error", "signature"):
        if hasattr(content, attr):
            out[attr] = normalise_content(getattr(content, attr))
    return out or repr(content)


class AuditLogger:
    """Append-only JSONL writer for one challenge's ``ai/agent_log.jsonl``.

    One ``AuditLogger`` instance is shared across a run so that every component
    (the agent loop, the tool dispatcher, the verifier) writes into the same
    ordered, sequence-numbered transcript.
    """

    def __init__(self, path: str, run_id: str | None = None,
                 provider: str | None = None, model: str | None = None,
                 challenge: str | None = None):
        self.path = path
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.provider = provider
        self.model = model
        self.challenge = challenge
        self._seq = 0
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    # -- low-level ---------------------------------------------------------
    def _write(self, record: dict) -> None:
        with self._lock:
            record = {
                "ts": _utcnow(),
                "run_id": self.run_id,
                "seq": self._seq,
                **record,
            }
            self._seq += 1
            try:
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, default=repr) + "\n")
            except Exception as exc:  # pragma: no cover - never break the run
                print(f"WARN: audit log write failed: {exc}")

    # -- high-level record types ------------------------------------------
    def run_start(self, **meta) -> None:
        self._write({"type": "run_start", "provider": self.provider,
                     "model": self.model, "challenge": self.challenge, **meta})

    def run_end(self, success: bool, **meta) -> None:
        self._write({"type": "run_end", "success": bool(success), **meta})

    def system(self, prompt: str) -> None:
        """Log the system prompt once per run (the agent's standing instructions)."""
        self._write({"type": "system", "role": "system", "text": prompt})

    def message(self, role: str, content: Any, *, attempt: int | None = None,
                stop_reason: str | None = None, usage: Any = None,
                model: str | None = None) -> None:
        """Log one chat message (user / assistant / tool_result turn).

        ``content`` may be a string or a list of Anthropic content blocks; it is
        normalised so tool-use and tool-result blocks are preserved verbatim.
        """
        self._write({
            "type": "message",
            "role": role,
            "attempt": attempt,
            "model": model or self.model,
            "stop_reason": stop_reason,
            "usage": normalise_content(usage) if usage is not None else None,
            "content": normalise_content(content),
        })

    def tool_call(self, name: str, tool_use_id: str, tool_input: Any) -> None:
        self._write({"type": "tool_call", "tool": name,
                     "tool_use_id": tool_use_id,
                     "input": normalise_content(tool_input)})

    def tool_result(self, name: str, tool_use_id: str, result: Any,
                    is_error: bool = False) -> None:
        self._write({"type": "tool_result", "tool": name,
                     "tool_use_id": tool_use_id, "is_error": bool(is_error),
                     "result": normalise_content(result)})

    def verdict(self, attempt: int, verdict: dict) -> None:
        """Log a verifier verdict (normal_ok / trigger_fires / area_ok / raw)."""
        self._write({"type": "verdict", "attempt": attempt,
                     "verdict": normalise_content(verdict)})

    def note(self, text: str, **meta) -> None:
        self._write({"type": "note", "text": text, **meta})

    # -- CSAW25-compatible convenience ------------------------------------
    def attempt(self, attempt: int, prompt: str, output: str, verdict: dict,
                provider: str | None = None, model: str | None = None) -> None:
        """One self-contained attempt record, matching the CSAW25 schema.

        Kept so that tooling written against the 2025 ``agent_log.jsonl`` (and
        the ``rebuild_from_scratch.sh`` summary parser) still works: it reads
        ``verdict.normal_ok`` / ``trigger_fires`` / ``area_ok`` from the last
        line of the log.
        """
        self._write({
            "type": "attempt",
            "attempt": attempt,
            "provider": provider or self.provider,
            "model": model or self.model,
            "prompt": prompt,
            "generated_output": output,
            "verdict": normalise_content(verdict),
        })


# -- module-level shim: a drop-in for CSAW25 `from logger import log` ---------
_DEFAULT_PATH = os.path.join("ai", "agent_log.jsonl")


def log(attempt, prompt, output, verdict, provider=None, model=None,
        path: str = _DEFAULT_PATH):
    """CSAW25-compatible append of one attempt to ``ai/agent_log.jsonl``."""
    AuditLogger(path, provider=provider, model=model).attempt(
        attempt, prompt, output, verdict, provider=provider, model=model)
