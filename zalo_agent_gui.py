from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from tkinter import scrolledtext

from zalo_agent.agent import ZaloAgent
from zalo_agent.browser import BrowserLaunchError
from zalo_agent.config import CONFIG_FILE, ENV_FILE, PROFILE_DIR, get_logger, ensure_runtime_files, load_config


class ZaloAgentGUI:
    def __init__(self, root: tk.Tk):
        ensure_runtime_files()
        self.root = root
        self.root.title("Zalo Personal Agent")
        self.root.geometry("980x660")
        self.root.minsize(820, 560)

        self.logger = get_logger()
        self.status_var = tk.StringVar(value="Ready")
        self.chat_var = tk.StringVar(
            value="Flow: Open Zalo Web -> login -> keep chat list visible -> Start Monitor -> Run In Background"
        )
        self.browser_mode_var = tk.StringVar(value="Browser mode: Closed")
        self.manual_message_var = tk.StringVar()

        self.agent = ZaloAgent(
            logger=self.logger,
            on_log=self._append_log,
            on_status=self._update_status,
        )

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        top_frame = tk.Frame(self.root, padx=12, pady=10)
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)

        title = tk.Label(top_frame, text="Zalo Personal Agent", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        status = tk.Label(
            top_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 11, "bold"),
            fg="#005a9e",
        )
        status.grid(row=0, column=1, sticky="e")

        hint = tk.Label(
            top_frame,
            textvariable=self.chat_var,
            anchor="w",
            justify="left",
            font=("Segoe UI", 10),
        )
        hint.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        mode_hint = tk.Label(
            top_frame,
            textvariable=self.browser_mode_var,
            anchor="w",
            justify="left",
            font=("Segoe UI", 10),
            fg="#475569",
        )
        mode_hint.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        button_frame = tk.Frame(self.root, padx=12, pady=6)
        button_frame.grid(row=1, column=0, sticky="ew")
        for index in range(8):
            button_frame.grid_columnconfigure(index, weight=1)

        self.open_button = tk.Button(button_frame, text="Open Zalo Web", command=self._open_zalo)
        self.open_button.grid(row=0, column=0, padx=4, sticky="ew")

        self.start_button = tk.Button(button_frame, text="Start Monitor", command=self._start_monitor)
        self.start_button.grid(row=0, column=1, padx=4, sticky="ew")

        self.stop_button = tk.Button(button_frame, text="Stop Monitor", command=self._stop_monitor)
        self.stop_button.grid(row=0, column=2, padx=4, sticky="ew")

        self.hide_button = tk.Button(button_frame, text="Run In Background", command=self._run_in_background)
        self.hide_button.grid(row=0, column=3, padx=4, sticky="ew")

        self.show_button = tk.Button(button_frame, text="Show Browser", command=self._show_browser)
        self.show_button.grid(row=0, column=4, padx=4, sticky="ew")

        self.snapshot_button = tk.Button(button_frame, text="Check Current Chat", command=self._check_chat)
        self.snapshot_button.grid(row=0, column=5, padx=4, sticky="ew")

        self.rules_button = tk.Button(button_frame, text="Open Rules File", command=self._open_rules_folder)
        self.rules_button.grid(row=0, column=6, padx=4, sticky="ew")

        self.env_button = tk.Button(button_frame, text="Open .env", command=self._open_env_file)
        self.env_button.grid(row=0, column=7, padx=4, sticky="ew")

        composer_frame = tk.Frame(self.root, padx=12, pady=6)
        composer_frame.grid(row=2, column=0, sticky="nsew")
        composer_frame.grid_columnconfigure(0, weight=1)
        composer_frame.grid_rowconfigure(1, weight=1)

        send_frame = tk.Frame(composer_frame)
        send_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        send_frame.grid_columnconfigure(0, weight=1)

        entry = tk.Entry(send_frame, textvariable=self.manual_message_var, font=("Segoe UI", 11))
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        entry.bind("<Return>", lambda _event: self._send_manual_message())

        send_button = tk.Button(send_frame, text="Send Manual Message", command=self._send_manual_message)
        send_button.grid(row=0, column=1, sticky="ew")

        self.log_widget = scrolledtext.ScrolledText(
            composer_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#ffffff",
        )
        self.log_widget.grid(row=1, column=0, sticky="nsew")

        footer_text = (
            f"Profile: {PROFILE_DIR}\n"
            f"Rules: {CONFIG_FILE}\n"
            f"Env: {ENV_FILE}\n"
            "The agent can scan multiple visible chats from the sidebar and optionally call an LLM API.\n"
            "Background mode keeps a headless Edge session alive, but this GUI process must stay running."
        )
        footer = tk.Label(
            composer_frame,
            text=footer_text,
            justify="left",
            anchor="w",
            font=("Segoe UI", 9),
            fg="#475569",
        )
        footer.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _append_log(self, message: str) -> None:
        def write() -> None:
            self.log_widget.insert(tk.END, message + "\n")
            self.log_widget.see(tk.END)

        self.root.after(0, write)

    def _update_status(self, message: str) -> None:
        self.root.after(0, lambda: self.status_var.set(message))

    def _update_browser_mode(self) -> None:
        mode_text = "Browser mode: Closed"
        if self.agent.driver:
            mode_text = f"Browser mode: {self.agent.get_browser_mode_label()}"
        self.root.after(0, lambda: self.browser_mode_var.set(mode_text))

    def _open_zalo(self) -> None:
        try:
            self.agent.ensure_browser(headless=False)
        except BrowserLaunchError as exc:
            messagebox.showerror("Edge launch failed", str(exc))
            return
        self._update_browser_mode()
        self._append_log(
            "Open Zalo Web, scan QR if needed, keep the sidebar chat list visible, then start monitor."
        )

    def _start_monitor(self) -> None:
        try:
            self.agent.ensure_browser(headless=False)
        except BrowserLaunchError as exc:
            messagebox.showerror("Edge launch failed", str(exc))
            return
        self.agent.start_monitoring()
        self._update_browser_mode()

    def _stop_monitor(self) -> None:
        self.agent.stop_monitoring()
        self._update_browser_mode()

    def _run_in_background(self) -> None:
        try:
            self.agent.ensure_browser(headless=False)
            self.agent.switch_browser_mode(headless=True)
        except BrowserLaunchError as exc:
            messagebox.showerror("Switch failed", str(exc))
            return
        self._update_browser_mode()
        self._append_log(
            "Browser switched to background mode. The Edge window can disappear but tracking continues while this app stays open."
        )

    def _show_browser(self) -> None:
        try:
            self.agent.ensure_browser(headless=True)
            self.agent.switch_browser_mode(headless=False)
        except BrowserLaunchError as exc:
            messagebox.showerror("Switch failed", str(exc))
            return
        self._update_browser_mode()
        self._append_log("Browser switched back to visible mode.")

    def _check_chat(self) -> None:
        try:
            snapshot = self.agent.read_snapshot()
        except Exception as exc:
            messagebox.showerror("Snapshot failed", str(exc))
            return

        chat_title = snapshot.get("chat_title", "Current chat")
        message_count = len(snapshot.get("normalized_messages", []))
        sidebar_count = len(snapshot.get("normalized_sidebar_chats", []))
        composer_ready = snapshot.get("composer_ready", False)
        llm_config = load_config().get("llm", {})
        llm_status = "on" if llm_config.get("enabled") else "off"
        self.chat_var.set(
            f"Current chat: {chat_title} | Visible messages: {message_count} | Sidebar chats: {sidebar_count} | LLM: {llm_status}"
        )
        self._append_log(
            f"Snapshot -> chat: {chat_title}, visible messages: {message_count}, sidebar chats: {sidebar_count}, composer ready: {composer_ready}, llm: {llm_status}"
        )

    def _send_manual_message(self) -> None:
        text = self.manual_message_var.get().strip()
        if not text:
            return
        try:
            sent = self.agent.send_manual_message(text)
        except Exception as exc:
            messagebox.showerror("Send failed", str(exc))
            return
        if not sent:
            messagebox.showwarning(
                "Composer not found",
                "Open one Zalo conversation first, then try again.",
            )
            return
        self._append_log(f"Manual message sent: {text}")
        self.manual_message_var.set("")

    def _open_rules_folder(self) -> None:
        target = Path(CONFIG_FILE)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        try:
            import os

            os.startfile(str(target))
        except OSError as exc:
            messagebox.showerror("Open file failed", str(exc))

    def _open_env_file(self) -> None:
        target = Path(ENV_FILE)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        try:
            import os

            os.startfile(str(target))
        except OSError as exc:
            messagebox.showerror("Open file failed", str(exc))

    def _on_close(self) -> None:
        try:
            self.agent.close()
        finally:
            self._update_browser_mode()
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ZaloAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
