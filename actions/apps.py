import os
import subprocess
import time
from pathlib import Path

# Window title keywords for focus-after-open
_WINDOW_TITLES = {
    "chrome":           ["Google Chrome", "Chrome"],
    "google chrome":    ["Google Chrome", "Chrome"],
    "firefox":          ["Mozilla Firefox", "Firefox"],
    "edge":             ["Microsoft Edge", "Edge"],
    "microsoft edge":   ["Microsoft Edge", "Edge"],
    "brave":            ["Brave"],
    "discord":          ["Discord"],
    "spotify":          ["Spotify"],
    "vscode":           ["Visual Studio Code"],
    "vs code":          ["Visual Studio Code"],
    "visual studio code": ["Visual Studio Code"],
    "notepad":          ["Notepad"],
    "explorer":         ["File Explorer", "Windows Explorer"],
    "file explorer":    ["File Explorer", "Windows Explorer"],
}

# Direct shell commands for well-known apps (fastest path)
_DIRECT_COMMANDS = {
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "wordpad": "wordpad",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "registry editor": "regedit",
    "snipping tool": "snippingtool",
    "sticky notes": "stikynot",
    "character map": "charmap",
    "remote desktop": "mstsc",
}

# Protocol handlers (for apps that register URI schemes)
_PROTOCOL_APPS = {
    "discord": "discord:",
    "spotify": "spotify:",
    "steam": "steam:",
    "whatsapp": "whatsapp:",
    "teams": "msteams:",
    "zoom": "zoommtg:",
    "slack": "slack:",
    "skype": "skype:",
}

# Common executable names — used only as last resort (some may not be on PATH)
_EXE_NAMES = {
    "chrome": ["chrome", "google chrome"],
    "google chrome": ["chrome"],
    "firefox": ["firefox"],
    "edge": ["msedge"],
    "microsoft edge": ["msedge"],
    "brave": ["brave", "brave-browser"],
    "opera": ["opera"],
    "vlc": ["vlc"],
    "obs": ["obs64", "obs"],
    "vscode": ["code"],
    "vs code": ["code"],
    "visual studio code": ["code"],
    "git bash": ["git-bash"],
    "python": ["python"],
    "node": ["node"],
    "winrar": ["winrar"],
    "7zip": ["7zfm"],
}


def open_app(name: str) -> str:
    """
    Open an application by name using multiple strategies:
    1. Direct shell command  (built-in Windows: notepad, calc, explorer…)
    2. Protocol handler      (Discord, Spotify, Steam, Teams…)
    3. Start Menu shortcuts  (.lnk files — catches Chrome, Firefox, VSCode, etc.)
    4. PATH lookup           (apps already on the system PATH via `where`)
    5. Program Files search  (brute-force .exe scan)
    6. Known exe names       (last-resort shell launch — may fail silently)
    """
    key = name.lower().strip()

    # Strategy 1: Direct Windows command
    if key in _DIRECT_COMMANDS:
        cmd = _DIRECT_COMMANDS[key]
        subprocess.Popen(cmd, shell=True)
        _focus_window(name)
        return f"Opened {name} via shell command"

    # Strategy 2: Protocol handler
    if key in _PROTOCOL_APPS:
        proto = _PROTOCOL_APPS[key]
        subprocess.Popen(f"start {proto}", shell=True)
        _focus_window(name)
        return f"Opened {name} via protocol handler"

    # Strategy 3: Start Menu shortcuts — most reliable for installed apps
    lnk_path = _find_start_menu_shortcut(name)
    if lnk_path:
        os.startfile(lnk_path)
        _focus_window(name)
        return f"Opened {name} from Start Menu shortcut"

    # Strategy 4: PATH lookup via `where`
    try:
        result = subprocess.run(
            ["where", name],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            path = result.stdout.strip().split("\n")[0].strip()
            subprocess.Popen(f'"{path}"', shell=True)
            _focus_window(name)
            return f"Opened {name} from PATH: {path}"
    except Exception:
        pass

    # Strategy 5: Search Program Files directories
    exe_path = _search_program_files(name)
    if exe_path:
        subprocess.Popen(f'"{exe_path}"', shell=True)
        _focus_window(name)
        return f"Opened {name} from {exe_path}"

    # Strategy 6: Try known exe names via start command
    exe_candidates = _EXE_NAMES.get(key, [])
    for exe in exe_candidates:
        try:
            result = subprocess.run(
                ["where", exe],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                path = result.stdout.strip().split("\n")[0].strip()
                subprocess.Popen(f'"{path}"', shell=True)
                _focus_window(name)
                return f"Opened {name} ({exe})"
        except Exception:
            pass

    # Last resort: Windows Search (Win key + type + Enter)
    try:
        import pyautogui
        pyautogui.press("winleft")
        time.sleep(0.6)
        pyautogui.typewrite(name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        _focus_window(name)
        return f"Launched {name} via Windows Search"
    except Exception as e:
        return f"Could not open {name}: {e}"


def _focus_window(app_name: str) -> None:
    """
    After launching an app, bring its window to the foreground so it covers
    the SudoAgent terminal and the AI screenshot shows the right window.
    """
    time.sleep(1.2)   # give the app time to create its window
    key = app_name.lower().strip()
    candidates = _WINDOW_TITLES.get(key, [app_name.title(), app_name])

    try:
        import pygetwindow as gw
        for title_kw in candidates:
            wins = [w for w in gw.getAllWindows()
                    if title_kw.lower() in w.title.lower() and w.title.strip()]
            if wins:
                w = wins[0]
                try:
                    w.restore()
                except Exception:
                    pass
                try:
                    w.maximize()       # always maximise so UI is at predictable coords
                except Exception:
                    pass
                try:
                    w.activate()
                except Exception:
                    pass
                time.sleep(0.5)
                return
    except Exception:
        pass

    # Fallback: use ctypes to force foreground if pygetwindow failed
    try:
        import ctypes
        # Give the shell permission to set foreground
        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    except Exception:
        pass


def _find_start_menu_shortcut(name: str) -> str | None:
    """Search Start Menu folders for a .lnk shortcut matching the app name."""
    search_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
    ]
    name_lower = name.lower()
    best: tuple[int, str] | None = None  # (match_quality, path)

    for base in search_dirs:
        if not base.exists():
            continue
        for lnk in base.rglob("*.lnk"):
            stem = lnk.stem.lower()
            if name_lower == stem:
                return str(lnk)          # exact match → use immediately
            if name_lower in stem:
                # prefer shorter stems (more specific match)
                score = len(stem)
                if best is None or score < best[0]:
                    best = (score, str(lnk))

    return best[1] if best else None


def _search_program_files(name: str) -> str | None:
    """Search Program Files directories for an exe matching the app name."""
    roots = [
        "C:/Program Files",
        "C:/Program Files (x86)",
        os.path.expandvars("%LOCALAPPDATA%"),
        os.path.expandvars("%APPDATA%"),
    ]
    name_lower = name.lower()
    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for exe in root_path.glob("**/*.exe"):
            try:
                if name_lower in exe.stem.lower():
                    return str(exe)
            except Exception:
                continue
    return None
