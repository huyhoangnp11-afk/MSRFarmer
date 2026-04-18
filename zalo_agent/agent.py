from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

from .browser import BrowserLaunchError, create_edge_driver
from .config import CONFIG_FILE, load_config
from .dom import click_sidebar_chat, send_chat_message, strip_accents, take_snapshot
from .llm import LLMClient


class ZaloAgent:
    def __init__(self, logger, on_log=None, on_status=None):
        self.logger = logger
        self.on_log = on_log or (lambda message: None)
        self.on_status = on_status or (lambda status: None)
        self.driver = None
        self.driver_lock = threading.RLock()
        self.monitor_thread = None
        self.monitor_stop = threading.Event()
        self.last_reply_at: dict[str, float] = {}
        self.chat_states: dict[str, dict] = {}
        self.headless = False
        self.llm_client = LLMClient(logger)
        self._last_llm_notice = ""

    def _emit_log(self, message: str) -> None:
        self.logger.info(message)
        self.on_log(message)

    def _set_status(self, message: str) -> None:
        self.on_status(message)

    def _chat_url_from_current_driver(self) -> str:
        if not self.driver:
            return "https://chat.zalo.me/"
        try:
            current_url = self.driver.current_url
        except Exception:
            return "https://chat.zalo.me/"

        parsed = urlparse(current_url or "")
        if parsed.scheme in {"http", "https"} and parsed.netloc.endswith("zalo.me"):
            return current_url
        return "https://chat.zalo.me/"

    def _launch_browser(self, headless: bool, target_url: str) -> None:
        self._set_status("Launching Edge...")
        self.driver = create_edge_driver(headless=headless)
        self.driver.get(target_url)
        self.headless = headless
        mode_label = "background" if headless else "visible"
        self._set_status(f"Edge ready ({mode_label})")
        self._emit_log(f"Edge session opened with a persistent profile in {mode_label} mode.")

    def _switch_browser_mode_locked(self, headless: bool) -> None:
        if not self.driver:
            self._launch_browser(headless=headless, target_url="https://chat.zalo.me/")
            return
        if self.headless == headless:
            return

        target_url = self._chat_url_from_current_driver()
        old_driver = self.driver
        old_mode = "background" if self.headless else "visible"
        new_mode = "background" if headless else "visible"

        self._emit_log(f"Switching browser from {old_mode} mode to {new_mode} mode...")
        self.driver = None
        try:
            old_driver.quit()
        except Exception:
            pass
        time.sleep(1.0)
        self._launch_browser(headless=headless, target_url=target_url)

    def ensure_browser(self, headless: bool = False) -> None:
        with self.driver_lock:
            if self.driver and self.headless == headless:
                return
            if self.driver:
                self._switch_browser_mode_locked(headless=headless)
                return
            try:
                self._launch_browser(headless=headless, target_url="https://chat.zalo.me/")
            except BrowserLaunchError:
                self.driver = None
                self.headless = False
                raise

    def switch_browser_mode(self, headless: bool) -> None:
        with self.driver_lock:
            try:
                self._switch_browser_mode_locked(headless=headless)
            except BrowserLaunchError:
                self.driver = None
                self.headless = False
                raise

    def close(self) -> None:
        self.stop_monitoring()
        with self.driver_lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
        self.headless = False
        self._set_status("Closed")

    def read_snapshot(self) -> dict:
        with self.driver_lock:
            if not self.driver:
                raise RuntimeError("Browser is not started.")
            return take_snapshot(self.driver)

    def send_manual_message(self, text: str) -> bool:
        with self.driver_lock:
            if not self.driver:
                raise RuntimeError("Browser is not started.")
            return send_chat_message(self.driver, text)

    def get_browser_mode_label(self) -> str:
        return "Background" if self.headless else "Visible"

    def start_monitoring(self) -> None:
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        self.monitor_stop.clear()
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="ZaloAgentMonitor",
            daemon=True,
        )
        self.monitor_thread.start()

    def stop_monitoring(self) -> None:
        self.monitor_stop.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        self.monitor_thread = None
        self._set_status("Monitor stopped")

    def _chat_key(self, title: str, preview: str = "") -> str:
        return f"{strip_accents(title)}|{strip_accents(preview)}"

    def _fingerprint(self, chat_key: str, message: dict) -> str:
        return f"{chat_key}|{message['side']}|{message['ordinal']}|{message['text']}"

    def _get_chat_state(self, chat_key: str, chat_title: str, preview: str = "") -> dict:
        state = self.chat_states.setdefault(
            chat_key,
            {
                "chat_title": chat_title,
                "preview": preview,
                "seen_fingerprints": set(),
                "initialized": False,
                "last_scan_at": 0.0,
                "last_llm_at": 0.0,
            },
        )
        state["chat_title"] = chat_title
        if preview:
            state["preview"] = preview
        return state

    def _pick_auto_reply(self, message_text: str, config: dict) -> str | None:
        normalized_text = strip_accents(message_text)
        for rule in config.get("rules", []):
            keywords = rule.get("contains", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            normalized_keywords = [strip_accents(keyword) for keyword in keywords if keyword]
            if normalized_keywords and any(keyword in normalized_text for keyword in normalized_keywords):
                reply = str(rule.get("reply", "")).strip()
                if reply:
                    return reply
        return None

    def _send_auto_reply_if_allowed(self, chat_key: str, chat_title: str, reply: str) -> bool:
        with self.driver_lock:
            if not self.driver:
                return False
            sent = send_chat_message(self.driver, reply)
        if sent:
            self.last_reply_at[chat_key] = time.time()
            self._emit_log(f"Auto reply sent to [{chat_title}]: {reply}")
        return sent

    def _try_rule_auto_reply(self, chat_key: str, chat_title: str, message: dict, config: dict) -> None:
        if not config.get("auto_reply_enabled"):
            return
        reply = self._pick_auto_reply(message["text"], config)
        if not reply:
            return
        cooldown_sec = max(int(config.get("reply_cooldown_sec", 90)), 0)
        now = time.time()
        if now - self.last_reply_at.get(chat_key, 0) < cooldown_sec:
            return
        self._send_auto_reply_if_allowed(chat_key, chat_title, reply)

    def _emit_llm_notice_if_needed(self, config: dict) -> None:
        llm_config = config.get("llm", {})
        if not llm_config.get("enabled"):
            return
        api_key_name = llm_config.get("api_key_env", "GEMINI_API_KEY")
        notice = ""
        if not self.llm_client.is_enabled(config):
            notice = f"LLM enabled but env var {api_key_name} is missing. Edit .env and restart the app."
        if notice and notice != self._last_llm_notice:
            self._emit_log(notice)
            self._last_llm_notice = notice

    def _recent_context(self, messages: list[dict], config: dict) -> list[dict]:
        limit = max(int(config.get("max_context_messages", 12)), 4)
        return messages[-limit:]

    def _analyze_with_llm(
        self,
        chat_key: str,
        chat_title: str,
        recent_messages: list[dict],
        new_messages: list[dict],
        config: dict,
    ) -> dict | None:
        llm_config = config.get("llm", {})
        if not llm_config.get("enabled") or not new_messages:
            return None

        self._emit_llm_notice_if_needed(config)
        if not self.llm_client.is_enabled(config):
            return None

        state = self.chat_states.get(chat_key, {})
        min_interval_sec = max(int(llm_config.get("min_interval_sec", 20)), 0)
        now = time.time()
        if now - float(state.get("last_llm_at", 0)) < min_interval_sec:
            return None

        analysis = self.llm_client.analyze_chat(
            config=config,
            chat_title=chat_title,
            recent_messages=recent_messages,
            new_messages=new_messages,
            my_aliases=list(config.get("my_aliases", [])),
            priority_keywords=list(config.get("priority_keywords", [])),
        )
        state["last_llm_at"] = now
        if not analysis:
            return None

        priority = analysis.get("priority", "low").upper()
        summary = analysis.get("summary", "")
        reason = analysis.get("reason", "")
        related = analysis.get("related_to_me", False)
        needs_reply = analysis.get("needs_reply", False)
        self._emit_log(
            f"[LLM][{chat_title}] {priority} | related={related} | needs_reply={needs_reply} | {summary}"
        )
        if reason:
            self._emit_log(f"[LLM][{chat_title}] reason: {reason}")
        suggested_reply = analysis.get("suggested_reply", "")
        if suggested_reply:
            self._emit_log(f"[LLM][{chat_title}] suggested reply: {suggested_reply}")
            if (
                llm_config.get("auto_send_suggested_reply")
                and config.get("auto_reply_enabled")
                and related
                and needs_reply
            ):
                cooldown_sec = max(int(config.get("reply_cooldown_sec", 90)), 0)
                if now - self.last_reply_at.get(chat_key, 0) >= cooldown_sec:
                    self._send_auto_reply_if_allowed(chat_key, chat_title, suggested_reply)
        return analysis

    def _collect_new_messages(
        self,
        chat_key: str,
        chat_title: str,
        preview: str,
        messages: list[dict],
        unread_hint: int,
    ) -> list[dict]:
        state = self._get_chat_state(chat_key, chat_title, preview)
        incoming_messages = [message for message in messages if message["side"] == "incoming"]
        new_messages: list[dict] = []

        if not state["initialized"]:
            if unread_hint > 0 and incoming_messages:
                take_count = min(max(unread_hint, 1), len(incoming_messages), 6)
                new_messages = incoming_messages[-take_count:]
            state["initialized"] = True
            state["seen_fingerprints"] = {
                self._fingerprint(chat_key, message) for message in messages
            }
        else:
            for message in messages:
                fingerprint = self._fingerprint(chat_key, message)
                if fingerprint in state["seen_fingerprints"]:
                    continue
                state["seen_fingerprints"].add(fingerprint)
                if message["side"] == "incoming":
                    new_messages.append(message)

        state["last_scan_at"] = time.time()
        return new_messages

    def _process_chat_snapshot(self, snapshot: dict, config: dict, sidebar_chat: dict | None = None) -> None:
        chat_title = snapshot.get("chat_title", "Current chat")
        preview = (sidebar_chat or {}).get("preview", "")
        chat_key = (sidebar_chat or {}).get("chat_key") or self._chat_key(chat_title, preview)
        unread_hint = int((sidebar_chat or {}).get("unread_count", 0) or 0)
        messages = snapshot.get("normalized_messages", [])

        new_messages = self._collect_new_messages(
            chat_key=chat_key,
            chat_title=chat_title,
            preview=preview,
            messages=messages,
            unread_hint=unread_hint,
        )
        if not new_messages:
            return

        for message in new_messages:
            self._emit_log(f"[{chat_title}] {message['text']}")
            self._try_rule_auto_reply(chat_key, chat_title, message, config)

        recent_messages = self._recent_context(messages, config)
        self._analyze_with_llm(
            chat_key=chat_key,
            chat_title=chat_title,
            recent_messages=recent_messages,
            new_messages=new_messages,
            config=config,
        )

    def _prioritize_sidebar_chats(self, snapshot: dict, config: dict) -> tuple[list[dict], dict | None]:
        sidebar_chats = list(snapshot.get("normalized_sidebar_chats", []))
        active_chat = next((chat for chat in sidebar_chats if chat.get("is_active")), None)
        if not sidebar_chats:
            return [], active_chat

        priority_keywords = [strip_accents(keyword) for keyword in config.get("priority_keywords", []) if keyword]
        scan_all = bool(config.get("scan_all_visible_chats", True))
        for chat in sidebar_chats:
            chat_key = self._chat_key(chat["title"], chat.get("preview", ""))
            state = self.chat_states.get(chat_key, {})
            searchable_text = strip_accents(f"{chat['title']} {chat.get('preview', '')}")
            chat["chat_key"] = chat_key
            chat["priority_match"] = any(keyword in searchable_text for keyword in priority_keywords)
            chat["last_scan_at"] = float(state.get("last_scan_at", 0))

        if scan_all:
            candidates = sidebar_chats
        else:
            candidates = [
                chat
                for chat in sidebar_chats
                if chat.get("is_active") or chat.get("unread_count", 0) > 0 or chat.get("priority_match")
            ]

        def sort_key(chat: dict) -> tuple:
            return (
                0 if chat.get("unread_count", 0) > 0 else 1,
                0 if chat.get("priority_match") else 1,
                0 if chat.get("is_active") else 1,
                chat.get("last_scan_at", 0),
                chat.get("top", 0),
            )

        max_chats = max(int(config.get("max_chats_per_cycle", 5)), 1)
        candidates = sorted(candidates, key=sort_key)[:max_chats]
        if active_chat and active_chat not in candidates:
            candidates = [active_chat] + candidates[:-1]
        return candidates, active_chat

    def _focus_sidebar_chat(self, sidebar_chat: dict, current_snapshot: dict) -> dict:
        current_title = current_snapshot.get("chat_title", "")
        target_title = sidebar_chat.get("title", "")
        if sidebar_chat.get("is_active") or (target_title and target_title == current_title):
            return current_snapshot

        with self.driver_lock:
            if not self.driver:
                raise RuntimeError("Browser is not started.")
            clicked = click_sidebar_chat(self.driver, sidebar_chat)
        if not clicked:
            return current_snapshot

        for _ in range(6):
            snapshot = self.read_snapshot()
            snapshot_title = snapshot.get("chat_title", "")
            if target_title and snapshot_title == target_title:
                return snapshot
            if snapshot_title and snapshot_title != current_title:
                return snapshot
            time.sleep(0.25)
        return self.read_snapshot()

    def _restore_sidebar_chat(self, sidebar_chat: dict) -> None:
        with self.driver_lock:
            if not self.driver:
                return
            click_sidebar_chat(self.driver, sidebar_chat, settle_sec=0.5)

    def _monitor_loop(self) -> None:
        self._set_status("Monitoring chats...")
        self._emit_log(f"Monitoring started. Edit rules in: {CONFIG_FILE}")

        while not self.monitor_stop.is_set():
            try:
                config = load_config()
                snapshot = self.read_snapshot()

                if not snapshot.get("composer_ready"):
                    self._set_status("Login to Zalo Web and open the chat list")
                    self.monitor_stop.wait(max(float(config.get("poll_interval_sec", 4)), 1))
                    continue

                candidates, original_active_chat = self._prioritize_sidebar_chats(snapshot, config)
                if not candidates:
                    self._process_chat_snapshot(snapshot, config)
                    self._set_status("Following current chat")
                else:
                    self._set_status(f"Scanning {len(candidates)} visible chats...")
                    current_snapshot = snapshot
                    for sidebar_chat in candidates:
                        if self.monitor_stop.is_set():
                            break
                        current_snapshot = self._focus_sidebar_chat(sidebar_chat, current_snapshot)
                        self._process_chat_snapshot(current_snapshot, config, sidebar_chat=sidebar_chat)
                    if original_active_chat:
                        self._restore_sidebar_chat(original_active_chat)

            except Exception as exc:
                self._emit_log(f"Monitor error: {exc}")
                self._set_status("Monitor error. Check the log and keep the agent app running.")

            interval = load_config().get("poll_interval_sec", 4)
            try:
                sleep_seconds = max(float(interval), 1)
            except (TypeError, ValueError):
                sleep_seconds = 4
            self.monitor_stop.wait(sleep_seconds)
