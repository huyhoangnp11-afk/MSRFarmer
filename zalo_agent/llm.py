from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


DEFAULT_ANALYSIS = {
    "related_to_me": False,
    "needs_reply": False,
    "priority": "low",
    "summary": "",
    "reason": "",
    "suggested_reply": "",
}


class LLMClient:
    def __init__(self, logger):
        self.logger = logger
        self.timeout_sec = 30

    def is_enabled(self, config: dict) -> bool:
        llm_config = config.get("llm", {})
        if not llm_config.get("enabled"):
            return False
        api_key_name = llm_config.get("api_key_env", "GEMINI_API_KEY")
        return bool(os.getenv(api_key_name, "").strip())

    def analyze_chat(
        self,
        config: dict,
        chat_title: str,
        recent_messages: list[dict],
        new_messages: list[dict],
        my_aliases: list[str],
        priority_keywords: list[str],
    ) -> dict | None:
        llm_config = config.get("llm", {})
        if not llm_config.get("enabled"):
            return None

        api_key_name = llm_config.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.getenv(api_key_name, "").strip()
        if not api_key:
            return None

        system_prompt = (
            "You are a message triage assistant for a Vietnamese user managing many Zalo chats. "
            "Return JSON only with keys: related_to_me, needs_reply, priority, summary, reason, suggested_reply. "
            "priority must be one of low, medium, high. "
            "summary and reason should each be under 160 characters. "
            "If the message is not really about the user, set related_to_me=false and keep suggested_reply empty."
        )
        user_prompt = self._build_user_prompt(
            chat_title=chat_title,
            recent_messages=recent_messages,
            new_messages=new_messages,
            my_aliases=my_aliases,
            priority_keywords=priority_keywords,
        )

        provider = str(llm_config.get("provider", "gemini")).strip().lower()
        try:
            if provider == "gemini":
                payload_text = self._call_gemini(llm_config, api_key, system_prompt, user_prompt)
            elif provider == "openrouter":
                payload_text = self._call_openrouter(llm_config, api_key, system_prompt, user_prompt)
            else:
                self.logger.warning("Unsupported LLM provider: %s", provider)
                return None
            result = self._parse_json_response(payload_text)
            return self._normalize_result(result)
        except Exception as exc:
            self.logger.warning("LLM analyze failed: %s", exc)
            return None

    def _build_user_prompt(
        self,
        chat_title: str,
        recent_messages: list[dict],
        new_messages: list[dict],
        my_aliases: list[str],
        priority_keywords: list[str],
    ) -> str:
        transcript_lines = []
        for message in recent_messages:
            speaker = "Me" if message.get("side") == "outgoing" else "Them"
            transcript_lines.append(f"{speaker}: {message.get('text', '').strip()}")

        new_lines = []
        for message in new_messages:
            speaker = "Me" if message.get("side") == "outgoing" else "Them"
            new_lines.append(f"{speaker}: {message.get('text', '').strip()}")

        aliases = ", ".join(alias for alias in my_aliases if alias) or "(none)"
        priorities = ", ".join(keyword for keyword in priority_keywords if keyword) or "(none)"

        return (
            f"Chat title: {chat_title}\n"
            f"My aliases: {aliases}\n"
            f"Priority keywords: {priorities}\n"
            "Recent context:\n"
            + "\n".join(transcript_lines[-20:])
            + "\n\nNew messages to evaluate:\n"
            + "\n".join(new_lines[-8:])
        )

    def _call_gemini(self, llm_config: dict, api_key: str, system_prompt: str, user_prompt: str) -> str:
        model = llm_config.get("model", "gemini-2.5-flash-lite")
        max_output_tokens = int(llm_config.get("max_output_tokens", 250))
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": max_output_tokens,
                    "responseMimeType": "application/json",
                },
            },
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_openrouter(self, llm_config: dict, api_key: str, system_prompt: str, user_prompt: str) -> str:
        model = llm_config.get("model", "google/gemini-2.0-flash-exp:free")
        max_output_tokens = int(llm_config.get("max_output_tokens", 250))
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "max_tokens": max_output_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        payload = (text or "").strip()
        if payload.startswith("```"):
            payload = re.sub(r"^```(?:json)?|```$", "", payload, flags=re.IGNORECASE | re.MULTILINE).strip()
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ValueError("LLM result was not an object")
        return parsed

    def _normalize_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(DEFAULT_ANALYSIS)
        result.update({key: payload.get(key, result[key]) for key in result})
        result["related_to_me"] = bool(result.get("related_to_me"))
        result["needs_reply"] = bool(result.get("needs_reply"))
        priority = str(result.get("priority", "low")).strip().lower()
        if priority not in {"low", "medium", "high"}:
            priority = "low"
        result["priority"] = priority
        for key in ("summary", "reason", "suggested_reply"):
            result[key] = str(result.get(key, "") or "").strip()
        return result
