import json
import os

ALLOWLIST_FILE = "security/allowlist.json"
BLOCKED_FILE = "security/blocked_actions.json"


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def is_action_allowed(action_name):

    blocked = load_json(BLOCKED_FILE)

    if action_name in blocked:
        return False

    return True