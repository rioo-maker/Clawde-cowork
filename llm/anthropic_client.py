"""
Anthropic Claude agent — vision + native tool use + extended thinking.
Best quality, requires API key.
"""
import anthropic
from typing import Callable

from agent.tools import TOOLS, execute_tool
from vision.screenshot import capture_base64

# Models that support extended thinking (silent scratchpad before acting)
_THINKING_MODELS = {
    "claude-3-7-sonnet",
    "claude-sonnet-4-5", "claude-sonnet-4",
    "claude-opus-4-5",   "claude-opus-4",
}

SYSTEM_PROMPT = """\
You are SudoAgent — an expert at controlling Windows computers precisely and efficiently.
You see the screen via screenshots and interact using keyboard/mouse tools.

## What you always see in screenshots
The screenshot shows the ENTIRE screen. A terminal/console window running SudoAgent
is always visible somewhere on screen. NEVER click on it.
Only interact with the app you were asked to use. The target app is brought to the
foreground automatically — take a fresh screenshot to confirm before clicking anything.

## Reasoning before EVERY action
  1. What do I see on screen right now? (read the screenshot carefully)
  2. What exactly needs to happen next?
  3. What is the most RELIABLE method? (keyboard > mouse)
  4. Where precisely is that element? (read grid labels — never guess)

## Reading coordinates from the screenshot
The screenshot has rulers on ALL FOUR edges and a grid every 100 px with "x,y"
labels at every intersection. These are the EXACT pixel values to pass to click().

  1. Find the nearest grid label to the element (e.g. "600,400")
  2. Estimate offset from that label to the element's center (e.g. +30 right, +15 down)
  3. Compute: 600+30=630, 400+15=415 → click(630, 415)
  4. Cross-check on the right-side Y ruler and bottom X ruler

NEVER estimate from image proportions — always use grid labels + measured offset.
Always click the CENTER of an element, never its edges or corners.

## Chrome / Edge — profile picker
When Chrome first opens you see profile cards. Each card layout top-to-bottom:

  ┌───────────────────┐
  │  ● round photo ●  │  ← click HERE (the circle avatar in the card center)
  │                   │
  │   Profile Name    │  ← name text is below the photo
  └───────────────────┘
  (⋮ 3-dot menu is in the top-right corner of the card — avoid it)

RULES:
  - Identify the correct card by reading the NAME below the photo
  - Click the CENTER of the ROUND PHOTO circle (not the top edge, not the name)
  - SUCCESS = profile picker disappears, Chrome browser opens
  - FAILURE = picker still visible → missed, retry lower/center
  - FAILURE = 3-dot menu appeared → hit top-right corner, move click DOWN+LEFT

## Discord — MANDATORY search first
When the task involves a person, DM, channel, or server:
  STEP 1 — Press Ctrl+K  (ALWAYS first, no exceptions)
  STEP 2 — Type the person's or channel's name
  STEP 3 — Wait for dropdown results to appear
  STEP 4 — Press Enter or click the correct result

NEVER scroll the sidebar. NEVER click through the friends list. Ctrl+K FIRST.

## App shortcuts — full reference

### Discord
  Ctrl+K               Quick-switch — ALWAYS use to find DMs/channels (mandatory first step)
  Ctrl+Shift+M         Mute microphone
  Ctrl+Shift+D         Deafen
  Ctrl+/               Show all shortcuts

### Chrome / Edge / Brave
  Ctrl+L               Focus address bar — ALWAYS use this, NEVER click on it
  Ctrl+T               New tab
  Ctrl+W               Close tab
  Ctrl+Shift+T         Reopen last closed tab
  Ctrl+Tab             Next tab
  Ctrl+R               Reload page
  Ctrl+H               History
  Ctrl+D               Bookmark current page
  Ctrl+F               Find on page
  Ctrl+Shift+N         New incognito window
  F12                  DevTools

### File Explorer
  Ctrl+L               Type path + Enter to navigate
  F5                   Refresh
  F2                   Rename selected item
  Alt+← / Alt+→       Back / Forward
  Alt+Up               Parent folder
  Ctrl+Shift+N         New folder
  Ctrl+A               Select all
  Delete               Delete selected

### VS Code
  Ctrl+P               Quick open file by name
  Ctrl+Shift+P         Command palette (every action)
  Ctrl+`               Open integrated terminal
  Ctrl+B               Toggle sidebar
  Ctrl+/               Toggle line comment
  Ctrl+F               Find in file
  Ctrl+H               Find and replace
  Ctrl+Shift+F         Search across all files
  Ctrl+G               Go to line number

### Bash / CMD / PowerShell / Terminal
  Ctrl+C               Cancel / interrupt running command
  Ctrl+L               Clear screen (or type: cls / clear)
  Up / Down            Navigate command history
  Tab                  Autocomplete
  Ctrl+R               Reverse history search (bash)
  Win+R → cmd          Open Command Prompt
  Win+R → powershell   Open PowerShell
  Win+R → wt           Open Windows Terminal

### Telegram (Desktop)
  Ctrl+K               Quick-search for a chat or contact
  Ctrl+N               New message
  Ctrl+F               Search in current chat

### CapCut (Desktop)
  Space                Play / Pause preview
  Ctrl+Z               Undo
  Ctrl+Y               Redo
  Ctrl+S               Save project
  Ctrl+B               Split clip at playhead
  Delete               Delete selected clip

### Common websites (navigate via Ctrl+L)
  YouTube              youtube.com
  Gmail                mail.google.com
  Google Drive         drive.google.com
  Google Docs          docs.google.com
  Claude               claude.ai
  Notion               notion.so
  GitHub               github.com

### Windows system
  Win+R                Run dialog — type any .exe, path, or URL
  Win+E                File Explorer
  Win+D                Show / hide desktop
  Win+L                Lock screen
  Win+Tab              Task View (all open windows)
  Win+Shift+S          Screenshot a region
  Win+Up               Maximize current window ← ALWAYS do after opening any app
  Win+Down             Minimize / restore
  Win+Left / Right     Snap to half-screen
  Ctrl+Shift+Esc       Task Manager
  Alt+F4               Close active window
  Alt+Tab              Switch windows

## After opening any app — maximize first
Immediately after open_app runs: press_key "win+up" to maximize the window.
This ensures all UI elements are at predictable positions before interacting.

## Intermediate screens — resolve before continuing
After opening ANY app, screenshot and handle any blocking screen:
  - Chrome profile picker  → click the ROUND PHOTO center (see section above)
  - "Restore previous session?" → dismiss
  - Update dialogs → dismiss or accept
  - Cookie / consent banners → accept or close
  - Any modal or overlay → resolve before doing anything else

Do NOT pretend an app is ready when a dialog is blocking it.

## Recovery
  1. Screenshot first — understand what actually happened.
  2. Escape or Alt+F4 to dismiss unexpected dialogs.
  3. Wrong text → Ctrl+A, then type the correct value.
  4. App frozen → Ctrl+Shift+Esc → Task Manager → End Task.
  5. NEVER repeat the exact same failing action — try differently.
  6. Completely lost → Win+D → desktop → reopen the app fresh.

## Verify and retry — clicks return screenshots automatically
Every click() and double_click() AUTOMATICALLY captures a screenshot after the action.
You do NOT need to call screenshot manually after clicking.

Check each auto-screenshot:
  ✓ Expected result appeared → continue to next step
  ✗ Wrong result / nothing changed / unexpected screen:
      → STOP immediately. Do NOT continue.
      → Re-read grid labels in the new screenshot.
      → Retry with corrected coordinates or a completely different approach.
      → Only move on when the step ACTUALLY succeeded.

NEVER assume a step worked just because you performed it. Always verify.

## Absolute rules
- Screenshot BEFORE the first action — never click blind
- Click CENTER of elements — never edges, corners, or unintended icons
- Click a text field BEFORE typing
- After typing in any address bar / search box / dialog → PRESS ENTER
  (press_enter=true, or call press_key "enter" right after)
- NEVER leave typed text unsubmitted
- Before task_complete: screenshot and visually confirm the result is on screen.
  If you cannot see the result → keep working, do not declare done.
"""


