"""
farm/driver.py - Driver setup, clone profile, crash recovery
"""
import os
import time
import logging
import shutil
import tempfile
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from .config import PROFILE_DIRECTORY, DRIVER_RETRY_ATTEMPTS, DRIVER_RETRY_DELAY
from .utils import apply_mobile_emulation


def _install_driver_with_retry():
    """Retry wrapper cho EdgeChromiumDriverManager"""
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    last_error = None
    for attempt in range(DRIVER_RETRY_ATTEMPTS):
        try:
            logging.info(f"Đang tải EdgeDriver (lần {attempt + 1}/{DRIVER_RETRY_ATTEMPTS})...")
            return EdgeChromiumDriverManager().install()
        except Exception as e:
            last_error = e
            logging.warning(f"Lần {attempt + 1} thất bại: {e}")
            if attempt < DRIVER_RETRY_ATTEMPTS - 1:
                time.sleep(DRIVER_RETRY_DELAY)
    raise last_error


def get_edge_version():
    """Auto-detect installed Edge version from registry."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                            r"Software\Microsoft\Edge\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return version
    except:
        return "133.0.0.0"  # Fallback


def cleanup_automation_processes():
    """Kill EdgeDriver and hidden Edge automation processes, but keep visible windows alive."""
    import subprocess
    try:
        subprocess.run(['taskkill', '/f', '/im', 'msedgedriver.exe'],
                       capture_output=True, timeout=5)
        time.sleep(1)

        workspace_profiles = os.path.normpath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
        ).lower()
        command = (
            f"$workspaceProfiles = '{workspace_profiles}'; "
            "$cloneMarker = 'msr_clone_'; "
            "$reservedMarker = 'zalo_web_agent'; "
            "Get-CimInstance Win32_Process -Filter \"name = 'msedge.exe'\" -ErrorAction SilentlyContinue | "
            "Where-Object { "
            "  $_.CommandLine -and ("
            "    $_.CommandLine.ToLower().Contains($cloneMarker) -or "
            "    ("
            "      $_.CommandLine.ToLower().Contains($workspaceProfiles) -and "
            "      $_.CommandLine.ToLower().Contains('--headless') -and "
            "      -not $_.CommandLine.ToLower().Contains($reservedMarker)"
            "    )"
            "  )"
            "} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ['powershell', '-NoProfile', '-Command', command],
            capture_output=True, timeout=10
        )
        time.sleep(2)
        logging.info("[CLONE] Cleaned up zombie Edge processes")
    except Exception as e:
        logging.debug(f"[CLONE] Cleanup note: {e}")


def _kill_zombie_edge():
    """Backward-compatible alias for automation cleanup."""
    cleanup_automation_processes()


def clone_edge_profile(profile_path):
    """Clone essential Edge profile files to temp folder with proper User Data structure."""
    profile_name = os.path.basename(profile_path)
    base_clone_dir = os.path.join(tempfile.gettempdir(), f"MSR_Clone_{profile_name.replace(' ', '_')}")
    
    # Clean old clone first to avoid stale data
    if os.path.exists(base_clone_dir):
        shutil.rmtree(base_clone_dir, ignore_errors=True)
    
    dest_profile_dir = os.path.join(base_clone_dir, profile_name)
    
    # Critical files that MUST be copied for login to work
    critical_files = ['Cookies', 'Login Data', 'Login Data For Account', 'Web Data']
    # Journal and preference files - nice to have
    extra_files = [
        'Cookies-journal', 'Login Data-journal',
        'Login Data For Account-journal', 'Web Data-journal',
        'Preferences', 'Secure Preferences',
    ]
    # Newer Edge Network subfolder
    network_files = ['Network/Cookies', 'Network/Cookies-journal']
    
    try:
        os.makedirs(dest_profile_dir, exist_ok=True)
        os.makedirs(os.path.join(dest_profile_dir, 'Network'), exist_ok=True)
        
        all_files = critical_files + extra_files + network_files
        copied = 0
        failed_critical = []
        
        # First attempt
        for f in all_files:
            src = os.path.normpath(os.path.join(profile_path, f))
            dest = os.path.normpath(os.path.join(dest_profile_dir, f))
            if not os.path.exists(src):
                continue
            try:
                shutil.copy2(src, dest)
                copied += 1
            except PermissionError:
                if os.path.basename(f) in [os.path.basename(c) for c in critical_files]:
                    failed_critical.append(f)
            except Exception:
                pass
        
        # If critical files failed, kill zombies and retry
        if failed_critical:
            logging.info(f"[CLONE] Critical files locked, killing zombie Edge processes...")
            _kill_zombie_edge()
            
            for f in failed_critical[:]:
                src = os.path.normpath(os.path.join(profile_path, f))
                dest = os.path.normpath(os.path.join(dest_profile_dir, f))
                try:
                    shutil.copy2(src, dest)
                    copied += 1
                    failed_critical.remove(f)
                except Exception:
                    pass
        
        # Copy Local State
        local_state_src = os.path.join(os.path.dirname(profile_path), 'Local State')
        if os.path.exists(local_state_src):
            try:
                shutil.copy2(local_state_src, os.path.join(base_clone_dir, 'Local State'))
            except Exception:
                pass
        
        if failed_critical:
            logging.error(f"[CLONE] CRITICAL files locked for '{profile_name}': {[os.path.basename(f) for f in failed_critical]}")
            logging.error(f"[CLONE] -> Có vẻ bạn đang mở Edge với profile này. Vui lòng đóng Edge để Tool farm được!")
            # Trả về None ngay, không cố đi tiếp gây stacktrace
            return None, None
        
        logging.info(f"[CLONE] Profile '{profile_name}' cloned OK ({copied} files)")
        return base_clone_dir, profile_name
    except Exception as e:
        logging.error(f"[CLONE] Failed to clone profile: {e}")
        return None, None


def setup_driver(profile_path, is_mobile=False, headless=True):
    options = Options()
    
    # Auto-detect Edge version for UA
    edge_version = get_edge_version()
    
    # Auto-detect Edge User Data profiles vs custom profiles
    edge_user_data_marker = os.path.join('Microsoft', 'Edge', 'User Data')
    if edge_user_data_marker in profile_path:
        base_dir, prof_name = clone_edge_profile(profile_path)
        if base_dir and prof_name:
            options.add_argument(f"user-data-dir={base_dir}")
            options.add_argument(f"profile-directory={prof_name}")
        else:
            # Nếu clone thất bại hoàn toàn (do user đang dùng Edge)
            logging.error("Lỗi: Không thể clone Profile. Dừng khởi tạo Driver để tránh corrupt data.")
            return None
    else:
        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument(f"profile-directory={PROFILE_DIRECTORY}")
    
    if headless:
        options.add_argument("--headless") 
        options.page_load_strategy = 'eager' # Tăng tốc x3 cho headless mode
    
    # === ANTI-DETECTION ===
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--mute-audio")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-webrtc")
    options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
    options.add_argument("--disable-reading-from-canvas")
    options.add_argument("--disable-3d-apis")
    
    # === RAM & RESOURCE OPTIMIZATION (Low-spec friendly) ===
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-features=CalculateNativeWinOcclusion") # Chống Crash/Died driver khi bị Minimized
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    
    # === AGGRESSIVE RAM SAVING ===
    options.add_argument("--renderer-process-limit=1")         # 1 renderer only
    options.add_argument("--js-flags=--max-old-space-size=64") # V8 heap 64MB (was 128)
    options.add_argument("--disable-software-rasterizer")      # No software rendering
    options.add_argument("--disable-smooth-scrolling")         # Less animation
    options.add_argument("--disable-logging")                  # Less I/O
    options.add_argument("--disable-breakpad")                 # No crash reporter
    options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees,AudioServiceOutOfProcess,MediaRouter")
    options.add_argument("--disable-shared-workers")           # No shared workers
    options.add_argument("--disable-domain-reliability")       # No telemetry
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--aggressive-cache-discard")         # Free cache aggressively
    options.add_argument("--memory-pressure-off")              # Don't preload
    options.add_argument("--process-per-site")                 # Share renderers per-site (stable RAM save)
    options.add_argument("--window-size=800,600" if not is_mobile else "--window-size=412,915")
    
    # Block images/fonts/media in headless to save RAM & bandwidth
    if headless:
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "disk-cache-size": 1,
        }
        options.add_experimental_option("prefs", prefs)
    
    if is_mobile:
        mobile_ua = f"Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{edge_version} Mobile Safari/537.36 EdgA/{edge_version}"
        options.add_argument(f"user-agent={mobile_ua}")
    else:
        options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{edge_version} Safari/537.36 Edg/{edge_version}")

    options.add_argument("--disable-dev-shm-usage") 
    options.add_argument("--remote-debugging-port=0")

    driver = None
    try:
        logging.info("Đang khởi tạo EdgeDriver (Sử dụng Selenium Manager tự động)...")
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)   # 30s: tránh treo 8 phút như trong log
        driver.set_script_timeout(30)
            
    except Exception as e:
        logging.error(f"Lỗi khởi tạo Driver (Headless: {headless}): {e}")
        
        if headless:
            logging.warning("⚠️ HEADLESS CRASH! Thử VISIBLE mode...")
            try:
                options.arguments.remove("--headless")
            except: pass
            try:
                logging.info("-> Chuyển sang Visible Mode...")
                return setup_driver(profile_path, is_mobile, headless=False)
            except Exception as e_vis:
                 logging.error(f"Fallback Visible thất bại: {e_vis}")

        try:
             logging.info("Thử tải driver bằng Manager (Fallback cuối)...")
             from webdriver_manager.microsoft import EdgeChromiumDriverManager
             service = Service(EdgeChromiumDriverManager().install())
             driver = webdriver.Edge(service=service, options=options)
        except Exception as e2:
             logging.error(f"Fallback thất bại: {e2}")
             return None

    if not driver:
        return None
    
    # === CDP ANTI-DETECT SCRIPTS ===
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'vi'] });
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """
    })
    
    # === CDP NETWORK RESOURCE BLOCKING (saves RAM + bandwidth) ===
    if headless:
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setBlockedURLs", {
                "urls": [
                    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.svg", "*.ico",
                    "*.woff", "*.woff2", "*.ttf", "*.eot",
                    "*.mp4", "*.mp3", "*.webm", "*.ogg",
                    "*google-analytics*", "*googletagmanager*", "*facebook.net*",
                    "*doubleclick*", "*adsense*",
                ]
            })
        except Exception:
            pass  # Some driver versions don't support this
    
    if is_mobile:
        apply_mobile_emulation(driver)
    
    return driver


