"""
Ollama agent — native ollama Python SDK.

Supports:
  • Local Ollama      http://localhost:11434  (no auth)
  • Cloud models      same URL, model = "gpt-oss:120b-cloud"  (needs ollama signin)
  • Ollama.com API    https://ollama.com  +  OLLAMA_API_KEY  (direct cloud access)

Tool calling uses the native /api/chat endpoint (not OpenAI-compat).
Images are passed via the `images` field in user messages.
Tool results use `tool_name` (Ollama has no tool-call IDs).
"""
import os
import json
import re
from typing import Callable

from ollama import Client

from agent.tools import TOOLS, execute_tool
from vision.screenshot import capture_base64

# ── capability detection ──────────────────────────────────────────────────────

# Model name substrings that support native tool calling via Ollama
_TOOLS_CAPABLE = {
    "llama3.1", "llama3.2", "llama3.3", "llama3.2-vision",
    "qwen2", "qwen2.5", "qwen2.5-vl", "qwen2-vl",
    "mistral", "mistral-nemo", "mistral-small",
    "command-r", "hermes3", "nemotron-mini", "phi4",
    # Ollama cloud / large models
    "gpt-oss",
}

# Model name substrings that support image input
_VISION_CAPABLE = {
    "llava", "llama3.2-vision", "qwen2-vl", "qwen2.5-vl",
    "minicpm-v", "moondream", "phi3v", "bakllava",
    # Ollama cloud model
    "gpt-oss",
}


def _supports(model: str, known: set) -> bool:
    base = model.lower().split(":")[0]
    # -cloud suffix = large capable model, assume full support
    if base.endswith("-cloud"):
        return True
    return any(k in base for k in known)


# ── tool schema (Ollama format = OpenAI function format) ─────────────────────

_OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOLS
]


# ── system prompts ────────────────────────────────────────────────────────────

_SYSTEM_TOOLS = """\
IDENTITY: You are SudoAgent, made by the SudoAgent Team. You are NOT Claude, \
ChatGPT, Gemini, or any other AI product. If anyone asks who you are, always \
say: "I am SudoAgent, made by the SudoAgent Team."

You control a Windows PC using tools. You see the screen via screenshots.

FULL-SCREEN SCREENSHOTS:
The screenshot shows the ENTIRE screen. A SudoAgent terminal is always visible —
NEVER click on it. Only interact with the app you were asked to use.
The target app is automatically brought to the foreground after opening.

BEFORE EVERY ACTION — reason through:
  1. What do I see? (read the screenshot carefully)
  2. What is the best next step?
  3. Most reliable method? (keyboard > mouse)
  4. Exact coordinates? (read grid labels, never guess)

COORDINATES — do this exactly:
  - Rulers on ALL 4 edges. Grid every 100px with "x,y" labels at every intersection.
  - To click: find nearest grid label → measure offset to element center → add them.
    Example: label "600,400", element 30px right + 15px down → click(630, 415)
  - Cross-check on right-side Y ruler and bottom X ruler.
  - NEVER estimate from image proportions. Read grid labels only.
  - Click CENTER of elements — never edges, corners, or icons.

CHROME PROFILE PICKER:
Each card layout (top to bottom):
  [ round photo ]   ← click HERE — the circle avatar in the center of the card
  [ Profile Name ]  ← name text is BELOW the photo
  (⋮ 3-dot menu is in the TOP-RIGHT corner — AVOID IT)
  - Click the CENTER of the ROUND PROFILE PHOTO
  - SUCCESS = picker disappears, browser opens
  - FAILURE: picker still visible → retry, aim lower/center
  - FAILURE: 3-dot menu appeared → hit top-right corner, move DOWN+LEFT

DISCORD — MANDATORY:
  When finding a person, DM, channel, or server:
  STEP 1: Press Ctrl+K (ALWAYS FIRST — no exceptions)
  STEP 2: Type the name
  STEP 3: Press Enter or click the correct result
  NEVER scroll the sidebar. NEVER click through the friends list.

APP SHORTCUTS:
  Discord:      Ctrl+K=quick-switch(MANDATORY FIRST) | Ctrl+Shift+M=mute | Ctrl+/=shortcuts
  Chrome/Edge:  Ctrl+L=address bar(ALWAYS,never click) | Ctrl+T=new tab | Ctrl+W=close | Ctrl+R=reload | F12=DevTools
  File Explorer:Ctrl+L=navigate | F2=rename | Alt+Left=back | Ctrl+Shift+N=new folder
  VS Code:      Ctrl+P=open file | Ctrl+Shift+P=commands | Ctrl+Backtick=terminal
  Terminal/CMD: Ctrl+C=cancel | Up/Down=history | Tab=autocomplete
  Telegram:     Ctrl+K=search chat | Ctrl+N=new message
  CapCut:       Space=play/pause | Ctrl+B=split clip | Ctrl+Z=undo | Delete=remove clip
  Windows:      Win+R=Run | Win+E=Explorer | Win+D=desktop | Win+Up=maximize
                Win+Shift+S=snip | Ctrl+Shift+Esc=TaskManager | Alt+F4=close | Alt+Tab=switch

WEBSITES (navigate with Ctrl+L in browser):
  youtube.com | mail.google.com | drive.google.com | docs.google.com
  claude.ai | notion.so | github.com | open.spotify.com

AFTER OPENING ANY APP: press Win+Up to maximize before interacting.

INTERMEDIATE SCREENS — handle before continuing:
  - Chrome profile picker → click ROUND PHOTO center (see above)
  - "Restore session?" / update dialogs → dismiss
  - Cookie/consent banners → accept or close
  - Any modal → resolve it before continuing
  Do NOT pretend the app is ready when a dialog is blocking it.

RECOVERY:
  1. Screenshot to see what happened
  2. Escape or Alt+F4 to close dialogs
  3. Ctrl+A then retype if text is wrong
  4. NEVER repeat the same failing action — try differently
  5. Win+D → desktop → start fresh if lost

VERIFY EVERY CLICK — click() auto-returns a screenshot:
  ✓ Expected result appeared → continue to next step
  ✗ Wrong / nothing changed:
      → STOP. Do NOT continue. Do NOT assume it worked.
      → Re-read grid labels → retry with corrected coords or different approach
      → Only move on when the step ACTUALLY succeeded.

CRITICAL RULES:
  - Screenshot BEFORE first action — never click blind
  - Click CENTER of elements — never edges or corners
  - Click a text field BEFORE typing
  - After typing URL/search: ALWAYS press Enter (press_enter=true or press_key enter)
  - NEVER leave typed text unsubmitted
  - Before task_complete: screenshot → confirm result is visibly on screen
  - NEVER assume a step worked — always verify from the auto-screenshot
"""

