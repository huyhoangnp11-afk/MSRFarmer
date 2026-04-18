"""
farm/points.py - Points tracking and detection
Supports BOTH old UI (#id_rc) and new UI (#id_rh_w, View profile button).
"""
import re
import json
import logging
from selenium.webdriver.common.by import By

from .utils import random_sleep


def get_search_quota(driver):
    """Read exact search quotas from rewards API.
    
    Returns dict with:
        pc_progress, pc_max, pc_remaining_searches,
        mobile_progress, mobile_max, mobile_remaining_searches,
        points_per_search, inferred (bool)
    Or None if API call completely fails.
    """
    import time
    try:
        current_url = driver.current_url
        driver.get("https://rewards.bing.com/api/getuserinfo?type=1")
        time.sleep(3)
        
        # Get JSON from page
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if not page_text:
            try:
                page_text = driver.find_element(By.TAG_NAME, "pre").text
            except:
                pass
        
        if not page_text:
            logging.warning("[QUOTA] API returned empty response")
            return None
        
        data = json.loads(page_text)
        dashboard = data.get('dashboard', {})
        user_status = dashboard.get('userStatus', {})
        
        # Merge counters from BOTH paths (some accounts use different paths)
        counters = {}
        c1 = dashboard.get('counters', {})
        c2 = user_status.get('counters', {})
        if c1:
            counters.update(c1)
        if c2:
            for k, v in c2.items():
                if k not in counters:
                    counters[k] = v
        
        logging.info(f"[QUOTA] Counter keys found: {list(counters.keys())}")
        
        # Helper to extract counter entry
        def get_counter(name):
            c = counters.get(name, [])
            if not c:
                return None, None
            entry = c[0] if isinstance(c, list) else c
            return entry.get('pointProgress', 0), entry.get('pointProgressMax', 0)
        
        # User level & points
        available_points = user_status.get('availablePoints', 0)
        level = user_status.get('levelName', user_status.get('activeLevel', 'Unknown'))
        
        # Read all counters
        pc_progress, pc_max = get_counter('pcSearch')
        mobile_progress, mobile_max = get_counter('mobileSearch')
        quiz_progress, quiz_max = get_counter('activityAndQuiz')
        daily_progress, daily_max = get_counter('dailyPoint')
        edge_progress, edge_max = get_counter('edgeSearch')
        
        inferred = False
        
        # === SMART INFERENCE when pcSearch is missing ===
        if pc_max is None:
            logging.info("[QUOTA] API không trả về pcSearch counter. Tự động dự đoán từ level (Inferred)...")
            inferred = True
            
            # Determine level from dailyPoint max or available points
            # Level 1 (Member): dailyPoint max ~200, PC max=30
            # Level 2 (Silver+): dailyPoint max ~150, PC max=150, Mobile max=100
            is_level2 = False
            if daily_max is not None and daily_max <= 150 and daily_max > 0:
                is_level2 = True
            elif available_points >= 1000:
                is_level2 = True
            elif str(level).lower() in ('level 2', 'silver', 'gold', 'platinum'):
                is_level2 = True
            
            if is_level2:
                pc_progress, pc_max = 0, 150        # 30 searches × 5 pts
                mobile_progress, mobile_max = 0, 100  # 20 searches × 5 pts
                logging.info(f"[QUOTA] → Inferred Level 2+: PC=0/150, Mobile=0/100")
            else:
                pc_progress, pc_max = 0, 30   # 10 searches × 3 pts
                mobile_progress, mobile_max = 0, 0
                logging.info(f"[QUOTA] → Inferred Level 1: PC=0/30, Mobile=N/A")
        
        if mobile_max is None:
            mobile_progress, mobile_max = 0, 0
        
        # Calculate points per search
        pps = 5 if pc_max >= 150 else 3
        
        # Calculate remaining searches
        pc_remaining = max(0, pc_max - (pc_progress or 0))
        pc_remaining_searches = (pc_remaining + pps - 1) // pps if pps > 0 else 0
        
        mobile_remaining = max(0, mobile_max - (mobile_progress or 0))
        mobile_remaining_searches = (mobile_remaining + pps - 1) // pps if pps > 0 else 0
        
        edge_remaining = max(0, (edge_max or 0) - (edge_progress or 0))
        edge_remaining_searches = (edge_remaining + pps - 1) // pps if pps > 0 and edge_remaining > 0 else 0
        
        result = {
            'pc_progress': pc_progress or 0,
            'pc_max': pc_max,
            'pc_remaining_searches': pc_remaining_searches,
            'mobile_progress': mobile_progress or 0,
            'mobile_max': mobile_max,
            'mobile_remaining_searches': mobile_remaining_searches,
            'points_per_search': pps,
            'inferred': inferred,
            'level': level,
            'available_points': available_points,
            'quiz_progress': quiz_progress or 0,
            'quiz_max': quiz_max or 0,
            'daily_progress': daily_progress or 0,
            'daily_max': daily_max or 0,
            'edge_progress': edge_progress or 0,
            'edge_max': edge_max or 0,
            'edge_remaining_searches': edge_remaining_searches,
        }
        
        # Log breakdown
        src = " (INFERRED)" if inferred else ""
        logging.info(f"[QUOTA] Level: {level} | Points: {available_points}{src}")
        logging.info(f"[QUOTA] PC Search: {result['pc_progress']}/{pc_max} → {pc_remaining_searches} searches left")
        if mobile_max > 0:
            logging.info(f"[QUOTA] Mobile: {result['mobile_progress']}/{mobile_max} → {mobile_remaining_searches} searches left")
        else:
            logging.info("[QUOTA] Mobile: N/A")
        if quiz_max and quiz_max > 0:
            logging.info(f"[QUOTA] Activity/Quiz: {quiz_progress}/{quiz_max}")
        if daily_max and daily_max > 0:
            logging.info(f"[QUOTA] Daily Point: {daily_progress}/{daily_max}")
        
        # Navigate back
        try:
            if "rewards.bing.com" in (current_url or ""):
                driver.get(current_url)
            else:
                driver.get("https://rewards.bing.com/")
            time.sleep(3)
        except:
            pass
        
        return result
        
    except Exception as e:
        logging.info(f"[QUOTA] Không đọc được Quota qua API. (Message: {e})")
        try:
            driver.get("https://rewards.bing.com/")
            time.sleep(3)
        except:
            pass
        return None
