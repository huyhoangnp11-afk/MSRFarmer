"""
farm/utils.py - Utility functions: logging, screenshots, human simulation
"""
import os
import time
import random
import string
import logging
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .config import LOG_DIR, SCREENSHOT_DIR, MOBILE_DEVICES


_logging_configured = False

def setup_logging():
    global _logging_configured
    
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    
    if _logging_configured:
        return
    _logging_configured = True
    
    log_file = os.path.join(LOG_DIR, f"farm_log_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Clear any existing handlers to prevent duplication
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    
    # Add exactly 1 file handler + 1 stream handler
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'))
    root.addHandler(fh)
    
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'))
    root.addHandler(sh)
    
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    logging.getLogger("selenium").setLevel(logging.CRITICAL)
    logging.getLogger("requests").setLevel(logging.CRITICAL)
    logging.getLogger("webdriver_manager").setLevel(logging.CRITICAL)
    
    logging.info("=== BẮT ĐẦU PHIÊN CHẠY MỚI ===")


def take_screenshot(driver, error_name="error"):
    if not driver: return
    try:
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{error_name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        driver.save_screenshot(filepath)
        logging.info(f"Đã chụp màn hình lỗi: {filepath}")
    except Exception as e:
        if "refused" in str(e) or "Max retries exceeded" in str(e):
            logging.warning("⚠️ Không thể chụp màn hình: Driver đã mất kết nối.")
        else:
            logging.error(f"Không thể chụp màn hình: {e}")


def random_sleep(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))


def check_and_recover_oom(driver, context=""):
    """Detect browser error pages (OOM, DNS, connection, timeout, etc.) and auto-refresh.
    
    Returns True if error was detected and recovery attempted, False if page is fine.
    """
    try:
        title = (driver.title or "").lower()
        current_url = (driver.current_url or "").lower()
        
        # Quick check: if title looks normal, skip expensive body check
        error_title_keywords = [
            "problem", "can't reach", "error", "aw, snap", "aw snap",
            "this page", "không thể", "trang này", "hmm",
        ]
        is_error_title = any(kw in title for kw in error_title_keywords)
        
        # Also check for about:blank or edge error URLs
        is_error_url = any(x in current_url for x in [
            "about:blank", "edge://", "chrome-error://", "neterror",
        ])
        
        if not is_error_title and not is_error_url:
            return False
        
        # Confirm: check body text for specific error indicators
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        except:
            body_text = ""
        
        error_body_keywords = [
            # OOM errors
            "out of memory", "not enough memory", "ran out of memory",
            "err_out_of_memory",
            # Connection errors
            "err_connection_refused", "err_connection_timed_out",
            "err_connection_reset", "err_network_changed",
            "err_internet_disconnected", "err_name_not_resolved",
            # DNS errors
            "dns_probe", "dns probe", "server dns address",
            # SSL errors
            "err_ssl", "err_cert", "net::err_cert",
            # Timeout & loading errors
            "err_timed_out", "err_empty_response",
            "err_too_many_redirects",
            # Generic Edge/Chrome error pages
            "having a problem", "try coming back",
            "this page isn't working", "took too long to respond",
            "can't be reached", "refused to connect",
            "there is no internet connection",
            "check your internet", "reload", "err_failed",
            # Vietnamese error messages
            "trang này đang gặp sự cố", "không thể truy cập",
        ]
        is_error_body = any(kw in body_text for kw in error_body_keywords)
        
        if not is_error_body and not is_error_url:
            return False
        
        # Error detected! Auto-refresh with retries
        ctx = f" ({context})" if context else ""
        logging.warning(f"⚠️ [ERROR PAGE] Error detected{ctx}: title='{title[:50]}'")
        
        for attempt in range(3):
            try:
                time.sleep(2 + attempt * 3)  # 2s, 5s, 8s increasing delay
                driver.refresh()
                time.sleep(5)
                
                # Check if recovered
                new_title = (driver.title or "").lower()
                if not any(kw in new_title for kw in error_title_keywords):
                    logging.info(f"✅ [ERROR PAGE] Recovered after refresh #{attempt + 1}")
                    return True
                    
                logging.warning(f"[ERROR PAGE] Still error after refresh #{attempt + 1}")
            except Exception as refresh_err:
                logging.warning(f"[ERROR PAGE] Refresh error: {refresh_err}")
        
        # If still error after 3 retries, try navigating to bing.com
        try:
            logging.warning("[ERROR PAGE] Trying fresh navigation to bing.com...")
            driver.get("https://www.bing.com/")
            time.sleep(5)
            logging.info("✅ [ERROR PAGE] Navigated to bing.com successfully")
            return True
        except:
            logging.error("[ERROR PAGE] Failed to recover!")
            return True  # Still return True so caller knows error happened
            
    except Exception:
        return False


def simulate_typing(element, text):
    for i, char in enumerate(text):
        if random.random() < 0.05 and i < len(text) - 1:
            wrong_char = random.choice(string.ascii_lowercase)
            element.send_keys(wrong_char)
            time.sleep(random.uniform(0.1, 0.3))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.2))
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.25))


def simulate_reading_interaction(driver):
    try:
        paragraphs = driver.find_elements(By.TAG_NAME, "p")
        if paragraphs:
            target_p = random.choice(paragraphs)
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_p)
            time.sleep(1)
            driver.execute_script("""
                var element = arguments[0];
                var range = document.createRange();
                range.selectNodeContents(element);
                var selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
            """, target_p)
            time.sleep(random.uniform(1, 3))
            driver.execute_script("window.getSelection().removeAllRanges();")
    except:
        pass


