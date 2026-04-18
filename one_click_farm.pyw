"""
One-Click Microsoft Rewards Farmer
===================================
Double-click để chạy. Tool sẽ:
1. Chạy ngầm (không hiện cửa sổ)
2. Hiện thông báo Windows khi xong/lỗi
3. Hiện icon trong System Tray để theo dõi
"""

import subprocess
import sys
import os
import threading
import time
from datetime import datetime

# Đường dẫn script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FARM_SCRIPT = os.path.join(SCRIPT_DIR, "farm_rewards.py")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")

# Cấu hình mặc định
PC_SEARCHES = 42
MOBILE_SEARCHES = 40

def send_notification(title, message, timeout=10):
    """Gửi Windows Toast Notification"""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="MS Rewards Farmer",
            timeout=timeout
        )
    except Exception as e:
        print(f"Notification error: {e}")

def get_today_log():
    """Lấy đường dẫn log file hôm nay"""
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(LOG_DIR, f"farm_log_{today}.log")

def run_farm():
    """Chạy farm_rewards.py và theo dõi kết quả"""
    send_notification(
        "🚀 MS Rewards Farmer",
        f"Đang bắt đầu farm...\nPC: {PC_SEARCHES} | Mobile: {MOBILE_SEARCHES}",
        timeout=5
    )
    
    start_time = time.time()
    
    try:
        # Chạy script với pythonw (không hiện console)
        result = subprocess.run(
            [sys.executable, FARM_SCRIPT, 
             "--pc", str(PC_SEARCHES), 
             "--mobile", str(MOBILE_SEARCHES)],
            capture_output=True,
            text=True,
            cwd=SCRIPT_DIR
        )
        
        elapsed = int(time.time() - start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        
        if result.returncode == 0:
            send_notification(
                "✅ Farm Hoàn Thành!",
                f"Đã xong trong {minutes}m {seconds}s\nCheck log để xem chi tiết.",
                timeout=15
            )
        else:
            # Đọc vài dòng cuối log để hiện lỗi
            error_hint = "Xem log để biết chi tiết."
            try:
                log_file = get_today_log()
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            error_hint = lines[-1][:100]
            except:
                pass
            
            send_notification(
                "⚠️ Farm Gặp Lỗi",
                f"Exit code: {result.returncode}\n{error_hint}",
                timeout=20
            )
            
    except Exception as e:
        send_notification(
            "❌ Lỗi Nghiêm Trọng",
            str(e)[:200],
            timeout=30
        )

def create_tray_icon():
    """Tạo System Tray icon (optional)"""
    try:
        import pystray
        from PIL import Image, ImageDraw
        
        # Tạo icon đơn giản (hình tròn xanh)
        def create_image():
            img = Image.new('RGB', (64, 64), color=(0, 120, 212))
            d = ImageDraw.Draw(img)
            d.ellipse([8, 8, 56, 56], fill=(255, 255, 255))
            d.text((20, 20), "MS", fill=(0, 120, 212))
            return img
        
        def on_quit(icon, item):
            icon.stop()
        
        def on_view_log(icon, item):
            log_file = get_today_log()
            if os.path.exists(log_file):
                os.startfile(log_file)
        
        icon = pystray.Icon(
            "MS Rewards",
            create_image(),
            "MS Rewards Farmer - Đang chạy...",
            menu=pystray.Menu(
                pystray.MenuItem("Xem Log", on_view_log),
                pystray.MenuItem("Thoát", on_quit)
            )
        )
        
        # Chạy farm trong thread riêng
        def run_and_quit():
            run_farm()
            time.sleep(3)  # Đợi notification hiện
            icon.stop()
        
        threading.Thread(target=run_and_quit, daemon=True).start()
        icon.run()
        
    except ImportError:
        # Không có pystray, chạy không có tray
        run_farm()

if __name__ == "__main__":
    # Đảm bảo thư mục log tồn tại
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Chạy với tray icon nếu có
    create_tray_icon()
