#!/usr/bin/env python3
"""Stage a comment-neutralized variant of the candidate RTL (finding §6).

Removes the comments that name the trojan ("AI-authored ... trigger and bounded
filter bypass", "payload", "AI-authored Q fix", "MAGIC_0") WITHOUT touching any
logic. Writes the proposed variant and a unified diff, then ASSERTS that every
differing line is a comment (`//`), so the change is provably non-behavioral
(identical synthesis netlist / untriggered output). The final candidate is NOT
modified; this is a reviewed proposal.

Usage:
    python -I destealth_comments.py --src <fir_audio_top.v> --out <variant.v> --diff <out.diff>
"""
import argparse
import difflib
from pathlib import Path

# exact source comment line -> neutral replacement (both are // comments)
REPLACE = {
    "    // AI-authored reliability-focused trigger and bounded filter bypass.":
        "    // Output-path selection stage.",
    "    // Match eight exact consecutive left-channel samples. On a full match,":
        "    // Compares the input word stream against a fixed reference sequence;",
    "    // pass the current and next 127 left samples directly to the output path.":
        "    // on a complete match, an alternate output source is selected for a bounded window.",
    "    // The existing serializer still supplies its original two-frame latency.":
        "    // The serializer still supplies the original two-frame latency.",
    "    // if that sample itself equals MAGIC_0. The matcher is clear during the":
        "    // if that sample equals the first reference word. The comparator is idle while",
    "    // payload and accepts a later trigger after the counter expires.":
        "    // the alternate-output window is active, and resumes after the counter expires.",
    "                    // This sample is already outside the 128-frame payload.":
        "                    // This sample is already outside the bounded window.",
    "                    // AI-authored Q fix: consume it as the next matcher's start.":
        "                    // Consume it as the next comparison's first word.",
}


def is_comment(line: str) -> bool:
    return line.strip().startswith("//")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--diff", required=True)
    args = ap.parse_args()

    src_lines = Path(args.src).read_text(encoding="utf-8").splitlines()
    out_lines, hits = [], 0
    for ln in src_lines:
        if ln in REPLACE:
            out_lines.append(REPLACE[ln]); hits += 1
        else:
            out_lines.append(ln)

    # verify: same line count, and every differing line is a comment on both sides
    assert len(out_lines) == len(src_lines), "line count changed"
    changed = [(a, b) for a, b in zip(src_lines, out_lines) if a != b]
    for a, b in changed:
        assert is_comment(a) and is_comment(b), f"non-comment change: {a!r} -> {b!r}"
    non_comment_src = [l for l in src_lines if not is_comment(l)]
    non_comment_out = [l for l in out_lines if not is_comment(l)]
    assert non_comment_src == non_comment_out, "a non-comment line differs"

    Path(args.out).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    diff = difflib.unified_diff(src_lines, out_lines,
                                fromfile="candidate/fir_audio_top.v",
                                tofile="proposed/fir_audio_top.v", lineterm="")
    Path(args.diff).write_text("\n".join(diff) + "\n", encoding="utf-8")

    print(f"replacements applied: {hits}/{len(REPLACE)}")
    print(f"lines changed: {len(changed)} (all comments)")
    print(f"non-comment (logic) lines identical: {non_comment_src == non_comment_out}")
    print(f"wrote {args.out} and {args.diff}")
    return 0 if hits == len(REPLACE) else 1


if __name__ == "__main__":
    raise SystemExit(main())
