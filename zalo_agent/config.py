from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
PROFILE_DIR = BASE_DIR / "profiles" / "zalo_web_agent"
PROFILE_NAME = "Default"
CONFIG_FILE = BASE_DIR / "zalo_agent_rules.json"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

DEFAULT_CONFIG = {
    "poll_interval_sec": 4,
    "scan_all_visible_chats": True,
    "max_chats_per_cycle": 5,
    "max_context_messages": 12,
    "my_aliases": [],
    "priority_keywords": ["gap", "khan", "urgent", "goi", "call", "ban oi"],
    "auto_reply_enabled": False,
    "reply_cooldown_sec": 90,
    "llm": {
        "enabled": False,
        "provider": "gemini",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash-lite",
        "min_interval_sec": 20,
        "max_output_tokens": 250,
        "auto_send_suggested_reply": False,
    },
    "rules": [
        {
            "contains": ["alo", "hello", "hi"],
            "reply": "Minh da thay tin nhan. Lat minh tra loi nhe.",
        },
        {
            "contains": ["gap", "khan", "urgent"],
            "reply": "Neu viec gap ban goi truc tiep giup minh nhe.",
        },
    ],
}


def ensure_runtime_files() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    (PROFILE_DIR / PROFILE_NAME).mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            "# Fill one of these keys, then restart the app.\n"
            "GEMINI_API_KEY=\n"
            "OPENROUTER_API_KEY=\n",
            encoding="utf-8",
        )


def _deep_merge(defaults: dict, raw: dict) -> dict:
    merged = deepcopy(defaults)
    for key, value in raw.items():
        if key not in merged:
            continue
        if isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    ensure_runtime_files()
    try:
        raw_config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw_config, dict):
            raise ValueError("Config root must be an object")
        config = _deep_merge(DEFAULT_CONFIG, raw_config)
    except Exception:
        config = deepcopy(DEFAULT_CONFIG)
        CONFIG_FILE.write_text(
            json.dumps(config, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    return config


def get_logger() -> logging.Logger:
    ensure_runtime_files()
    logger = logging.getLogger("zalo_agent")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_path = LOG_DIR / f"zalo_agent_{datetime.now().strftime('%Y%m%d')}.log"

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger
