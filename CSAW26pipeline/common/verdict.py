"""Turn a simulator log into a structured verdict.

Every challenge's exploit testbench prints the same machine-readable markers on
their own lines:

    NORMAL_OK      | NORMAL_FAIL       normal operation preserved (Trojan dormant)
    TRIGGER_FIRES  | TRIGGER_NONE      the trigger fired and the payload executed
    AREA_OK        | AREA_OVER         (optional) resource overhead within budget

``parse_markers`` reduces a log to ``{normal_ok, trigger_fires, ...}`` so the
agent, the loop, and the summary all read the same verdict shape the CSAW25
pipeline used.
"""

from __future__ import annotations


def parse_markers(output: str) -> dict:
    """Extract the last occurrence of each marker from a simulator log."""
    normal_ok = trigger = None
    area_ok = None
    for line in output.splitlines():
        s = line.strip()
        if s == "NORMAL_OK":
            normal_ok = True
        elif s == "NORMAL_FAIL":
            normal_ok = False
        elif s == "TRIGGER_FIRES":
            trigger = True
        elif s == "TRIGGER_NONE":
            trigger = False
        elif s == "AREA_OK":
            area_ok = True
        elif s == "AREA_OVER":
            area_ok = False
    verdict = {"normal_ok": bool(normal_ok), "trigger_fires": bool(trigger)}
    if area_ok is not None:
        verdict["area_ok"] = bool(area_ok)
    return verdict


def classify_failure(output: str) -> str:
    """A short hint appended to the raw log to help the model (and humans)."""
    low = output.lower()
    if "[iverilog compile failed]" in low or "error:" in low or "syntax error" in low:
        return "classification: the candidate RTL did not compile."
    if "timeout" in low:
        return "classification: simulation timed out (possible deadlock / bad FSM)."
    if "normal_fail" in low:
        return ("classification: normal operation is broken - the design must "
                "behave correctly with the Trojan dormant before the trigger "
                "matters.")
    if "trigger_none" in low:
        return ("classification: normal operation is preserved but the trigger "
                "never fired - the payload did not execute under the trigger "
                "condition.")
    return "classification: see the simulator log above."