def check_logged_in(driver):
    """Check if user is signed in on the current page."""
    try:
        # Check for sign-in indicators
        sign_in_selectors = [
            "a[href*='login.live.com']",
            "a#id_s",  # Sign-in link on Bing
            "a[href*='signup']",
            "#id_n",   # Sign-in name (means logged in)
        ]
        
        # If we find sign-in name → logged in
        try:
            name_el = driver.find_element(By.CSS_SELECTOR, "#id_n")
            if name_el:
                return True
        except:
            pass
        
        # Check page for login redirect
        current_url = driver.current_url
        if "login.live.com" in current_url or "signup" in current_url:
            return False
        
        # Check for "Sign in" text/buttons
        try:
            sign_in_btns = driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Sign in') or contains(text(), 'Đăng nhập')]")
            # Filter to only visible, prominent sign-in buttons
            for btn in sign_in_btns:
                if btn.is_displayed() and btn.tag_name in ('a', 'button', 'span'):
                    text = btn.text.strip()
                    if text in ('Sign in', 'Đăng nhập', 'Sign In'):
                        return False
        except:
            pass
        
        # If no sign-in indicators found, assume logged in
        return True
    except:
        return True  # Assume logged in on error


def get_points_from_search_page(driver):
    """Get points from the Bing search page (inline check)."""
    # Try NEW UI first: #id_rh_w contains points in a span
    try:
        elm = driver.find_element(By.CSS_SELECTOR, "#id_rh_w span")
        txt = elm.text.replace(",", "").replace(".", "")
        if txt.isdigit():
            return int(txt)
    except:
        pass
    
    # Try OLD UI: #id_rc
    try:
        elm = driver.find_element(By.ID, "id_rc")
        txt = elm.text.replace(",", "").replace(".", "")
        if txt.isdigit():
            return int(txt)
    except:
        pass
    
    # Try aria-label approach for new UI
    try:
        elm = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Microsoft Rewards'] span")
        txt = elm.text.replace(",", "").replace(".", "")
        if txt.isdigit():
            return int(txt)
    except:
        pass
    
    return None


def get_current_points(driver):
    """Get points from the rewards dashboard page."""
    try:
        if "rewards.bing.com" not in driver.current_url:
            driver.get("https://rewards.bing.com/")
            random_sleep(3, 5)
        
        selectors = [
            # === NEW UI selectors (accordion-based dashboard) ===
            (By.CSS_SELECTOR, "button[aria-label='View profile'] p"),
            (By.CSS_SELECTOR, "button[aria-label='View profile'] span"),
            (By.XPATH, "//button[contains(@aria-label, 'profile')]//p"),
            (By.CSS_SELECTOR, "#id_rh_w span"),
            (By.CSS_SELECTOR, "a[aria-label='Microsoft Rewards'] span"),
            # === OLD UI selectors ===
            (By.CSS_SELECTOR, "mee-rewards-counter-animation span"),
            (By.CSS_SELECTOR, "p.pointsValue span"),
            (By.ID, "rewards-dashboard-count"),
            (By.ID, "id_rc"),
            (By.CLASS_NAME, "points-balance"),
            (By.CSS_SELECTOR, "#balanceTooltipDiv p"),
            (By.XPATH, "//div[contains(@class, 'points-balance')]"),
            (By.XPATH, "//span[contains(@class, 'number')]"),
        ]
        
        for by, val in selectors:
            try:
                el = driver.find_element(by, val)
                txt = el.text
                digits = re.findall(r'\d+', txt)
                if digits:
                    points_str = "".join(digits)
                    points = int(points_str)
                    if points > 0:
                        logging.info(f"[POINTS] Tìm thấy điểm: {points} (selector: {val})")
                        return points
            except: pass
            
        return "Unknown"
    except:
        return "Error"
