import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import os

class ChatWindow:
    def __init__(self, parent, switch_to_config_callback):
        self.parent = parent
        self.switch_to_config = switch_to_config_callback
        self.setup_ui()

    def setup_ui(self):
        # Zone de chat
        self.chat_display = scrolledtext.ScrolledText(self.parent, wrap=tk.WORD, width=80, height=20)
        self.chat_display.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        # Entrée utilisateur
        self.user_input = tk.Entry(self.parent, width=70)
        self.user_input.grid(row=1, column=0, padx=5, pady=5)

        # Boutons
        self.send_button = tk.Button(self.parent, text="Send", command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=5, pady=5)

        self.file_button = tk.Button(self.parent, text="Upload File", command=self.upload_file)
        self.file_button.grid(row=1, column=2, padx=5, pady=5)

        self.config_button = tk.Button(self.parent, text="Change Settings", command=self.switch_to_config)
        self.config_button.grid(row=2, column=0, columnspan=3, pady=10)

    def send_message(self):
        message = self.user_input.get()
        if message:
            self.chat_display.insert(tk.END, f"You: {message}\n")
            self.user_input.delete(0, tk.END)
            # TODO: Envoyer à l'IA et afficher la réponse

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.chat_display.insert(tk.END, f"File uploaded: {os.path.basename(file_path)}\n")
            # TODO: Traiter le fichier (PDF, image, etc.)