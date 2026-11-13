"""The Claude agent loop - the core of the 2026 pipeline.

Where the 2025 pipeline called a model once per attempt and did the insert /
verify / retry in Python around it, the 2026 pipeline hands that whole loop to
Claude as a *tool-using agent*. Claude is given the recovered RTL, the interface
documentation, and a set of tools (read / write_rtl / run_verifier / ...); it
reads the design, writes a Trojan candidate, runs the verifier, reads the
simulator feedback, and iterates - all inside one conversation, with every turn
recorded to the audit log.

This is the "integrate an agent into the Claude interface" deliverable: a thin,
robust driver around Anthropic's Messages API tool-use protocol.

Termination:
  * success - the verifier accepts a candidate (checked after every tool batch);
  * the model ends its turn without tool use twice in a row (no progress);
  * ``max_steps`` model calls are reached.

On exit without success the work RTL is restored to the pristine recovered RTL,
so a failed run leaves the tree clean for the next one (mirrors CSAW25).
"""

from __future__ import annotations

import shutil
import time

from . import tools as tools_mod
from .models import is_transient, make_anthropic_client, DEFAULT_MAX_TOKENS


def _create_with_retry(client, logger, **kwargs):
    """messages.create with transient-error backoff (rate limit / 5xx)."""
    for retry in range(7):
        try:
            return client.messages.create(**kwargs)
        except Exception as exc:
            transient, delay = is_transient(exc)
            if not transient or retry == 6:
                raise
            logger.note(f"transient API error, retry {retry+1}/6 in {delay:g}s",
                        error=str(exc))
            print(f"Transient API error; retrying in {delay:g}s...")
            time.sleep(delay)


def run_agent(*, ctx: tools_mod.ToolContext, system_prompt: str,
              task_prompt: str, pristine_rtl_path: str | None = None,
              max_steps: int = 24, max_tokens: int = DEFAULT_MAX_TOKENS,
              client=None, model: str | None = None) -> dict:
    """Run the agentic generate/insert/verify/retry loop. Returns a result dict.

    ``ctx`` wires the tools to this challenge (paths + verify callable + logger).
    ``pristine_rtl_path`` and ``ctx.work_rtl_dir`` candidate file are used to
    restore a clean tree if the run does not converge.
    """
    logger = ctx.logger
    if client is None:
        client, model = make_anthropic_client()

    schemas = tools_mod.tool_schemas(area_check=ctx.area_check is not None)
    logger.run_start(max_steps=max_steps, max_tokens=max_tokens,
                     tools=[s["name"] for s in schemas])
    logger.system(system_prompt)
    logger.message("user", task_prompt, attempt=0)

    messages = [{"role": "user", "content": task_prompt}]
    success = False
    steps = 0
    empty_turns = 0

    try:
        while steps < max_steps:
            steps += 1
            response = _create_with_retry(
                client, logger,
                model=model, max_tokens=max_tokens, system=system_prompt,
                tools=schemas, messages=messages)

            # Record the assistant turn verbatim (text + thinking + tool_use).
            logger.message("assistant", response.content, attempt=steps,
                           stop_reason=response.stop_reason,
                           usage=getattr(response, "usage", None), model=model)
            messages.append({"role": "assistant",
                             "content": _blocks_to_params(response.content)})

            if response.stop_reason != "tool_use":
                # The model talked but took no action. Nudge once; stop if it
                # happens twice running (no progress).
                empty_turns += 1
                if empty_turns >= 2:
                    logger.note("stopping: two turns without tool use")
                    break
                nudge = ("You have not reached a passing verdict yet. Use "
                         "write_rtl to insert or refine the Trojan, then "
                         "run_verifier. Keep iterating until normal operation "
                         "is preserved AND the trigger fires.")
                logger.message("user", nudge)
                messages.append({"role": "user", "content": nudge})
                continue
            empty_turns = 0

            # Execute every tool_use block in this turn.
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                logger.tool_call(block.name, block.id, block.input)
                result_text, is_error = tools_mod.dispatch(ctx, block.name,
                                                           dict(block.input))
                logger.tool_result(block.name, block.id, result_text,
                                   is_error=is_error)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                    "is_error": is_error,
                })

            messages.append({"role": "user", "content": tool_results})
            logger.message("user", tool_results)

            # Did the latest verifier run (via run_verifier or submit) pass?
            if ctx.last_verdict is not None and ctx.is_success(ctx.last_verdict):
                success = True
                logger.note("verifier accepted a candidate", step=steps)
                break

        if not success and steps >= max_steps:
            logger.note(f"hit max_steps ({max_steps}) without success")

    finally:
        logger.run_end(success=success, steps=steps,
                       last_verdict=ctx.last_verdict,
                       submitted_note=ctx.submitted_note)
        if not success and pristine_rtl_path:
            try:
                dest = f"{ctx.work_rtl_dir}/{ctx.candidate_filename}"
                shutil.copyfile(pristine_rtl_path, dest)
                logger.note("restored pristine recovered RTL after failure")
            except OSError as exc:
                logger.note(f"failed to restore pristine RTL: {exc}")

    return {"success": success, "steps": steps,
            "verdict": ctx.last_verdict, "note": ctx.submitted_note}


def _blocks_to_params(content):
    """Normalise an assistant response's blocks into message-param dicts.

    Passing the SDK block objects straight back works, but turning them into
    plain dicts keeps the conversation we send independent of SDK object
    identity and mirrors exactly what the audit log stored.
    """
    params = []
    for block in content:
        btype = getattr(block, "type", None)
        if btype == "text":
            params.append({"type": "text", "text": block.text})
        elif btype == "thinking":
            params.append({"type": "thinking",
                           "thinking": getattr(block, "thinking", ""),
                           "signature": getattr(block, "signature", "")})
        elif btype == "tool_use":
            params.append({"type": "tool_use", "id": block.id,
                           "name": block.name, "input": block.input})
        else:  # unknown block: best-effort passthrough
            dump = getattr(block, "model_dump", None)
            params.append(dump() if callable(dump) else {"type": str(btype)})
    return params
