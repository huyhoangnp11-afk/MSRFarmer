"""
farm/search.py - Search execution and farming logic
"""
import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import PC_SEARCH_COUNT
from .query import query_gen
from .utils import (
    random_sleep, simulate_typing, simulate_reading_interaction,
    human_scroll, human_hover_and_click, take_screenshot,
    check_and_recover_oom
)
from .points import get_points_from_search_page
from .driver import setup_driver, safe_driver_quit, is_driver_alive


def interact_with_results(driver):
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "li.b_algo h2 a, li.b_algo h3 a")
        if not links or len(links) < 2: return
        if random.random() > 0.2: return  # 20% chance (was 40%)

        # Track tabs before clicking
        original_window = driver.current_window_handle
        tabs_before = set(driver.window_handles)

        target_link = random.choice(links[:3])
        logging.info(" -> [DEEP BROWSE] Click vào kết quả tìm kiếm...")
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_link)
        time.sleep(random.uniform(1, 2))
        human_hover_and_click(driver, target_link)
        
        time.sleep(random.uniform(5, 8))
        
        # Check if new tab was opened
        tabs_after = set(driver.window_handles)
        new_tabs = tabs_after - tabs_before
        
        if new_tabs:
            # Close all new tabs and switch back
            for tab in new_tabs:
                try:
                    driver.switch_to.window(tab)
                    time.sleep(1)
                    driver.close()
                except: pass
            driver.switch_to.window(original_window)
            logging.info(" -> Đã đóng tab mới, quay lại trang tìm kiếm.")
        else:
            # Same tab navigation
            simulate_reading_interaction(driver)
            human_scroll(driver)
            
            try:
                sub_links = driver.find_elements(By.TAG_NAME, "a")
                valid_subs = [l for l in sub_links if len(l.text) > 10 and l.is_displayed()]
                if valid_subs and random.random() > 0.3:
                    sub = random.choice(valid_subs)
                    logging.info(f"    -> [DEEP] Click tiếp: {sub.text[:15]}...")
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", sub)
                    time.sleep(1)
                    try: sub.click()
                    except: driver.execute_script("arguments[0].click();", sub)
                    
                    time.sleep(random.uniform(5, 8))
                    
                    # Close new tabs from sub-link clicks too
                    sub_new_tabs = set(driver.window_handles) - tabs_before
                    if sub_new_tabs:
                        for tab in sub_new_tabs:
                            try:
                                driver.switch_to.window(tab)
                                driver.close()
                            except: pass
                        driver.switch_to.window(original_window)
                    else:
                        try:
                            page_title = driver.title
                            if page_title and len(page_title) > 5:
                                clean_topic = page_title.split('-')[0].split('|')[0].strip()
                                new_query = f"more information about {clean_topic}"
                                from .config import query_gen_lock
                                with query_gen_lock:
                                    query_gen.chain_queue.insert(0, new_query)
                                logging.info(f"    [AI LEARNING] Đọc thấy: '{clean_topic}' -> Thêm vào lịch sử tìm kiếm.")
                        except: pass
                        human_scroll(driver)
                        driver.back()
                        time.sleep(2)
            except: pass
            
            driver.back()
            logging.info(" -> Đã quay lại trang tìm kiếm.")
            time.sleep(random.uniform(2, 4))
        
    except:
        pass


def do_one_search(driver, query):
    try:
        # Check for OOM before searching
        check_and_recover_oom(driver, f"before search '{query[:20]}'")
        
        try:
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
        except:
            driver.get("https://www.bing.com/")
            time.sleep(3)
            check_and_recover_oom(driver, "after bing nav")
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )

        search_box.clear()
        simulate_typing(search_box, query)
        time.sleep(0.5)
        search_box.send_keys(Keys.RETURN)
        
        random_sleep(2, 4)
        
        # Check for OOM after search results load
        check_and_recover_oom(driver, f"after search '{query[:20]}'")
        
        human_scroll(driver)
        
    except Exception as e:
        msg = str(e)
        if "disconnected" in msg or "refused" in msg:
            raise Exception("Driver disconnected during search") # Để farm_parallel bắt và retry
        logging.error(f"[SEARCH] Lỗi search '{query}': {msg[:100]}")