# ============== BEZIER MOUSE CURVES ==============
def bezier_curve_points(start, end, num_points=25, jitter=3):
    """Tạo Bezier curve với jitter noise"""
    ctrl1 = (
        start[0] + (end[0] - start[0]) * random.uniform(0.2, 0.4) + random.randint(-50, 50),
        start[1] + (end[1] - start[1]) * random.uniform(0.1, 0.3) + random.randint(-30, 30)
    )
    ctrl2 = (
        start[0] + (end[0] - start[0]) * random.uniform(0.6, 0.8) + random.randint(-50, 50),
        start[1] + (end[1] - start[1]) * random.uniform(0.7, 0.9) + random.randint(-30, 30)
    )
    
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        t_eased = t * t * (3 - 2 * t)
        
        x = (1-t_eased)**3 * start[0] + 3*(1-t_eased)**2*t_eased * ctrl1[0] + 3*(1-t_eased)*t_eased**2 * ctrl2[0] + t_eased**3 * end[0]
        y = (1-t_eased)**3 * start[1] + 3*(1-t_eased)**2*t_eased * ctrl1[1] + 3*(1-t_eased)*t_eased**2 * ctrl2[1] + t_eased**3 * end[1]
        
        if 0 < i < num_points:
            x += random.randint(-jitter, jitter)
            y += random.randint(-jitter, jitter)
        
        points.append((int(x), int(y)))
    
    if random.random() < 0.3:
        overshoot_x = end[0] + random.randint(5, 15) * (1 if random.random() > 0.5 else -1)
        overshoot_y = end[1] + random.randint(3, 10) * (1 if random.random() > 0.5 else -1)
        points.append((int(overshoot_x), int(overshoot_y)))
        points.append((int(end[0]), int(end[1])))
    
    return points


def human_bezier_move(driver, element):
    try:
        viewport_width = driver.execute_script("return window.innerWidth;")
        viewport_height = driver.execute_script("return window.innerHeight;")
        start_x = random.randint(0, viewport_width)
        start_y = random.randint(0, viewport_height)
        elem_location = element.location
        elem_size = element.size
        end_x = elem_location['x'] + elem_size['width'] // 2 + random.randint(-5, 5)
        end_y = elem_location['y'] + elem_size['height'] // 2 + random.randint(-5, 5)
        
        curve_points = bezier_curve_points((start_x, start_y), (end_x, end_y))
        actions = ActionChains(driver)
        last_x, last_y = start_x, start_y
        
        for point in curve_points:
            dx = point[0] - last_x
            dy = point[1] - last_y
            actions.move_by_offset(dx, dy)
            last_x, last_y = point
            actions.pause(random.uniform(0.01, 0.03))
        
        actions.perform()
        return True
    except Exception as e:
        logging.debug(f"Bezier move failed: {e}")
        return False


def human_hover_and_click(driver, element):
    try:
        if random.random() < 0.7:
            if human_bezier_move(driver, element):
                time.sleep(random.uniform(0.2, 0.5))
                element.click()
                return
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        time.sleep(random.uniform(0.3, 0.8))
        element.click()
    except:
        try: element.click()
        except: driver.execute_script("arguments[0].click();", element)


def apply_mobile_emulation(driver, device_name=None):
    try:
        if device_name is None:
            device_name = random.choice(list(MOBILE_DEVICES.keys()))
        device = MOBILE_DEVICES.get(device_name, MOBILE_DEVICES['pixel_7'])
        
        # Get actual Edge version for UA
        try:
            from .driver import get_edge_version
            edge_ver = get_edge_version()
        except:
            edge_ver = "133.0.0.0"
        
        ua = device['ua'].replace('{VERSION}', edge_ver)
        
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
            'width': device['width'], 'height': device['height'],
            'deviceScaleFactor': device['deviceScaleFactor'], 'mobile': device['mobile'],
            'screenWidth': device['screenWidth'], 'screenHeight': device['screenHeight']
        })
        driver.execute_cdp_cmd('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
        driver.execute_cdp_cmd('Emulation.setUserAgentOverride', {
            'userAgent': ua,
            'platform': 'Android' if 'Android' in ua else 'iPhone'
        })
        
        driver.set_window_size(device['width'], device['height'])
        
        logging.info(f"   [MOBILE CDP] Emulating: {device_name} ({device['width']}x{device['height']}) Edge/{edge_ver}")
        return True
    except Exception as e:
        logging.warning(f"Mobile emulation failed: {e}")
        return False


def human_scroll(driver):
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        current_position = 0
        while current_position < (total_height * 0.6):
            scroll_step = random.randint(300, 700)
            current_position += scroll_step
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(random.uniform(0.5, 1.2))
        scroll_up = random.randint(200, 500)
        driver.execute_script(f"window.scrollBy(0, -{scroll_up});")
        time.sleep(random.uniform(0.8, 1.5))
    except:
        pass


def prevent_os_sleep():
    """Prevent Windows from entering sleep mode."""
    try:
        import ctypes
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        logging.info("🛡️ Đã bật chống Sleep Windows (OS Awaken)")
    except: pass


def allow_os_sleep():
    """Allow Windows to enter sleep mode again."""
    try:
        import ctypes
        # ES_CONTINUOUS
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        logging.info("💤 Đã tắt chống Sleep Windows")
    except: pass
