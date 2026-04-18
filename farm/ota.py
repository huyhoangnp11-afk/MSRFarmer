import time
import json
import ssl
import urllib.request
import logging

# --- CẤU HÌNH LIVE OTA (Trung tâm điều khiển Data Sống) ---
# Điền Link Pastebin Raw hoặc Github Gist Raw chứa cấu hình JSON vào đây.
LIVE_CONFIG_URL = "https://gist.githubusercontent.com/huyhoangnp11-afk/a62b45c33dc415d988e0eb78143313e1/raw/gistfile1.txt"

_cached_ota_data = None
_last_ota_fetch_time = 0

def get_live_ota_config():
    global _cached_ota_data, _last_ota_fetch_time
    
    default_config = {
        "selectors": [
            "a[href*='search?q=']",
            "a[href*='rewards.bing.com/redirect']",
            "a[href*='PUBL=Rewards']",
            "a[href*='OCID=']"
        ],
        "keywords": [
            "quote", "quiz", "puzzle", "answer", "poll", "trivia", "knowledge", 
            "star", "streak", "+5", "+10", "+30", "+40", "+50"
        ],
        "affiliate_links": []
    }
    
    if not LIVE_CONFIG_URL:
        return default_config
        
    current_time = time.time()
    # Tải lại sau tối thiểu 1 tiếng (3600 giây) để tránh bị rate limit
    if _cached_ota_data and (current_time - _last_ota_fetch_time < 3600):
        return _cached_ota_data
        
    try:
        req = urllib.request.Request(LIVE_CONFIG_URL, headers={'User-Agent': 'Mozilla/5.0 MSR-Bot'})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                
                # Merge with default config
                final_data = default_config.copy()
                if "selectors" in data: final_data["selectors"] = data["selectors"]
                if "keywords" in data: final_data["keywords"] = data["keywords"]
                if "affiliate_links" in data: final_data["affiliate_links"] = data["affiliate_links"]
                
                logging.info("[OTA] Đã nạp thành công Dữ Liệu Sống từ máy chủ!")
                _cached_ota_data = final_data
                _last_ota_fetch_time = current_time
                return final_data
    except Exception as e:
        logging.warning(f"[OTA] Không thể tải Data (Có thể mất mạng). Dùng bộ nhớ cục bộ. Lỗi: {e}")
        
    return default_config
