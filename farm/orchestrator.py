"""
farm/orchestrator.py - Orchestration logic decoupled from GUI
"""
import time
import random
import os

from farm import (
    setup_driver, safe_driver_quit, is_driver_alive, get_current_points,
    get_points_from_search_page,
    complete_daily_set_and_activities, query_gen,
    simulate_typing, human_scroll, interact_with_results, random_sleep,
    check_and_recover_oom,
    EarlyStopDetector, adaptive_batch, auto_speed_config, log_quota_confidence
)
from farm.points import check_logged_in, get_search_quota
from farm.history import was_farmed_today
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

EDGE_USER_DATA = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data')

class FarmOrchestrator:
    def __init__(self, callbacks):
        """
        callbacks: dictionary of functions to update UI
        {
            'log': func(msg),
            'progress': func(percent_float),
            'status': func(msg),
            'eta': func(msg),
            'points': func(),
            'is_running': func() -> bool
        }
        """
        self.log = callbacks.get('log', print)
        self.set_progress = callbacks.get('progress', lambda x: None)
        self.set_status = callbacks.get('status', lambda x: None)
        self.set_eta = callbacks.get('eta', lambda x: None)
        self.update_points_ui = callbacks.get('points', lambda: None)
        self.check_running = callbacks.get('is_running', lambda: True)
        
        self.speed_configs = {
            "🤖 Auto (Smart)": {'wait': (5, 10), 'post': (3, 6)},
            "🐢 Safe":   {'wait': (10, 18), 'post': (5, 10)},
            "🚶 Medium": {'wait': (5, 10),  'post': (3, 6)},
            "🏃 Fast":   {'wait': (3, 6),   'post': (2, 4)},
            "⚡ Turbo":  {'wait': (2, 4),   'post': (1, 2)}
        }
        self.farm_results = []

    @staticmethod
    def _safe_int(value, default):
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _resolve_profile_context(profile_id, profile_mapping):
        default_path = os.path.join(EDGE_USER_DATA, profile_id)
        profile_entry = profile_mapping.get(profile_id, {})
        if isinstance(profile_entry, dict):
            return {
                "path": profile_entry.get("path", default_path),
                "label": profile_entry.get("label", profile_id),
                "history_id": profile_entry.get("history_id", profile_id),
            }
        if isinstance(profile_entry, str):
            return {"path": profile_entry, "label": profile_id, "history_id": profile_id}
        return {"path": default_path, "label": profile_id, "history_id": profile_id}
        
    def detailed_search(self, driver, count, mode, speed_config, successful_batches=0):
        """Perform searches with adaptive delay. Returns number of actually completed searches."""
        base_url = "https://www.bing.com/"
        wait_min, wait_max = speed_config['wait']
        post_min, post_max = speed_config['post']
        
        if successful_batches >= 3:
            speed_factor = 0.85
            self.log(f"  ⚡ Adaptive: speed boost active (3+ successful batches)")
        elif successful_batches >= 1:
            speed_factor = 0.95
        else:
            speed_factor = 1.0
        
        self.log(f"  → Navigating to Bing...")
        try:
            driver.get(base_url)
            time.sleep(random.uniform(2, 4))
            check_and_recover_oom(driver, f"{mode} initial nav")
        except Exception as e:
            self.log(f"  ❌ Cannot access Bing: {e}")
            return 0
        
        completed = 0
        for i in range(count):
            if not self.check_running():
                self.log(f"  ⏹️ Stopped")
                return completed
            
            try:
                query = query_gen.generate()
                self.log(f"  🔎 [{mode}] {i+1}/{count}: \"{query[:25]}...\"")
                
                try:
                    search_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "q"))
                    )
                except:
                    self.log(f"     ↻ Reloading Bing...")
                    try:
                        driver.get(base_url)
                        time.sleep(2)
                        check_and_recover_oom(driver, f"{mode} reload")
                        search_box = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, "q"))
                        )
                    except Exception as reload_err:
                        err_msg2 = str(reload_err).lower()
                        if any(k in err_msg2 for k in ["httpconnectionpool", "connectionpool", "target closed", "timed out"]):
                            self.log(f"  ❌ Driver died during reload!")
                            return completed
                        raise
                
                search_box.click()
                time.sleep(random.uniform(0.3, 0.6))
                search_box.clear()
                simulate_typing(search_box, query)
                time.sleep(random.uniform(0.3, 0.6))
                search_box.send_keys(Keys.RETURN)
                
                wait_time = max(2, int(random.randint(wait_min, wait_max) * speed_factor))
                self.log(f"     ⏳ Waiting {wait_time}s...")
                time.sleep(wait_time)
                
                check_and_recover_oom(driver, f"{mode} search {i+1}")
                human_scroll(driver)
                interact_with_results(driver)
                post_time = max(1, random.uniform(post_min, post_max) * speed_factor)
                time.sleep(post_time)
                
            except Exception as e:
                err_msg = str(e).lower()
                fatal_keywords = ["refused", "disconnected", "httpconnectionpool",
                                  "connectionpool", "max retries", "target closed",
                                  "session not created", "no such window"]
                if any(k in err_msg for k in fatal_keywords):
                    self.log(f"  ❌ Driver connection lost! (will retry with new driver)")
                    return completed
                
                self.log(f"  ⚠️ Error on search {i+1}: {str(e)[:40]}")
                if not hasattr(self, '_search_retries'): self._search_retries = 0
                self._search_retries += 1
                
                if self._search_retries >= 3:
                    self.log(f"  ❌ Too many errors ({self._search_retries}x). Stopping.")
                    self._search_retries = 0
                    return False
                
                try:
                    driver.get(base_url)
                    time.sleep(5)
                except:
                    self.log(f"  ❌ Cannot recover. Driver needs restart.")
                    return completed
            completed += 1
            self._search_retries = 0
        return completed

    def farm_profiles(self, profiles, config, profile_paths, force_retry=False):
        """
        Main orchestration loop
        config = {pc_count, mobile_count, delay_min, speed_mode, debug_mode, auto_quota}
        force_retry = True: skip was_farmed_today check (for manual retry)
        """
        pc_count = self._safe_int(config.get('pc_count', 30), 30)
        mobile_count = self._safe_int(config.get('mobile_count', 20), 20)
        delay_min = self._safe_int(config.get('delay_min', 5), 5)
        speed_mode = config.get('speed_mode', "🤖 Auto (Smart)")
        debug_mode = config.get('debug_mode', False)
        auto_quota = config.get('auto_quota', True)
        
        speed_config = self.speed_configs.get(speed_mode, self.speed_configs["🤖 Auto (Smart)"])
        self.log(f"⚡ Speed Mode: {speed_mode}")
        
        PROFILE_TIMEOUT = 1500
        total_profiles = len(profiles)
        if total_profiles == 0:
            self.log("⚠️ No profiles selected.")
            self.set_status("No profiles selected")
            self.set_eta("ETA: --:--")
            self.set_progress(0)
            return
        
        self.update_points_ui()
        self.farm_results = []
        
        try:
            from farm.utils import prevent_os_sleep, allow_os_sleep
            prevent_os_sleep()
        except: pass
        
        for i, profile in enumerate(profiles):
            base_progress = (i / total_profiles) * 100
            self.set_progress(base_progress)
            profile_id = profile
            profile_context = self._resolve_profile_context(profile_id, profile_paths)
            profile = profile_context["label"]
            history_profile = profile_context["history_id"]
            profile_path = profile_context["path"]
            
            remaining_profs = total_profiles - i
            eta_seconds = remaining_profs * 15 * 60 
            if speed_mode == "⚡ Turbo": eta_seconds = remaining_profs * 5 * 60
            elif speed_mode == "🏃 Fast": eta_seconds = remaining_profs * 8 * 60
            elif speed_mode == "🐢 Safe": eta_seconds = remaining_profs * 30 * 60
            
            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            self.set_eta(f"ETA: ~{eta_str}")
            
            if not self.check_running():
                self.log("⏹️ Stopped by user")
                break
            
            self.set_status(f"Running: {i+1}/{len(profiles)} - {profile}")
            self.log(f"\n{'='*40}")
            self.log(f"🎯 Starting profile: {profile}")
            
            try:
                query_gen.reset_history()
            except: pass

            try:
                if not force_retry and was_farmed_today(history_profile):
                    self.log(f"⏭️ [{profile}] Đã farm hôm nay. Bỏ qua!")
                    continue
                elif force_retry:
                    self.log(f"🔁 [{profile}] Force retry - bỏ qua kiểm tra lịch sử!")
            except: pass
            
            initial_points = "?"
            starting_points = "?"
            search_phase_start_points = "?"
            final_points = None
            profile_start_time = time.time()
            
            try:
                if i == 0:
                    self.log("📂 Clone mode: farming mà không cần đóng Edge")
                
                self.log(f"[{profile}] Phase 1: PC Searches ({pc_count})")
                
                driver = None
                for attempt in range(2):
                    driver = setup_driver(profile_path, is_mobile=False, headless=not debug_mode)
                    if driver: break
                    self.log(f"⚠️ [{profile}] Driver attempt {attempt+1} failed, retrying...")
                    time.sleep(5)
                
                if driver is None:
                    self.log(f"❌ [{profile}] Failed to create driver! Đóng Edge và thử lại.")
                    continue
                
                try:
                    load_success = False
                    for _ in range(3):
                        try:
                            driver.get("https://rewards.bing.com/")
                            time.sleep(5)
                            load_success = True
                            break
                        except Exception as e:
                            self.log(f"⚠️ [{profile}] Timeout tải Bing Rewards, thử lại: {str(e)[:40]}")
                            try: driver.refresh()
                            except: pass
                            time.sleep(5)
                            
                    if not load_success:
                        raise Exception("Không thể tải trang Bing Rewards ban đầu")
                    
                    if not check_logged_in(driver):
                        self.log(f"❌ [{profile}] Chưa đăng nhập! Bỏ qua profile.")
                        safe_driver_quit(driver)
                        continue
                    
                    initial_points = get_current_points(driver)
                    starting_points = initial_points
                    search_phase_start_points = initial_points
                    self.log(f"[{profile}] Initial Points: {initial_points}")
                    
                    quota = None
                    try:
                        quota = get_search_quota(driver)
                        log_quota_confidence(quota, history_profile)
                    except: pass
                    
                    actual_pc_count = pc_count
                    actual_mobile_count = mobile_count
                    
                    if quota:
                        api_pc = quota.get('pc_remaining_searches', 0)
                        api_mobile = quota.get('mobile_remaining_searches', 0)
                        
                        if auto_quota:
                            actual_pc_count = api_pc
                            actual_mobile_count = api_mobile
                            self.log(f"🤖 [Auto-Quota] Chạy theo số liệu thực tế: PC={actual_pc_count}, Mobile={actual_mobile_count}")
                            if api_pc == 0:
                                self.log(f"✅ [{profile}] PC Search đã đạt max!")
                        else:
                            if api_pc == 0:
                                self.log(f"✅ [{profile}] PC Search đã đạt max!")
                            else:
                                actual_pc_count = max(pc_count, api_pc + 2)
                                self.log(f"📊 [{profile}] Cần ít nhất {api_pc} PC searches")
                                
                            if api_mobile == 0 and quota.get('mobile_max', 0) > 0:
                                self.log(f"✅ [{profile}] Mobile Search đã đạt max!")
                            elif quota.get('mobile_max', 0) > 0:
                                actual_mobile_count = max(mobile_count, api_mobile + 2)
                                self.log(f"📊 [{profile}] Cần ít nhất {api_mobile} Mobile searches")
                    
                    self.log(f"[{profile}] 📋 Phase 1: Daily Set & More Activities...")
                    try:
                        complete_daily_set_and_activities(driver)
                        self.log(f"[{profile}] ✅ Daily activities completed!")
                    except Exception as act_err:
                        self.log(f"[{profile}] ⚠️ Activities error: {str(act_err)[:50]}")
                    
                    try:
                        driver.get("https://rewards.bing.com/")
                        time.sleep(5)
                        post_activity_points = get_current_points(driver)
                        if isinstance(post_activity_points, int) and isinstance(starting_points, int):
                            act_delta = post_activity_points - starting_points
                            if act_delta > 0:
                                self.log(f"📈 [{profile}] Activities earned +{act_delta} pts (Total: {post_activity_points})")
                                search_phase_start_points = post_activity_points
                    except: pass
                    
                    if quota is None or quota.get('inferred'):
                        try:
                            if not is_driver_alive(driver):
                                raise Exception("Driver connection lost during Activities!")
                            self.log(f"🔄 [{profile}] Re-reading quota sau activities...")
                            quota2 = get_search_quota(driver)
                            if quota2: quota = quota2
                        except Exception as e:
                            self.log(f"⚠️ [{profile}] Lỗi đọc quota: {str(e)[:50]}")

                    self._search_retries = 0
                    pc_stopper = EarlyStopDetector(zero_threshold=5, min_samples=5)
                    
                    if quota and quota.get('pc_remaining_searches', 0) == 0:
                        self.log(f"⏭️ [{profile}] PC search đã max. Skip!")
                    elif quota:
                        needed = quota['pc_remaining_searches'] + 6
                        self.log(f"[{profile}] 🔎 Phase 2: PC Search ({needed})")
                        done = 0
                        last_loop_time = time.time()
                        while done < needed and self.check_running():
                            current_time = time.time()
                            if current_time - last_loop_time > 120:
                                profile_start_time += (current_time - last_loop_time)
                                self.log(f"💤 Vừa thức dậy (Sleep {int(current_time - last_loop_time)}s). Đã chỉnh lại Timer!")
                            last_loop_time = current_time
                            
                            prof_progress = base_progress + ((done/needed) * (100/total_profiles) * 0.5)
                            self.set_progress(prof_progress)
                            
                            if time.time() - profile_start_time > PROFILE_TIMEOUT:
                                self.log(f"⏰ [{profile}] Timeout! Done {done}/{needed}")
                                break
                                
                            if not is_driver_alive(driver):
                                self.log(f"🔄 [{profile}] Driver crashed, restarting...")
                                safe_driver_quit(driver)
                                driver = setup_driver(profile_path, is_mobile=False, headless=not debug_mode)
                                if not driver: break
                                try: driver.get("https://www.bing.com/"); time.sleep(3)
                                except: pass

                            batch = adaptive_batch(done, needed, base=3)
                            smart_speed = auto_speed_config(
                                remaining_searches=needed - done,
                                elapsed_seconds=time.time() - profile_start_time,
                                timeout_seconds=PROFILE_TIMEOUT,
                                user_speed=speed_mode
                            )
                            
                            actually_done = self.detailed_search(driver, batch, "PC", smart_speed, done)
                            if actually_done is False:
                                self.log(f"⚠️ [{profile}] PC search aborted after repeated errors.")
                                break
                            done += actually_done
                            self.log(f"  🔎 [{profile}] PC: {done}/{needed} searches done")
                            
                            try:
                                pts_now = get_points_from_search_page(driver)
                                pc_stopper.update(pts_now)
                                if pc_stopper.should_stop():
                                    self.log(f"✅ [{profile}] PC quota đạt thực tế! Dừng sớm ({done}/{needed})")
                                    break
                            except: pass
                    else:
                        self.log(f"[{profile}] 🔎 Phase 2: PC Searches ({pc_count}, no quota API)")
                        remaining_pc = pc_count
                        last_check_points = search_phase_start_points
                        zero_delta = 0
                        last_loop_time = time.time()
                        while remaining_pc > 0 and self.check_running():
                            current_time = time.time()
                            if current_time - last_loop_time > 120:
                                profile_start_time += (current_time - last_loop_time)
                            last_loop_time = current_time
                            
                            if time.time() - profile_start_time > PROFILE_TIMEOUT: break
                            batch = min(2, remaining_pc)
                            actually_done = self.detailed_search(driver, batch, "PC", speed_config, 0)
                            if actually_done is False:
                                self.log(f"⚠️ [{profile}] PC search aborted after repeated errors.")
                                break
                            remaining_pc -= actually_done
                            pts = get_points_from_search_page(driver)
                            if isinstance(pts, int) and isinstance(last_check_points, int):
                                if pts == last_check_points:
                                    zero_delta += 1
                                    if zero_delta >= 6:
                                        self.log(f"🚫 [{profile}] PC limit reached")
                                        break
                                else:
                                    zero_delta = 0
                                last_check_points = pts
                                
                finally:
                    safe_driver_quit(driver)
                
                if not self.check_running():
                    break
                
                time.sleep(10)
                
                profile_start_time = time.time()
                self._search_retries = 0
                if quota and quota.get('mobile_max', 0) == 0:
                    self.log(f"⏭️ [{profile}] Mobile search không khả dụng ở level hiện tại.")
                elif quota and quota.get('mobile_remaining_searches', 0) == 0:
                    self.log(f"⏭️ [{profile}] Mobile search đã max.")
                elif quota:
                    needed = quota['mobile_remaining_searches'] + 6
                    self.log(f"[{profile}] 📱 Phase 3: Mobile Search ({needed})")
                    
                    driver = None
                    for attempt in range(2):
                        driver = setup_driver(profile_path, is_mobile=True, headless=not debug_mode)
                        if driver: break
                        time.sleep(5)
                    
                    if driver:
                        try:
                            driver.get("https://www.bing.com/")
                            time.sleep(3)
                            done = 0
                            mobile_stopper = EarlyStopDetector(zero_threshold=5, min_samples=5)
                            
                            last_loop_time = time.time()
                            while done < needed and self.check_running():
                                current_time = time.time()
                                if current_time - last_loop_time > 120:
                                    profile_start_time += (current_time - last_loop_time)
                                    self.log(f"💤 Vừa thức dậy (Sleep {int(current_time - last_loop_time)}s). Đã chỉnh lại Timer!")
                                last_loop_time = current_time
                                
                                prof_progress = base_progress + 50 + ((done/needed) * (100/total_profiles) * 0.5)
                                self.set_progress(prof_progress)
                                
                                if time.time() - profile_start_time > PROFILE_TIMEOUT: break
                                
                                if not is_driver_alive(driver):
                                    safe_driver_quit(driver)
                                    driver = setup_driver(profile_path, is_mobile=True, headless=not debug_mode)
                                    if not driver: break
                                    try: driver.get("https://www.bing.com/"); time.sleep(3)
                                    except: pass
                                    
                                batch = adaptive_batch(done, needed, base=3)
                                smart_speed = auto_speed_config(needed - done, time.time() - profile_start_time, PROFILE_TIMEOUT, speed_mode)
                                
                                actually_done = self.detailed_search(driver, batch, "MOBILE", smart_speed, done)
                                if actually_done is False:
                                    self.log(f"⚠️ [{profile}] Mobile search aborted after repeated errors.")
                                    break
                                done += actually_done
                                
                                try:
                                    pts_now = get_points_from_search_page(driver)
                                    mobile_stopper.update(pts_now)
                                    if mobile_stopper.should_stop():
                                        self.log(f"✅ [{profile}] Mobile quota đạt thực tế! Dừng sớm.")
                                        break
                                except: pass
                        finally:
                            safe_driver_quit(driver)
                else:
                    self.log(f"[{profile}] 📱 Phase 3: Mobile Searches ({mobile_count}, no quota)")
                    driver = setup_driver(profile_path, is_mobile=True, headless=not debug_mode)
                    if driver:
                        try:
                            driver.get("https://www.bing.com/"); time.sleep(3)
                            remaining = mobile_count
                            last_loop_time = time.time()
                            while remaining > 0 and self.check_running():
                                current_time = time.time()
                                if current_time - last_loop_time > 120:
                                    profile_start_time += (current_time - last_loop_time)
                                last_loop_time = current_time
                                
                                if time.time() - profile_start_time > PROFILE_TIMEOUT: break
                                batch = min(3, remaining)
                                actually_done = self.detailed_search(driver, batch, "MOBILE", speed_config, 0)
                                if actually_done is False:
                                    self.log(f"⚠️ [{profile}] Mobile search aborted after repeated errors.")
                                    break
                                remaining -= actually_done
                        finally:
                            safe_driver_quit(driver)

                driver = None
                try:
                    driver = setup_driver(profile_path, is_mobile=False, headless=not debug_mode)
                    if driver:
                        driver.get("https://rewards.bing.com/")
                        time.sleep(5)
                        final_points = get_current_points(driver)
                except: pass
                finally: safe_driver_quit(driver)

                if isinstance(starting_points, int) and isinstance(final_points, int):
                    delta = final_points - starting_points
                    self.log(f"✅ [{profile}] Done! {initial_points} -> {final_points} (+{delta})")
                    self.farm_results.append(f"{profile}: +{delta} pts ({final_points})")
                    try:
                        from farm.history import log_points
                        log_points(history_profile, starting_points, final_points)
                        self.update_points_ui()
                    except: pass
                elif final_points is not None:
                    self.log(f"✅ [{profile}] Done! Points: {final_points}")
                else:
                    self.log(f"⚠️ [{profile}] Done! Could not read final points.")
                    
            except Exception as e:
                self.log(f"❌ [{profile}] Error: {str(e)[:50]}")
            
            if i < len(profiles) - 1 and self.check_running():
                self.log(f"⏳ Waiting {delay_min} minutes before next profile...")
                for sec in range(delay_min * 60):
                    if not self.check_running(): break
                    time.sleep(1)
        
        self.log(f"\n{'='*40}")
        self.log("🎉 All done!")
        try:
            from farm.history import get_streak_days
            streak = get_streak_days()
            if streak > 0: self.log(f"🔥 Streak: {streak} ngày liên tiếp!")
        except: pass
        
        try:
            from farm.driver import cleanup_clone_profiles
            cleanup_clone_profiles()
        except: pass
        
        try:
            from farm.utils import allow_os_sleep
            allow_os_sleep()
        except: pass