@contextmanager
def get_driver(profile_path, is_mobile=False, headless=True):
    """Context manager để đảm bảo driver.quit()"""
    driver = setup_driver(profile_path, is_mobile, headless)
    try:
        yield driver
    finally:
        if driver:
            try:
                driver.quit()
                logging.info("Driver đã được đóng sạch.")
            except Exception as e:
                logging.warning(f"Lỗi khi đóng driver: {e}")


def is_driver_alive(driver):
    """Kiểm tra driver còn sống không"""
    try:
        driver.current_url
        return True
    except:
        return False


def safe_driver_quit(driver):
    """Đóng driver an toàn"""
    if driver:
        try:
            driver.quit()
        except:
            pass


def cleanup_clone_profiles():
    """Remove temporary cloned profile files."""
    temp_dir = tempfile.gettempdir()
    try:
        count = 0
        for item in os.listdir(temp_dir):
            if item.startswith("MSR_Clone_") or item == "MSRewards_Clone": # including old ones
                clone_path = os.path.join(temp_dir, item)
                if os.path.isdir(clone_path):
                    shutil.rmtree(clone_path, ignore_errors=True)
                    count += 1
        if count > 0:
            logging.info(f"[CLEANUP] Removed {count} temp clone folder(s).")
    except Exception as e:
        logging.warning(f"[CLEANUP] Failed to remove temp files: {e}")

