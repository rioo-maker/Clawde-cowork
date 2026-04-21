import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "settings.json"

DEFAULTS = {
    "provider": "anthropic",
    "anthropic_api_key": "",
    "anthropic_model": "claude-sonnet-4-6",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2-vision:11b",
    "ollama_api_key": "",          # For direct ollama.com cloud API
    "max_iterations": 50,
    "action_delay": 0.4,
    # Telegram bot — optional remote control
    "telegram_token": "",          # Bot token from @BotFather
    "telegram_allowed_ids": [],    # List of authorized Telegram user IDs (integers)
    # Auto-startup — managed via Windows Registry
    "autostart": False,
}


def load_settings() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return DEFAULTS.copy()


def save_settings(settings: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def get_api_key(settings: dict | None = None) -> str:
    """Return the Anthropic API key from env or config."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        s = settings or load_settings()
        key = s.get("anthropic_api_key", "")
    return key
