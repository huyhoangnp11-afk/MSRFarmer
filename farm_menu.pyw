"""
MS Rewards Farmer - GUI Menu
============================
Giao diện đơn giản với các nút bấm dễ dùng
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import threading
from datetime import datetime

# Đường dẫn
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FARM_SCRIPT = os.path.join(SCRIPT_DIR, "farm_rewards.py")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")

# Cấu hình mặc định
DEFAULT_PC = 42
DEFAULT_MOBILE = 40

class FarmLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MS Rewards Farmer")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 400) // 2
        y = (self.root.winfo_screenheight() - 500) // 2
        self.root.geometry(f"400x500+{x}+{y}")
        
        self.is_running = False
        self.setup_ui()
        
    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        header = tk.Frame(self.root, bg="#16213e", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title = tk.Label(header, text="🎮 MS Rewards Farmer", 
                        font=("Segoe UI", 18, "bold"),
                        fg="#00d4ff", bg="#16213e")
        title.pack(pady=20)
        
        # Status
        self.status_label = tk.Label(self.root, text="Sẵn sàng", 
                                    font=("Segoe UI", 10),
                                    fg="#4ade80", bg="#1a1a2e")
        self.status_label.pack(pady=10)
        
        # Main buttons frame
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=20, padx=30, fill="x")
        
        # Button style
        btn_style = {
            "font": ("Segoe UI", 12),
            "width": 25,
            "height": 2,
            "cursor": "hand2",
            "relief": "flat",
            "bd": 0
        }
        
        # Farm All button
        self.btn_all = tk.Button(btn_frame, text="🚀 Farm Tất Cả (PC + Mobile)",
                                bg="#4f46e5", fg="white", 
                                activebackground="#6366f1", activeforeground="white",
                                command=self.farm_all, **btn_style)
        self.btn_all.pack(pady=8)
        
        # Mobile Only button
        self.btn_mobile = tk.Button(btn_frame, text="📱 Chỉ Farm Mobile",
                                   bg="#0891b2", fg="white",
                                   activebackground="#06b6d4", activeforeground="white",
                                   command=self.farm_mobile, **btn_style)
        self.btn_mobile.pack(pady=8)
        
        # PC Only button
        self.btn_pc = tk.Button(btn_frame, text="💻 Chỉ Farm PC",
                               bg="#059669", fg="white",
                               activebackground="#10b981", activeforeground="white",
                               command=self.farm_pc, **btn_style)
        self.btn_pc.pack(pady=8)
        
        # Separator
        sep = ttk.Separator(btn_frame, orient="horizontal")
        sep.pack(fill="x", pady=15)
        
        # View Log button
        self.btn_log = tk.Button(btn_frame, text="📊 Xem Log Hôm Nay",
                                bg="#374151", fg="white",
                                activebackground="#4b5563", activeforeground="white",
                                command=self.view_log, **btn_style)
        self.btn_log.pack(pady=8)
        
        # Settings Frame
        settings_frame = tk.LabelFrame(self.root, text=" ⚙️ Cài Đặt Số Lượng ",
                                      font=("Segoe UI", 10),
                                      fg="#94a3b8", bg="#1a1a2e",
                                      labelanchor="n")
        settings_frame.pack(pady=15, padx=30, fill="x")
        
        # PC Count
        pc_frame = tk.Frame(settings_frame, bg="#1a1a2e")
        pc_frame.pack(pady=10, padx=20, fill="x")
        tk.Label(pc_frame, text="PC Searches:", fg="#94a3b8", bg="#1a1a2e",
                font=("Segoe UI", 10)).pack(side="left")
        self.pc_var = tk.StringVar(value=str(DEFAULT_PC))
        self.pc_entry = tk.Entry(pc_frame, textvariable=self.pc_var, width=8,
                                font=("Segoe UI", 10), justify="center")
        self.pc_entry.pack(side="right")
        
        # Mobile Count
        mobile_frame = tk.Frame(settings_frame, bg="#1a1a2e")
        mobile_frame.pack(pady=10, padx=20, fill="x")
        tk.Label(mobile_frame, text="Mobile Searches:", fg="#94a3b8", bg="#1a1a2e",
                font=("Segoe UI", 10)).pack(side="left")
        self.mobile_var = tk.StringVar(value=str(DEFAULT_MOBILE))
        self.mobile_entry = tk.Entry(mobile_frame, textvariable=self.mobile_var, width=8,
                                    font=("Segoe UI", 10), justify="center")
        self.mobile_entry.pack(side="right")
        
        # Footer
        footer = tk.Label(self.root, text="Made with ❤️ by Antigravity", 
                         font=("Segoe UI", 8),
                         fg="#475569", bg="#1a1a2e")
        footer.pack(side="bottom", pady=10)
        
    def set_status(self, text, color="#4ade80"):
        self.status_label.config(text=text, fg=color)
        self.root.update()
        
    def disable_buttons(self):
        self.is_running = True
        for btn in [self.btn_all, self.btn_mobile, self.btn_pc]:
            btn.config(state="disabled")
            
    def enable_buttons(self):
        self.is_running = False
        for btn in [self.btn_all, self.btn_mobile, self.btn_pc]:
            btn.config(state="normal")
            
    def run_farm(self, pc_count, mobile_count):
        """Chạy farm trong thread riêng"""
        def worker():
            self.disable_buttons()
            self.set_status(f"🔄 Đang chạy... (PC: {pc_count}, Mobile: {mobile_count})", "#fbbf24")
            
            try:
                result = subprocess.run(
                    [sys.executable, FARM_SCRIPT,
                     "--pc", str(pc_count),
                     "--mobile", str(mobile_count)],
                    cwd=SCRIPT_DIR,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.set_status("✅ Hoàn thành!", "#4ade80")
                    self.notify("Farm hoàn thành!", "success")
                else:
                    self.set_status("⚠️ Có lỗi xảy ra", "#ef4444")
                    self.notify("Farm gặp lỗi. Xem log để biết chi tiết.", "error")
                    
            except Exception as e:
                self.set_status(f"❌ Lỗi: {str(e)[:30]}...", "#ef4444")
                
            finally:
                self.enable_buttons()
                
        threading.Thread(target=worker, daemon=True).start()
        
    def notify(self, message, msg_type="info"):
        """Gửi notification"""
        try:
            from plyer import notification
            notification.notify(
                title="MS Rewards Farmer",
                message=message,
                app_name="MS Rewards",
                timeout=10
            )
        except:
            pass
            
    def farm_all(self):
        pc = int(self.pc_var.get() or 0)
        mobile = int(self.mobile_var.get() or 0)
        self.run_farm(pc, mobile)
        
    def farm_mobile(self):
        mobile = int(self.mobile_var.get() or 0)
        self.run_farm(0, mobile)
        
    def farm_pc(self):
        pc = int(self.pc_var.get() or 0)
        self.run_farm(pc, 0)
        
    def view_log(self):
        today = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(LOG_DIR, f"farm_log_{today}.log")
        
        if os.path.exists(log_file):
            os.startfile(log_file)
        else:
            messagebox.showinfo("Thông báo", "Chưa có log cho hôm nay.")
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = FarmLauncher()
    app.run()
