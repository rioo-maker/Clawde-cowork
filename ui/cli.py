"""
Rich terminal interface — supports Anthropic and Ollama providers.
"""
import sys
import time
import threading
import pyautogui
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from agent.agent import Agent
from config.settings import load_settings, save_settings, get_api_key
from ui.overlay import AIOverlay


class _UserStopped(Exception):
    pass


def _handle_error(e: Exception) -> None:
    """Print a human-readable error message for common Ollama/network failures."""
    msg = str(e)
    code = getattr(e, "status_code", None)

    if code == 401 or "401" in msg or "unauthorized" in msg.lower():
        console.print("  [bold red]API key rejected (401 Unauthorized).[/bold red]")
        console.print("  [dim]→ Your Ollama API key is invalid or expired.[/dim]")
        console.print("  [dim]→ Get a fresh key at [bold]ollama.com/settings/keys[/bold][/dim]")
        console.print("  [dim]→ Then type [bold]config[/bold] to update it.[/dim]")
    elif code == 403 or "403" in msg or "forbidden" in msg.lower():
        console.print("  [bold red]Access denied (403).[/bold red] This model may require a paid Ollama plan.")
    elif code == 404 or "404" in msg or "not found" in msg.lower():
        console.print(f"  [bold red]Model not found (404).[/bold red]")
        console.print("  [dim]→ For the direct cloud API (ollama.com), use [bold]gpt-oss:120b[/bold] (no -cloud suffix)[/dim]")
        console.print("  [dim]→ For local Ollama with cloud routing, use [bold]gpt-oss:120b-cloud[/bold][/dim]")
    elif "connection" in msg.lower() or "connect" in msg.lower() or "refused" in msg.lower():
        console.print("  [bold red]Cannot reach Ollama.[/bold red]")
        console.print("  [dim]→ Local: run [bold]ollama serve[/bold] in a terminal[/dim]")
        console.print("  [dim]→ Cloud: check your internet connection[/dim]")
    else:
        console.print(f"  [bold red]Error:[/bold red] {e}")

console = Console()

BANNER = """\
[bold cyan]  ___           _        _                    _   [/bold cyan]
[bold cyan] / __| _  _  __| | ___  /_\\  __ _  ___ _ _| |_ [/bold cyan]
[bold cyan] \\__ \\| || |/ _` |/ _ \\/ _ \\/ _` |/ -_) ' \\  _|[/bold cyan]
[bold cyan] |___/ \\_,_|\\__,_|\\___/_/ \\_\\__,_|\\___|_||_\\__|[/bold cyan]
"""

_ICONS = {
    "screenshot":   "📷",
    "click":        "🖱 ",
    "double_click": "🖱 ",
    "type_text":    "⌨ ",
    "press_key":    "⌨ ",
    "scroll":       "↕ ",
    "drag":         "↔ ",
    "open_app":     "🚀",
    "task_complete":"✓ ",
}


def _brief(tool: str, args: dict) -> str:
    """One-liner for the overlay status bar."""
    if tool == "screenshot":   return "screenshot"
    if tool == "click":        return f"click ({args.get('x')}, {args.get('y')})"
    if tool == "double_click": return f"double-click ({args.get('x')}, {args.get('y')})"
    if tool == "type_text":
        t = args.get("text", "")
        return f'type "{t[:28]}…"' if len(t) > 28 else f'type "{t}"'
    if tool == "press_key":    return f"key  {args.get('key')}"
    if tool == "open_app":     return f"open  {args.get('name')}"
    if tool == "scroll":       return f"scroll {args.get('direction')}"
    if tool == "drag":         return f"drag ({args.get('from_x')},{args.get('from_y')}) → ({args.get('to_x')},{args.get('to_y')})"
    if tool == "task_complete":return "done"
    return tool


