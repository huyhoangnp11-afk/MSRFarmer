from __future__ import annotations

import re
import time
import unicodedata
from collections import defaultdict

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


SNAPSHOT_SCRIPT = r"""
const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();
const isVisible = (element) => {
  if (!element) return false;
  const style = window.getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) {
    return false;
  }
  const rect = element.getBoundingClientRect();
  return rect.width > 8 && rect.height > 8;
};

const collectTextEntries = (root, maxRight = window.innerWidth) => {
  const entries = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const text = normalize(node.nodeValue);
    if (!text || text.length > 500) continue;

    const parent = node.parentElement;
    if (!parent || !isVisible(parent)) continue;
    if (parent.closest("script,style,noscript,svg,path")) continue;

    const rect = parent.getBoundingClientRect();
    if (rect.right < 0 || rect.left > maxRight) continue;
    entries.push({
      text,
      top: rect.top,
      left: rect.left,
      right: rect.right,
    });
  }
  return entries.sort((a, b) => {
    if (Math.abs(a.top - b.top) > 6) return a.top - b.top;
    return a.left - b.left;
  });
};

const uniqueTexts = (entries) => {
  const seen = new Set();
  const values = [];
  for (const entry of entries) {
    const key = `${entry.text}|${Math.round(entry.top / 4)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    values.push(entry.text);
  }
  return values;
};

const composerCandidates = Array.from(document.querySelectorAll("[contenteditable='true'], textarea"))
  .filter((element) => {
    if (!isVisible(element)) return false;
    const rect = element.getBoundingClientRect();
    return rect.bottom > (window.innerHeight - 190);
  })
  .map((element) => {
    const rect = element.getBoundingClientRect();
    return { left: rect.left, right: rect.right, bottom: rect.bottom };
  })
  .sort((a, b) => a.left - b.left);

const mainLeft = composerCandidates.length
  ? Math.max(composerCandidates[0].left - 24, window.innerWidth * 0.16)
  : window.innerWidth * 0.24;
const headerLimit = 92;
const footerLimit = window.innerHeight - 130;
const messageBuckets = new Map();
const headerBuckets = new Map();

const bodyEntries = collectTextEntries(document.body, window.innerWidth);
for (const entry of bodyEntries) {
  const rectTop = entry.top;
  const rectLeft = entry.left;
  const rectRight = entry.right;

  if (rectRight < mainLeft || rectLeft > window.innerWidth) continue;
  const bucketKey = `${Math.round(rectTop / 6) * 6}|${Math.round(rectLeft / 6) * 6}|${Math.round(rectRight / 6) * 6}`;

  if (rectTop >= headerLimit && rectTop <= footerLimit && rectRight > mainLeft && rectLeft <= window.innerWidth) {
    if (!messageBuckets.has(bucketKey)) {
      messageBuckets.set(bucketKey, {
        top: rectTop,
        left: rectLeft,
        center_x: (rectLeft + rectRight) / 2,
        text_parts: [],
      });
    }
    messageBuckets.get(bucketKey).text_parts.push(entry.text);
  }

  if (rectTop < headerLimit && rectRight > mainLeft && rectLeft < (mainLeft + 420)) {
    if (!headerBuckets.has(bucketKey)) {
      headerBuckets.set(bucketKey, {
        top: rectTop,
        left: rectLeft,
        text_parts: [],
      });
    }
    headerBuckets.get(bucketKey).text_parts.push(entry.text);
  }
}

const messages = Array.from(messageBuckets.values())
  .map((item) => ({
    top: item.top,
    left: item.left,
    center_x: item.center_x,
    text: Array.from(new Set(item.text_parts)).join(" ").trim(),
  }))
  .filter((item) => item.text.length > 0)
  .sort((a, b) => {
    if (Math.abs(a.top - b.top) > 8) return a.top - b.top;
    return a.left - b.left;
  });

const paneMidpoint = (mainLeft + window.innerWidth) / 2;
const headerTexts = Array.from(headerBuckets.values())
  .map((item) => ({
    top: item.top,
    left: item.left,
    text: Array.from(new Set(item.text_parts)).join(" ").trim(),
  }))
  .filter((item) => item.text.length > 0)
  .sort((a, b) => {
    if (Math.abs(a.top - b.top) > 8) return a.top - b.top;
    return a.left - b.left;
  })
  .map((item) => item.text);

const composerReady = composerCandidates.some((item) => item.right > mainLeft);

const sidebarProbeX = Math.max(36, Math.min(mainLeft / 2, 220));
const seenSidebarKeys = new Set();
const sidebarRoots = [];

const pickSidebarRoot = (seed) => {
  let current = seed;
  while (current && current !== document.body) {
    const rect = current.getBoundingClientRect();
    const fits = (
      rect.left <= sidebarProbeX + 48 &&
      rect.right >= sidebarProbeX &&
      rect.width >= 140 &&
      rect.height >= 42 &&
      rect.height <= 140 &&
      rect.top >= (headerLimit - 18) &&
      rect.bottom <= (window.innerHeight - 18)
    );
    if (fits) return current;
    current = current.parentElement;
  }
  return null;
};

for (let y = headerLimit + 18; y < window.innerHeight - 80; y += 18) {
  const seed = document.elementFromPoint(sidebarProbeX, y);
  const root = pickSidebarRoot(seed);
  if (!root) continue;
  const rect = root.getBoundingClientRect();
  const key = `${Math.round(rect.top / 4) * 4}|${Math.round(rect.height / 4) * 4}`;
  if (seenSidebarKeys.has(key)) continue;
  seenSidebarKeys.add(key);
  sidebarRoots.push(root);
}

const headerTextSet = new Set(headerTexts.map((item) => normalize(item)));
const sidebarChats = sidebarRoots
  .map((root) => {
    const rect = root.getBoundingClientRect();
    const entries = collectTextEntries(root, mainLeft + 80);
    const texts = uniqueTexts(entries);
    let title = "";
    let preview = "";
    let unreadCount = 0;

    for (const entry of entries) {
      if (/^\d{1,2}$/.test(entry.text) && entry.left > (rect.left + rect.width * 0.55)) {
        unreadCount = Math.max(unreadCount, Number(entry.text));
      }
    }

    for (const value of texts) {
      if (/^\d{1,2}$/.test(value) || /^\d{1,2}:\d{2}$/.test(value)) continue;
      title = value;
      break;
    }

    for (const value of texts) {
      if (!value || value === title) continue;
      if (/^\d{1,2}$/.test(value) || /^\d{1,2}:\d{2}$/.test(value)) continue;
      preview = value;
      break;
    }

    return {
      title,
      preview,
      unread_count: unreadCount,
      top: rect.top,
      center_x: Math.min(rect.left + Math.min(rect.width * 0.22, 64), Math.max(48, mainLeft - 32)),
      center_y: rect.top + (rect.height / 2),
      is_active: !!title && headerTextSet.has(normalize(title)),
      raw_texts: texts.slice(0, 6),
    };
  })
  .filter((item) => item.title || item.preview)
  .sort((a, b) => a.top - b.top);

return {
  title: document.title || "",
  main_left: mainLeft,
  pane_midpoint: paneMidpoint,
  header_texts: Array.from(new Set(headerTexts)).slice(0, 12),
  messages: messages.slice(-50).map((item) => ({
    text: item.text,
    top: item.top,
    left: item.left,
    side: item.center_x < paneMidpoint ? "incoming" : "outgoing",
  })),
  composer_ready: composerReady,
  sidebar_chats: sidebarChats,
};
"""


