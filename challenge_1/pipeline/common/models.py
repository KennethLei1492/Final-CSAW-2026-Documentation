"""Model provider switchboard for the CSAW 2026 pipeline - Claude-first.

The 2025 pipeline was provider-agnostic (Anthropic / OpenAI / Google) and ran on
a free Gemini tier. For 2026 the task is to *integrate an agent into the Claude
interface*, so the default and the agentic path are Anthropic's Claude: this
module creates the ``anthropic.Anthropic`` client and names the model, and
``common/claude_agent.py`` drives the tool-using loop on top of it.

The switchboard is kept (and ``call_model`` still works for a single-shot,
non-agentic generation) so the framework stays config-driven and a reviewer can
swap the model without touching the loop - but the pipeline's headline mode is
Claude as a tool-using agent.

Environment:
  * ``ANTHROPIC_API_KEY``  - required for the Claude path (default).
  * ``CSAW_CLAUDE_MODEL``  - optional override of the model id.
"""

from __future__ import annotations

import importlib
import os
import sys
import time

# Current Claude model for the pipeline. Override with CSAW_CLAUDE_MODEL.
DEFAULT_ANTHROPIC_MODEL = os.environ.get("CSAW_CLAUDE_MODEL", "claude-opus-4-8")
DEFAULT_MAX_TOKENS = 16000

PROVIDERS = {
    "anthropic": {"env_key": "ANTHROPIC_API_KEY", "pip_package": "anthropic",
                  "import_name": "anthropic"},
    "openai": {"env_key": "OPENAI_API_KEY", "pip_package": "openai",
               "import_name": "openai"},
    "google": {"env_key": "GOOGLE_API_KEY", "pip_package": "google-genai",
               "import_name": "google.genai"},
}


def setup_model(provider: str) -> str:
    """Validate a provider's SDK and API key; return the key (or exit clearly)."""
    info = PROVIDERS.get(provider)
    if info is None:
        sys.exit(f"Unknown model provider {provider!r}; choose one of: "
                 f"{', '.join(PROVIDERS)}")
    try:
        importlib.import_module(info["import_name"])
    except ImportError:
        sys.exit(f"SDK for provider {provider!r} is not installed. Install it "
                 f"with: {sys.executable} -m pip install {info['pip_package']}")
    key = os.environ.get(info["env_key"])
    if not key:
        sys.exit(f"Missing API key for provider {provider!r}: set the "
                 f"{info['env_key']} environment variable.")
    return key


def anthropic_model() -> str:
    return DEFAULT_ANTHROPIC_MODEL


def make_anthropic_client():
    """Return ``(client, model)`` for the agentic Claude loop."""
    key = setup_model("anthropic")
    import anthropic
    return anthropic.Anthropic(api_key=key), DEFAULT_ANTHROPIC_MODEL


def is_transient(exc) -> tuple[bool, float]:
    """Classify an SDK exception as transient (rate limit / 5xx) and suggest a delay."""
    message = str(exc)
    status = getattr(exc, "status_code", None)
    rate_limited = (status == 429 or "429" in message
                    or "rate limit" in message.lower()
                    or "overloaded" in message.lower())
    server_error = status in (500, 503, 529) or any(
        code in message for code in ("500", "503", "529"))
    if not rate_limited and not server_error:
        return False, 0.0
    # Honour Retry-After when present.
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", {}) or {}
    retry_after = headers.get("retry-after") if hasattr(headers, "get") else None
    if retry_after is not None:
        try:
            return True, float(retry_after)
        except (TypeError, ValueError):
            pass
    return True, 30.0 if rate_limited else 6.0


def call_model(provider, system, user, max_tokens=DEFAULT_MAX_TOKENS):
    """Single-shot generation (non-agentic fallback). Returns reply text.

    Retained from the 2025 pipeline for a simple generate-only mode and for
    providers other than Anthropic. The main 2026 path is the agentic loop in
    ``claude_agent.py``, not this function.
    """
    key = setup_model(provider)

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        for retry in range(7):
            try:
                response = client.messages.create(
                    model=DEFAULT_ANTHROPIC_MODEL,
                    max_tokens=max(max_tokens, DEFAULT_MAX_TOKENS),
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(getattr(b, "text", "") for b in response.content)
                if not text:
                    raise RuntimeError(f"no text blocks; stop_reason="
                                       f"{response.stop_reason!r}")
                return text
            except Exception as exc:
                transient, delay = is_transient(exc)
                if not transient or retry == 6:
                    raise
                print(f"Transient API error; retrying in {delay:g}s...")
                time.sleep(delay)

    if provider == "google":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        model = os.environ.get("CSAW_GOOGLE_MODEL", "gemini-3.5-flash-lite")
        response = client.models.generate_content(
            model=model, contents=f"{system}\n\n{user}",
            config=types.GenerateContentConfig(max_output_tokens=65536))
        return response.text

    if provider == "openai":
        import openai
        client = openai.OpenAI(api_key=key)
        model = os.environ.get("CSAW_OPENAI_MODEL", "gpt-5")
        response = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return response.choices[0].message.content

    sys.exit(f"Unsupported model provider {provider!r}")


if __name__ == "__main__":
    prov = sys.argv[1] if len(sys.argv) == 2 else "anthropic"
    setup_model(prov)
    extra = f" (model {DEFAULT_ANTHROPIC_MODEL})" if prov == "anthropic" else ""
    print(f"Provider {prov!r} is configured and ready{extra}.")
