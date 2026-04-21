from agent.parser import parse_llm_output
from agent.executor import execute_actions
from llm.ollama_client import OllamaClient
from vision.screen_analyzer import analyze_screen
from skills.skill_loader import find_skill_for_task, run_skill, load_all_skills

class AgentController:

    def __init__(self):
        self.llm = OllamaClient()
        # Charger les skills au démarrage
        load_all_skills()

    def run_instruction(self, instruction: str):
        import re
        try:
            print("🧠 Thinking...")
            
            # Chercher un skill adapté à la tâche
            skill = find_skill_for_task(instruction)
            if skill:
                skill_name, skill_type, json_examples = skill
                print(f"🛠️  Skill trouvé: {skill_name} ({skill_type})")
                
                if skill_type == "md" and json_examples:
                    # Utiliser les exemples JSON extraits du .md
                    print(f"✅ Exécution automatique des actions depuis {skill_name}.md")
                    for example in json_examples:
                        if isinstance(example, list):
                            execute_actions(example)
                        else:
                            execute_actions([example])
                    return
                else:
                    # Afficher les instructions ou exécuter le .py
                    if not run_skill(skill_name):
                        print(f"❌ Erreur lors de l'utilisation du skill {skill_name}.")
                    else:
                        # Si c'est un skill .py, on arrête ici
                        if skill_type == "py":
                            return
            
            # Si aucun skill trouvé, utiliser le LLM
            screen_text = analyze_screen()
            full_prompt = f"""
            SCREEN CONTENT:
            {screen_text}

            USER:
            {instruction}

            Réponds UNIQUEMENT en JSON valide. Exemple :
            [
              {{"action": "open_app", "app_name": "discord"}},
              {{"action": "move_mouse", "x": 500, "y": 300, "duration": 0.5}},
              {{"action": "click"}}
            ]
            """
            
            response = self.llm.generate(full_prompt)
            actions = parse_llm_output(response)
            
            # Extraire le texte clair (première partie avant le JSON)
            text_match = re.search(r"([\s\S]*?)(?=\[)", response.strip())
            if text_match:
                print(f"\n🤖 Sudo Agent:\n{text_match.group(1).strip()}\n")
            
            # Afficher les actions à exécuter
            if actions:
                print("⚠️ Actions à exécuter:")
                for i, action in enumerate(actions, 1):
                    if action["action"] == "move_mouse":
                        print(f"{i}. Déplacer la souris vers ({action.get('x', 0)}, {action.get('y', 0)}) en {action.get('duration', 0.5)} seconde.")
                    elif action["action"] == "click":
                        print(f"{i}. Cliquer.")
                    elif action["action"] == "open_app":
                        print(f"{i}. Ouvrir l'application {action.get('app_name', 'inconnue')}.")
                    elif action["action"] == "run_skill":
                        print(f"{i}. Exécuter le skill {action.get('skill_name', 'inconnu')}.")
                
                confirm = input("\nConfirmer ? (y/n): ").strip().lower()
                if confirm == 'y':
                    execute_actions(actions)
                else:
                    print("❌ Annulé.")
            else:
                print("❌ Aucune action valide trouvée.")
                
        except Exception as e:
            print(f"❌ Error: {e}")