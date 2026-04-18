import json
import os
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "points_history.json")
today = datetime.now().strftime("%Y-%m-%d")

with open(HISTORY_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

before = len(data["records"])
removed = [r for r in data["records"] if r.get("date") == today]
data["records"] = [r for r in data["records"] if r.get("date") != today]
after = len(data["records"])

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Reset ngay {today}: xoa {before - after} records")
for r in removed:
    print(f"  - {r['profile']}: +{r['earned']} pts luc {r['time']}")
print("Xong! Tat ca profiles co the farm lai hom nay.")
