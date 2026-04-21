import time
import pyautogui

# Maps user-friendly key names to pyautogui key names
_KEY_MAP = {
    "win": "winleft",
    "windows": "winleft",
    "super": "winleft",
    "return": "enter",
    "esc": "escape",
    "del": "delete",
    "backspace": "backspace",
    "tab": "tab",
    "space": "space",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "home": "home",
    "end": "end",
    "insert": "insert",
    "prtsc": "printscreen",
}


def press_key(key: str) -> str:
    """
    Press a single key or combination like 'ctrl+c', 'win+r', 'alt+f4'.
    Handles aliases (win, esc, del, etc.).
    """
    parts = [p.strip().lower() for p in key.replace(" ", "").split("+")]
    normalized = [_KEY_MAP.get(p, p) for p in parts]

    if len(normalized) == 1:
        pyautogui.press(normalized[0])
    else:
        pyautogui.hotkey(*normalized)

    return f"Pressed: {key}"


def type_text(text: str, press_enter: bool = False, interval: float = 0.03) -> str:
    """
    Type text at the current cursor position.
    Uses pyperclip paste for reliability with unicode/special chars.
    Clipboard is cleared immediately after pasting so it cannot be
    accidentally pasted into the terminal when the task ends.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.18)        # wait for paste to land before clearing
        pyperclip.copy("")      # ← clear clipboard — prevents terminal pollution
    except ImportError:
        pyautogui.write(text, interval=interval)

    if press_enter:
        time.sleep(0.1)
        pyautogui.press("enter")

    return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
