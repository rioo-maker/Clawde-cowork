import pyautogui
from typing import List, Dict
from actions.app_launcher import launch_app

def execute_action(action: Dict) -> bool:
    """Exécute une action (move_mouse, click, open_app, etc.)."""
    try:
        if action["action"] == "move_mouse":
            x = action.get("x", 0)
            y = action.get("y", 0)
            duration = action.get("duration", 0.5)
            
            # Vérifier que les coordonnées sont dans l'écran
            screen_width, screen_height = pyautogui.size()
            if not (0 <= x <= screen_width and 0 <= y <= screen_height):
                print(f"❌ Coordonnées hors écran: ({x}, {y})")
                return False
            
            pyautogui.moveTo(x, y, duration=duration)
            return True
            
        elif action["action"] == "click":
            pyautogui.click()
            return True
            
        elif action["action"] == "open_app":
            app_name = action.get("app_name", "")
            if not app_name:
                print("❌ Nom de l'application manquant.")
                return False
            return launch_app(app_name)
            
        else:
            print(f"❌ Action inconnue: {action['action']}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        return False

def execute_actions(actions: List[Dict]) -> bool:
    """Exécute une liste d'actions."""
    if not actions:
        print("⚠️ Aucune action à exécuter.")
        return False
        
    for action in actions:
        if not execute_action(action):
            return False
    return True