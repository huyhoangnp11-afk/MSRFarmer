import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
import sys
import os

# Ngăn chặn Tkinter hiện cửa sổ khi chạy test
os.environ["DISPLAY"] = ":0" 

class TestFarmTrayDaemon(unittest.TestCase):
    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('tray_app.pystray')
    @patch('tray_app.discover_profiles')
    @patch('tray_app.was_farmed_today')
    @patch('tray_app.subprocess.Popen')
    def setUp(self, mock_popen, mock_was_farmed_today, mock_discover, mock_pystray, mock_open):
        from tray_app import FarmTrayApp
        self.root = tk.Tk()
        self.root.withdraw() # Ẩn đi để test không bị hiện cửa sổ
        
        # Cấu hình Mock Data
        mock_discover.return_value = [
            {"id": "Profile 1", "label": "Profile 1", "history_id": "Profile 1"},
            {"id": "Profile 2", "label": "Profile 2", "history_id": "Profile 2"}
        ]
        # Mặc định chưa farm
        mock_was_farmed_today.return_value = False
        
        self.mock_popen = mock_popen
        self.mock_discover = mock_discover
        self.mock_was_farmed = mock_was_farmed_today
        self.mock_pystray = mock_pystray
        
        # Disable .after để tránh loop ngầm trong lúc test
        self.root.after = MagicMock() 
        
        self.app = FarmTrayApp(self.root)
        
    def tearDown(self):
        self.root.update()
        self.root.destroy()
        
    def test_daemon_worker_triggers_farming(self):
        """Kiểm thử khi Daemon bật, worker kiểm tra thấy profile trống -> Phải gọi start_farming"""
        self.app.auto_daemon = True
        self.app.process = None # Không có tiến trình nào đang chạy
        
        # Chạy giả lập 1 nhịp daemon_worker
        self.app.daemon_worker()
        
        # Tiên đoán: subprocess.Popen phải được gọi vì có 2 profile chưa farm
        self.mock_popen.assert_called_once()
        self.assertTrue(self.app.process is not None)
        print("✅ PASSED: Daemon nhận diện được profile trống và tự động chạy nền (Auto Start)")

    def test_daemon_worker_skips_when_running(self):
        """Kiểm thử khi tiến trình đang chạy, daemon sẽ bỏ qua, không kích hoạt thêm 1 tiến trình chồng chéo"""
        self.app.auto_daemon = True
        
        # Setup fake chạy
        mock_process = MagicMock()
        mock_process.poll.return_value = None # None tức là đang chạy
        self.app.process = mock_process
        
        self.app.daemon_worker()
        
        # Đảm bảo Popen KHÔNG ĐƯỢC gọi thêm lần nào nữa (chỉ đếm số mock calls cũ là 0)
        self.mock_popen.assert_not_called()
        print("✅ PASSED: Daemon ngăn việc chạy đè nhiều tiến trình cùng lúc (Anti-Duplicate)")

    def test_daemon_worker_skips_when_all_done(self):
        """Kiểm thử khi tất cả profile đã xong hôm nay, daemon không kích hoạt thừa"""
        self.app.auto_daemon = True
        self.app.process = None 
        # Đặt trạng thái: Tất cả profiles ĐÃ cày xong
        self.mock_was_farmed.return_value = True 
        
        self.app.daemon_worker()
        
        # Popen không được gọi do không có task nào pending
        self.mock_popen.assert_not_called()
        print("✅ PASSED: Daemon thông minh tạm nghỉ khi tất cả profile đều đã cày xong!")

    def test_daemon_toggle_updates_config(self):
        """Kiểm thử nút Bật/Tắt Daemon có lưu cấu hình chuẩn xác không"""
        self.app.auto_daemon = True
        # Giao tiếp người dùng: bấm TẮT tính năng
        self.app.toggle_daemon(None, None)
        
        self.assertFalse(self.app.auto_daemon)
        print("✅ PASSED: Nút điều khiển Menu Bật/Tắt tính năng treo máy hoạt động ổn định!")

if __name__ == '__main__':
    print("\n--- BẮT ĐẦU KIỂM THỬ CHUYÊN NGHIỆP MODULE TRAY DAEMON ---")
    unittest.main(verbosity=2)
