"""
farm/history.py - Points history tracking (JSON-based)
"""
import os
import json
from datetime import datetime, timedelta

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "points_history.json")


def load_history():
    """Load points history from JSON file."""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"records": []}


def save_history(data):
    """Save points history to JSON file."""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")


def log_points(profile_name, points_before, points_after, farm_type="full"):
    """Log a farming session result."""
    data = load_history()
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "profile": profile_name,
        "before": points_before,
        "after": points_after,
        "earned": (points_after - points_before) if isinstance(points_before, int) and isinstance(points_after, int) else 0,
        "type": farm_type
    }
    data["records"].append(record)
    
    # Keep only last 90 days
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    data["records"] = [r for r in data["records"] if r.get("date", "") >= cutoff]
    
    save_history(data)
    return record


def get_today_stats():
    """Get today's stats grouped by profile."""
    data = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    stats = {}
    for r in data.get("records", []):
        if r.get("date") == today:
            profile = r.get("profile", "Unknown")
            if profile not in stats:
                stats[profile] = {"earned": 0, "sessions": 0, "last_points": 0}
            stats[profile]["earned"] += r.get("earned", 0)
            stats[profile]["sessions"] += 1
            if isinstance(r.get("after"), int):
                stats[profile]["last_points"] = r["after"]
    
    return stats


def get_weekly_total():
    """Get total points earned in last 7 days."""
    data = load_history()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    total = 0
    for r in data.get("records", []):
        if r.get("date", "") >= week_ago:
            total += r.get("earned", 0)
    return total


def get_daily_totals(days=14):
    """Get daily totals for last N days."""
    data = load_history()
    
    daily = {}
    for i in range(days):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily[d] = 0
    
    for r in data.get("records", []):
        date = r.get("date", "")
        if date in daily:
            daily[date] += r.get("earned", 0)
    
    # Return ordered list
    return [(d, daily[d]) for d in sorted(daily.keys())]


def was_farmed_today(profile_name):
    """Check if a profile has already been farmed today (earned > 0)."""
    data = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    for r in data.get("records", []):
        if r.get("date") == today and r.get("profile") == profile_name:
            if r.get("earned", 0) > 0:
                return True
    return False


def get_profile_summary():
    """Get summary stats for each profile ever farmed."""
    data = load_history()
    summary = {}
    for r in data.get("records", []):
        profile = r.get("profile", "Unknown")
        if profile not in summary:
            summary[profile] = {"total_earned": 0, "sessions": 0, "last_date": "", "last_points": 0}
        summary[profile]["total_earned"] += r.get("earned", 0)
        summary[profile]["sessions"] += 1
        if r.get("date", "") >= summary[profile]["last_date"]:
            summary[profile]["last_date"] = r.get("date", "")
            if isinstance(r.get("after"), int):
                summary[profile]["last_points"] = r["after"]
    return summary


def get_streak_days():
    """Get number of consecutive days with farming activity."""
    data = load_history()
    dates_with_earnings = set()
    for r in data.get("records", []):
        if r.get("earned", 0) > 0:
            dates_with_earnings.add(r.get("date", ""))
    
    if not dates_with_earnings:
        return 0
    
    streak = 0
    check_date = datetime.now()
    for _ in range(365):
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in dates_with_earnings:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak

