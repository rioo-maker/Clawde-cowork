import time
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.04   # small global pause between pyautogui calls


def click(x: int, y: int, button: str = "left") -> str:
    """Move mouse to position first, then click — never teleport-and-click."""
    pyautogui.moveTo(x, y, duration=0.18)
    time.sleep(0.06)                      # let the cursor settle on the target
    pyautogui.click(button=button)
    return f"Clicked {button} at ({x}, {y})"


def double_click(x: int, y: int) -> str:
    pyautogui.moveTo(x, y, duration=0.18)
    time.sleep(0.06)
    pyautogui.doubleClick()
    return f"Double-clicked at ({x}, {y})"


def right_click(x: int, y: int) -> str:
    pyautogui.moveTo(x, y, duration=0.18)
    time.sleep(0.06)
    pyautogui.rightClick()
    return f"Right-clicked at ({x}, {y})"


def move(x: int, y: int) -> str:
    pyautogui.moveTo(x, y, duration=0.2)
    return f"Moved mouse to ({x}, {y})"


def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5) -> str:
    pyautogui.moveTo(from_x, from_y, duration=0.18)
    time.sleep(0.06)
    pyautogui.mouseDown()
    time.sleep(0.08)
    pyautogui.moveTo(to_x, to_y, duration=duration)
    time.sleep(0.05)
    pyautogui.mouseUp()
    return f"Dragged from ({from_x}, {from_y}) to ({to_x}, {to_y})"


def scroll(x: int, y: int, direction: str, amount: int = 3) -> str:
    pyautogui.moveTo(x, y, duration=0.12)
    time.sleep(0.04)
    if direction in ("left", "right"):
        pyautogui.hscroll(amount if direction == "right" else -amount)
    else:
        clicks = amount if direction == "up" else -amount
        pyautogui.scroll(clicks)
    return f"Scrolled {direction} at ({x}, {y})"
