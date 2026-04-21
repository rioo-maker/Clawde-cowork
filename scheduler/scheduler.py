"""
Task Scheduler for SudoAgent.

Schedules are stored in config/schedules.json as a list:
  [
    {
      "id": "a1b2c3d4",
      "name": "Morning routine",
      "time": "08:00",            ← HH:MM (24-hour clock)
      "days": ["mon","tue","wed","thu","fri"],  ← or ["daily"]
      "task": "open chrome and open gmail",
      "enabled": true
    },
    ...
  ]

The scheduler checks every 30 seconds.  Tasks fire at most once per
HH:MM slot per calendar day (tracked in self._fired_today).
"""
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

SCHEDULES_PATH = Path(__file__).parent.parent / "config" / "schedules.json"

# Canonical day abbreviations (index = weekday() value)
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DAY_NUM = {d: i for i, d in enumerate(_DAYS)}


# ── persistence ───────────────────────────────────────────────────────────────

def load_schedules() -> list[dict]:
    if SCHEDULES_PATH.exists():
        try:
            with open(SCHEDULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_schedules(schedules: list[dict]) -> None:
    SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULES_PATH, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2, ensure_ascii=False)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def add_schedule(name: str, time_str: str, days: list[str], task: str) -> dict:
    """Add a new schedule entry and return it."""
    schedules = load_schedules()
    entry = {
        "id":      str(uuid.uuid4())[:8],
        "name":    name,
        "time":    time_str,
        "days":    days,
        "task":    task,
        "enabled": True,
    }
    schedules.append(entry)
    save_schedules(schedules)
    return entry


def remove_schedule(schedule_id: str) -> bool:
    """Remove a schedule by ID. Returns True if found and removed."""
    schedules = load_schedules()
    before = len(schedules)
    schedules = [s for s in schedules if s.get("id") != schedule_id]
    save_schedules(schedules)
    return len(schedules) < before


def toggle_schedule(schedule_id: str) -> bool | None:
    """Toggle enabled/disabled. Returns new state, or None if not found."""
    schedules = load_schedules()
    for s in schedules:
        if s.get("id") == schedule_id:
            s["enabled"] = not s.get("enabled", True)
            save_schedules(schedules)
            return s["enabled"]
    return None


# ── background loop ───────────────────────────────────────────────────────────

class Scheduler:
    """
    Background daemon thread that fires scheduled tasks at the right time.

    Usage:
        scheduler = Scheduler(on_task=lambda task: agent.run_task(task))
        scheduler.start()
    """

    def __init__(self, on_task: Callable[[str], None]):
        """
        on_task: called with the task string whenever a schedule fires.
                 Runs in a separate daemon thread — keep it thread-safe.
        """
        self._on_task   = on_task
        self._thread    = threading.Thread(target=self._loop, daemon=True)
        self._fired_today: set[str] = set()   # "id:HH:MM" fired this calendar day
        self._last_date: str        = ""

    def start(self):
        self._thread.start()

    # ── internal ──────────────────────────────────────────────────────────────

    def _loop(self):
        while True:
            now        = datetime.now()
            today_str  = now.strftime("%Y-%m-%d")
            hhmm       = now.strftime("%H:%M")
            weekday    = now.weekday()   # 0 = Monday … 6 = Sunday

            # Reset fired set at each new calendar day
            if today_str != self._last_date:
                self._fired_today.clear()
                self._last_date = today_str

            for sched in load_schedules():
                if not sched.get("enabled", True):
                    continue
                if sched.get("time") != hhmm:
                    continue

                fire_key = f"{sched['id']}:{hhmm}"
                if fire_key in self._fired_today:
                    continue

                # Day-of-week check
                days = sched.get("days", ["daily"])
                if "daily" not in days:
                    allowed = {_DAY_NUM.get(d, -1) for d in days}
                    if weekday not in allowed:
                        continue

                self._fired_today.add(fire_key)
                task = sched.get("task", "")
                if task:
                    threading.Thread(
                        target=self._on_task, args=(task,), daemon=True,
                    ).start()

            time.sleep(30)   # check twice per minute — fine for minute-level precision
