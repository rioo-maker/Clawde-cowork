import importlib.util
import os
import re
from pathlib import Path
from typing import Dict, Callable, Optional, List, Tuple

# Chemin vers le dossier des skills
SKILLS_DIR = Path(__file__).parent.parent / "skills"

# Dictionnaires pour stocker les skills
skills_py: Dict[str, Callable] = {}  # Skills exécutables (.py)
skills_md: Dict[str, Dict] = {}       # Skills documentés (.md)


def load_skill_py(skill_name: str) -> bool:
    """Charge un skill exécutable (.py)."""
    skill_path = SKILLS_DIR / f"{skill_name}.py"
    if not skill_path.exists():
        return False
    
    try:
        spec = importlib.util.spec_from_file_location(skill_name, skill_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Vérifier si le skill a une fonction 'run'
        if hasattr(module, "run"):
            skills_py[skill_name] = module.run
            return True
        return False
    except Exception as e:
        print(f"❌ Erreur lors du chargement du skill {skill_name}: {e}")
        return False


def load_skill_md(skill_name: str) -> bool:
    """Charge un skill documenté (.md)."""
    skill_path = SKILLS_DIR / f"{skill_name}.md"
    if not skill_path.exists():
        return False
    
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extraire le titre et la description
        title_match = re.search(r"^# Skill: (.+)$", content, re.MULTILINE)
        desc_match = re.search(r"^## Description\n(.+?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
        
        if not title_match or not desc_match:
            return False
        
        skills_md[skill_name] = {
            "title": title_match.group(1).strip(),
            "description": desc_match.group(1).strip(),
            "content": content
        }
        return True
    except Exception as e:
        print(f"❌ Erreur lors du chargement du skill {skill_name}: {e}")
        return False


def load_all_skills():
    """Charge tous les skills (.py et .md) du dossier skills."""
    if not SKILLS_DIR.exists():
        return
    
    for file in SKILLS_DIR.glob("*.py"):
        skill_name = file.stem
        load_skill_py(skill_name)
    
    for file in SKILLS_DIR.glob("*.md"):
        skill_name = file.stem
        load_skill_md(skill_name)


def find_skill_for_task(task: str) -> Optional[Tuple[str, str, Optional[List[Dict]]]]:
    """Trouve un skill adapté à une tâche donnée et extrait les exemples JSON."""
    task_lower = task.lower()
    
    # Vérifier d'abord les skills documentés (.md)
    for skill_name, skill_data in skills_md.items():
        if skill_name.lower() in task_lower or skill_name.lower() in skill_data["description"].lower():
            # Extraire les exemples JSON du fichier .md
            json_examples = extract_json_examples(skill_data["content"])
            return (skill_name, "md", json_examples)
    
    # Vérifier les skills exécutables (.py) en dernier
    for skill_name, skill_func in skills_py.items():
        if skill_name.lower() in task_lower:
            return (skill_name, "py", None)
    
    return None

def extract_json_examples(md_content: str) -> Optional[List[Dict]]:
    """Extrait les exemples JSON d'un fichier Markdown."""
    json_blocks = re.findall(r"```json\n([\s\S]*?)\n```", md_content)
    examples = []
    
    for block in json_blocks:
        try:
            examples.append(json.loads(block))
        except json.JSONDecodeError:
            continue
    
    return examples if examples else None


def run_skill(skill_name: str, *args, **kwargs) -> bool:
    """Exécute un skill (.py) ou affiche sa documentation (.md)."""
    if skill_name in skills_py:
        try:
            skills_py[skill_name](*args, **kwargs)
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution du skill {skill_name}: {e}")
            return False
    elif skill_name in skills_md:
        print(f"\n📖 Skill: {skills_md[skill_name]['title']}")
        print(f"\n{skills_md[skill_name]['description']}")
        print("\n📜 Contenu du skill :")
        print(skills_md[skill_name]['content'])
        return True
    else:
        return False

# Exemple d'utilisation :
# load_all_skills()  # Charger tous les skills au démarrage
# skill = find_skill_for_task("ouvrir discord")  # Trouve un skill adapté
# if skill:
#     run_skill(skill[0], app_name="discord")  # Exécute le skill