_SYSTEM_JSON = """\
IDENTITY: You are SudoAgent, made by the SudoAgent Team. Not Claude, not ChatGPT.

You control a Windows PC. Output ONLY valid JSON — no other text.

Format: {"thought":"reason here","action":"tool_name","args":{}}

Tools:
screenshot:{} | click:{"x":int,"y":int,"button":"left"} | double_click:{"x":int,"y":int}
type_text:{"text":"...","press_enter":false} | press_key:{"key":"..."}
scroll:{"x":int,"y":int,"direction":"up|down","amount":3}
drag:{"from_x":int,"from_y":int,"to_x":int,"to_y":int}
open_app:{"name":"app name"} | task_complete:{"summary":"..."}

RULES:
- Grid labels "x,y" appear every 100px — read them for exact coords. Never guess.
- Use grid label + measured offset. Cross-check on right/bottom rulers.
- Chrome profile picker: click the ROUND PHOTO circle (center of card).
  NOT top edge, NOT top-right corner (3-dot menu). Round photo = center of card.
  Success = picker disappears. 3-dot appeared = hit corner, move DOWN+LEFT, retry.
- Discord: Ctrl+K FIRST to find any person/channel. NEVER sidebar-scroll.
- Browser address bar: ALWAYS Ctrl+L — never click it.
- After opening any app: Win+Up to maximize first.
- click/double_click return auto-screenshot — check before continuing.
  ✓ Expected → next step. ✗ Wrong → STOP, re-read grid, retry differently.
- After typing URL/search: press_enter=true or follow with press_key enter.
- Before task_complete: screenshot to confirm result is visible.
- NEVER assume a step worked — verify from the auto-screenshot.
- If action fails: try a completely different approach, never repeat same failure.
"""


# ── JSON response parser (fallback mode) ─────────────────────────────────────

def _parse_json(text: str) -> dict | None:
    text = text.strip()
    try:
        d = json.loads(text)
        if "action" in d:
            return d
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group())
            if "action" in d:
                return d
        except json.JSONDecodeError:
            pass
    return None


# ── agent class ───────────────────────────────────────────────────────────────