def do_one_news_read(driver):
    try:
        if random.random() > 0.7:
            driver.refresh()
            time.sleep(3)

        articles = driver.find_elements(By.CSS_SELECTOR, "a.title, div.news-card a")
        if not articles:
            return False

        idx = random.randint(0, min(len(articles)-1, 15))
        target = articles[idx]
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target)
        time.sleep(1)
        
        url = target.get_attribute("href")
        if url:
            logging.info(f"   [NEWS] Đọc: {target.text[:20]}...")
            driver.get(url)
            random_sleep(3, 5)
            simulate_reading_interaction(driver)
            human_scroll(driver)
            driver.back()
            time.sleep(2)
            return True
    except:
        return False
    return False


def perform_searches(driver, count, mode="PC"):
    logging.info(f"[{mode}] Bắt đầu thực hiện {count} lần tìm kiếm...")
    base_url = "https://www.bing.com/"
    
    from .decision import EarlyStopDetector
    early_stop = EarlyStopDetector(zero_threshold=5, min_samples=3)
    
    try:
        driver.get(base_url)
        random_sleep(3, 5)
    except Exception as e:
        logging.error(f"[{mode}] Không thể truy cập Bing: {e}")
        take_screenshot(driver, "bing_access_error")
        return

    for i in range(count):
        try:
            query = query_gen.generate()
            logging.info(f"[{mode} {i+1}/{count}] Searching: {query}")
            
            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
            except:
                driver.get(base_url)
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )

            search_box.click()
            time.sleep(random.uniform(0.5, 1.0))
            search_box.clear()
            simulate_typing(search_box, query)
            time.sleep(random.uniform(0.5, 1.0))
            search_box.send_keys(Keys.RETURN)
            
            random_sleep(10, 18)
            human_scroll(driver)
            interact_with_results(driver)
            random_sleep(5, 10)
            
            # Check point realtime để smart stop
            current_pts = get_points_from_search_page(driver)
            if current_pts and current_pts > 0:
                if early_stop.update(current_pts) and early_stop.should_stop():
                    break
            
        except Exception as e:
            msg = str(e)
            if "refused" in msg or "Max retries exceeded" in msg or "disconnected" in msg or "not created" in msg:
                logging.error(f"[{mode}] ❌ MẤT KẾT NỐI VỚI DRIVER ({msg[:50]}...). Cần khởi động lại.")
                raise Exception("Driver disconnected") # Đẩy lỗi ra ngoài để farm_parallel tự phục hồi
                
            logging.error(f"[{mode}] Lỗi trong lần tìm kiếm {i+1}: {msg[:100]}")
            take_screenshot(driver, f"search_error_{i+1}")
            try:
                driver.get(base_url)
                random_sleep(5, 10)
            except: 
                logging.error(f"[{mode}] Không thể truy cập Bing sau lỗi. Abort retry cục bộ.")
                raise Exception("Cannot recover bing tab")


def perform_mobile_news_reads(driver, count=10):
    """Đọc báo trên Mobile (Bing News)"""
    logging.info(f"--- [MOBILE READ] Bắt đầu đọc {count} bài báo ---")
    try:
        driver.get("https://www.bing.com/news")
        random_sleep(3, 5)
        
        selectors = ["a.title", ".news-card a", "a.news_title", ".b_algo a"]
        articles = []
        for sel in selectors:
            try:
                found = driver.find_elements(By.CSS_SELECTOR, sel)
                if found:
                    articles.extend(found)
            except: pass
            
        valid_links = []
        seen_urls = set()
        for a in articles:
            try:
                href = a.get_attribute("href")
                if href and "bing.com/news" not in href and href not in seen_urls:
                    valid_links.append(href)
                    seen_urls.add(href)
            except: pass
            
        logging.info(f"--- [MOBILE READ] Tìm thấy {len(valid_links)} bài báo hợp lệ ---")
        
        read_count = 0
        for i, link in enumerate(valid_links):
            if read_count >= count:
                break
                
            logging.info(f"[MOBILE READ {read_count+1}/{count}] Đang đọc: {link[:50]}...")
            try:
                driver.get(link)
                random_sleep(3, 5)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                random_sleep(2, 4)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                random_sleep(2, 4)
                read_count += 1
            except Exception as e:
                logging.error(f"Lỗi khi đọc báo: {e}")
                
        logging.info(f"--- [MOBILE READ] Hoàn thành {read_count}/{count} bài ---")
        
    except Exception as e:
        logging.error(f"Lỗi Mobile News: {e}")