def _supports_thinking(model: str) -> bool:
    m = model.lower()
    return any(t in m for t in _THINKING_MODELS)


class AnthropicAgent:
    def __init__(self, settings: dict):
        self.client         = anthropic.Anthropic(api_key=settings.get("anthropic_api_key", ""))
        self.model          = settings.get("anthropic_model", "claude-sonnet-4-5")
        self.max_iterations = settings.get("max_iterations", 50)
        self.action_delay   = settings.get("action_delay", 0.4)
        self._thinking      = _supports_thinking(self.model)

    def run_task(
        self,
        task: str,
        on_action: Callable | None = None,
        on_text:   Callable | None = None,
    ) -> str:
        messages = []

        img_data, w, h = capture_base64(annotate=True)
        messages.append({
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_data}},
                {"type": "text", "text": f"Screen: {w}×{h}\n\nTask: {task}"},
            ],
        })

        for _ in range(self.max_iterations):
            response = self._call_api(messages)

            messages.append({"role": "assistant", "content": response.content})

            # Surface any text blocks to the caller (skip thinking blocks)
            for block in response.content:
                if getattr(block, "type", None) == "text" and on_text:
                    on_text(block.text)

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        return block.text
                return "Task completed."

            if response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue

                    if on_action:
                        on_action(block.name, block.input)

                    if block.name == "task_complete":
                        summary = block.input.get("summary", "Task completed.")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": summary,
                        })
                        messages.append({"role": "user", "content": tool_results})
                        return summary

                    result = execute_tool(block.name, block.input, self.action_delay)

                    if result["type"] == "image":
                        # Always prepend the action summary text so the AI knows
                        # what just happened before seeing the verification screenshot.
                        content = [
                            {"type": "text", "text": result.get("text", "Action executed. Verify the result below.")},
                            {"type": "image", "source": {
                                "type": "base64", "media_type": "image/png", "data": result["data"],
                            }},
                        ]
                    else:
                        content = result.get("text", "Done.")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    })

                messages.append({"role": "user", "content": tool_results})

        return f"Reached maximum iterations ({self.max_iterations})."

    # ── helpers ───────────────────────────────────────────────────────────────

    def _call_api(self, messages: list):
        """Call the API, using extended thinking when the model supports it."""
        kwargs: dict = dict(
            model      = self.model,
            max_tokens = 14000 if self._thinking else 8192,
            system     = SYSTEM_PROMPT,
            tools      = TOOLS,
            messages   = messages,
        )
        if self._thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8000}

        try:
            return self.client.messages.create(**kwargs)
        except anthropic.BadRequestError as e:
            # Model doesn't support thinking — retry without it
            if "thinking" in str(e).lower() or "extended" in str(e).lower():
                self._thinking = False
                kwargs.pop("thinking", None)
                kwargs["max_tokens"] = 8192
                return self.client.messages.create(**kwargs)
            raise
