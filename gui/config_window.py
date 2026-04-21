import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os

class ConfigWindow:
    def __init__(self, parent, switch_to_chat_callback):
        self.parent = parent
        self.switch_to_chat = switch_to_chat_callback
        self.setup_ui()

    def setup_ui(self):
        # Mode (API publique ou LLM local)
        tk.Label(self.parent, text="Choose Mode:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.mode = ttk.Combobox(self.parent, values=["Public API (Ollama/OpenAI)", "Local LLM"])
        self.mode.current(0)
        self.mode.grid(row=0, column=1, padx=10, pady=5)

        # API Key / URL
        tk.Label(self.parent, text="API URL or Local Address:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.api_entry = tk.Entry(self.parent, width=50)
        self.api_entry.grid(row=1, column=1, padx=10, pady=5)

        # Model
        tk.Label(self.parent, text="Model:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.model_entry = tk.Entry(self.parent, width=50)
        self.model_entry.insert(0, "qwen3.5:4b")
        self.model_entry.grid(row=2, column=1, padx=10, pady=5)

        # Test Connection
        self.test_button = tk.Button(self.parent, text="Test Connection", command=self.test_connection)
        self.test_button.grid(row=3, column=0, padx=10, pady=10)

        # Save & Continue
        self.save_button = tk.Button(self.parent, text="Save & Continue", command=self.save_config)
        self.save_button.grid(row=3, column=1, padx=10, pady=10)

    def test_connection(self):
        api_url = self.api_entry.get()
        model = self.model_entry.get()

        if not api_url:
            messagebox.showerror("Error", "Please enter an API URL or local address.")
            return

        try:
            response = requests.get(f"{api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if any(m["name"] == model for m in models):
                    messagebox.showinfo("Success", "Connection successful! Model available.")
                else:
                    messagebox.showerror("Error", f"Model '{model}' not found on this server.")
            else:
                messagebox.showerror("Error", f"HTTP Error: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

    def save_config(self):
        config = {
            "api_url": self.api_entry.get(),
            "model": self.model_entry.get(),
            "mode": self.mode.get()
        }
        os.makedirs("config", exist_ok=True)
        with open("config/settings.json", "w") as f:
            json.dump(config, f, indent=4)
        messagebox.showinfo("Success", "Configuration saved!")
        self.switch_to_chat()