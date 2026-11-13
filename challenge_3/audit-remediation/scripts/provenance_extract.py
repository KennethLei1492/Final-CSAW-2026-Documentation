#!/usr/bin/env python3
"""Extract SAFE, submission-grade provenance metrics from the AI transcripts.

Reads the 11 archived rollout transcripts and emits aggregate provenance
evidence for the Creative-Use-of-GenAI category: per-candidate model ids,
record/role counts, tool-activity counts, session timespans, and build/test
("test-in-the-loop") activity markers.

SAFETY: emits only aggregate counts, detected model ids, and timestamps. It
never writes message content, and it refuses to emit anything matching an
email / token / home-path (so the output is safe for a public repo). It does
not surface transcript content to the caller.

Usage:
    python -I provenance_extract.py --archive <dir/with/index.json> --out <dir>
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

MODEL_RE = re.compile(r"(?i)\b(gpt-[0-9][0-9a-z.\-]{0,20}|claude-(?:opus|sonnet|haiku)[0-9a-z.\-]{0,20}|claude-[0-9][0-9a-z.\-]{0,20}|o[0-9]-[a-z0-9.\-]{1,20})\b")
TS_RE = re.compile(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
TOOLWORDS = ["iverilog", "vvp", "yosys", "nextpnr", "icepack", "icetime",
             "run.py", "validate", "pytest", "manifest.json", "prepare_vectors",
             "candidate_reference", ".pcf", "synth", "testbench", "tb_i2s",
             "apply_patch", "shell", "read_file", "update_plan"]
# forbidden in OUTPUT (PII / secrets) -- we assert the emitted files are clean
PII_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|gh[pousr]_[A-Za-z0-9]{20,}|/c/Users/[^/\s]+|C:\\\\Users\\\\[^\\\s]+")


def scan_file(path: Path) -> dict:
    types = Counter()
    roles = Counter()
    models = Counter()
    tools = 0
    toolhits = Counter()
    ts_min = ts_max = None
    records = 0
    for line in path.open("r", encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        records += 1
        try:
            o = json.loads(line)
        except Exception:
            types["<unparsed>"] += 1
            continue
        t = o.get("type") or o.get("record_type") or "<none>"
        types[str(t)] += 1
        r = o.get("role")
        if not r and isinstance(o.get("message"), dict):
            r = o["message"].get("role")
        if r:
            roles[str(r)] += 1
        # tool/function activity (schema-tolerant, name-level only)
        if any(k in line for k in ('"function_call"', '"tool_use"', '"tool_result"',
                                   '"tool_calls"', '"local_shell_call"', '"custom_tool_call"')):
            tools += 1
        for m in MODEL_RE.findall(line):
            models[m.lower()] += 1
        for w in TOOLWORDS:
            if w in line:
                toolhits[w] += 1
        for ts in TS_RE.findall(line):
            if ts_min is None or ts < ts_min:
                ts_min = ts
            if ts_max is None or ts > ts_max:
                ts_max = ts
    return {"records": records, "types": dict(types.most_common()),
            "roles": dict(roles), "models": dict(models.most_common()),
            "tool_activity_records": tools,
            "build_test_markers": dict(toolhits.most_common()),
            "ts_min": ts_min, "ts_max": ts_max}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.archive)
    out = Path(args.out)
    (out / "digests").mkdir(parents=True, exist_ok=True)
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    per_file = []
    for e in index:
        s = scan_file(root / e["archive_relative"])
        s["phase"] = e["phase"]
        s["archive_relative"] = e["archive_relative"]
        s["bytes"] = e["bytes"]
        per_file.append(s)

    # aggregate per candidate
    cands = {}
    for s in per_file:
        c = cands.setdefault(s["phase"], {"sessions": 0, "records": 0,
            "tool_activity_records": 0, "models": Counter(),
            "build_test_markers": Counter(), "roles": Counter(),
            "ts_min": None, "ts_max": None, "bytes": 0})
        c["sessions"] += 1
        c["records"] += s["records"]
        c["tool_activity_records"] += s["tool_activity_records"]
        c["bytes"] += s["bytes"]
        c["models"].update(s["models"])
        c["build_test_markers"].update(s["build_test_markers"])
        c["roles"].update(s["roles"])
        for k in ("ts_min", "ts_max"):
            v = s[k]
            if v and (c[k] is None or (v < c[k] if k == "ts_min" else v > c[k])):
                c[k] = v
    for c in cands.values():
        c["models"] = dict(c["models"].most_common())
        c["build_test_markers"] = dict(c["build_test_markers"].most_common())
        c["roles"] = dict(c["roles"])

    agent_by_phase = {"05A": "Codex (OpenAI)", "05B": "Codex (OpenAI)",
                      "05C": "Claude", "05D": "Claude"}
    metrics = {"schema_version": 1, "generated": "2026-11-13",
               "archive": "state/phase-07-private (private, gitignored)",
               "transcripts": len(per_file),
               "candidates": {k: {**v, "agent": agent_by_phase.get(k, "?")}
                              for k, v in sorted(cands.items())},
               "per_transcript": per_file}

    metrics_path = out / "provenance-metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    # per-candidate sanitized digest (for downstream characterization)
    for k, c in sorted(cands.items()):
        d = [f"# Provenance digest — candidate {k} ({agent_by_phase.get(k,'?')})",
             "",
             f"- Sessions (transcripts): {c['sessions']}",
             f"- Total records: {c['records']:,}",
             f"- Role counts: {c['roles']}",
             f"- Tool/function-call records: {c['tool_activity_records']:,}",
             f"- Model identifiers detected: {c['models']}",
             f"- Session timespan: {c['ts_min']} .. {c['ts_max']}",
             f"- Build/test activity markers (name-level counts): {c['build_test_markers']}",
             f"- Archived bytes: {c['bytes']:,}",
             "",
             "(Structural provenance only — no message content, no exploit design.)"]
        (out / "digests" / f"{k}.md").write_text("\n".join(d) + "\n", encoding="utf-8")

    # SAFETY: assert emitted files carry no PII/secrets
    bad = []
    for p in [metrics_path, *sorted((out / "digests").glob("*.md"))]:
        hits = PII_RE.findall(p.read_text(encoding="utf-8"))
        if hits:
            bad.append((p.name, hits[:3]))
    if bad:
        raise SystemExit(f"REFUSING: PII/secret-like content in output: {bad}")

    # console summary (safe)
    print(f"transcripts scanned: {len(per_file)}")
    for k, c in sorted(cands.items()):
        print(f"  {k} [{agent_by_phase.get(k)}]: {c['sessions']} sessions, "
              f"{c['records']:,} records, {c['tool_activity_records']:,} tool records, "
              f"models={list(c['models'])}, span {c['ts_min']}..{c['ts_max']}")
    print(f"PII/secret scan of outputs: CLEAN")
    print(f"wrote {metrics_path} and {len(cands)} digests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
