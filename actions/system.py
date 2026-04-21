import os
import subprocess
import platform

def open_app(app):

    system = platform.system()

    if system == "Windows":
        subprocess.Popen(app)

    elif system == "Linux":
        subprocess.Popen([app])

    elif system == "Darwin":
        subprocess.Popen(["open", "-a", app])

from security.sandbox import is_path_safe

import subprocess
import platform


def open_app(app):

    allowed_apps = [
        "notepad",
        "calc",
        "chrome"
    ]

    if app.lower() not in allowed_apps:
        print(f"🚫 App blocked: {app}")
        return

    system = platform.system()

    if system == "Windows":
        subprocess.Popen(app)

    elif system == "Linux":
        subprocess.Popen([app])