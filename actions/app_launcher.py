import os
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

MAPPING_FILE = Path(__file__).parent.parent / "config" / "app_mappings.json"

def load_app_mappings() -> Dict:
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_app_mappings(mappings: Dict):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=4)

def find_app_path(app_name: str) -> Optional[str]:
    mappings = load_app_mappings()
    app_name_lower = app_name.lower()

    if app_name_lower in mappings:
        app_info = mappings[app_name_lower]
        for path in app_info.get("paths", []):
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                return expanded_path
        if "command" in app_info:
            return app_info["command"]

    search_paths = [
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        os.path.expandvars("C:\\Users\\%USERNAME%\\AppData\\Local"),
        os.path.expandvars("C:\\Users\\%USERNAME%\\AppData\\Roaming")
    ]

    for root in search_paths:
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.lower() == f"{app_name_lower}.exe":
                    return os.path.join(dirpath, filename)
    return None

def launch_app(app_name: str) -> bool:
    # D'abord essayer via CMD (plus rapide et plus fiable)
    app_name_lower = app_name.lower()
    try:
        if app_name_lower == "discord":
            subprocess.run("start discord:", shell=True, check=True)
        elif app_name_lower == "chrome":
            subprocess.run("start chrome", shell=True, check=True)
        elif app_name_lower == "notepad":
            subprocess.run("start notepad", shell=True, check=True)
        elif app_name_lower == "calc":
            subprocess.run("start calc", shell=True, check=True)
        elif app_name_lower == "spotify":
            subprocess.run("start spotify:", shell=True, check=True)
        elif app_name_lower == "edge":
            subprocess.run("start msedge", shell=True, check=True)
        elif app_name_lower == "firefox":
            subprocess.run("start firefox", shell=True, check=True)
        elif app_name_lower == "steam":
            subprocess.run("start steam:", shell=True, check=True)
        else:
            # Si CMD échoue, essayer via le chemin
            app_path = find_app_path(app_name)
            if not app_path:
                return False
            
            if app_path.startswith("start ") or app_path.startswith("explorer "):
                subprocess.run(app_path, shell=True, check=True)
            else:
                subprocess.run(f'start "" "{app_path}"', shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du lancement de {app_name}: {e}")
        return False