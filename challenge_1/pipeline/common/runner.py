"""Shared entry-point logic for a challenge's ``agent.py``.

Each challenge's ``agent.py`` builds a :class:`ChallengeConfig` and calls
:func:`main`; everything common - seeding the work tree, wiring the tools to the
verifier, running the agent loop, and the offline ``--replay`` / ``--clean``
modes - lives here so the three challenges stay consistent.

Modes:
  (default)   run the Claude agent loop (needs ANTHROPIC_API_KEY).
  --replay    copy the shipped Trojan solution into the work tree and verify it
              (demonstrates the full verify path offline, no API key).
  --clean     verify the pristine recovered design (expect normal_ok, no trigger).
  --area      include the yosys iCE40 area/stealth estimate in the verdict.
  --steps N   cap the number of agent model-calls (default 24).
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Callable

from . import claude_agent, tools as tools_mod
from .logger import AuditLogger
from .models import anthropic_model
from .summary import summarise


@dataclass
class ChallengeConfig:
    name: str
    root: str                               # challenge dir (absolute)
    candidate_filename: str                 # e.g. "crypto_top.v"
    pristine_rtl: str                       # recovered_rtl/<candidate>
    solution_rtl: str                       # solution/<...>_trojan.v
    verify: Callable[..., dict]             # verify(rtl_path=None, area=False)
    is_success: Callable[[dict], bool]
    system_prompt: str
    task_prompt: str

    @property
    def work_rtl_dir(self) -> str:
        return os.path.join(self.root, "work", "rtl")

    @property
    def candidate_path(self) -> str:
        return os.path.join(self.work_rtl_dir, self.candidate_filename)

    @property
    def log_path(self) -> str:
        return os.path.join(self.root, "ai", "agent_log.jsonl")


def seed_work(cfg: ChallengeConfig) -> None:
    os.makedirs(cfg.work_rtl_dir, exist_ok=True)
    shutil.copyfile(cfg.pristine_rtl, cfg.candidate_path)


def _print_verdict(tag: str, v: dict) -> None:
    flags = {k: v.get(k) for k in ("normal_ok", "trigger_fires", "area_ok") if k in v}
    print(f"[{tag}] {flags}")


def cmd_clean(cfg: ChallengeConfig, area: bool) -> int:
    v = cfg.verify(cfg.pristine_rtl, area=area)
    print(v["raw"])
    _print_verdict("clean recovered design", v)
    # clean should preserve normal operation and NOT trigger
    ok = v.get("normal_ok") and not v.get("trigger_fires")
    print("clean baseline as expected (normal_ok, no trigger)" if ok
          else "unexpected: clean baseline verdict")
    return 0 if ok else 1


def cmd_replay(cfg: ChallengeConfig, area: bool) -> int:
    seed_work(cfg)
    shutil.copyfile(cfg.solution_rtl, cfg.candidate_path)
    v = cfg.verify(area=area)
    print(v["raw"])
    _print_verdict("replay shipped Trojan", v)
    ok = cfg.is_success(v)
    print("SUCCESS: shipped Trojan passes the verifier"
          if ok else "FAIL: shipped Trojan did not pass")
    return 0 if ok else 1


def cmd_run(cfg: ChallengeConfig, area: bool, max_steps: int) -> int:
    seed_work(cfg)
    model = anthropic_model()
    logger = AuditLogger(cfg.log_path, provider="anthropic", model=model,
                         challenge=cfg.name)
    ctx = tools_mod.ToolContext(
        challenge_root=cfg.root,
        work_rtl_dir=cfg.work_rtl_dir,
        candidate_filename=cfg.candidate_filename,
        verify=(lambda: cfg.verify(area=area)),
        is_success=cfg.is_success,
        logger=logger,
        area_check=(lambda: cfg.verify(area=True)["raw"]) if area else None,
    )
    result = claude_agent.run_agent(
        ctx=ctx, system_prompt=cfg.system_prompt, task_prompt=cfg.task_prompt,
        pristine_rtl_path=cfg.pristine_rtl, max_steps=max_steps, model=model)

    if result["success"]:
        # preserve the agent's converged Trojan next to the curated reference
        out = os.path.join(cfg.root, "solution",
                           cfg.candidate_filename.replace(".v", "_agent.v"))
        shutil.copyfile(cfg.candidate_path, out)
        print(f"SUCCESS in {result['steps']} steps. Agent Trojan saved to {out}")
    else:
        print(f"Did not converge in {result['steps']} steps "
              f"(max {max_steps}). Work tree restored to the clean design.")
    print()
    print(summarise(cfg.log_path))
    return 0 if result["success"] else 1


def main(cfg: ChallengeConfig, argv: list[str]) -> int:
    area = "--area" in argv
    max_steps = 24
    if "--steps" in argv:
        try:
            max_steps = int(argv[argv.index("--steps") + 1])
        except (ValueError, IndexError):
            pass
    os.makedirs(os.path.join(cfg.root, "ai"), exist_ok=True)
    if "--clean" in argv:
        return cmd_clean(cfg, area)
    if "--replay" in argv:
        return cmd_replay(cfg, area)
    return cmd_run(cfg, area, max_steps)
