import re
import codecs

emojis_to_replace = {
    "🎮 ": "", "💎 ": "", "🎁 ": "", "📊 ": "", "👥 ": "", "🔄 ": "",
    "➕ ": "", "❌ ": "", "☑️ ": "", "🤖 ": "", "🐢 ": "", "🚶 ": "",
    "🏃 ": "", "⚡ ": "", "▶️ ": "", "🔁 ": "", "⏹️ ": "", "⚙️": "",
    "💤 ": "", "📅 ": "", "📱 ": "", "💎": "", "👤 ": "", "🌟 ": "",
    "💎": "", "👤": "", "🎁": "", "📊": "", "👥": "", "🔄": "", "➕": "",
    "❌": "", "☑️": "", "🤖": "", "🐢": "", "🚶": "", "🏃": "", "⚡": "",
    "▶️": "", "🔁": "", "⏹️": "", "💤": "", "📅": "", "📱": "", "🌟": "", "⭐": ""
}

target = r"d:\sao lưu E\MSrequat\launcher_gui.py"

with codecs.open(target, 'r', 'utf-8') as f:
    text = f.read()

for emoji, replacement in emojis_to_replace.items():
    text = text.replace(emoji, replacement)

# Fix a couple formatting glitches if any
text = text.replace("Nâng cao ", "Nâng cao")

with codecs.open(target, 'w', 'utf-8') as f:
    f.write(text)

print("DE_EMOJI_SUCCESS")
