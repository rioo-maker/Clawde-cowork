import os
from config.settings import get_config

# Charger la configuration
config = get_config()
SANDBOX_ENABLED = config.get("sandbox_enabled", True)
WORKING_DIRECTORY = config.get("working_directory", os.getcwd())

# Créer le répertoire de travail si nécessaire
os.makedirs(WORKING_DIRECTORY, exist_ok=True)


def is_path_safe(path: str) -> bool:
    """Vérifie si un chemin est sûr (dans le répertoire de travail si la sandbox est activée)."""
    if not SANDBOX_ENABLED:
        return True
    abs_path = os.path.abspath(path)
    return abs_path.startswith(os.path.abspath(WORKING_DIRECTORY))


def safe_file_write(path: str, content: str):
    """Écrit un fichier uniquement dans le répertoire de travail si la sandbox est activée."""
    if not is_path_safe(path):
        raise PermissionError("🚫 Chemin en dehors de la sandbox")
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        raise PermissionError(f"🚫 Erreur lors de l'écriture du fichier: {e}")


def safe_file_read(path: str) -> str:
    """Lit un fichier uniquement dans le répertoire de travail si la sandbox est activée."""
    if not is_path_safe(path):
        raise PermissionError("🚫 Chemin en dehors de la sandbox")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except IOError as e:
        raise PermissionError(f"🚫 Erreur lors de la lecture du fichier: {e}")