CLICK_SIDEBAR_CHAT_SCRIPT = r"""
const x = Math.max(10, Math.min(arguments[0], window.innerWidth - 10));
const y = Math.max(10, Math.min(arguments[1], window.innerHeight - 10));
const dispatchMouse = (target, type) => {
  target.dispatchEvent(new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
  }));
};
const seed = document.elementFromPoint(x, y);
if (!seed) return false;
let target = seed;
while (target && target !== document.body) {
  const rect = target.getBoundingClientRect();
  if (rect.width >= 120 && rect.height >= 36 && rect.height <= 140) break;
  target = target.parentElement;
}
target = target || seed;
dispatchMouse(target, "mousemove");
dispatchMouse(target, "mousedown");
dispatchMouse(target, "mouseup");
dispatchMouse(target, "click");
return true;
"""


GENERIC_HEADER_TEXTS = {
    "search",
    "tim kiem",
    "thong tin hoi thoai",
    "conversation info",
    "members",
    "member",
    "media",
    "file",
    "more",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", without_marks).strip().lower()


def is_system_text(text: str) -> bool:
    normalized = strip_accents(text)
    if not normalized:
        return True
    if normalized in {"hom nay", "today", "yesterday", "ban", "dang nhap"}:
        return True
    if re.fullmatch(r"\d{1,2}:\d{2}", normalized):
        return True
    if re.fullmatch(r"thu \d", normalized):
        return True
    if normalized.startswith("da xem") or normalized.startswith("seen"):
        return True
    if normalized.startswith("typing") or normalized.startswith("dang nhap"):
        return True
    return False


def pick_chat_title(snapshot: dict) -> str:
    for candidate in snapshot.get("header_texts", []):
        normalized = strip_accents(candidate)
        if not normalized or normalized in GENERIC_HEADER_TEXTS:
            continue
        if 1 <= len(candidate.strip()) <= 80:
            return candidate.strip()
    title = snapshot.get("title", "").strip()
    return title or "Current chat"


def normalize_messages(snapshot: dict) -> list[dict]:
    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    normalized = []
    for item in snapshot.get("messages", []):
        text = re.sub(r"\s+", " ", str(item.get("text", ""))).strip()
        side = item.get("side", "incoming")
        if not text or is_system_text(text):
            continue
        counts[(side, text)] += 1
        normalized.append(
            {
                "side": side,
                "text": text,
                "ordinal": counts[(side, text)],
            }
        )
    return normalized


def normalize_sidebar_chats(snapshot: dict) -> list[dict]:
    normalized: list[dict] = []
    seen_keys: set[str] = set()
    for item in snapshot.get("sidebar_chats", []):
        title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
        preview = re.sub(r"\s+", " ", str(item.get("preview", ""))).strip()
        unread_count = item.get("unread_count", 0)
        try:
            unread_count = max(int(unread_count), 0)
        except (TypeError, ValueError):
            unread_count = 0
        if not title and not preview:
            continue
        key = f"{strip_accents(title)}|{strip_accents(preview)}|{round(float(item.get('top', 0)) / 8)}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        normalized.append(
            {
                "title": title or preview or "Unknown chat",
                "preview": preview,
                "unread_count": unread_count,
                "top": float(item.get("top", 0)),
                "center_x": float(item.get("center_x", 0)),
                "center_y": float(item.get("center_y", 0)),
                "is_active": bool(item.get("is_active", False)),
                "raw_texts": item.get("raw_texts", []),
            }
        )
    return normalized


