import json
import re
from typing import List, Dict

def parse_llm_output(output: str) -> List[Dict]:
    """Parse la sortie du LLM pour extraire les actions."""
    try:
        # Correction du regex pour éviter les erreurs de syntaxe
        json_match = re.search(r'\[.*\]', output.strip(), re.DOTALL)
        if not json_match:
            print("❌ Aucun JSON trouvé dans la sortie LLM.")
            return []
            
        json_text = json_match.group(0)
        print(f"🔍 JSON brut: {json_text}")  # Log pour débogage
        
        data = json.loads(json_text)
        
        # Accepter liste directe ou objet avec clé "actions"
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "actions" in data:
            return data["actions"]
        else:
            print("❌ Structure JSON inconnue.")
            return []
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        return []
    except re.error as e:
        print(f"❌ Regex error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []