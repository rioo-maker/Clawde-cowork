import requests
import os
import urllib.parse
from typing import Dict
from config.settings import save_config, DEFAULT_CONFIG


def is_valid_url(url: str) -> bool:
    """Vérifie si l'URL est valide (format uniquement)."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except:
        return False

def test_ollama_connection(url: str, model: str) -> bool:
    """Teste la connexion à l'API Ollama."""
    if not is_valid_url(url):
        print("❌ URL invalide. Exemple: 'http://localhost:11434' ou 'https://ollama.com/api'.")
        return False
    
    test_url = f"{url.rstrip('/')}/api/tags"
    try:
        print(f"🔍 Test de connexion à {test_url}...")
        response = requests.get(test_url, timeout=10)  # Timeout augmenté à 10 secondes
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            if any(m["name"] == model for m in models):
                print("✅ Connexion réussie ! Modèle disponible.")
                return True
            else:
                print(f"❌ Modèle '{model}' non disponible sur ce serveur.")
                return False
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Timeout: Le serveur n'a pas répondu dans les temps.")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Erreur de connexion: Impossible d'atteindre le serveur.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur inconnue: {e}")
        return False


def interactive_setup() -> Dict:
    """Lance la configuration interactive."""
    print("⚙️  Configuration initiale de SudoAgent")
    print("----------------------------------------")
    
    config = DEFAULT_CONFIG.copy()
    
    while True:
        print("\n1. Configurer l'API LLM")
        print("2. Configurer la sandbox")
        print("3. Définir le répertoire de travail")
        print("4. Sauvegarder et continuer")
        choice = input("\nChoisissez une option (1-4): ").strip()
        
        if choice == "1":
            print("\n⚙️  Configuration de l'API LLM")
            print("--------------------------------")
            config["ollama_url"] = input(f"URL de l'API [{config['ollama_url']}]: ") or config["ollama_url"]
            config["ollama_model"] = input(f"Modèle [{config['ollama_model']}]: ") or config["ollama_model"]
            
            print("\nTest de la connexion à l'API Ollama...")
            if test_ollama_connection(config["ollama_url"], config["ollama_model"]):
                print("✅ Connexion réussie ! Modèle disponible.")
            else:
                print("❌ Échec de la connexion. Veuillez vérifier les informations saisies.")
                
        elif choice == "2":
            print("\n⚙️  Configuration de la sandbox")
            print("--------------------------------")
            sandbox_choice = input(f"Activer la sandbox ? (Oui/Non) [{'Oui' if config['sandbox_enabled'] else 'Non'}]: ").strip().lower()
            if sandbox_choice in ["non", "n"]:
                print("\n⚠️  ATTENTION : Désactiver la sandbox permet à SudoAgent d'accéder à tout votre système de fichiers.")
                print("Cela peut être dangereux et entraîner des modifications non désirées.")
                confirm = input("\nConfirmer ? (Oui/Non): ").strip().lower()
                if confirm in ["oui", "o"]:
                    config["sandbox_enabled"] = False
            else:
                config["sandbox_enabled"] = True
                
        elif choice == "3":
            print("\n⚙️  Définir le répertoire de travail")
            print("--------------------------------")
            working_dir = input(f"Répertoire de travail [{config['working_directory']}]: ").strip()
            if working_dir:
                if os.path.isdir(working_dir):
                    config["working_directory"] = working_dir
                else:
                    print("❌ Répertoire invalide.")
                    
        elif choice == "4":
            if save_config(config):
                print("\n✅ Configuration sauvegardée !")
                return config
            else:
                print("❌ Erreur lors de la sauvegarde de la configuration.")
                
        else:
            print("❌ Option invalide.")