def _fmt(tool: str, args: dict, step: int) -> str:
    icon  = _ICONS.get(tool, "▶ ")
    num   = f"[dim]{step:>2}[/dim]  "

    if tool == "screenshot":
        return f"{num}{icon} [dim]screenshot[/dim]"

    if tool in ("click", "double_click"):
        lbl = "double-click" if tool == "double_click" else "click"
        btn = args.get("button", "left")
        b   = f" [dim]({btn})[/dim]" if btn != "left" else ""
        return f"{num}{icon} [yellow]{lbl}[/yellow]{b}  [bold]({args['x']}, {args['y']})[/bold]"

    if tool == "type_text":
        t     = args["text"]
        preview = t[:55] + ("…" if len(t) > 55 else "")
        enter = "  [dim]↵[/dim]" if args.get("press_enter") else ""
        return f'{num}{icon} [green]type[/green]  [italic]"{preview}"[/italic]{enter}'

    if tool == "press_key":
        return f"{num}{icon} [magenta]key[/magenta]  [bold]{args['key']}[/bold]"

    if tool == "scroll":
        arrow = "↑" if args["direction"] == "up" else "↓"
        return f"{num}{icon} [blue]scroll[/blue] {arrow}  ({args['x']}, {args['y']})"

    if tool == "drag":
        return f"{num}{icon} [blue]drag[/blue]  ({args['from_x']},{args['from_y']}) → ({args['to_x']},{args['to_y']})"

    if tool == "open_app":
        return f"{num}{icon} [cyan]open[/cyan]  [bold]{args['name']}[/bold]"

    if tool == "task_complete":
        return f"{num}{icon} [bold green]{args.get('summary', 'done')}[/bold green]"

    return f"{num}▶  {tool}  {args}"


def _provider_tag(settings: dict) -> str:
    p = settings.get("provider", "anthropic")
    if p == "ollama":
        model = settings.get("ollama_model", "?")
        url   = settings.get("ollama_url", "")
        mode  = "cloud" if "ollama.com" in url else "local"
        return f"[bold]Ollama[/bold] [dim]·[/dim] {model} [dim]·[/dim] {mode}"
    model = settings.get("anthropic_model", "?")
    return f"[bold]Anthropic[/bold] [dim]·[/dim] {model}"


def _install_startup() -> bool:
    """Add SudoAgent to Windows startup registry."""
    try:
        import winreg
        python_exe = sys.executable
        pythonw = python_exe.replace("python.exe", "pythonw.exe")
        from pathlib import Path as _Path
        if _Path(pythonw).exists():
            python_exe = pythonw
        script = str(_Path(__file__).resolve().parent.parent / "main.py")
        cmd = f'"{python_exe}" "{script}" --autostart'
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "SudoAgent", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        console.print(f"  [red]Startup install failed:[/red] {e}")
        return False


