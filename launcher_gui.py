"""
Microsoft Rewards Multi-Profile GUI Launcher
=============================================
Giao diện đồ họa siêu gọn với CustomTkinter.
"""

import os
import sys
import threading
import ctypes
import json
import winreg
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from farm.orchestrator import FarmOrchestrator
from farm.profiles import discover_profiles, create_workspace_profile
from farm.support import open_support

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")
EDGE_USER_DATA = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
MAX_PROFILES = 6

def get_edge_profiles():
    profiles = []
    try:
        local_state_path = os.path.join(EDGE_USER_DATA, 'Local State')
        if os.path.exists(local_state_path):
            with open(local_state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            info_cache = data.get('profile', {}).get('info_cache', {})
            for folder_name, info in info_cache.items():
                display_name = info.get('name', folder_name)
                profile_path = os.path.join(EDGE_USER_DATA, folder_name)
                if os.path.isdir(profile_path):
                    profiles.append({
                        'folder': folder_name,
                        'name': display_name,
                        'path': profile_path
                    })
    except Exception as e:
        print(f"Error reading Edge profiles: {e}")
    return profiles

class FarmingGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bảng Điều Khiển MSR Management Console")
        self.geometry("640x510")
        self.minsize(600, 480)
        
        self.is_running = False
        self.current_thread = None
        self.idle_monitoring = False
        self.idle_thread = None
        self.scheduler_running = False
        self.scheduler_thread = None
        self.available_profiles = []
        
        self.create_widgets()
        self.refresh_profiles()
        self.load_config()
        self.refresh_points_summary()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- ROW 0: TOP BAR ---
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=35)
        top_bar.grid(row=0, column=0, padx=8, pady=(5, 0), sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(top_bar, text="MSR Console", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        self.points_today_var = ctk.StringVar(value="Sản lượng: Đang tính...")
        ctk.CTkLabel(top_bar, textvariable=self.points_today_var, text_color="#facc15", font=("Segoe UI", 13, "bold")).grid(row=0, column=1, sticky="w", padx=20)
        
        self.btn_support = ctk.CTkButton(top_bar, text="Ủng hộ 1 giây Shopee để tác giả vui", fg_color="#ea580c", hover_color="#c2410c", width=220, height=28, command=self.open_support_link)
        self.btn_support.grid(row=0, column=2, sticky="e", padx=5)
        
        self.btn_dashboard = ctk.CTkButton(top_bar, text="Dashboard", fg_color="#7c3aed", hover_color="#6d28d9", width=100, height=28, command=self.show_dashboard)
        self.btn_dashboard.grid(row=0, column=3, sticky="e", padx=5)

        # --- ROW 1: CONTROLS & PROFILES COMBINED ---
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, padx=8, pady=5, sticky="ew")
        ctrl_frame.grid_columnconfigure(1, weight=1)

        # PROFILES (Left)
        prof_section = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        prof_section.grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        
        prof_header = ctk.CTkFrame(prof_section, fg_color="transparent")
        prof_header.pack(fill="x", pady=2)
        ctk.CTkLabel(prof_header, text="Profiles", font=("Segoe UI", 13, "bold")).pack(side="left")
        
        btn_prof = ctk.CTkFrame(prof_section, fg_color="transparent")
        btn_prof.pack(fill="x", pady=2)
        ctk.CTkButton(btn_prof, text="Tải lại", width=60, height=24, command=self.refresh_profiles).pack(side="left")
        ctk.CTkButton(btn_prof, text="Thêm", width=50, height=24, command=self.add_profile).pack(side="left", padx=2)
        ctk.CTkButton(btn_prof, text="Xoá", width=40, height=24, fg_color="#ef4444", hover_color="#dc2626", command=self.delete_profile).pack(side="left", padx=2)
        ctk.CTkButton(btn_prof, text="Tất cả", width=50, height=24, command=self.select_all).pack(side="left")
        
        self.profile_container = ctk.CTkFrame(prof_section, fg_color="transparent")
        self.profile_container.pack(fill="x", pady=4)
        self.profile_vars = {}

        # SETTINGS & ACTION (Right)
        set_section = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        set_section.grid(row=0, column=1, padx=8, pady=5, sticky="ne")
        
        row1 = ctk.CTkFrame(set_section, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkLabel(row1, text="Tốc độ cày:", font=("Segoe UI", 12)).pack(side="left", padx=2)
        self.speed_var = ctk.StringVar(value="Auto (Smart)")
        ctk.CTkOptionMenu(row1, variable=self.speed_var, values=["Auto (Smart)", "Safe", "Medium", "Fast", "Turbo"], width=130, height=26).pack(side="left", padx=5)
        
        self.auto_quota_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(row1, text="Auto Quota", variable=self.auto_quota_var, font=("Segoe UI", 12), switch_width=32, switch_height=16).pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(set_section, fg_color="transparent")
        row2.pack(fill="x", pady=(5, 8))
        self.debug_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(row2, text="Visual Debug (Internal Edge)", variable=self.debug_var, font=("Segoe UI", 12), switch_width=32, switch_height=16).pack(side="left", padx=5)
        
        btn_action_frame = ctk.CTkFrame(set_section, fg_color="transparent")
        btn_action_frame.pack(fill="x", pady=4)
        self.btn_start = ctk.CTkButton(btn_action_frame, text="BẮT ĐẦU", fg_color="#10b981", hover_color="#059669", font=("Segoe UI", 13, "bold"), height=32, command=self.start_farming)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_retry = ctk.CTkButton(btn_action_frame, text="CÀY LẠI", fg_color="#f59e0b", hover_color="#d97706", font=("Segoe UI", 13, "bold"), height=32, command=self.retry_farming)
        self.btn_retry.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_stop = ctk.CTkButton(btn_action_frame, text="DỪNG LẠI", fg_color="#ef4444", hover_color="#dc2626", font=("Segoe UI", 13, "bold"), height=32, state="disabled", command=self.stop_farming)
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=2)

        self.show_adv_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(set_section, text="Cài đặt nâng cao", variable=self.show_adv_var, command=self.toggle_advanced, font=("Segoe UI", 12), switch_width=32, switch_height=16).pack(anchor="w", pady=2, padx=5)
        
        # --- ROW 2: ADVANCED ---
        self.adv_frame = ctk.CTkFrame(self)
        
        row_adv1 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        row_adv1.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(row_adv1, text="Số luồng (PC/Mobile/Delay):", font=("Segoe UI", 11)).pack(side="left")
        self.pc_var = ctk.StringVar(value="30")
        ctk.CTkEntry(row_adv1, textvariable=self.pc_var, width=35, height=22).pack(side="left", padx=2)
        self.mobile_var = ctk.StringVar(value="20")
        ctk.CTkEntry(row_adv1, textvariable=self.mobile_var, width=35, height=22).pack(side="left", padx=2)
        self.delay_var = ctk.StringVar(value="5")
        ctk.CTkEntry(row_adv1, textvariable=self.delay_var, width=35, height=22).pack(side="left", padx=2)
        
        self.idle_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(row_adv1, text="Treo máy IDLE sau:", variable=self.idle_var, command=self.toggle_idle_monitor, font=("Segoe UI", 11), switch_width=30, switch_height=15).pack(side="left", padx=(10, 2))
        self.idle_time_var = ctk.StringVar(value="5")
        ctk.CTkEntry(row_adv1, textvariable=self.idle_time_var, width=35, height=22).pack(side="left")
        self.idle_status = ctk.CTkLabel(row_adv1, text="", text_color="#94a3b8", font=("Segoe UI", 10))
        self.idle_status.pack(side="left", padx=(6, 0))
        
        row_adv2 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        row_adv2.pack(fill="x", padx=5, pady=2)
        self.schedule_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(row_adv2, text="Hẹn giờ chạy (HH:MM)", variable=self.schedule_var, command=self.toggle_scheduler, font=("Segoe UI", 11), switch_width=30, switch_height=15).pack(side="left", padx=2)
        self.schedule_hour_var = ctk.StringVar(value="02")
        ctk.CTkOptionMenu(row_adv2, variable=self.schedule_hour_var, values=[f"{h:02d}" for h in range(24)], width=50, height=22).pack(side="left", padx=2)
        self.schedule_min_var = ctk.StringVar(value="00")
        ctk.CTkOptionMenu(row_adv2, variable=self.schedule_min_var, values=[f"{m:02d}" for m in range(0, 60, 15)], width=50, height=22).pack(side="left", padx=2)
        
        ctk.CTkLabel(row_adv2, text="TG:", font=("Segoe UI", 11)).pack(side="left", padx=(10, 2))
        self.tg_token_var = ctk.StringVar(value="")
        ctk.CTkEntry(row_adv2, textvariable=self.tg_token_var, width=70, placeholder_text="Token", show="*", height=22).pack(side="left", padx=2)
        self.tg_chat_var = ctk.StringVar(value="")
        ctk.CTkEntry(row_adv2, textvariable=self.tg_chat_var, width=70, placeholder_text="ChatID", height=22).pack(side="left", padx=2)
        
        # New Row 3 for Startup
        row_adv3 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        row_adv3.pack(fill="x", padx=5, pady=2)
        
        # Mặc định là ON nếu máy chưa được cài đặt startup
        is_enabled = self.is_startup_enabled()
        self.startup_var = ctk.BooleanVar(value=True) # Luôn để biến là True lúc khởi tạo
        
        ctk.CTkSwitch(row_adv3, text="Khởi động cùng Windows", variable=self.startup_var, command=self.toggle_startup, font=("Segoe UI", 11), switch_width=30, switch_height=15).pack(side="left", padx=2)
        
        # Nếu máy chưa có trong Registry, thực hiện ghi đè luôn để mặc định là ON
        if not is_enabled:
            self.root.after(1000, self.toggle_startup)




        # --- ROW 3: PROGRESS & LOGS ---
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=3, column=0, padx=8, pady=(2, 8), sticky="nsew")
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_rowconfigure(2, weight=1)
        
        status_top = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
        status_top.grid_columnconfigure(0, weight=1)
        
        self.status_var = ctk.StringVar(value="Sẵn sàng cày")
        ctk.CTkLabel(status_top, textvariable=self.status_var, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.eta_var = ctk.StringVar(value="Dự kiến xong: --:--")
        ctk.CTkLabel(status_top, textvariable=self.eta_var, text_color="#a78bfa", font=("Segoe UI", 11)).grid(row=0, column=1, sticky="e")
        
        self.progress_bar = ctk.CTkProgressBar(status_frame, height=8)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=2)
        self.progress_bar.set(0)
        
        self.log_text = ctk.CTkTextbox(status_frame, font=("Consolas", 11), text_color="#10b981", fg_color="#0d0d14", border_spacing=2)
        self.log_text.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 8))

    def toggle_advanced(self):
        if self.show_adv_var.get():
            self.adv_frame.grid(row=2, column=0, padx=8, pady=(0, 4), sticky="ew")
        else:
            self.adv_frame.grid_forget()

    def is_startup_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "MSRAutomationService")
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False

    def toggle_startup(self):
        app_name = "MSRAutomationService"
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        # We start the Hub/Tray app instead of GUI for background service
        # If Hub exists, start that, otherwise start tray_app.py
        target_script = "MSR_Smart_Launcher.py" if os.path.exists(os.path.join(os.path.dirname(__file__), "MSR_Smart_Launcher.py")) else "tray_app.py"
        
        pythonw_path = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "pythonw.exe")
        script_path = os.path.join(os.path.dirname(__file__), target_script)
        cmd = f'"{pythonw_path}" "{script_path}"'

        try:
            if self.startup_var.get():
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                self.log("Đã BẬT tự động khởi động cùng Windows.")
            else:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError: pass
                winreg.CloseKey(key)
                self.log("Đã TẮT tự động khởi động cùng Windows.")
        except Exception as e:
            self.log(f"Lỗi cấu hình Startup: {e}")
            messagebox.showerror("Lỗi", f"Không thể cấu hình khởi động: {e}")

    def refresh_profiles(self):
        for widget in self.profile_container.winfo_children():
            widget.destroy()
        self.profile_vars.clear()
        self.profile_paths = {}

        self.available_profiles = discover_profiles(mode="all", limit=MAX_PROFILES)
        container = self.profile_container
        if not self.available_profiles:
            ctk.CTkLabel(container, text="(No profiles found)").pack()
        else:
            for profile in self.available_profiles:
                var = ctk.BooleanVar(value=True)
                profile_id = profile["id"]
                self.profile_vars[profile_id] = var
                self.profile_paths[profile_id] = profile
                
                # Row Frame for each profile
                row = ctk.CTkFrame(container, fg_color="transparent")
                row.pack(fill="x", pady=1, anchor="w")
                
                cb = ctk.CTkCheckBox(row, text=profile["label"], variable=var, checkbox_width=16, checkbox_height=16, font=("Segoe UI", 11))
                cb.pack(side="left", padx=2)
                
                # Login Button for each profile
                btn_login = ctk.CTkButton(row, text="Login", width=45, height=20, font=("Segoe UI", 10), 
                                         fg_color="#334155", hover_color="#475569", 
                                         command=lambda p=profile: self.open_profile_browser(p))
                btn_login.pack(side="right", padx=5)
                
        self.log(f"Tìm thấy {len(self.available_profiles)} profiles")

    def select_all(self):
        all_selected = all(v.get() for v in self.profile_vars.values())
        for var in self.profile_vars.values():
            var.set(not all_selected)

    def add_profile(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Thêm Profile")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Tên Profile mới:").pack(pady=(10, 5))
        name_var = tk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=name_var, width=150)
        entry.pack(pady=2)
        entry.focus()
        
        def confirm():
            name = name_var.get().strip()
            if name:
                path = create_workspace_profile(name)
                self.log(f"Đã tạo profile: {name}.")
                dialog.destroy()
                self.refresh_profiles()
                
                # Suggest login immediately
                if messagebox.askyesno("Đăng nhập ngay", f"Đã tạo xong profile '{name}'. Bạn có muốn mở trình duyệt để Đăng Nhập ngay không?"):
                    self.open_profile_browser({"path": path, "name": name})
                    
        ctk.CTkButton(dialog, text="Tạo Mới", command=confirm, height=28).pack(pady=10)

    def open_profile_browser(self, profile):
        path = profile.get("path")
        if not path: return
        self.log(f"Đang mở trình duyệt cho profile: {profile.get('name')}...")
        
        # Determine Edge path (common locations)
        edge_paths = [
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Microsoft\\Edge\\Application\\msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft\\Edge\\Application\\msedge.exe"),
        ]
        
        edge_bin = "msedge.exe" # Fallback to PATH
        for p in edge_paths:
            if os.path.exists(p):
                edge_bin = p
                break
        
        try:
            import subprocess
            # Cấu hình các Flag siêu mạnh để cô lập Profile, tránh tự động đăng nhập Acc Windows chính
            flags = [
                f'--user-data-dir="{path}"',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-sync',
                '--disable-features=IdentityConsistency,WebToBrowserSignIn,ImplicitRootScp,MSBB',
                '--no-signin'
            ]
            target_url = "https://rewards.bing.com/"
            cmd = f'start "" "{edge_bin}" {" ".join(flags)} "{target_url}"'
            subprocess.Popen(cmd, shell=True)
            messagebox.showinfo("Đang mở trình duyệt", "Đang mở Edge... Hãy Đăng nhập tài khoản Microsoft của bạn rồi Đóng trình duyệt trước khi chạy Bot nhé!")
        except Exception as e:
            self.log(f"Lỗi mở Edge: {e}")
            messagebox.showerror("Lỗi", f"Không thể mở Edge: {e}")

    def delete_profile(self):
        selected = [p for p, v in self.profile_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Warning", "Hãy tick chọn ít nhất 1 profile để xóa!")
            return
            
        target_profiles = []
        for pid in selected:
            prof = self.profile_paths[pid]
            if prof.get("source") == "local":
                target_profiles.append(prof)
            else:
                messagebox.showerror("Error", f"Không thể xóa Profile gốc từ môi trường làm việc chính của Edge ({prof['name']}). Chức năng này chỉ cho phép dọn dẹp các tài khoản phụ dã được nạp vào Local/Clone!")
                return
                
        if not target_profiles:
            return
            
        confirm_msg = f"CẢNH BÁO: Rủi ro tàng hình!\nBạn sắp XÓA VĨNH VIỄN {len(target_profiles)} profile máy phụ sau đây:\n"
        for p in target_profiles:
            confirm_msg += f"- {p['name']}\n"
        confirm_msg += "\nĐiều này sẽ CÀN QUÉT toàn bộ Dữ liệu duyệt, Lịch sử, Cookies và Tài khoản đã đăng nhập bên trong! Bạn có chắc tay không?"
        
        if messagebox.askyesno("Xóa Profile", confirm_msg):
            import shutil
            for prof in target_profiles:
                try:
                    shutil.rmtree(prof["path"])
                    self.log(f"Đã xóa vĩnh viễn profile Local: {prof['name']}")
                except Exception as e:
                    self.log(f"Lỗi khi xóa profile {prof['name']}: {e}")
            self.refresh_profiles()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        self.log_text.insert("end", formatted)
        self.log_text.see("end")
        try:
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"gui_farm_{datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(formatted)
        except: pass

    def refresh_points_summary(self):
        try:
            from farm.history import get_today_stats
            stats = get_today_stats()
            total = sum(item.get("earned", 0) for item in stats.values())
            self.points_today_var.set(f"Daily Stat: +{total} pts")
        except:
            self.points_today_var.set("Hôm nay: --")

    def start_farming(self):
        selected = [p for p, v in self.profile_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Warning", "Hãy chọn ít nhất 1 profile!")
            return
            
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set("Starting...")
        
        self.current_thread = threading.Thread(target=self.farming_worker, args=(selected,), daemon=True)
        self.current_thread.start()

    def retry_farming(self):
        """Force re-farm selected profiles, bypassing was_farmed_today check."""
        selected = [p for p, v in self.profile_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Warning", "Hãy chọn ít nhất 1 profile!")
            return
        
        if self.is_running:
            messagebox.showwarning("Warning", "Đang chạy! Hãy dừng trước khi Farm thêm.")
            return
        
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log("FARM THÊM - Bỏ qua kiểm tra lịch sử, farm lại tất cả profile đã chọn!")
        
        self.status_var.set("Starting retry...")
        self.current_thread = threading.Thread(target=self.farming_worker, args=(selected, True), daemon=True)
        self.current_thread.start()

    def farming_worker(self, profiles, force_retry=False):
        from farm.history import get_today_stats
        
        def safe_log(msg):
            self.after(0, lambda: self.log(msg))
            
        def update_points_ui():
            self.after(0, self.refresh_points_summary)
            return
            try:
                stats = get_today_stats()
                total = sum(s.get("earned", 0) for s in stats.values())
                self.after(0, lambda: self.points_today_var.set(f"Hôm nay: +{total} pts"))
            except: pass
            
        callbacks = {
            'log': safe_log,
            'progress': lambda p: self.after(0, lambda: self.progress_bar.set(p/100.0)),
            'status': lambda s: self.after(0, lambda: self.status_var.set(s)),
            'eta': lambda e: self.after(0, lambda: self.eta_var.set(e)),
            'points': update_points_ui,
            'is_running': lambda: self.is_running
        }
        
        config = {
            'pc_count': self.pc_var.get(),
            'mobile_count': self.mobile_var.get(),
            'delay_min': self.delay_var.get(),
            'speed_mode': self.speed_var.get(),
            'auto_quota': self.auto_quota_var.get(),
            'debug_mode': self.debug_var.get()
        }
        
        orchestrator = FarmOrchestrator(callbacks)
        orchestrator.farm_profiles(profiles, config, self.profile_paths, force_retry=force_retry)
        
        self.after(0, self.send_telegram_notification)
        self.after(0, self.reset_ui)

    def stop_farming(self):
        self.is_running = False
        self.status_var.set("Stopping...")
        self.log("Đang dừng...")

    def reset_ui(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_retry.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set("Ready")
        self.eta_var.set("ETA: --:--")
        self.progress_bar.set(0)
        self.refresh_points_summary()

    # ===== CONFIG, IDLE, SCHEDULER, TELEGRAM =====
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.pc_var.set(cfg.get('pc_searches', '30'))
                self.mobile_var.set(cfg.get('mobile_searches', '20'))
                self.delay_var.set(cfg.get('delay_minutes', '5'))
                self.speed_var.set(cfg.get('speed_mode', 'Auto (Smart)'))
                self.auto_quota_var.set(cfg.get('auto_quota', True))
                self.debug_var.set(cfg.get('debug_mode', False))
                self.idle_time_var.set(cfg.get('idle_minutes', '5'))
                self.schedule_hour_var.set(cfg.get('schedule_hour', '02'))
                self.schedule_min_var.set(cfg.get('schedule_min', '00'))
                self.tg_token_var.set(cfg.get('telegram_token', ''))
                self.tg_chat_var.set(cfg.get('telegram_chat_id', ''))
            except: pass

    def save_config(self):
        try:
            cfg = {
                'pc_searches': self.pc_var.get(),
                'mobile_searches': self.mobile_var.get(),
                'delay_minutes': self.delay_var.get(),
                'speed_mode': self.speed_var.get(),
                'auto_quota': self.auto_quota_var.get(),
                'debug_mode': self.debug_var.get(),
                'idle_minutes': self.idle_time_var.get(),
                'schedule_hour': self.schedule_hour_var.get(),
                'schedule_min': self.schedule_min_var.get(),
                'telegram_token': self.tg_token_var.get(),
                'telegram_chat_id': self.tg_chat_var.get()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4)
        except: pass

    def on_close(self):
        self.save_config()
        self.idle_monitoring = False
        self.scheduler_running = False
        if getattr(self, 'is_running', False):
            try:
                from farm.driver import cleanup_automation_processes
                cleanup_automation_processes()
            except: pass
        self.destroy()

    def get_idle_seconds(self):
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0

    def toggle_idle_monitor(self):
        if self.idle_var.get():
            if self.idle_monitoring:
                return
            self.idle_monitoring = True
            self.idle_thread = threading.Thread(target=self.idle_monitor_loop, daemon=True)
            self.idle_thread.start()
        else:
            self.idle_monitoring = False
            self.idle_status.configure(text="")

    def idle_monitor_loop(self):
        import time
        while self.idle_monitoring:
            try: idle_threshold = int(self.idle_time_var.get()) * 60
            except: idle_threshold = 300
            
            idle_secs = self.get_idle_seconds()
            if not self.is_running:
                self.after(0, lambda m=int(idle_secs//60): self.idle_status.configure(text=f"(Rảnh {m}m)"))
            
            if idle_secs >= idle_threshold and not self.is_running:
                self.after(0, self.start_farming)
                while self.is_running and self.idle_monitoring:
                    time.sleep(5)
                if self.idle_monitoring:
                    time.sleep(300)
            else:
                time.sleep(30)

    def toggle_scheduler(self):
        if self.schedule_var.get():
            if self.scheduler_running:
                return
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()
        else:
            self.scheduler_running = False

    def scheduler_loop(self):
        import time
        last_farm_date = None
        while getattr(self, 'scheduler_running', False):
            now = datetime.now()
            try:
                target_h = int(self.schedule_hour_var.get())
                target_m = int(self.schedule_min_var.get())
                if (now.hour == target_h and now.minute == target_m and not self.is_running 
                    and last_farm_date != now.strftime('%Y-%m-%d')):
                    last_farm_date = now.strftime('%Y-%m-%d')
                    self.after(0, self.start_farming)
                    while self.is_running and getattr(self, 'scheduler_running', False):
                        time.sleep(5)
            except: pass
            time.sleep(30)

    def send_telegram_notification(self):
        token = self.tg_token_var.get().strip()
        chat_id = self.tg_chat_var.get().strip()
        if not token or not chat_id: return
        try:
            from farm.history import get_today_stats
            today = get_today_stats()
            lines = [f"MS Rewards Complete! {datetime.now().strftime('%d/%m/%Y')}"]
            for profile, stats in today.items():
                lines.append(f"{profile}: +{stats['earned']} pts")
            message = "\n".join(lines)
            
            import urllib.request
            import urllib.parse
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({'chat_id': chat_id, 'text': message}).encode()
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            self.log(f"⚠️ Telegram error: {e}")

    def show_dashboard(self):
        try: from farm.history import get_today_stats
        except: return
        
        dash = ctk.CTkToplevel(self)
        dash.title("Thống Kê")
        dash.geometry("420x480")
        dash.transient(self)
        dash.grab_set()
        dash.configure(fg_color="#0f172a") # Dark slate background
        
        # Header Section
        header = ctk.CTkFrame(dash, fg_color="transparent")
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        ctk.CTkLabel(header, text="DAILY PERFORMANCE REPORT", font=("Segoe UI Black", 20, "bold"), text_color="#f8fafc").pack()
        ctk.CTkLabel(header, text="Real-time task productivity analytics", font=("Segoe UI", 12), text_color="#94a3b8").pack()
        
        today = get_today_stats()
        total_points = sum(s.get("earned", 0) for s in today.values()) if today else 0
        
        # Shiny Total Points Counter
        total_box = ctk.CTkFrame(dash, fg_color="#1e293b", corner_radius=15, border_color="#6366f1", border_width=2)
        total_box.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(total_box, text="CUMULATIVE OUTPUT", font=("Segoe UI", 12, "bold"), text_color="#818cf8").pack(pady=(12, 0))
        ctk.CTkLabel(total_box, text=f"+{total_points:,}", font=("Impact", 32), text_color="#fbbf24").pack(pady=(0, 12))
        
        # Scrollable Profiles List
        scroll = ctk.CTkScrollableFrame(dash, fg_color="transparent", border_color="#334155", border_width=1, corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
        if today:
            sorted_today = sorted(today.items(), key=lambda x: x[1].get('earned', 0), reverse=True)
            for idx, (profile, stats) in enumerate(sorted_today):
                pts = stats.get('earned', 0)
                card_color = "#1e293b" if idx % 2 == 0 else "#0f172a"
                card = ctk.CTkFrame(scroll, fg_color=card_color, corner_radius=6)
                card.pack(fill="x", pady=3, padx=2)
                
                # Biểu tượng Profile + Tên
                left_info = ctk.CTkFrame(card, fg_color="transparent")
                left_info.pack(side="left", padx=10, fill="y")
                ctk.CTkLabel(left_info, text="", font=("Segoe UI", 18)).pack(side="left")
                ctk.CTkLabel(left_info, text=f" {profile}", font=("Segoe UI", 13, "bold"), text_color="#e2e8f0").pack(side="left", padx=(5,0))
                
                # Điểm
                ctk.CTkLabel(card, text=f"+{pts:,} pts", font=("Consolas", 14, "bold"), text_color="#10b981").pack(side="right", padx=15, pady=12)
        else:
            ctk.CTkLabel(scroll, text="Chưa có dữ liệu hôm nay...\nHãy nhấn START để máy đi farm!", 
                         font=("Segoe UI", 13), text_color="#64748b").pack(pady=50)

    def open_support_link(self):
        import webbrowser
        import random
        # DANH SÁCH CÁC LINK SHOPEE CỦA BẠN (Bạn thay thế các link Affiliate vào đây nhé)
        shopee_links = [
            "https://s.shopee.vn/6L0ZozZ82r",
            "https://s.shopee.vn/6Ah9cgZlNq",
            "https://s.shopee.vn/60NjQNaOip",
            "https://s.shopee.vn/5q4JE4b23o",
            "https://s.shopee.vn/5fkt1lbfOn",
            "https://s.shopee.vn/5VRSpScIjm",
            "https://s.shopee.vn/5L82d9cw4l",
            "https://s.shopee.vn/AUq8meJGam",
            "https://s.shopee.vn/AKWiaLJtvl",
            "https://s.shopee.vn/AADIO2KXGk",
            "https://s.shopee.vn/9ztsBjLAbj",
            "https://s.shopee.vn/9paRzQLnwi",
            "https://s.shopee.vn/9fH1n7MRHh",
            "https://s.shopee.vn/9UxbaoN4cg",
            "https://s.shopee.vn/9KeBOVNhxf",
            "https://s.shopee.vn/9AKlCCOLIe",
            "https://s.shopee.vn/901KztOydd",
            "https://s.shopee.vn/8phunaPbyc",
            "https://s.shopee.vn/8fOUbHQFJb",
            "https://s.shopee.vn/8V54OyQsea",
            "https://s.shopee.vn/8KleCfRVzZ",
            "https://s.shopee.vn/8ASE0MS9KY",
            "https://s.shopee.vn/808no3SmfX",
            "https://s.shopee.vn/2VnrFwnipU",
            "https://s.shopee.vn/2LUR3doMAT",
            "https://s.shopee.vn/2BB0rKozVS",
            "https://s.shopee.vn/20raf1pcqR",
            "https://s.shopee.vn/1qYASiqGBQ",
            "https://s.shopee.vn/1gEkGPqtWP",
            "https://s.shopee.vn/1VvK46rWrO",
            "https://s.shopee.vn/1LbtrnsACN",
            "https://s.shopee.vn/1BITfUsnXM",
            "https://s.shopee.vn/10z3TBtQsL",
            "https://s.shopee.vn/qfdGsu4DK",
            "https://s.shopee.vn/gMD4ZuhYJ",
            "https://s.shopee.vn/W2msGvKtI",
            "https://s.shopee.vn/LjMfxvyEH",
            "https://s.shopee.vn/BPwTewbZG",
            "https://s.shopee.vn/16WHLxEuF",
            "https://s.shopee.vn/5AocQqdZQG",
            "https://s.shopee.vn/50VCEXeClF",
            "https://s.shopee.vn/4qBm2Eeq6E",
            "https://s.shopee.vn/4fsLpvfTRD",
            "https://s.shopee.vn/4VYvdcg6mC",
            "https://s.shopee.vn/4LFVRJgk7B",
            "https://s.shopee.vn/4Aw5F0hNSA",
            "https://s.shopee.vn/40cf2hi0n9",
            "https://s.shopee.vn/3qJEqOie88",
            "https://s.shopee.vn/3fzoe5jHT7",
            "https://s.shopee.vn/3VgORmjuo6",
            "https://s.shopee.vn/3LMyFTkY95",
            "https://s.shopee.vn/3B3Y3AlBU4",
            "https://s.shopee.vn/30k7qrlop3",
            "https://s.shopee.vn/2qQheYmSA2",
            "https://s.shopee.vn/2g7HSFn5V1",
            "https://s.shopee.vn/7fVxPRU3M0",
            "https://s.shopee.vn/7ppNbkTQ13",
            "https://s.shopee.vn/7Kt70pVK1y",
            "https://s.shopee.vn/7VCXD8Ugh1",
            "https://s.shopee.vn/70GGcDWahw",
            "https://s.shopee.vn/7AZgoWVxMz",
            "https://s.shopee.vn/6fdQDbXrNu",
            "https://s.shopee.vn/6pwqPuXE2x",
            "https://s.shopee.vn/6L0ZozZ83s",
            "https://s.shopee.vn/6VK01IYUiv",
            "https://s.shopee.vn/60NjQNaOjq",
            "https://s.shopee.vn/6Ah9cgZlOt",
            "https://s.shopee.vn/5fkt1lbfPo",
            "https://s.shopee.vn/5q4JE4b24r",
            "https://s.shopee.vn/5L82d9cw5m",
            "https://s.shopee.vn/5VRSpScIkp",
            "https://s.shopee.vn/AKWiaLJtwm",
            "https://s.shopee.vn/AUq8meJGbp",
            "https://s.shopee.vn/9ztsBjLAck",
            "https://s.shopee.vn/AADIO2KXHn",
            "https://s.shopee.vn/9fH1n7MRIi",
            "https://s.shopee.vn/9paRzQLnxl",
            "https://s.shopee.vn/9KeBOVNhyg",
            "https://s.shopee.vn/9UxbaoN4dj",
            "https://s.shopee.vn/901KztOyee",
            "https://s.shopee.vn/9AKlCCOLJh",
            "https://s.shopee.vn/8fOUbHQFKc",
            "https://s.shopee.vn/8phunaPbzf",
            "https://s.shopee.vn/8KleCfRW0a",
            "https://s.shopee.vn/8V54OyQsfd",
            "https://s.shopee.vn/808no3SmgY",
            "https://s.shopee.vn/8ASE0MS9Lb",
            "https://s.shopee.vn/2LUR3doMBU",
            "https://s.shopee.vn/2VnrFwniqX",
            "https://s.shopee.vn/20raf1pcrS",
            "https://s.shopee.vn/2BB0rKozWV",
            "https://s.shopee.vn/1gEkGPqtXQ",
            "https://s.shopee.vn/1qYASiqGCT",
            "https://s.shopee.vn/1LbtrnsADO",
            "https://s.shopee.vn/1VvK46rWsR",
            "https://s.shopee.vn/10z3TBtQtM",
            "https://s.shopee.vn/1BITfUsnYP",
            "https://s.shopee.vn/gMD4ZuhZK",
            "https://s.shopee.vn/qfdGsu4EN",
            "https://s.shopee.vn/LjMfxvyFI"
        ]
        # Lấy ngày hiện tại làm hạt giống (seed) để random
        # Nghĩa là trong cùng 1 ngày, nếu ấn nhiều lần sẽ chỉ ra đúng 1 link. Sang ngày mai sẽ tự động đổi link khác.
        today_str = datetime.now().strftime("%Y-%m-%d")
        random.seed(today_str)
        
        selected_link = random.choice(shopee_links)
        
        # Phục hồi lại seed ngẫu nhiên cho các hàm khác của app nếu có dùng
        random.seed() 
        
        # Mở link bằng trình duyệt mặc định của máy tính người dùng
        webbrowser.open(selected_link)
        self.log(f"Đã mở link ủng hộ Shopee cho ngày {today_str}!")

if __name__ == "__main__":
    # Đảm bảo chỉ có một instance của Console được chạy cùng lúc
    mutex_name = "Global\\MSR_Automation_Console_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        # In Windows, we can't show a messagebox easily before app initialization, 
        # but the GUI will just quietly exit or we can use a basic ctypes messagebox.
        ctypes.windll.user32.MessageBoxW(0, "Bảng quản lý MSR Console đang mở rồi bạn ơi!", "Thông báo", 0x40 | 0x0)
        sys.exit(0)

    app = FarmingGUI()
    app.mainloop()
