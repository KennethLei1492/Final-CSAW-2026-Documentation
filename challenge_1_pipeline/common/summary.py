"""Summarise a challenge's audit log for the judges / the submission README.

Reads ``<challenge>/ai/agent_log.jsonl`` and prints a compact, human-readable
account of the run(s): the model, how many turns, every tool call, and the final
verdict. This is the bridge between the raw, complete chat-history log (which the
rules require) and a reviewer who wants the story at a glance.

    python3 -m common.summary challenge_1/ai/agent_log.jsonl
"""

from __future__ import annotations

import json
import sys


def summarise(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            records = [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        return f"(no audit log at {path})"
    if not records:
        return f"(empty audit log at {path})"

    out = [f"# Audit-log summary: {path}", f"records: {len(records)}", ""]
    runs: dict[str, list] = {}
    for r in records:
        runs.setdefault(r.get("run_id", "?"), []).append(r)

    for run_id, rs in runs.items():
        start = next((r for r in rs if r.get("type") == "run_start"), {})
        end = next((r for r in rs if r.get("type") == "run_end"), {})
        model = start.get("model") or next((r.get("model") for r in rs
                                            if r.get("model")), "?")
        tool_calls = [r for r in rs if r.get("type") == "tool_call"]
        verdicts = [r for r in rs if r.get("type") == "verdict"]
        out.append(f"## run {run_id}")
        out.append(f"  model:        {model}")
        out.append(f"  started:      {start.get('ts', '?')}")
        out.append(f"  tool calls:   {len(tool_calls)}")
        counts: dict[str, int] = {}
        for t in tool_calls:
            counts[t["tool"]] = counts.get(t["tool"], 0) + 1
        if counts:
            out.append("    " + ", ".join(f"{k}x{v}" for k, v in counts.items()))
        if verdicts:
            v = verdicts[-1].get("verdict", {})
            flags = {k: v.get(k) for k in ("normal_ok", "trigger_fires", "area_ok")
                     if k in v}
            out.append(f"  last verdict: {flags}")
        out.append(f"  success:      {end.get('success')}")
        if end.get("submitted_note"):
            out.append(f"  trojan note:  {end['submitted_note']}")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "ai/agent_log.jsonl"
    print(summarise(target))