def _remove_startup() -> bool:
    """Remove SudoAgent from Windows startup registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, "SudoAgent")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        console.print(f"  [red]Startup remove failed:[/red] {e}")
        return False


def _startup_installed() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, "SudoAgent")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


class CLI:
    def __init__(self, settings: dict, telegram_bot=None):
        self.settings = settings
        self._telegram_bot = telegram_bot

    def run(self):
        console.print(BANNER)
        console.print(f"  {_provider_tag(self.settings)}  [dim]· max {self.settings['max_iterations']} steps[/dim]")

        if self.settings.get("telegram_token"):
            n = len(self.settings.get("telegram_allowed_ids", []))
            console.print(f"  [green]Telegram bot active[/green]  [dim]· {n} authorized user(s)[/dim]")

        if _startup_installed():
            console.print(f"  [dim]Auto-startup: [green]on[/green][/dim]")

        console.print(f"  [dim]commands: [bold]config[/bold]  schedule  startup  exit[/dim]")

        agent = Agent(self.settings)

        while True:
            console.print()
            try:
                task = Prompt.ask(f"[bold cyan]›[/bold cyan]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye.[/dim]")
                break

            task = task.strip()
            if not task:
                continue
            if task.lower() == "exit":
                console.print("[dim]Goodbye.[/dim]")
                break
            if task.lower() == "config":
                self._config_menu()
                console.print(f"\n  {_provider_tag(self.settings)}  [dim]· max {self.settings['max_iterations']} steps[/dim]")
                agent = Agent(self.settings)
                continue
            if task.lower() in ("schedule", "schedules"):
                self._schedule_menu()
                continue
            if task.lower() in ("startup", "autostart"):
                self._startup_menu()
                continue

            console.print(Rule(f" {task} ", style="cyan", align="left"))
            self._run_task(agent, task)

    # ── task runner ───────────────────────────────────────────────────────────

    def _run_task(self, agent: Agent, task: str):
        step       = 0
        t0         = time.time()
        last_tool  = [None]

        # ── stop mechanism ────────────────────────────────────────────────────
        stop_event = threading.Event()
        overlay    = AIOverlay(on_stop=stop_event.set)
        overlay.start()

        # Disable pyautogui corner-failsafe while agent runs
        _prev_failsafe      = pyautogui.FAILSAFE
        pyautogui.FAILSAFE  = False

        def on_action(tool, args):
            nonlocal step
            # Check if user hit Stop before executing next action
            if stop_event.is_set():
                raise _UserStopped()
            step += 1
            overlay.update(f"🤖  step {step}  ·  {_brief(tool, args)}")
            if tool != "screenshot" and last_tool[0] == "screenshot":
                console.print()
            last_tool[0] = tool
            console.print(f"  {_fmt(tool, args, step)}")

        def on_text(text):
            stripped = text.strip()
            if stripped:
                console.print(f"\n  [dim italic]{stripped}[/dim italic]\n")

        try:
            with console.status("  [bold cyan]thinking…[/bold cyan]", spinner="dots"):
                result = agent.run_task(task, on_action=on_action, on_text=on_text)

            elapsed = time.time() - t0
            footer  = f"[dim]{step} step{'s' if step != 1 else ''} · {elapsed:.1f}s[/dim]"
            console.print()
            console.print(Panel(
                f"[bold green]{result}[/bold green]\n{footer}",
                border_style="green",
                padding=(0, 1),
            ))
            self._notify_telegram(task, result)

        except (_UserStopped, KeyboardInterrupt):
            elapsed = time.time() - t0
            console.print(f"\n  [yellow]Stopped[/yellow] [dim]after {step} step{'s' if step != 1 else ''} · {elapsed:.1f}s[/dim]")

        except anthropic.AuthenticationError:
            console.print("  [bold red]Invalid Anthropic API key.[/bold red] Type [bold]config[/bold] to update it.")

        except Exception as e:
            _handle_error(e)

        finally:
            pyautogui.FAILSAFE = _prev_failsafe
            time.sleep(0.5)   # flush lingering keyboard/mouse events before prompt returns
            overlay.close()

    # ── telegram notification ─────────────────────────────────────────────────

    def _notify_telegram(self, task: str, result: str):
        """After a CLI task completes, send result + screenshot to Telegram."""
        bot = self._telegram_bot
        if not bot:
            return
        ids = self.settings.get("telegram_allowed_ids", [])
        if not ids:
            return
        try:
            import base64
            from vision.screenshot import capture_base64
            img_b64, _, _ = capture_base64(annotate=False)
            img_bytes = base64.b64decode(img_b64)
            uid = int(ids[0])
            bot.send_message(uid, f"✅ Task done:\n{result}")
            bot.send_photo(uid, img_bytes, caption=f"📸 {task[:80]}")
        except Exception:
            pass

    # ── schedule menu ─────────────────────────────────────────────────────────

    def _schedule_menu(self):
        from scheduler.scheduler import (
            load_schedules, add_schedule, remove_schedule, toggle_schedule,
        )

        while True:
            schedules = load_schedules()
            console.print()
            console.print(Rule(" Schedules ", style="cyan", align="left"))

            if not schedules:
                console.print("  [dim]No schedules yet. Type [bold]add[/bold] to create one.[/dim]")
            else:
                t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
                t.add_column("ID",     style="bold yellow")
                t.add_column("Name")
                t.add_column("Time",   style="bold")
                t.add_column("Days",   style="dim")
                t.add_column("Status")
                t.add_column("Task",   style="dim")
                for s in schedules:
                    status     = "[green]on[/green]" if s.get("enabled", True) else "[red]off[/red]"
                    days_str   = ", ".join(s.get("days", ["daily"]))
                    preview    = s.get("task", "")[:45]
                    if len(s.get("task", "")) > 45:
                        preview += "…"
                    t.add_row(s["id"], s.get("name", ""), s.get("time", ""), days_str, status, preview)
                console.print(t)

            console.print()
            console.print("  [dim]add  ·  remove <id>  ·  toggle <id>  ·  back[/dim]")

            try:
                cmd = Prompt.ask("[cyan]schedule›[/cyan]").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd in ("", "back", "exit", "q", "quit"):
                break

            elif cmd == "add":
                name     = Prompt.ask("  Name (e.g. Morning routine)")
                time_str = Prompt.ask("  Time (HH:MM, 24h)", default="09:00")
                console.print("  Days: [bold]daily[/bold], mon, tue, wed, thu, fri, sat, sun (comma-separated)")
                days_raw = Prompt.ask("  Days", default="daily")
                days     = [d.strip().lower() for d in days_raw.split(",") if d.strip()]
                task     = Prompt.ask("  Task to run (what SudoAgent will do)")
                entry    = add_schedule(name, time_str, days, task)
                console.print(f"  [green]✓ Schedule [{entry['id']}] created.[/green]")

            elif cmd.startswith("remove "):
                sid = cmd[7:].strip()
                if remove_schedule(sid):
                    console.print("  [green]✓ Removed.[/green]")
                else:
                    console.print("  [red]Not found.[/red]")

            elif cmd.startswith("toggle "):
                sid   = cmd[7:].strip()
                state = toggle_schedule(sid)
                if state is not None:
                    console.print(f"  [green]{'Enabled' if state else 'Disabled'}.[/green]")
                else:
                    console.print("  [red]Not found.[/red]")

            else:
                console.print(f"  [dim]Unknown: {cmd}[/dim]")

    # ── startup menu ──────────────────────────────────────────────────────────

    def _startup_menu(self):
        console.print()
        console.print(Rule(" Auto-startup ", style="cyan", align="left"))
        console.print("  Adds SudoAgent to Windows startup so it runs on every boot.")
        console.print("  In background mode: Telegram bot + Scheduler run silently.")
        console.print()

        installed = _startup_installed()
        status    = "[green]installed ✓[/green]" if installed else "[dim]not installed[/dim]"
        console.print(f"  Status: {status}")
        console.print()

        if installed:
            choice = Prompt.ask("  Remove from startup?", choices=["yes", "no"], default="no")
            if choice == "yes":
                if _remove_startup():
                    console.print("  [green]✓ Removed from startup.[/green]")
        else:
            console.print("  [dim]Requires Telegram bot token to be configured (type [bold]config[/bold]).[/dim]")
            choice = Prompt.ask("  Install auto-startup?", choices=["yes", "no"], default="yes")
            if choice == "yes":
                if _install_startup():
                    console.print("  [green]✓ SudoAgent will start automatically on next boot.[/green]")
                    console.print("  [dim]Runs silently in background — control via Telegram.[/dim]")

    # ── config menu ───────────────────────────────────────────────────────────

    def _config_menu(self):
        console.print()
        console.print(Rule(" Settings ", style="yellow", align="left"))

        provider = Prompt.ask(
            "Provider",
            choices=["anthropic", "ollama"],
            default=self.settings.get("provider", "anthropic"),
        )
        self.settings["provider"] = provider

        if provider == "anthropic":
            self._config_anthropic()
        else:
            self._config_ollama()

        val = Prompt.ask("Max steps", default=str(self.settings["max_iterations"]))
        try:
            self.settings["max_iterations"] = int(val)
        except ValueError:
            pass

        # ── Telegram ──────────────────────────────────────────────────────────
        console.print()
        console.print(Rule(" Telegram Bot (optional) ", style="yellow", align="left"))
        console.print("  [dim]Control SudoAgent from your phone. Get a bot token from @BotFather.[/dim]")
        console.print("  [dim]Get your user ID from @userinfobot (send /start).[/dim]")
        console.print()

        cur_token = self.settings.get("telegram_token", "")
        token_hint = "keep" if cur_token else "skip"
        new_token = Prompt.ask(
            f"  Bot token [dim](Enter = {token_hint})[/dim]",
            default="",
            password=True,
        )
        if new_token.strip():
            self.settings["telegram_token"] = new_token.strip()

        cur_ids = self.settings.get("telegram_allowed_ids", [])
        ids_hint = ", ".join(str(i) for i in cur_ids) if cur_ids else "none"
        console.print(f"  Current authorized IDs: [bold]{ids_hint}[/bold]")
        new_ids = Prompt.ask(
            "  Authorized user IDs [dim](comma-separated integers, Enter = keep)[/dim]",
            default="",
        )
        if new_ids.strip():
            try:
                self.settings["telegram_allowed_ids"] = [
                    int(x.strip()) for x in new_ids.split(",") if x.strip()
                ]
            except ValueError:
                console.print("  [red]Invalid IDs — keeping existing.[/red]")

        save_settings(self.settings)
        console.print("[green]Saved.[/green]")

    def _config_anthropic(self):
        new_key = Prompt.ask("Anthropic API key [dim](Enter = keep)[/dim]", default="", password=True)
        if new_key.strip():
            self.settings["anthropic_api_key"] = new_key.strip()
        new_model = Prompt.ask("Model", default=self.settings.get("anthropic_model", "claude-sonnet-4-6"))
        self.settings["anthropic_model"] = new_model

    def _config_ollama(self):
        console.print(
            "\n  [cyan]local[/cyan]  Ollama on your PC  [dim](ollama serve)[/dim]\n"
            "  [cyan]cloud[/cyan]  ollama.com API  [dim](needs API key from ollama.com/settings/keys)[/dim]\n"
        )
        mode = Prompt.ask("Mode", choices=["local", "cloud"],
                          default="cloud" if self.settings.get("ollama_api_key") else "local")

        if mode == "cloud":
            api_key = Prompt.ask("Ollama API key [dim](Enter = keep)[/dim]", default="", password=True)
            if api_key.strip():
                self.settings["ollama_api_key"] = api_key.strip()
            self.settings["ollama_url"] = "https://ollama.com"
            console.print("  [dim]Browse models: ollama.com/search?c=cloud[/dim]")
            new_model = Prompt.ask("Model", default=self.settings.get("ollama_model", "gpt-oss:120b-cloud"))
        else:
            self.settings["ollama_api_key"] = ""
            console.print()
            t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
            t.add_column("Model",        style="bold")
            t.add_column("Vision",       style="dim")
            t.add_column("Tools",        style="dim")
            t.add_column("Size",         style="dim")
            t.add_row("llama3.2-vision:11b", "yes", "yes", "6.7 GB")
            t.add_row("llama3.2-vision:3b",  "yes", "yes", "2.0 GB")
            t.add_row("qwen2.5-vl:7b",       "yes", "yes", "4.7 GB")
            t.add_row("qwen2.5-vl:3b",       "yes", "yes", "2.3 GB")
            t.add_row("qwen2.5:7b",          "—",   "yes", "4.7 GB")
            t.add_row("llama3.1:8b",         "—",   "yes", "4.7 GB")
            console.print(t)
            console.print("  [dim]Pull a model: ollama pull llama3.2-vision:11b[/dim]\n")
            new_url = Prompt.ask("Ollama URL", default=self.settings.get("ollama_url", "http://localhost:11434"))
            self.settings["ollama_url"] = new_url
            new_model = Prompt.ask("Model", default=self.settings.get("ollama_model", "llama3.2-vision:11b"))

        self.settings["ollama_model"] = new_model

        try:
            from ollama import Client
            url     = self.settings["ollama_url"]
            api_key = self.settings.get("ollama_api_key", "")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            Client(host=url, headers=headers).list()
            console.print("[green]Connected.[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not connect:[/yellow] {e}")
