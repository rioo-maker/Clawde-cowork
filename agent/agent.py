"""
Thin factory — selects Anthropic or Ollama agent based on settings.
Keeps a rolling session history so each task knows what was done before.
"""
from typing import Callable


def create_agent(settings: dict):
    """Return the right agent instance for the configured provider."""
    provider = settings.get("provider", "anthropic")
    if provider == "ollama":
        from llm.ollama_client import OllamaAgent
        return OllamaAgent(settings)
    else:
        from llm.anthropic_client import AnthropicAgent
        return AnthropicAgent(settings)


class Agent:
    """
    Wrapper that holds a provider agent and exposes run_task().
    Maintains a rolling history of completed tasks so the AI has context
    about what it already did in this session.
    Recreate (via CLI config menu) only when settings change.
    """
    _MAX_HISTORY = 5   # keep last N tasks in context

    def __init__(self, settings: dict):
        self._agent   = create_agent(settings)
        self._history: list[tuple[str, str]] = []   # [(task, summary), ...]

    def run_task(
        self,
        task: str,
        on_action: Callable | None = None,
        on_text:   Callable | None = None,
    ) -> str:
        # Build an enriched task string that includes recent session history
        full_task = self._with_context(task)

        result = self._agent.run_task(full_task, on_action=on_action, on_text=on_text)

        # Store original (short) task + summary for future context
        self._history.append((task, result))
        if len(self._history) > self._MAX_HISTORY:
            self._history.pop(0)

        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    def _with_context(self, task: str) -> str:
        if not self._history:
            return task
        lines = "\n".join(
            f"  [{i + 1}] {t}  →  {s}"
            for i, (t, s) in enumerate(self._history)
        )
        return (
            f"Session history (what you already did):\n{lines}\n\n"
            f"New task: {task}"
        )
