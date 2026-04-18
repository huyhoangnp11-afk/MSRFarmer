import json
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
import winreg
from tkinter import scrolledtext

import ctypes
import pystray
from PIL import Image

from farm.driver import cleanup_automation_processes
from farm.history import was_farmed_today
from farm.profiles import discover_profiles
from farm.support import get_random_greeting, open_support


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "farm_icon.png")
SCRIPT_PATH = os.path.join(BASE_DIR, "farm_rewards.py")
LOG_DIR = os.path.join(BASE_DIR, "logs")
TRAY_CONFIG_PATH = os.path.join(BASE_DIR, "tray_config.json")


class FarmTrayApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.root.title("Microsoft Rewards Farmer")

        self.process = None
        self.log_window_open = False
        self.current_log_file = None
        self.last_pos = 0
        self.available_profiles = []
        self.selected_profile_ids = None

        self._load_selection_config()
        self._sync_profiles()

        try:
            self.root.iconphoto(False, tk.PhotoImage(file=ICON_PATH))
        except Exception:
            pass

        try:
            self.icon_image = Image.open(ICON_PATH)
        except Exception:
            self.icon_image = Image.new("RGB", (64, 64), color=(0, 120, 215))

        self.menu = pystray.Menu()
        self.icon = pystray.Icon("MSRewardsFarmer", self.icon_image, "Microsoft Rewards Farmer", self.menu)
        self.rebuild_menu()

        self.tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        self.tray_thread.start()

        self.update_log_gui()
        self.monitor_process_gui()
        self.refresh_state_gui()
        self.root.after(1500, self.auto_start_if_needed)
        self.root.after(2000, self.show_startup_popup)
        self.root.after(900000, self.daemon_worker)  # 15 minutes polling for daemon mode
        
        # Mặc định bật Startup nếu chưa có
        if not self.is_startup_enabled():
            self.toggle_startup(None, None)


    def _load_selection_config(self):
        self.auto_daemon = True
        try:
            with open(TRAY_CONFIG_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
            saved_ids = data.get("selected_profile_ids")
            if isinstance(saved_ids, list):
                self.selected_profile_ids = set(str(item) for item in saved_ids)
            if "auto_daemon" in data:
                self.auto_daemon = data["auto_daemon"]
        except Exception:
            self.selected_profile_ids = None

    def _save_selection_config(self):
        data = {
            "selected_profile_ids": sorted(self.selected_profile_ids or set()),
            "auto_daemon": self.auto_daemon
        }
        try:
            with open(TRAY_CONFIG_PATH, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _sync_profiles(self):
        self.available_profiles = discover_profiles(mode="all", limit=None)
        available_ids = {profile["id"] for profile in self.available_profiles}

        if self.selected_profile_ids is None:
            self.selected_profile_ids = set(available_ids)
        else:
            self.selected_profile_ids &= available_ids

    def _selected_profiles(self):
        return [profile for profile in self.available_profiles if profile["id"] in self.selected_profile_ids]

    def _pending_profiles(self):
        pending = []
        for profile in self._selected_profiles():
            if not was_farmed_today(profile["history_id"]):
                pending.append(profile)
        return pending

    def _completed_selected_count(self):
        completed = 0
        for profile in self._selected_profiles():
            if was_farmed_today(profile["history_id"]):
                completed += 1
        return completed

    def _status_text(self):
        if self.process and self.process.poll() is None:
            return "Đang cày..."

        if not self.available_profiles:
            return "Tạm dừng (Không thấy tài khoản)"

        selected = self._selected_profiles()
        if not selected:
            return "Tạm dừng (Chưa chọn acc)"

        pending = self._pending_profiles()
        if not pending:
            return "Tạm nghỉ (Đã xong hết)"

        return f"Sẵn sàng ({len(pending)} acc chờ cày)"

    def show_startup_popup(self):
        """Hiển thị một thông báo popup nhỏ khi bắt đầu phiên làm việc."""
        def _create_popup():
            popup = tk.Toplevel(self.root)
            popup.title("MSR Automation")
            popup.geometry("300x145")
            popup.overrideredirect(True) # No title bar
            popup.attributes("-topmost", True)
            popup.attributes("-alpha", 0.9) # Thêm độ mờ cho đẹp
            
            # Position: Bottom-right
            sw = popup.winfo_screenwidth()
            sh = popup.winfo_screenheight()
            x = sw - 320 
            y = sh - 200
            popup.geometry(f"+{x}+{y}")
            
            popup.configure(bg="#1e293b", highlightthickness=1, highlightbackground="#818cf8")
            
            greeting = get_random_greeting()
            lbl = tk.Label(popup, text="CHÀO NGÀY MỚI! ✨", font=("Segoe UI", 11, "bold"), bg="#1e293b", fg="#818cf8")
            lbl.pack(pady=(10, 0))
            
            msg = tk.Label(popup, text=greeting, font=("Segoe UI", 9), bg="#1e293b", fg="#e2e8f0", wraplength=260)
            msg.pack(pady=8, padx=15)
            
            btn_support = tk.Button(popup, text="Ủng hộ Shopee 1 giây :3 🧡", font=("Segoe UI", 9, "bold"), 
                                   bg="#ea580c", fg="white", activebackground="#c2410c", activeforeground="white",
                                   relief="flat", cursor="hand2", command=lambda: [open_support(), popup.destroy()])
            btn_support.pack(pady=(0, 10), fill="x", padx=50)
            
            # Auto-close after 15 seconds
            popup.after(15000, lambda: popup.destroy() if popup.winfo_exists() else None)
            
        self.root.after(0, _create_popup)

    def _summary_text(self):
        selected = self._selected_profiles()
        total_selected = len(selected)
        total_pending = len(self._pending_profiles()) if total_selected else 0
        total_completed = self._completed_selected_count() if total_selected else 0
        return f"Chọn: {total_selected} | Đang chờ: {total_pending} | Đã xong: {total_completed}"

    def _notify(self, message):
        try:
            self.icon.notify(message, "Microsoft Rewards Farmer")
        except Exception:
            pass

    def _make_toggle_action(self, profile_id):
        return lambda icon, item: self.toggle_profile(profile_id)

    def _make_checked_action(self, profile_id):
        return lambda item: profile_id in self.selected_profile_ids

    def rebuild_menu(self):
        profile_items = []
        for profile in self.available_profiles:
            profile_items.append(
                pystray.MenuItem(
                    profile["label"],
                    self._make_toggle_action(profile["id"]),
                    checked=self._make_checked_action(profile["id"]),
                )
            )

        if not profile_items:
            profile_items = [pystray.MenuItem("(No profiles found)", self.do_nothing, enabled=False)]

        self.menu = pystray.Menu(
            pystray.MenuItem("Mở Bảng Điều Khiển", self.open_console, default=True),
            pystray.MenuItem(f"Trạng thái: {self._status_text()}", self.do_nothing, enabled=False),
            pystray.MenuItem(self._summary_text(), self.do_nothing, enabled=False),
            pystray.MenuItem("===================", self.do_nothing, enabled=False),
            pystray.MenuItem(
                "Khởi động cùng Windows", 
                self.toggle_startup, 
                checked=lambda item: self.is_startup_enabled()
            ),
            pystray.MenuItem(
                "Tự động cày hàng ngày (Treo máy)", 
                self.toggle_daemon, 
                checked=lambda item: self.auto_daemon
            ),
            pystray.MenuItem("Danh sách Tài khoản", pystray.Menu(*profile_items)),
            pystray.MenuItem("Chọn tất cả", self.select_all_profiles),
            pystray.MenuItem("Bỏ chọn tất cả", self.clear_all_profiles),
            pystray.MenuItem("Tải lại danh sách", self.refresh_profiles),
            pystray.MenuItem("===================", self.do_nothing, enabled=False),
            pystray.MenuItem("Bắt đầu Cày", self.start_farming),
            pystray.MenuItem("Dừng cày", self.stop_farming),
            pystray.MenuItem("Xem Nhật ký (Log)", self.show_log_window_thread_safe),
            pystray.MenuItem("Hướng dẫn sử dụng", self.show_instructions),
            pystray.MenuItem("Thoát hoàn toàn", self.exit_app),
        )
        self.icon.menu = self.menu

    def open_console(self, icon=None, item=None):
        launcher_script = os.path.join(BASE_DIR, "launcher_gui.py")
        pythonw_path = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
        
        # Use subprocess to start independently
        subprocess.Popen(
            [pythonw_path, launcher_script],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def toggle_daemon(self, icon, item):
        self.auto_daemon = not self.auto_daemon
        self._save_selection_config()
        self.rebuild_menu()
        state_str = "BẬT" if self.auto_daemon else "TẮT"
        self._notify(f"Chế độ treo máy đang: {state_str}.")

    def is_startup_enabled(self):
        """Kiểm tra xem ứng dụng đã được đăng ký khởi động cùng Windows chưa."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "MSRAutomationService")
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False

    def toggle_startup(self, icon, item):
        """Bật/Tắt khởi động cùng Windows."""
        app_name = "MSRAutomationService"
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        pythonw_path = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
        script_path = os.path.join(BASE_DIR, "tray_app.py")
        cmd = f'"{pythonw_path}" "{script_path}"'

        if self.is_startup_enabled():
            # Tắt startup
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, app_name)
                winreg.CloseKey(key)
                self._notify("Đã TẮT tự động khởi động cùng Windows.")
            except Exception as e:
                self._notify(f"Lỗi khi tắt startup: {e}")
        else:
            # Bật startup
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                self._notify("Đã BẬT tự động khởi động cùng Windows.")
            except Exception as e:
                self._notify(f"Lỗi khi bật startup: {e}")
        
        self.rebuild_menu()

    def show_instructions(self, icon=None, item=None):
        def _show():
            top = tk.Toplevel(self.root)
            top.title("Hướng dẫn sử dụng Dịch vụ Tự động")
            top.geometry("500x420")
            top.attributes("-topmost", True)
            top.configure(bg="#f8f9fa")
            
            txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Segoe UI", 11), bg="#f8f9fa", bd=0)
            txt.pack(expand=True, fill="both", padx=15, pady=15)
            instructions = (
                "DỊCH VỤ TỰ ĐỘNG MICROSOFT REWARDS - HƯỚNG DẪN\n"
                "--------------------------------------------------\n\n"
                "1. CHẾ ĐỘ TREO MÁY (AUTO):\n"
                "- Khi bật, dịch vụ sẽ kiểm tra tài khoản của bạn mỗi 15 phút.\n"
                "- Nó sẽ tự động cày cho các tài khoản chưa xong mà không cần bạn bấm nút.\n"
                "- Giúp bạn rảnh tay hoàn toàn, chỉ cần mở máy tính là có điểm.\n\n"
                "2. CHỌN TÀI KHOẢN (PROFILES):\n"
                "- Dùng menu 'Danh sách Tài khoản' để chọn hoặc bỏ chọn nick muốn cày tự động.\n\n"
                "3. SỬ DỤNG SONG SONG:\n"
                "- Bot chạy ở chế độ 'Ẩn' (Headless), không chiếm chuột hay màn hình.\n"
                "- Bạn vẫn có thể chơi game, xem phim hay làm việc bình thường.\n"
                "- Lưu ý quan trọng: Hãy ĐÓNG trình duyệt Edge của tài khoản đang cày trước khi bot bắt đầu để tránh bị lỗi tranh chấp file.\n"
            )
            txt.insert(tk.END, instructions)
            txt.config(state=tk.DISABLED)
            
            btn_frame = tk.Frame(top, bg="#f8f9fa")
            btn_frame.pack(fill="x", pady=(0, 15))
            btn = tk.Button(btn_frame, text="Đã hiểu", command=top.destroy, font=("Segoe UI", 11, "bold"), bg="#0d6efd", fg="white", padx=20, pady=5)
            btn.pack()
            
        self.root.after(0, _show)

    def do_nothing(self, *args, **kwargs):
        return None

    def toggle_profile(self, profile_id):
        if profile_id in self.selected_profile_ids:
            self.selected_profile_ids.remove(profile_id)
        else:
            self.selected_profile_ids.add(profile_id)
        self._save_selection_config()
        self.rebuild_menu()

    def select_all_profiles(self, icon, item):
        self.selected_profile_ids = {profile["id"] for profile in self.available_profiles}
        self._save_selection_config()
        self.rebuild_menu()

    def clear_all_profiles(self, icon, item):
        self.selected_profile_ids = set()
        self._save_selection_config()
        self.rebuild_menu()

    def refresh_profiles(self, icon=None, item=None):
        self._sync_profiles()
        self._save_selection_config()
        self.rebuild_menu()

    def auto_start_if_needed(self):
        if self.process and self.process.poll() is None:
            return
        if not self._pending_profiles():
            self.rebuild_menu()
            return
        # Chỉ chạy lúc mở app nếu được phép Daemon
        if self.auto_daemon:
            self._start_farming_logic(auto_started=True)
            
    def daemon_worker(self):
        if self.auto_daemon:
            if self.process is None or self.process.poll() is not None:
                if self._pending_profiles():
                    self._sync_profiles()
                    self._start_farming_logic(auto_started=True)
        self.root.after(900000, self.daemon_worker)

    def start_farming(self, icon=None, item=None):
        self._start_farming_logic(auto_started=False)

    def _start_farming_logic(self, auto_started=False):
        if self.process and self.process.poll() is None:
            return

        selected = self._selected_profiles()
        if not selected:
            self.rebuild_menu()
            self._notify("Không có tài khoản nào được chọn")
            return

        pending = self._pending_profiles()
        if not pending:
            self.rebuild_menu()
            self._notify("Tất cả tài khoản đã xong hôm nay")
            return

        cmd = [sys.executable, SCRIPT_PATH, "--source", "all"]
        for profile in pending:
            cmd.extend(["--profile-id", profile["id"]])

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.rebuild_menu()

        if auto_started:
            self._notify(f"Tu dong bat dau {len(pending)} profile dang con pending")
        else:
            self._notify(f"Bat dau farm {len(pending)} profile da chon")

    def stop_farming(self, icon=None, item=None):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None

        cleanup_automation_processes()
        self.rebuild_menu()
        self._notify("Đã dừng quá trình cày")

    def monitor_process_gui(self):
        if self.process and self.process.poll() is not None:
            self.process = None
            self.rebuild_menu()
            if self._pending_profiles():
                self._notify("Dịch vụ cày đã dừng. Vẫn còn tài khoản chưa xong hôm nay!")
            else:
                self._notify("Tất cả tài khoản đã hoàn thành nhiệm vụ hôm nay!")

        self.root.after(2000, self.monitor_process_gui)

    def refresh_state_gui(self):
        if not (self.process and self.process.poll() is None):
            self._sync_profiles()
            self.rebuild_menu()
        self.root.after(30000, self.refresh_state_gui)

    def show_log_window_thread_safe(self, icon=None, item=None):
        self.root.after(0, self.open_log_window)

    def open_log_window(self):
        self.root.deiconify()
        self.log_window_open = True

        if not self.root.winfo_children():
            self.text_area = scrolledtext.ScrolledText(
                self.root,
                wrap=tk.WORD,
                font=("Consolas", 10),
                bg="#1e1e1e",
                fg="#d4d4d4",
            )
            self.text_area.pack(expand=True, fill="both")
            self.text_area.tag_config("INFO", foreground="#d4d4d4")
            self.text_area.tag_config("WARNING", foreground="#cca700")
            self.text_area.tag_config("ERROR", foreground="#f44747")
            self.text_area.tag_config("SUCCESS", foreground="#6a9955")
            self.text_area.tag_config("POINTS", foreground="#569cd6")
            self.root.protocol("WM_DELETE_WINDOW", self.hide_log_window)

    def hide_log_window(self):
        self.root.withdraw()
        self.log_window_open = False

    def get_latest_log_file(self):
        if not os.path.exists(LOG_DIR):
            return None
        files = [
            os.path.join(LOG_DIR, filename)
            for filename in os.listdir(LOG_DIR)
            if filename.startswith("farm_log_") and filename.endswith(".log")
        ]
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    def update_log_gui(self):
        if self.log_window_open:
            latest = self.get_latest_log_file()
            if latest and latest != self.current_log_file:
                self.current_log_file = latest
                self.last_pos = 0
                self.text_area.delete("1.0", tk.END)

            if self.current_log_file:
                try:
                    with open(self.current_log_file, "r", encoding="utf-8") as file:
                        file.seek(self.last_pos)
                        new_data = file.read()
                        if new_data:
                            self.last_pos = file.tell()
                            for line in new_data.splitlines():
                                self.append_clean_log(line)
                            self.text_area.see(tk.END)
                except Exception:
                    pass

        self.root.after(1000, self.update_log_gui)

    def append_clean_log(self, raw_line):
        match = re.match(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),\d{3} - \[(.*?)\] - (.*?) - (.*)", raw_line)
        if not match:
            self.text_area.insert(tk.END, raw_line + "\n")
            return

        _, time_str, _, level, msg = match.groups()
        icon = "*"
        tag = "INFO"

        upper_msg = msg.upper()
        if "SEARCH" in upper_msg:
            icon = "?"
        if "MOBILE" in upper_msg:
            icon = "M"
        if " PC" in upper_msg or upper_msg.startswith("PC"):
            icon = "P"
        if "POINTS" in upper_msg or "DIEM" in upper_msg:
            icon = "$"
            tag = "POINTS"
        if "ERROR" in level or "ERROR" in upper_msg:
            icon = "X"
            tag = "ERROR"
        if "WARNING" in level or "WARN" in upper_msg:
            icon = "!"
            tag = "WARNING"
        if "SUCCESS" in upper_msg or "HOAN THANH" in upper_msg:
            icon = "OK"
            tag = "SUCCESS"

        msg_clean = re.sub(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]+", "", msg).strip()
        self.text_area.insert(tk.END, f"[{time_str}] {icon} {msg_clean}\n", tag)

    def exit_app(self, icon=None, item=None):
        self.stop_farming()
        self.icon.stop()
        self.root.quit()
        sys.exit()


if __name__ == "__main__":
    # Đảm bảo chỉ có một instance của Service được chạy cùng lúc
    mutex_name = "Global\\MSR_Automation_Service_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        print("Dịch vụ MSR Automation đang chạy ngầm rồi!")
        sys.exit(0)

    root = tk.Tk()
    app = FarmTrayApp(root)
    root.mainloop()
