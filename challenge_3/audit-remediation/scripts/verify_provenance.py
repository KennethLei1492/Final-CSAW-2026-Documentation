#!/usr/bin/env python3
"""Verify the AI-provenance archive against its SHA-256 index.

Non-destructive. Recomputes the SHA-256 and size of each archived rollout
transcript and compares against .state/phase-07-private/index.json, so the
provenance report can cite *verified* integrity rather than a bare claim.

Usage:
    python -I verify_provenance.py --archive <dir with index.json> [--json out.json]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_of(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True, help="dir containing index.json")
    ap.add_argument("--json", help="optional path to write a JSON summary")
    args = ap.parse_args()

    root = Path(args.archive)
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    rows = []
    ok = 0
    by_phase: dict[str, int] = {}
    total_bytes = 0
    for e in index:
        rel = e["archive_relative"]
        p = root / rel
        rec = {"phase": e["phase"], "archive_relative": rel,
               "expected_sha256": e["sha256"], "expected_bytes": e["bytes"]}
        if not p.exists():
            rec.update(status="MISSING")
        else:
            got, n = sha256_of(p)
            match = (got == e["sha256"]) and (n == e["bytes"])
            rec.update(status="OK" if match else "MISMATCH",
                       actual_sha256=got, actual_bytes=n)
            if match:
                ok += 1
                by_phase[e["phase"]] = by_phase.get(e["phase"], 0) + 1
                total_bytes += n
        rows.append(rec)
        print(f"[{rec['status']:8}] {e['phase']:4} {rel}  ({e['bytes']:,} B)")

    summary = {
        "archive": str(root),
        "transcripts_total": len(index),
        "verified_ok": ok,
        "by_phase": by_phase,
        "total_verified_bytes": total_bytes,
        "all_ok": ok == len(index),
        "rows": rows,
    }
    print(f"\n{ok}/{len(index)} transcripts verified; "
          f"by phase {by_phase}; {total_bytes:,} bytes total.")
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
