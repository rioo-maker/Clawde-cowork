"""
Always-on-top status overlay + animated neon screen border.
  • Status bar: step + action text, Stop button, ESC hotkey, draggable
  • Neon border: 3-layer glow (bright core + mid bloom + wide halo) on all 4 edges
"""
import ctypes
import math
import threading
import time
import tkinter as tk
from typing import Callable

# ── neon glow design ──────────────────────────────────────────────────────────
# Three layers per edge, from thinnest/brightest to widest/softest.
# They stack on the screen edge and together create a real neon-glow look.
#   (thickness_px, base_alpha, color)
_GLOW_LAYERS = [
    ( 3, 0.92, "#00ffff"),    # core  — razor-thin bright cyan line
    (14, 0.48, "#00ccee"),    # bloom — mid spread
    (32, 0.14, "#0088bb"),    # halo  — wide faint ambient glow
]


def _make_clickthrough(hwnd: int) -> None:
    """WS_EX_TRANSPARENT so the strip passes all mouse events through."""
    try:
        GWL_EXSTYLE       = -20
        WS_EX_LAYERED     = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        cur = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, cur | WS_EX_LAYERED | WS_EX_TRANSPARENT
        )
    except Exception:
        pass


class AIOverlay:
    BG     = "#111118"
    FG     = "#b8ffd0"
    BTN_FG = "#ff6b6b"
    BTN_BG = "#281414"
    W, H   = 580, 46

    def __init__(self, on_stop: Callable[[], None]):
        self._on_stop  = on_stop
        self._root: tk.Tk | None = None
        self._var:  tk.StringVar | None = None
        self._stopped  = False
        self._drag_x = self._drag_y = 0
        # list of (Toplevel, base_alpha) for pulse animation
        self._strips: list[tuple[tk.Toplevel, float]] = []
        self._thread = threading.Thread(target=self._tk_main, daemon=True)

    def start(self):
        self._thread.start()
        time.sleep(0.22)           # give tkinter time to build windows
        self._listen_esc_global()

    def update(self, text: str):
        if self._var:
            try:
                self._var.set(text)
            except Exception:
                pass

    def close(self):
        if self._root and not self._stopped:
            self._stopped = True
            # Remove the global ESC hotkey FIRST so it cannot fire into the
            # next terminal prompt while the user types the next task.
            try:
                import keyboard
                keyboard.remove_hotkey("esc")
            except Exception:
                pass
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    # ── internal ─────────────────────────────────────────────────────────────

    def _stop(self):
        if not self._stopped:
            self._on_stop()
            self.close()

    def _tk_main(self):
        root = tk.Tk()
        self._root = root

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()

        # ── status bar ───────────────────────────────────────────────────────
        root.title("SudoAgent")
        root.attributes("-topmost", True)
        root.overrideredirect(True)
        root.attributes("-alpha", 0.93)

        bar_x = (sw - self.W) // 2
        root.geometry(f"{self.W}x{self.H}+{bar_x}+8")
        root.configure(bg=self.BG)

        frame = tk.Frame(root, bg=self.BG)
        frame.pack(fill="both", expand=True)

        self._var = tk.StringVar(value="🤖  starting…")
        lbl = tk.Label(
            frame, textvariable=self._var,
            fg=self.FG, bg=self.BG,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        lbl.pack(side="left", padx=14, fill="x", expand=True)

        btn = tk.Button(
            frame, text=" ■  Stop ",
            fg=self.BTN_FG, bg=self.BTN_BG,
            activeforeground="#ff4444", activebackground="#3a1a1a",
            font=("Segoe UI", 9, "bold"),
            bd=0, padx=6, pady=4,
            cursor="hand2",
            relief="flat",
            command=self._stop,
        )
        btn.pack(side="right", padx=10, pady=5)

        root.bind("<Escape>", lambda _e: self._stop())

        for widget in (frame, lbl):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>",     self._drag_move)

        # ── neon border — 3 layers × 4 edges = 12 strips ────────────────────
        for thickness, base_alpha, color in _GLOW_LAYERS:
            t = thickness
            # All 4 edge strips for this layer span the full screen edges
            # (corners get double-covered which makes them look extra glowy)
            edge_specs = [
                (0,      0,      sw, t),    # top
                (0,      sh - t, sw, t),    # bottom
                (0,      0,      t,  sh),   # left
                (sw - t, 0,      t,  sh),   # right
            ]
            for (x, y, w, h) in edge_specs:
                strip = tk.Toplevel(root)
                strip.overrideredirect(True)
                strip.attributes("-topmost", True)
                strip.attributes("-alpha", base_alpha)
                strip.configure(bg=color)
                strip.geometry(f"{w}x{h}+{x}+{y}")
                strip.update()
                _make_clickthrough(strip.winfo_id())
                self._strips.append((strip, base_alpha))

        # ── pulse animation (50 ms) ───────────────────────────────────────────
        def _pulse():
            if self._stopped:
                return
            # Sine wave: full range 0.6→1.0 so glow never fully disappears
            t_now = time.time()
            pulse = 0.60 + 0.40 * abs(math.sin(t_now * 2.2))
            for strip, base_alpha in self._strips:
                try:
                    strip.attributes("-alpha", base_alpha * pulse)
                except Exception:
                    pass
            root.after(50, _pulse)

        # ── keep-on-top refresh (350 ms) ─────────────────────────────────────
        # Re-lift all windows so apps that steal focus can't push us behind.
        def _keep_on_top():
            if self._stopped:
                return
            try:
                for strip, _ in self._strips:
                    strip.lift()
                    strip.attributes("-topmost", True)
                root.lift()
                root.attributes("-topmost", True)
            except Exception:
                pass
            root.after(350, _keep_on_top)

        _pulse()
        _keep_on_top()
        root.mainloop()

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        if self._root:
            x = self._root.winfo_x() + event.x - self._drag_x
            y = self._root.winfo_y() + event.y - self._drag_y
            self._root.geometry(f"+{x}+{y}")

    def _listen_esc_global(self):
        """
        Register a global ESC hotkey using keyboard.add_hotkey().
        This is properly cleaned up in close() so it never leaks into
        the next terminal prompt after a task finishes.
        """
        try:
            import keyboard
            # suppress=False lets ESC still work normally inside the terminal
            keyboard.add_hotkey("esc", self._stop, suppress=False)
        except Exception:
            pass
