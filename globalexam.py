"""
globalexam.py
Main entry point — Tkinter GUI that drives the autonomous agent.
Credentials and settings are loaded from config.py (edit that file).
"""

import logging
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

import config
from agent import browser as browser_mod
from agent import solver as solver_mod
from agent.tracker import Tracker

# ---------------------------------------------------------------------------
# Logging -> also pipe into the GUI text widget
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Suppress noisy debug spam from third-party libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
logging.getLogger("webdriver_manager").setLevel(logging.WARNING)
logging.getLogger("WDM").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GlobalExam Solver")
        self.geometry("780x700")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        self._driver = None
        self._thread = None
        self._running = False

        self._build_ui()
        self._attach_log_handler()

    def _build_ui(self):
        PAD = dict(padx=12, pady=6)
        BG = "#1e1e2e"
        FG = "#cdd6f4"
        ENTRY_BG = "#313244"
        BTN_START = "#a6e3a1"
        BTN_STOP  = "#f38ba8"
        FONT_LABEL = ("Segoe UI", 10)
        FONT_BOLD  = ("Segoe UI", 10, "bold")
        FONT_MONO  = ("Consolas", 9)

        tk.Label(self, text="GlobalExam Autonomous Solver",
                 font=("Segoe UI", 14, "bold"), bg=BG, fg="#89b4fa"
                 ).pack(pady=(14, 4))

        cred_frame = tk.LabelFrame(self, text=" Credentials ",
                                   bg=BG, fg=FG, font=FONT_BOLD,
                                   bd=1, relief="groove")
        cred_frame.pack(fill="x", **PAD)

        tk.Label(cred_frame, text="Email:", bg=BG, fg=FG, font=FONT_LABEL).grid(
            row=0, column=0, sticky="e", padx=8, pady=4)
        self._email_var = tk.StringVar(value=config.EMAIL)
        tk.Entry(cred_frame, textvariable=self._email_var, width=36,
                 bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat"
                 ).grid(row=0, column=1, padx=8, pady=4, sticky="w")

        tk.Label(cred_frame, text="Password:", bg=BG, fg=FG, font=FONT_LABEL).grid(
            row=1, column=0, sticky="e", padx=8, pady=4)
        self._pass_var = tk.StringVar(value=config.PASSWORD)
        tk.Entry(cred_frame, textvariable=self._pass_var, show="*", width=36,
                 bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat"
                 ).grid(row=1, column=1, padx=8, pady=4, sticky="w")

        cfg_frame = tk.LabelFrame(self, text=" Settings ",
                                  bg=BG, fg=FG, font=FONT_BOLD,
                                  bd=1, relief="groove")
        cfg_frame.pack(fill="x", **PAD)

        labels   = ["Subdomain:", "Target hours:", "Page delay (s):", "Exercise delay (s):"]
        defaults = [config.SUBDOMAIN, config.TARGET_HOURS,
                    config.PAGE_LOAD_DELAY, config.EXERCISE_DELAY]
        self._cfg_vars = []
        for col, (lbl, val) in enumerate(zip(labels, defaults)):
            tk.Label(cfg_frame, text=lbl, bg=BG, fg=FG, font=FONT_LABEL).grid(
                row=0, column=col*2, sticky="e", padx=(10, 2), pady=6)
            var = tk.StringVar(value=str(val))
            tk.Entry(cfg_frame, textvariable=var, width=10,
                     bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat"
                     ).grid(row=0, column=col*2+1, padx=(0, 10), pady=6, sticky="w")
            self._cfg_vars.append(var)

        # ---- Buttons (above log so always visible) ----
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(4, 4))

        self._start_btn = tk.Button(
            btn_frame, text="Start Agent", width=20,
            bg=BTN_START, fg="#1e1e2e", font=FONT_BOLD,
            relief="flat", cursor="hand2",
            command=self._on_start,
        )
        self._start_btn.grid(row=0, column=0, padx=8)

        self._stop_btn = tk.Button(
            btn_frame, text="Stop", width=12,
            bg=BTN_STOP, fg="#1e1e2e", font=FONT_BOLD,
            relief="flat", cursor="hand2", state="disabled",
            command=self._on_stop,
        )
        self._stop_btn.grid(row=0, column=1, padx=8)

        tk.Button(
            btn_frame, text="Quit", width=10,
            bg="#45475a", fg=FG, font=FONT_LABEL,
            relief="flat", cursor="hand2",
            command=self._on_quit,
        ).grid(row=0, column=2, padx=8)

        # ---- Status + progress ----
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(fill="x", padx=12, pady=(0, 2))

        self._status_var = tk.StringVar(value="Idle")
        tk.Label(prog_frame, textvariable=self._status_var,
                 bg=BG, fg="#a6e3a1", font=FONT_LABEL).pack(side="left")

        self._progress = ttk.Progressbar(prog_frame, mode="indeterminate", length=200)
        self._progress.pack(side="right", padx=(0, 4))

        # ---- Log (fills remaining space) ----
        log_frame = tk.LabelFrame(self, text=" Live Log ",
                                  bg=BG, fg=FG, font=FONT_BOLD,
                                  bd=1, relief="groove")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._log_box = scrolledtext.ScrolledText(
            log_frame, state="disabled", bg="#11111b", fg="#cdd6f4",
            font=FONT_MONO, relief="flat", wrap="word",
        )
        self._log_box.pack(fill="both", expand=True, padx=4, pady=4)

    def _attach_log_handler(self):
        handler = _TkLogHandler(self._append_log)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(handler)

    def _append_log(self, text):
        self.after(0, self._do_append_log, text)

    def _do_append_log(self, text):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", text + "\n")
        self._log_box.configure(state="disabled")
        self._log_box.see("end")

    def _on_start(self):
        email    = self._email_var.get().strip()
        password = self._pass_var.get().strip()
        if not email or not password:
            self._append_log("[ERROR] Email and password cannot be empty.")
            return

        config.EMAIL    = email
        config.PASSWORD = password
        config.SUBDOMAIN = self._cfg_vars[0].get().strip() or config.SUBDOMAIN
        try:
            config.TARGET_HOURS    = float(self._cfg_vars[1].get())
            config.PAGE_LOAD_DELAY = float(self._cfg_vars[2].get())
            config.EXERCISE_DELAY  = float(self._cfg_vars[3].get())
        except ValueError:
            self._append_log("[WARN] Invalid numeric setting -- using defaults.")

        self._running = True
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._status_var.set("Running...")
        self._progress.start(12)

        self._thread = threading.Thread(target=self._agent_loop, daemon=True)
        self._thread.start()

    def _on_stop(self):
        self._running = False
        self._append_log("[INFO] Stop requested -- finishing current exercise...")
        self._status_var.set("Stopping...")
        self._stop_btn.configure(state="disabled")

    def _on_quit(self):
        self._running = False
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
        self.destroy()

    def _agent_loop(self):
        import time
        driver = None
        try:
            self._append_log("[INFO] Building browser...")
            driver = browser_mod.build_driver()
            self._driver = driver

            self._append_log(f"[INFO] Logging in as {config.EMAIL}...")
            ok = browser_mod.login(driver, config.EMAIL, config.PASSWORD)
            if not ok:
                self._append_log("[ERROR] Login failed. Check credentials.")
                return

            self._append_log("[INFO] Login successful. Starting exercise loop...")
            tracker = Tracker()
            consecutive_failures = 0

            while self._running and tracker.elapsed_hours() < config.TARGET_HOURS:
                self.after(0, self._status_var.set, tracker.summary())
                try:
                    success = solver_mod.solve_one_exercise(driver, config.SUBDOMAIN, tracker)
                    if success:
                        tracker.record_success()
                        consecutive_failures = 0
                        self._append_log(f"[OK] {tracker.summary()}")
                    else:
                        tracker.record_failure()
                        consecutive_failures += 1
                        self._append_log(f"[WARN] Failed ({consecutive_failures} consecutive).")
                        if consecutive_failures >= 5:
                            self._append_log("[WARN] 5 consecutive failures -- pausing 30s...")
                            end = time.time() + 30
                            while self._running and time.time() < end:
                                time.sleep(0.5)
                            consecutive_failures = 0
                except Exception as exc:
                    tracker.record_failure()
                    consecutive_failures += 1
                    self._append_log(f"[ERROR] {exc}")
                    time.sleep(5)

            if not self._running:
                self._append_log("[INFO] Agent stopped by user.")
            else:
                self._append_log(f"[INFO] Target reached! {tracker.summary()}")

        except Exception as exc:
            self._append_log(f"[FATAL] {exc}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            self._driver = None
            self.after(0, self._reset_ui)

    def _reset_ui(self):
        self._running = False
        self._progress.stop()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_var.set("Idle")


class _TkLogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self._cb = callback

    def emit(self, record):
        try:
            self._cb(self.format(record))
        except Exception:
            pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
