# 🤖 Sudo Agent

**Sudo Agent** is an open-source AI computer control agent that can operate your computer using natural language commands.

It converts user instructions into real computer actions such as:

* Moving the mouse
* Clicking
* Typing
* Opening applications
* Reading the screen
* Executing tasks step-by-step

The goal of Sudo Agent is to make **local AI computer control simple, modular, and accessible to everyone.**

---

## Star History

<a href="https://www.star-history.com/?repos=rioo-maker%2FClawde-cowork&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=rioo-maker/Clawde-cowork&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=rioo-maker/Clawde-cowork&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=rioo-maker/Clawde-cowork&type=date&legend=top-left" />
 </picture>
</a>

---

# 🚀 Overview

Sudo Agent is a **CLI-based autonomous computer operator** designed to control a machine using AI reasoning.

It supports:

* Local AI models (Ollama)
* Cloud AI APIs
* Mouse & keyboard automation
* Screen reading (OCR)
* Structured action execution
* User confirmation before actions

This project is **inspired by the concepts behind Claude Cowork and OpenClaw**, combining ideas from both into a simple and extensible open-source system.

---

# ✨ Features

* 🧠 AI-powered task execution
* 🖱 Mouse automation
* ⌨ Keyboard automation
* 📷 Screenshot & OCR support
* 🧩 Modular architecture
* 🔒 Safe confirmation system
* ⚡ CLI-based interface
* 🧱 Supports local or API models
* 🧪 Easy to extend with new tools

---

# 🧠 How It Works

Sudo Agent follows a simple loop:

1. Receive user command
2. Send request to AI
3. AI returns structured actions
4. User confirms execution
5. Actions run on the computer
6. Repeat until task is complete

Example:

User:

```
open discord
```

Agent generates:

```json
[
  {"action": "press_key", "key": "win"},
  {"action": "type_text", "text": "discord"},
  {"action": "press_key", "key": "enter"}
]
```

Then executes it.

---

# 🛠 Installation

## 1 — Clone the repository

```bash
git clone https://github.com/rioo-maker/Clawde-cowork.git

```

---

## 2 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3 — Install Tesseract (OCR)

Download:

https://github.com/UB-Mannheim/tesseract/wiki

Then make sure:

```
tesseract.exe
```

is added to your PATH.

---

## 4 — Setup environment

Create:

```
.env
```

Example:

```
OPENAI_API_KEY=your_key_here
OLLAMA_MODEL=llama3
```

---

# ▶ Usage

Run:

```bash
python main.py
```

Then type:

```
>>> open notepad
```

or:

```
>>> open discord
```

The agent will:

1. Think
2. Generate actions
3. Ask confirmation
4. Execute

---

# 🖱 Supported Actions

Currently supported:

* move_mouse
* click
* double_click
* right_click
* scroll
* type_text
* press_key
* drag_mouse
* wait
* screenshot
* read_screen

More actions will be added in future versions.

---

# 🔒 Security

Sudo Agent includes:

* Confirmation before executing actions
* Controlled action execution
* Optional sandbox system
* Restricted dangerous operations

⚠️ Important:

This software **controls your computer**.

Always:

* Review generated actions
* Avoid running unknown prompts
* Use responsibly

---

# 🧩 Models Supported

You can use:

## Local Models

Via:

```
Ollama
```

Example:

```
ollama run llama3
```

---

## API Models

Such as:

* OpenAI
* Other compatible APIs

---

# 🎯 Goals

The long-term vision of Sudo Agent:

* Local-first AI control
* Multi-agent support
* UI automation
* Autonomous workflows
* Cross-platform compatibility
* Plugin ecosystem

---

# 🧪 Example Commands

```
open discord
```

```
type hello world
```

```
open browser
```

```
search google for weather
```

```
open file explorer
```

---

# 🧱 Architecture Philosophy

Sudo Agent is built with:

* Modularity
* Transparency
* Extensibility
* Safety-first execution
* Human confirmation loop

Everything is designed to be:

**simple to understand
easy to modify
easy to expand**

---

# 🌍 Open Source

This project is:

* Free to use
* Open-source
* Community-driven

We hope developers, builders, and researchers will:

* Improve it
* Extend it
* Share ideas
* Build new tools

If this project helps you, consider contributing ⭐

---

# 🙌 Inspiration

Sudo Agent is inspired by ideas from:

* Claude Cowork
* OpenClaw

This project combines concepts from both into a simplified and customizable open-source implementation.

Huge respect to the teams and communities pushing forward AI agents.

---

# 🛣 Roadmap

Planned features:

* GUI interface
* Vision-based UI detection
* Memory system
* Multi-agent coordination
* Browser automation
* Plugin system
* Task persistence
* Cross-platform support
* Voice commands

---

# 🐞 Known Limitations

Current limitations:

* CLI only (no GUI yet)
* UI navigation may require tuning
* OCR accuracy depends on screen quality
* Requires user confirmation
* Still experimental

---

# 🤝 Contributing

Contributions are welcome.

You can:

* Submit issues
* Suggest features
* Improve code
* Add modules
* Fix bugs

Steps:

```bash
fork repo

create branch

make changes

submit pull request
```

---

 GPL-3.0 license

 ---

# ❤️ Final Words

Sudo Agent is an experimental project created with passion for AI automation and computer control.

The goal is simple:

**make AI capable of operating computers in a transparent, modular, and open way.**

We hope this project inspires developers and creators around the world.

Enjoy building.

🚀
