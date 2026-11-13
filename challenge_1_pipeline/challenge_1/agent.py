#!/usr/bin/env python3
"""Entry point for challenge 1 (qualifying Trojan on the Hackster board).

Runs the Claude agent loop that inserts and verifies the key-leak Trojan in the
recovered qualifier accelerator. Offline modes let judges exercise the verify
path without an API key.

    python3 agent.py            # live: Claude generates/inserts/verifies (needs key)
    python3 agent.py --replay   # verify the shipped Trojan solution (offline)
    python3 agent.py --clean    # verify the clean recovered design (offline)
    python3 agent.py --area      # also report yosys iCE40 area
    python3 agent.py --steps 30  # cap agent model-calls
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # repo root, for `common`
sys.path.insert(0, HERE)                     # this dir, for `generate`/`verifier`

from common import runner                 # noqa: E402
import generate                            # noqa: E402
import verifier                            # noqa: E402

CFG = runner.ChallengeConfig(
    name="challenge_1",
    root=HERE,
    candidate_filename="crypto_core.v",
    pristine_rtl=os.path.join(HERE, "recovered_rtl", "crypto_core.v"),
    solution_rtl=os.path.join(HERE, "solution", "crypto_core_trojan.v"),
    verify=verifier.verify,
    is_success=generate.is_success,
    system_prompt=generate.SYSTEM_PROMPT,
    task_prompt=generate.build_task_prompt("crypto_core.v"),
)

if __name__ == "__main__":
    raise SystemExit(runner.main(CFG, sys.argv[1:]))