def take_snapshot(driver) -> dict:
    snapshot = driver.execute_script(SNAPSHOT_SCRIPT)
    snapshot["chat_title"] = pick_chat_title(snapshot)
    snapshot["normalized_messages"] = normalize_messages(snapshot)
    snapshot["normalized_sidebar_chats"] = normalize_sidebar_chats(snapshot)
    return snapshot


def send_chat_message(driver, text: str) -> bool:
    candidates = []
    for element in driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true'], textarea"):
        try:
            if not element.is_displayed():
                continue
            rect = driver.execute_script(
                "const r = arguments[0].getBoundingClientRect(); return {top:r.top,bottom:r.bottom,right:r.right};",
                element,
            )
            if rect["bottom"] < 0 or rect["bottom"] < 450:
                continue
            candidates.append((rect["bottom"], element))
        except Exception:
            continue

    if not candidates:
        return False

    composer = max(candidates, key=lambda item: item[0])[1]
    composer.click()
    composer.send_keys(text)
    composer.send_keys(Keys.ENTER)
    return True


def click_sidebar_chat(driver, sidebar_chat: dict, settle_sec: float = 0.8) -> bool:
    center_x = float(sidebar_chat.get("center_x", 0))
    center_y = float(sidebar_chat.get("center_y", 0))
    if center_x <= 0 or center_y <= 0:
        return False
    clicked = bool(driver.execute_script(CLICK_SIDEBAR_CHAT_SCRIPT, center_x, center_y))
    if clicked and settle_sec > 0:
        time.sleep(settle_sec)
    return clicked
