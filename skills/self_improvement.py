import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List

# Chemin vers les logs et la configuration
LOG_FILE = Path(__file__).parent.parent / "logs" / "sudo_agent.log"
CONFIG_FILE = Path(__file__).parent.parent / "config" / "settings.json"


def analyze_logs() -> Dict[str, int]:
    """Analyse les logs pour identifier les erreurs fréquentes."""
    if not LOG_FILE.exists():
        return {"errors": 0, "warnings": 0}
    
    error_count = 0
    warning_count = 0
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "❌" in line:
                error_count += 1
            elif "⚠️" in line:
                warning_count += 1
    
    return {"errors": error_count, "warnings": warning_count}


def optimize_prompts():
    """Optimise les prompts en fonction des erreurs fréquentes."""
    log_analysis = analyze_logs()
    if log_analysis["errors"] > 5:
        print("⚠️  Beaucoup d'erreurs détectées. Optimisation des prompts...")
        
        # Exemple : Ajouter des instructions pour éviter les erreurs JSON
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Modifier le prompt système pour insister sur le format JSON
        system_prompt = config.get("system_prompt", "")
        if "JSON" not in system_prompt:
            system_prompt += "\n⚠️  Réponds UNIQUEMENT en JSON valide. Exemple : [{'action': 'open_app', 'app_name': 'discord'}]"
            config["system_prompt"] = system_prompt
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            
            print("✅ Prompt optimisé pour éviter les erreurs JSON.")


def update_dependencies():
    """Met à jour les dépendances du projet."""
    print("⚙️  Mise à jour des dépendances...")
    try:
        subprocess.run(["pip", "install", "--upgrade", "-r", "requirements.txt"], check=True)
        print("✅ Dépendances mises à jour.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la mise à jour des dépendances: {e}")


def run():
    """Exécute le skill d'auto-amélioration."""
    print("🔧 Self-Improvement Skill activé.")
    
    # Analyser les logs
    log_analysis = analyze_logs()
    print(f"📊 Analyse des logs : {log_analysis['errors']} erreurs, {log_analysis['warnings']} avertissements.")
    
    # Optimiser les prompts si nécessaire
    if log_analysis["errors"] > 0:
        optimize_prompts()
    
    # Mettre à jour les dépendances
    update_dependencies()
    
    print("✅ Self-Improvement Skill terminé.")

# Exemple d'utilisation :
# run()  # Exécute le skill
