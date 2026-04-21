"""
Tool definitions for Claude + execution dispatcher.
"""
import time
from typing import Any

from actions.mouse import click, double_click, right_click, drag, scroll
from actions.keyboard import press_key, type_text
from actions.apps import open_app
from vision.screenshot import capture_base64


# ──────────────────────────────────────────────
# Tool schemas (sent to Claude API)
# ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "screenshot",
        "description": (
            "Capture the current screen state. Returns an annotated image with "
            "pixel-coordinate rulers on the top and left edges so you can "
            "identify exact (x, y) positions for clicks. "
            "Call this before every interaction to see what's on screen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "click",
        "description": (
            "Click the mouse at a specific screen position. "
            "Use screenshot first to identify the correct coordinates. "
            "button can be 'left' (default), 'right', or 'middle'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (pixels from left)"},
                "y": {"type": "integer", "description": "Y coordinate (pixels from top)"},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button to use (default: left)",
                },
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "double_click",
        "description": "Double-click at a screen position. Useful for opening files or activating items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "type_text",
        "description": (
            "Type text at the current cursor position. "
            "Click the target field first to focus it, then call this. "
            "IMPORTANT: set press_enter=true whenever you type in a browser address bar, "
            "search box, Run dialog, or any field that needs submitting — "
            "never leave typed text unsubmitted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "press_enter": {
                    "type": "boolean",
                    "description": "Press Enter after typing (default: false)",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "press_key",
        "description": (
            "Press a keyboard key or combination. "
            "Examples: 'enter', 'escape', 'tab', 'ctrl+c', 'ctrl+v', 'ctrl+a', "
            "'alt+f4', 'win', 'win+r', 'win+d', 'alt+tab', 'ctrl+shift+esc', "
            "'f5', 'delete', 'backspace', 'pagedown', 'home', 'end'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key or key combination"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll at a position on screen. Move mouse to the target area first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                },
                "amount": {
                    "type": "integer",
                    "description": "Scroll units (default: 3)",
                },
            },
            "required": ["x", "y", "direction"],
        },
    },
    {
        "name": "drag",
        "description": "Click and drag from one position to another. Useful for moving windows, sliders, or selecting text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_x": {"type": "integer"},
                "from_y": {"type": "integer"},
                "to_x": {"type": "integer"},
                "to_y": {"type": "integer"},
                "duration": {
                    "type": "number",
                    "description": "Drag duration in seconds (default: 0.5)",
                },
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        },
    },
    {
        "name": "open_app",
        "description": (
            "Open an application by name. This is the most reliable way to launch "
            "any installed app — smarter than searching manually. "
            "Examples: 'chrome', 'discord', 'notepad', 'spotify', 'vscode', "
            "'calculator', 'explorer', 'powershell', 'steam'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "task_complete",
        "description": (
            "Call this ONLY when the task is fully and visibly done. "
            "Before calling it you MUST take a screenshot and confirm with your own eyes "
            "that the result is visible on screen. "
            "If you cannot see the result yet, keep working instead of completing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what was accomplished",
                },
            },
            "required": ["summary"],
        },
    },
]


# ──────────────────────────────────────────────
# Tool executor
# ──────────────────────────────────────────────

def _auto_screenshot(label: str) -> dict:
    """
    Capture the screen right after an action and return it as an image result.
    Bundled with a text label so the AI knows what action was just performed.
    """
    time.sleep(0.30)   # let the UI settle before capturing
    data, w, h = capture_base64(annotate=True)
    return {
        "type":  "image",
        "data":  data,
        "width": w,
        "height": h,
        "text":  label,   # extra field — used by clients that want the action summary
    }


def execute_tool(name: str, inputs: dict, action_delay: float = 0.4) -> dict:
    """
    Execute a tool and return a result dict.

    click / double_click automatically capture the screen after the action so
    the AI always sees what happened — it cannot skip the verify step.

    Return types:
      {"type": "text",  "text": "..."}
      {"type": "image", "data": "<b64>", "width": w, "height": h, "text": "..."}
    """
    time.sleep(action_delay)

    try:
        if name == "screenshot":
            data, w, h = capture_base64(annotate=True)
            return {"type": "image", "data": data, "width": w, "height": h, "text": "screenshot"}

        elif name == "click":
            msg = click(inputs["x"], inputs["y"], inputs.get("button", "left"))
            return _auto_screenshot(msg)

        elif name == "double_click":
            msg = double_click(inputs["x"], inputs["y"])
            return _auto_screenshot(msg)

        elif name == "type_text":
            msg = type_text(inputs["text"], press_enter=inputs.get("press_enter", False))
            return {"type": "text", "text": msg}

        elif name == "press_key":
            msg = press_key(inputs["key"])
            return {"type": "text", "text": msg}

        elif name == "scroll":
            msg = scroll(inputs["x"], inputs["y"], inputs["direction"], inputs.get("amount", 3))
            return {"type": "text", "text": msg}

        elif name == "drag":
            msg = drag(
                inputs["from_x"], inputs["from_y"],
                inputs["to_x"], inputs["to_y"],
                inputs.get("duration", 0.5),
            )
            return {"type": "text", "text": msg}

        elif name == "open_app":
            # open_app already waits and focuses the window
            msg = open_app(inputs["name"])
            return {"type": "text", "text": msg}

        elif name == "task_complete":
            return {"type": "text", "text": inputs.get("summary", "Task completed.")}

        else:
            return {"type": "text", "text": f"Unknown tool: {name}"}

    except Exception as e:
        return {"type": "text", "text": f"Error executing {name}: {e}"}
