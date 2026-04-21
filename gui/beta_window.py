import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

class BetaWindow:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        # Shortcuts pour apps/fichiers
        tk.Label(self.parent, text="App/File Shortcuts").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.shortcuts_list = tk.Listbox(self.parent, width=50, height=5)
        self.shortcuts_list.grid(row=1, column=0, padx=10, pady=5, columnspan=2)

        self.add_shortcut_button = tk.Button(self.parent, text="Add Shortcut", command=self.add_shortcut)
        self.add_shortcut_button.grid(row=2, column=0, padx=10, pady=5)

        # Prompt Optimization
        tk.Label(self.parent, text="Prompt Optimization").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.prompt_text = tk.Text(self.parent, width=50, height=5)
        self.prompt_text.grid(row=4, column=0, padx=10, pady=5, columnspan=2)

        self.save_prompt_button = tk.Button(self.parent, text="Save Prompt", command=self.save_prompt)
        self.save_prompt_button.grid(row=5, column=0, columnspan=2, pady=5)

    def add_shortcut(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.shortcuts_list.insert(tk.END, file_path)

    def save_prompt(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if prompt:
            os.makedirs("prompts", exist_ok=True)
            with open("prompts/custom_prompt.md", "w") as f:
                f.write(prompt)
            messagebox.showinfo("Success", "Prompt saved!")