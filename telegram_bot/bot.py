"""
Telegram bot interface for SudoAgent.

Prerequisites:
  pip install pyTelegramBotAPI

Setup:
  1. @BotFather → /newbot → copy the token
  2. @userinfobot → /start → copy your numeric user ID
  3. SudoAgent CLI → type  config  → Telegram section

Design:
  • Tasks are queued (one at a time) — no simultaneous PC control
  • Polling restarts automatically on any error (including BaseException)
  • pyautogui FAILSAFE is disabled for tasks, restored after
  • Screenshot sent automatically after every task
"""
import io
import base64
import queue
import threading
import time
from typing import Callable

_AVAILABLE = False
try:
    import telebot          # pip install pyTelegramBotAPI
    _AVAILABLE = True
except ImportError:
    pass


class TelegramBot:
    """
    Wraps pyTelegramBotAPI.
    • One background polling thread  (restarts forever on any error)
    • One worker thread              (processes tasks from a queue, one at a time)
    • Sends result + screenshot back after every task
    """

    def __init__(
        self,
        token: str,
        allowed_ids: list[int],
        on_task: Callable[[str, Callable[[str], None]], None],
    ):
        self._token   = token
        self._allowed = set(int(i) for i in allowed_ids) if allowed_ids else set()
        self._on_task = on_task
        self._bot     = None

        # Queue holds (task, chat_id) — maxsize 10 so messages aren't lost
        self._queue: queue.Queue = queue.Queue(maxsize=10)
        self._busy  = threading.Event()   # set while a task is running

        if not _AVAILABLE:
            print(
                "  [Telegram] pyTelegramBotAPI not installed.\n"
                "  Run:  pip install pyTelegramBotAPI"
            )
            return

        self._bot = telebot.TeleBot(token, parse_mode=None)
        self._setup_handlers()

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        if not self._bot:
            return
        # Worker: runs tasks from the queue, one at a time
        threading.Thread(target=self._worker, daemon=True, name="tg-worker").start()
        # Polling: forever-restarting receive loop
        threading.Thread(target=self._poll_forever, daemon=True, name="tg-poll").start()

    def send_message(self, chat_id: int, text: str):
        if not self._bot:
            return
        try:
            self._bot.send_message(chat_id, text)
        except BaseException:
            pass

    def send_photo(self, chat_id: int, img_bytes: bytes, caption: str = ""):
        if not self._bot:
            return
        try:
            self._bot.send_photo(chat_id, io.BytesIO(img_bytes), caption=caption)
        except BaseException:
            pass

    # ── handlers ──────────────────────────────────────────────────────────────

    def _setup_handlers(self):
        bot = self._bot

        @bot.message_handler(commands=["start"])
        def cmd_start(msg):
            uid = msg.from_user.id
            if not self._auth(uid):
                bot.reply_to(msg, f"⛔ Not authorized.\nYour ID: {uid}")
                return
            bot.reply_to(
                msg,
                "👾 *SudoAgent* ready!\n\n"
                "Send me any task and I'll control your PC.\n"
                "_Example: open Chrome and go to YouTube_\n\n"
                "/id — your Telegram user ID\n"
                "/status — is a task running?\n"
                "/help — commands",
                parse_mode="Markdown",
            )

        @bot.message_handler(commands=["help"])
        def cmd_help(msg):
            if not self._auth(msg.from_user.id):
                return
            bot.reply_to(
                msg,
                "📋 *Commands*\n\n"
                "Just type any task to run it on your PC.\n\n"
                "/status — check if a task is running\n"
                "/id     — your numeric Telegram user ID\n"
                "/help   — this message",
                parse_mode="Markdown",
            )

        @bot.message_handler(commands=["id"])
        def cmd_id(msg):
            bot.reply_to(
                msg,
                f"Your Telegram user ID: `{msg.from_user.id}`\n"
                f"Add this to SudoAgent config → Telegram → Authorized user IDs.",
                parse_mode="Markdown",
            )

        @bot.message_handler(commands=["status"])
        def cmd_status(msg):
            if not self._auth(msg.from_user.id):
                return
            pending = self._queue.qsize()
            if self._busy.is_set():
                extra = f"\n{pending} more in queue." if pending else ""
                bot.reply_to(msg, f"⚙️ Task running…{extra}")
            else:
                bot.reply_to(msg, "✅ Idle — send a task!")

        @bot.message_handler(func=lambda m: True)
        def on_message(msg):
            uid     = msg.from_user.id
            chat_id = msg.chat.id

            if not self._auth(uid):
                bot.reply_to(
                    msg,
                    f"⛔ Not authorized.\n"
                    f"Your ID: `{uid}`\n"
                    "Add it via SudoAgent config → Telegram → Authorized user IDs.",
                    parse_mode="Markdown",
                )
                return

            task = msg.text.strip()
            if not task:
                return

            try:
                self._queue.put_nowait((task, chat_id))
            except queue.Full:
                bot.reply_to(msg, "⏳ Too many queued tasks. Try again shortly.")
                return

            pending = self._queue.qsize()
            if self._busy.is_set() or pending > 1:
                bot.reply_to(msg, f"⏳ Queued (position {pending}). Will run when current task finishes.")
            else:
                bot.reply_to(msg, f"🤖 Starting:\n_{task}_", parse_mode="Markdown")

    # ── worker (sequential task execution) ───────────────────────────────────

    def _worker(self):
        """
        Pulls one task at a time from the queue and runs it.
        Catches ALL exceptions (including BaseException) so the worker
        never dies and is always ready for the next task.
        """
        while True:
            try:
                task, chat_id = self._queue.get(timeout=2)
            except queue.Empty:
                continue

            self._busy.set()
            self.send_message(chat_id, f"▶ Running: _{task}_\n\nPlease wait…")

            # Disable pyautogui FAILSAFE so the agent can move to screen corners
            _prev_failsafe = True
            try:
                import pyautogui
                _prev_failsafe     = pyautogui.FAILSAFE
                pyautogui.FAILSAFE = False
            except Exception:
                pass

            result = "Task finished."
            try:
                # reply_fn is called by on_task when the task completes
                _done = threading.Event()
                _result_box = [result]

                def _reply(res: str):
                    _result_box[0] = res
                    _done.set()

                # Run the task
                self._on_task(task, _reply)
                _done.wait(timeout=600)   # up to 10 min
                result = _result_box[0]

            except BaseException as e:
                result = f"❌ Error: {e}"

            finally:
                # Restore FAILSAFE
                try:
                    import pyautogui
                    pyautogui.FAILSAFE = _prev_failsafe
                except Exception:
                    pass
                self._busy.clear()
                self._queue.task_done()

            # Send result
            try:
                self.send_message(chat_id, f"✅ Done:\n{result}")
            except BaseException:
                pass

            # Send screenshot
            try:
                from vision.screenshot import capture_base64
                img_b64, _, _ = capture_base64(annotate=False)
                img_bytes     = base64.b64decode(img_b64)
                self.send_photo(chat_id, img_bytes, caption=f"📸 {task[:80]}")
            except BaseException as e:
                try:
                    self.send_message(chat_id, f"(Screenshot failed: {e})")
                except BaseException:
                    pass

    # ── polling (forever-restarting) ─────────────────────────────────────────

    def _poll_forever(self):
        """
        Keeps the bot polling loop alive forever.
        On ANY error (network, crash, BaseException) waits 5 s then restarts.
        """
        while True:
            try:
                # infinity_polling handles reconnects internally too;
                # fall back to polling(non_stop=True) for older versions.
                try:
                    self._bot.infinity_polling(
                        timeout=20,
                        long_polling_timeout=15,
                        skip_pending=True,
                        allowed_updates=["message"],
                    )
                except AttributeError:
                    # pyTelegramBotAPI < 4.x doesn't have infinity_polling
                    self._bot.polling(
                        non_stop=True,
                        skip_pending=True,
                        timeout=20,
                        long_polling_timeout=15,
                    )
            except BaseException as e:
                print(f"  [Telegram] Polling crashed ({type(e).__name__}: {e}). Restarting in 5 s…")
                try:
                    self._bot.stop_polling()
                except BaseException:
                    pass
                time.sleep(5)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _auth(self, uid: int) -> bool:
        """Return True if this user ID is authorized to send tasks."""
        # Empty list = nobody authorized (safe default)
        return bool(self._allowed) and uid in self._allowed