def farm_parallel(driver, profile_path=None, pc_count=PC_SEARCH_COUNT):
    """Farm PC searches in single-tab mode (RAM-friendly)."""
    logging.info("\n--- CHẾ ĐỘ ĐƠN NHIỆM (TIẾT KIỆM RAM) ---")
    
    MAX_RESTART_ATTEMPTS = 3
    restart_count = 0
    searches_done = 0
    
    if pc_count <= 0:
        logging.info("   [INFO] PC Count = 0 -> Bỏ qua PC Farming.")
        return driver
    
    total_searches = pc_count
    
    while restart_count < MAX_RESTART_ATTEMPTS:
        try:
            driver.get("https://www.bing.com/")
            time.sleep(3)
            
            last_points = get_points_from_search_page(driver)
            no_gain_count = 0
            
            logging.info(f"-> Single-tab search: Max {total_searches} searches")
            
            while searches_done < total_searches:
                if not is_driver_alive(driver):
                    raise Exception("Driver crashed")
                
                q = query_gen.generate()
                logging.info(f"[SEARCH] {searches_done+1}/{total_searches}: {q}")
                
                do_one_search(driver, q)
                searches_done += 1
                
                # Check points every search (inline on results page)
                current_pts = get_points_from_search_page(driver)
                if current_pts is not None and last_points is not None:
                    if current_pts > last_points:
                        diff = current_pts - last_points
                        logging.info(f"   📈 +{diff} điểm (Total: {current_pts})")
                        last_points = current_pts
                        no_gain_count = 0
                    else:
                        no_gain_count += 1
                        if no_gain_count % 4 == 0:
                            logging.warning(f"   ⚠️ Điểm không tăng sau {no_gain_count} searches ({current_pts})")
                        
                    if no_gain_count >= 10:  # Nâng từ 6 lên 10 để chống stop sớm do Web load điểm chậm
                        logging.info("-> ĐÃ ĐẠT GIỚI HẠN ĐIỂM SEARCH (không tăng sau 10 lần liên tục). DỪNG.")
                        break
                elif current_pts is not None:
                    last_points = current_pts
                    logging.info(f"   📊 Điểm hiện tại: {current_pts}")
                
                interact_with_results(driver)
                random_sleep(1, 3)
                
                # Coffee break every 12-15 searches
                if searches_done > 0 and searches_done % random.randint(20, 25) == 0:
                    break_time = random.randint(20, 40)
                    logging.info(f"\n[COFFEE BREAK] Nghỉ {break_time} giây...")
                    time.sleep(break_time)
                    logging.info("-> Quay lại!\n")
            
            # Quick news reads in same tab (5 articles)
            logging.info("-> Đọc tin tức (cùng tab)...")
            try:
                driver.get("https://www.bing.com/news")
                time.sleep(3)
                for i in range(2):  # Reduced from 5
                    if do_one_news_read(driver):
                        logging.info(f"   [NEWS] Đọc bài {i+1}/5")
                    else:
                        break
            except Exception:
                pass
            
            logging.info("--- HOÀN THÀNH SEARCH + NEWS ---")
            return driver
            
        except Exception as e:
            restart_count += 1
            logging.error(f"Lỗi Critical (lần {restart_count}/{MAX_RESTART_ATTEMPTS}): {e}")
            
            if restart_count >= MAX_RESTART_ATTEMPTS:
                logging.error("Đã hết số lần thử. Dừng farm.")
                return driver
            
            logging.warning(f"-> Sẽ khởi động lại Driver sau 10 giây...")
            safe_driver_quit(driver)
            time.sleep(10)
            
            if profile_path:
                driver = setup_driver(profile_path, is_mobile=False, headless=True)
                if driver:
                    logging.info(f"[RECOVERY] Driver đã restart. Tiếp tục từ search #{searches_done + 1}")
                else:
                    logging.error("[RECOVERY] Không thể restart driver.")
                    return None
            else:
                logging.error("[RECOVERY] Không có profile_path, không thể restart.")
                return driver
    
    return driver