class OllamaAgent:
    def __init__(self, settings: dict):
        url = settings.get("ollama_url", "http://localhost:11434")
        self.model = settings.get("ollama_model", "llama3.2-vision:11b")
        self.max_iterations = settings.get("max_iterations", 50)
        self.action_delay = settings.get("action_delay", 0.4)

        # Build client — inject API key both via headers and the env var the SDK
        # reads at init time (ollama._client line 107: os.getenv('OLLAMA_API_KEY'))
        api_key = settings.get("ollama_api_key", "") or os.environ.get("OLLAMA_API_KEY", "")
        if api_key:
            os.environ["OLLAMA_API_KEY"] = api_key   # picked up by SDK at init
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = Client(host=url, headers=headers)

        self.use_tools = _supports(self.model, _TOOLS_CAPABLE)
        self.use_vision = _supports(self.model, _VISION_CAPABLE)

    # ── public entry point ───────────────────────────────────────────────────

    def run_task(
        self,
        task: str,
        on_action: Callable | None = None,
        on_text: Callable | None = None,
    ) -> str:
        if self.use_tools:
            try:
                return self._tools_loop(task, on_action, on_text)
            except Exception as e:
                err = str(e).lower()
                if "tool" in err or "function" in err or "does not support" in err:
                    self.use_tools = False
                    return self._json_loop(task, on_action, on_text)
                raise
        return self._json_loop(task, on_action, on_text)

    # ── tools mode ───────────────────────────────────────────────────────────

    def _tools_loop(self, task, on_action, on_text) -> str:
        img_b64, w, h = capture_base64(annotate=True)
        messages = [self._user_msg(f"Screen: {w}×{h}\n\nTask: {task}", img_b64)]

        for _ in range(self.max_iterations):
            resp = self.client.chat(
                model=self.model,
                messages=[{"role": "system", "content": _SYSTEM_TOOLS}] + messages,
                tools=_OLLAMA_TOOLS,
            )

            msg = resp.message
            text = msg.content or ""
            tool_calls = msg.tool_calls or []

            # Save assistant turn to history
            assistant_entry: dict = {"role": "assistant", "content": text}
            if tool_calls:
                assistant_entry["tool_calls"] = [
                    {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in tool_calls
                ]
            messages.append(assistant_entry)

            if text and on_text:
                on_text(text)

            # No tool calls → model finished (or gave up)
            if not tool_calls:
                if len(messages) <= 3:
                    # Model never engaged with tools → fall back
                    self.use_tools = False
                    return self._json_loop(task, on_action, on_text)
                return text or "Task completed."

            # Execute every tool call
            pending_screenshot: str | None = None

            for tc in tool_calls:
                name = tc.function.name
                # arguments is already a dict in the native ollama SDK
                args = tc.function.arguments if isinstance(tc.function.arguments, dict) else {}

                if on_action:
                    on_action(name, args)

                if name == "task_complete":
                    messages.append({"role": "tool", "tool_name": name, "content": args.get("summary", "Done.")})
                    return args.get("summary", "Task completed.")

                result = execute_tool(name, args, self.action_delay)

                if result["type"] == "image" and self.use_vision:
                    # Ack the tool result as text; deliver image as follow-up user message
                    summary = result.get("text", "")
                    caption = f"{summary} — Screen captured. See next message."
                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": caption,
                    })
                    pending_screenshot = result["data"]
                else:
                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": result.get("text", "Done."),
                    })

            # Deliver screenshot as a new user message (after all tool results)
            if pending_screenshot:
                messages.append(self._user_msg("Current screen state:", pending_screenshot))

        return f"Reached maximum iterations ({self.max_iterations})."

    # ── JSON fallback mode ────────────────────────────────────────────────────

    def _json_loop(self, task, on_action, on_text) -> str:
        img_b64, w, h = capture_base64(annotate=True)
        history = [self._user_msg(f"Screen: {w}×{h}\n\nTask: {task}\n\nRespond with JSON:", img_b64)]

        for _ in range(self.max_iterations):
            resp = self.client.chat(
                model=self.model,
                messages=[{"role": "system", "content": _SYSTEM_JSON}] + history,
            )
            text = resp.message.content or ""
            history.append({"role": "assistant", "content": text})

            if on_text and text:
                on_text(text)

            action = _parse_json(text)
            if not action:
                history.append({
                    "role": "user",
                    "content": 'Bad format. Output ONLY JSON: {"action":"tool_name","args":{}}',
                })
                continue

            name = action.get("action", "")
            args = action.get("args", {})

            if on_action:
                on_action(name, args)

            if name == "task_complete":
                return args.get("summary", "Task completed.")

            result = execute_tool(name, args, self.action_delay)

            if result["type"] == "image" and self.use_vision:
                summary = result.get("text", "")
                prompt  = f"{summary} — Did it work? If not, retry with corrected coords. (JSON)"
                history.append(self._user_msg(prompt, result["data"]))
            else:
                history.append({
                    "role": "user",
                    "content": f"Result: {result.get('text', 'Done.')} — What next? (JSON)",
                })

        return f"Reached maximum iterations ({self.max_iterations})."

    # ── helpers ───────────────────────────────────────────────────────────────

    def _user_msg(self, text: str, img_b64: str | None = None) -> dict:
        """Build a user message, optionally with an image in the `images` field."""
        msg: dict = {"role": "user", "content": text}
        if img_b64 and self.use_vision:
            msg["images"] = [img_b64]
        return msg
