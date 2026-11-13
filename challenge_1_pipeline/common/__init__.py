"""Shared library for the CSAW 2026 AI Hardware Attack pipeline.

The reusable pieces every challenge shares:
  * ``logger``       - append-only JSONL audit log of all chat history;
  * ``models``       - Claude-first provider switchboard + client factory;
  * ``tools``        - the agent's tools (read / write_rtl / run_verifier / ...);
  * ``claude_agent`` - the tool-using agent loop (the Claude-interface agent);
  * ``toolchain``    - Icarus Verilog / yosys helpers for the verifiers.

A per-challenge ``agent.py`` supplies the target (recovered RTL + interface
doc), the system/task prompts, and a ``verify()`` callable, then calls
``claude_agent.run_agent``.
"""
