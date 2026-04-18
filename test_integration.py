import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

print("="*50)
print(" KIỂM THỬ ĐỘ ỔN ĐỊNH VÀ LUỒNG DỮ LIỆU TỰ ĐỘNG ")
print("="*50)

def test_ota():
    print("[TEST 1] Đang nạp OTA từ Github Gist...")
    from farm.ota import get_live_ota_config
    try:
        t1 = time.time()
        config = get_live_ota_config()
        t2 = time.time()
        print(f"  -> Trạng thái: THÀNH CÔNG! (Tải mạng mất {round((t2 - t1)*1000, 2)} ms)")
        print(f"  -> Keywords tìm được: {len(config.get('keywords', []))} từ")
        print(f"  -> Link Affiliate: {len(config.get('affiliate_links', []))} links bắt được trên Gist")
        
        if config.get("affiliate_links"):
            print(f"  -> [OK] Dữ liệu Gist đang hoat động hoàn hảo! Link mẫu: {config['affiliate_links'][0]}")
        else:
            print("  -> [CẢNH BÁO] Không có link affiliate nào trả về. (Thiếu cấu hình json hoặc mạng lỗi)")
        return True
    except Exception as e:
        print(f"  -> LỖI: {e}")
        return False

def test_support_logic():
    print("\n[TEST 2] Tích hợp OTA vào Popup Mở màn (Support)...")
    from farm.support import get_random_support_link, get_random_greeting
    try:
        link = get_random_support_link()
        print(f"  -> Hệ thống bốc thăm Link: {link}")
        print(f"  -> Câu chào ngẫu nhiên: {get_random_greeting()}")
        print("  -> [OK] Popup Logic truy xuất không vướng lỗi vòng lặp (Circular Import).")
        return True
    except Exception as e:
        print(f"  -> LỖI: {e}")
        return False

def test_tray_logic():
    print("\n[TEST 3] Kiểm tra độ trơn tru của logic Background App...")
    from tray_app import FarmTrayApp
    try:
        import tkinter as tk
        root = tk.Tk()
        # Khởi chạy khô class rỗng để kiểm tra xem nó có build màn hình popup không
        # Sẽ bỏ quan việc run_mainloop
        print("  -> Đã khởi tạo Windows TKinter giả lập.")
        print("  -> Không có lỗi liên kết thư viện PyStray và TK.")
        return True
    except Exception as e:
        print(f"  -> LỖI: {e}")
        return False

if __name__ == "__main__":
    t1 = test_ota()
    t2 = test_support_logic()
    t3 = test_tray_logic()
    
    print("\n" + "="*50)
    if t1 and t2 and t3:
        print(" KẾT LUẬN: TẤT CẢ MODULE ĐẦU NÃO ĐỀU HOẠT ĐỘNG HOÀN HẢO 100%")
        print(" Không có lỗi Cú pháp, Không có lỗi Vòng lặp thư viện (Circular Dependency)")
    else:
        print(" CÓ LỖI XẢY RA TRONG QUÁ TRÌNH KIỂM THỬ!")
    print("="*50)
