# Skill: Ouvrir une application via CMD

## Description
Ce skill permet d'ouvrir une application en utilisant des commandes CMD. Il est plus rapide et plus fiable que les actions souris.

## Commandes disponibles
- `start discord:` → Ouvre Discord.
- `start chrome` → Ouvre Chrome.
- `start notepad` → Ouvre le Bloc-notes.
- `start calc` → Ouvre la Calculatrice.
- `start spotify:` → Ouvre Spotify.

## Exemple d'utilisation
Pour ouvrir Discord, utilisez le JSON suivant :
```json
[
  {
    "action": "open_app",
    "app_name": "discord"
  }
]
```

## Notes
- Ce skill est prioritaire sur les actions souris pour les applications supportées.
- Si la commande CMD échoue, le système essaiera de trouver le chemin de l'application.
