import tkinter as tk
from tkinter import ttk
from config_window import ConfigWindow
from chat_window import ChatWindow
from beta_window import BetaWindow

class SudoAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SudoAgent - AI Assistant")
        self.root.geometry("800x600")

        # Onglets
        self.tab_control = ttk.Notebook(root)
        self.config_tab = ttk.Frame(self.tab_control)
        self.chat_tab = ttk.Frame(self.tab_control)
        self.beta_tab = ttk.Frame(self.tab_control)

        self.tab_control.add(self.config_tab, text="Configuration")
        self.tab_control.add(self.chat_tab, text="Chat")
        self.tab_control.add(self.beta_tab, text="Beta")
        self.tab_control.pack(expand=1, fill="both")

        # Initialiser les fenêtres
        self.config_window = ConfigWindow(self.config_tab, self.switch_to_chat)
        self.chat_window = ChatWindow(self.chat_tab, self.switch_to_config)
        self.beta_window = BetaWindow(self.beta_tab)

    def switch_to_chat(self):
        self.tab_control.select(self.chat_tab)

    def switch_to_config(self):
        self.tab_control.select(self.config_tab)

if __name__ == "__main__":
    root = tk.Tk()
    app = SudoAgentGUI(root)
    root.mainloop()