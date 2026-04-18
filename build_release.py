import os
import sys
import shutil
import zipfile

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR_NAME = "MSR_Farmer_Release"
RELEASE_DIR_PATH = os.path.join(BASE_DIR, RELEASE_DIR_NAME)
ZIP_FILE_PATH = os.path.join(BASE_DIR, f"{RELEASE_DIR_NAME}.zip")

# Danh sách cho phép copy (Whitelist) - Chỉ định các file có đuôi cụ thể hoặc tên chính xác
ALLOWED_EXTENSIONS = {'.py', '.pyw', '.bat', '.ps1', '.vbs', '.ico', '.png', '.md', '.txt', '.example'}
# Những thư mục/file TUYỆT ĐỐI BỎ QUA (Blacklist)
EXCLUDED_NAMES = {
    ".venv", ".git", ".gitnexus", ".vscode", "__pycache__", 
    "logs", "profiles", "Farming_Profile", ".selenium", "zalo_agent",
    "points_history.json", "tray_config.json", "farm_task.xml",
    "multi_profile.log", "config.json", "build_release.py"
}

def is_allowed(filename):
    if filename in EXCLUDED_NAMES:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS

def build():
    print(f"[*] Starting standard distribution build at: {RELEASE_DIR_PATH}")
    
    if os.path.exists(RELEASE_DIR_PATH):
        shutil.rmtree(RELEASE_DIR_PATH)
    os.makedirs(RELEASE_DIR_PATH)
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_NAMES and not d.startswith('.')]
        
        if RELEASE_DIR_NAME in root:
            continue
            
        rel_path = os.path.relpath(root, BASE_DIR)
        dest_dir = os.path.join(RELEASE_DIR_PATH, rel_path) if rel_path != '.' else RELEASE_DIR_PATH
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        for f in files:
            if is_allowed(f):
                src_file = os.path.join(root, f)
                dest_file = os.path.join(dest_dir, f)
                shutil.copy2(src_file, dest_file)
    
    os.makedirs(os.path.join(RELEASE_DIR_PATH, "logs"), exist_ok=True)
    os.makedirs(os.path.join(RELEASE_DIR_PATH, "profiles"), exist_ok=True)
    
    with open(os.path.join(RELEASE_DIR_PATH, "logs", ".gitkeep"), "w") as f: f.write("")
    with open(os.path.join(RELEASE_DIR_PATH, "profiles", ".gitkeep"), "w") as f: f.write("")

    req_content = "selenium>=4.0.0\\npystray\\nPillow\\n"
    with open(os.path.join(RELEASE_DIR_PATH, "requirements.txt"), "w") as f:
        f.write(req_content)
        
    readme_content = (
        "=========================================\\n"
        "MICROSOFT REWARDS FARMER - AUTO TOOL\\n"
        "=========================================\\n\\n"
        "HƯỚNG DẪN CÀI ĐẶT DÀNH CHO NGƯỜI MỚI:\\n\\n"
        "BƯỚC 1: Cài đặt Python\\n"
        "- Tải và Cài đặt Python (phiên bản 3.10 trở lên) tại python.org\\n"
        "- LƯU Ý QUAN TRỌNG: Lúc cài đặt tích vào ô 'Add Python to PATH' ở dòng dưới cùng.\\n\\n"
        "BƯỚC 2: Cài thư viện yêu cầu\\n"
        "- Mở Terminal / CMD tại thư mục này lên.\\n"
        "- Gõ lệnh: pip install -r requirements.txt\\n"
        "- Ấn Enter và chờ nó tải xong.\\n\\n"
        "BƯỚC 3: Khởi động Tool\\n"
        "- Nhấp đúp chuột vào file: MSR_Smart_Launcher.py để kích hoạt Bảng Điều Khiển Giao Diện Ẩn.\\n"
        "- Hoặc chạy file: Setup_Run_On_Startup.bat nếu bạn muốn tự chạy ngầm cùng Windows.\\n"
    )
    with open(os.path.join(RELEASE_DIR_PATH, "README_INSTALL.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    print(f"[*] Compressing to ZIP...")
    zipF = zipfile.ZipFile(ZIP_FILE_PATH, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(RELEASE_DIR_PATH):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, RELEASE_DIR_PATH)
            zipF.write(filepath, arcname)
    zipF.close()
    
    print(f"[+] SUCCESS! Package created at: {ZIP_FILE_PATH}")
    shutil.rmtree(RELEASE_DIR_PATH)

if __name__ == "__main__":
    build()
