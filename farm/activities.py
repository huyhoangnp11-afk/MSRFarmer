"""
farm/activities.py - Daily set and more activities completion
Supports BOTH old UI (mee-rewards-*) and new UI (accordion cards).
"""
import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import random_sleep, human_scroll, take_screenshot, check_and_recover_oom
from .ota import get_live_ota_config



def _is_new_ui(driver):
    """Detect if the dashboard is using the new accordion-based UI."""
    # New UI has accordion buttons with aria-labels like "Daily set", "Your activity"
    new_ui_indicators = [
        "button[aria-label='Daily set']",
        "button[aria-label='Your activity']",
        "button[aria-label='Achievements']",
    ]
    for selector in new_ui_indicators:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logging.info("[ACTIVITIES] Phát hiện UI MỚI (accordion-based)")
                return True
        except:
            pass
    
    # Also check for "See more tasks" text which is unique to new UI
    try:
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'See more tasks')]")
        if elements:
            logging.info("[ACTIVITIES] Phát hiện UI MỚI (See more tasks)")
            return True
    except:
        pass
    
    logging.info("[ACTIVITIES] Sử dụng UI CŨ (mee-rewards)")
    return False


def _expand_new_ui_sections(driver):
    """Expand all accordion sections in the new UI."""
    # Try multiple possible section names (UI changes labels over time)
    sections = [
        "Daily set", "Your activity", "Achievements",
        "Your progress", "More activities", "More promotions",
        "Keep earning",
    ]
    expanded = 0
    
    for section_name in sections:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, f"button[aria-label='{section_name}']")
            # Check if already expanded
            is_expanded = btn.get_attribute("aria-expanded")
            if is_expanded == "false" or is_expanded is None:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(random.uniform(1, 2))
                expanded += 1
                logging.info(f"   [NEW UI] Expanded: {section_name}")
        except:
            pass
    
    # Fallback: find ALL buttons with aria-expanded="false" and expand them
    if expanded == 0:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-expanded='false']")
            for btn in buttons:
                try:
                    label = btn.get_attribute("aria-label") or btn.text
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(random.uniform(1, 2))
                    expanded += 1
                    logging.info(f"   [NEW UI] Expanded (fallback): {label}")
                except:
                    pass
        except:
            pass
    
    # Also click "See more tasks" if visible
    try:
        see_more = driver.find_elements(By.XPATH, "//*[contains(text(), 'See more tasks')]")
        for btn in see_more:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                logging.info("   [NEW UI] Clicked 'See more tasks'")
                break
    except:
        pass
    
    return expanded


def _get_new_ui_task_cards(driver):
    """Get all task cards from the new UI after expanding sections."""
    cards = []
    seen_texts = set()
    
    import re as _re
    _xofx_pat = _re.compile(r'(\d+)/(\d+)')

    def _is_progress_complete(text: str) -> bool:
        """Check if progress text shows X/X = fully completed."""
        for num, denom in _xofx_pat.findall(text):
            if num == denom and int(num) > 0:
                return True
        return False

    def _should_skip_element(el):
        """Check if element is a progress tracking button or already completed."""
        try:
            tag = el.tag_name.lower()
            text = (el.text or "").lower()
            
            # Skip dashboard nav links
            href = (el.get_attribute("href") or "").lower()
            if "dashboard" in href:
                return True
                
            # Skip buttons that are just tracking progress (e.g., Progress modals)
            progress_keywords = ["search:", "activity:", "check-in:", "how to activate", "check in:"]
            if tag == 'button' and any(kw in text for kw in progress_keywords):
                return True
                
            # Skip if it shows fully completed X/X 
            if _is_progress_complete(text):
                return True
                
            # Or if it shows completion icons
            if "\u2713" in text or "completed" in text:
                return True
                
        except:
            pass
        return False

    # Tải bộ từ điển OTA Sống 
    ota_config = get_live_ota_config()
    task_selectors = ota_config.get("selectors", [])
    task_keywords = ota_config.get("keywords", [])

    # The New UI Strategy: Find all <a> tags that contain specific Rewards URL signatures
    # A task card is usually an <a> tag pointing to a specific search query or redirect
    try:
        # Common patterns in task URLs
        combined_selector = ", ".join(task_selectors)
        all_links = driver.find_elements(By.CSS_SELECTOR, combined_selector)
        
        for el in all_links:
            if _should_skip_element(el):
                continue
                
            # Extract clean text for deduplication
            try:
                # Get only the first line or a substring to avoid matching descriptions
                raw_text = (el.text or "").strip()
                if not raw_text or len(raw_text) < 3:
                    continue
                # Use the first 50 chars of the first line as a fingerprint
                text_fingerprint = raw_text.split('\n')[0][:50]
                
                if text_fingerprint not in seen_texts:
                    seen_texts.add(text_fingerprint)
                    cards.append(el)
                    logging.info(f"   [CARDS] Found Task: {text_fingerprint}")
            except:
                pass
    except Exception as e:
        logging.warning(f"[CARDS] Lỗi khi quét link URL: {e}")

    # Fallback 2: Nhận diện bằng từ khóa (Keyword-based) hoặc điểm số (+5, +10)
    # Lấy TẤT CẢ các thẻ <a> trên trang và bóc tách nội dung của chúng
    try:
        all_a_tags = driver.find_elements(By.TAG_NAME, "a")
        
        for el in all_a_tags:
            if _should_skip_element(el):
                continue
                
            try:
                raw_text = (el.text or "").strip()
                text_lower = raw_text.lower()
                
                # CÁI QUAN TRỌNG: Kiểm tra xem thẻ <a> này có chứa TỪ KHÓA NHIỆM VỤ hay không
                has_keyword = any(kw in text_lower for kw in task_keywords)
                
                if has_keyword and len(raw_text) > 3:
                    text_fingerprint = raw_text.split('\n')[0][:50]
                    if text_fingerprint not in seen_texts:
                        seen_texts.add(text_fingerprint)
                        cards.append(el)
                        logging.info(f"   [CARDS] Found by Keyword: {text_fingerprint}")
            except:
                pass
    except Exception as e:
        logging.warning(f"[CARDS] Lỗi khi quét từ khóa: {e}")

    logging.info(f"[CARDS] Total task cards found: {len(cards)}")
    return cards


def _is_card_completed_new_ui(card):
    """Check if a new UI card is already completed."""
    import re
    try:
        card_html = card.get_attribute("outerHTML") or ""
        card_text = (card.text or "").lower()
        
        # 1. Check HTML for checkmark/completion icons
        completed_indicators = ["\u2713", "check", "completed", "Completed", "SkypeCircleCheck"]
        for indicator in completed_indicators:
            if indicator in card_html:
                return True
        
        # 2. Check aria attributes
        aria_label = card.get_attribute("aria-label") or ""
        if "completed" in aria_label.lower() or "done" in aria_label.lower():
            return True
        
        # 3. Check progress X/X patterns — e.g. "search: 3/3", "activity: 2/2"
        #    If the progress numerator == denominator, the task is complete
        xofx_matches = re.findall(r'(\d+)/(\d+)', card_text)
        for num, denom in xofx_matches:
            if num == denom and int(num) > 0:
                return True
        
        # 4. Check for "Nice work" text that appears on completed streak cards
        if "nice work" in card_text:
            return True
            
    except:
        pass
    return False


def solve_potential_quiz(driver):
    try:
        start_btns = driver.find_elements(By.XPATH, "//input[@value='Start playing'] | //span[contains(@class, 'rq_button')]")
        if start_btns:
            logging.info("   -> Phát hiện Quiz/Poll, bấm Start...")
            try:
                driver.execute_script("arguments[0].click();", start_btns[0])
                time.sleep(3)
            except: pass

        for step in range(15): 
            options = driver.find_elements(By.CSS_SELECTOR, ".btOption, .rq_option, .wk_OptionClick, .b_cards, #currentQuestionContainer .b_answer")
            if not options:
                if step == 0: continue 
                else: break
            
            try:
                choice = random.choice(options)
                driver.execute_script("arguments[0].click();", choice)
                time.sleep(random.uniform(2, 4))
                
                if driver.find_elements(By.CSS_SELECTOR, ".btPollResult, .cico"):
                    logging.info("   -> Quiz/Poll hoàn thành.")
                    break
            except:
                pass
    except:
        pass


def click_daily_checkin(driver):
    """Click daily streak check-in button on rewards dashboard."""
    logging.info("[CHECKIN] Đang điểm danh daily streak...")
    try:
        driver.get("https://rewards.bing.com/")
        random_sleep(4, 6)
        
        # Scroll to see streak section
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(1)
        
        # Try multiple selectors for the streak/check-in card
        streak_selectors = [
            # Streak card button
            "mee-rewards-daily-set-item-content a[href*='streak']",
            # Daily check-in button
            "#daily-sets mee-rewards-daily-set-item-content a",
            # Streak bonus card
            "a[data-bi-id*='Streak']",
            "a[data-bi-id*='streak']",
            # General daily set first item (usually check-in)
            "mee-rewards-daily-set-section mee-rewards-daily-set-item-content:first-child a",
            # Keep streak alive card
            ".c-card-content a[href*='rewards']",
            # Lightbox streak
            "#streak-banner a",
        ]
        
        clicked = False
        for selector in streak_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.lower()
                    # Look for streak-related text
                    if any(k in text for k in ['streak', 'điểm danh', 'check', 'day', 'ngày', 'bonus']):
                        driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", el)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", el)
                        logging.info(f"[CHECKIN] ✅ Đã click điểm danh: '{text[:40]}'")
                        clicked = True
                        break
                if clicked:
                    break
            except:
                continue
        
        if not clicked:
            # Fallback: click the first uncompleted daily set item (usually check-in)
            try:
                daily_items = driver.find_elements(By.CSS_SELECTOR, "mee-rewards-daily-set-item-content")
                for item in daily_items:
                    try:
                        item.find_element(By.CSS_SELECTOR, ".mee-icon-SkypeCircleCheck")
                        continue  # Already completed
                    except:
                        pass
                    # This is uncompleted - click it
                    link = item.find_element(By.TAG_NAME, "a")
                    driver.execute_script("arguments[0].click();", link)
                    logging.info("[CHECKIN] ✅ Đã click daily set item đầu tiên chưa hoàn thành")
                    clicked = True
                    break
            except:
                pass
        
        if clicked:
            time.sleep(random.uniform(3, 5))
            # Handle new tab
            all_windows = driver.window_handles
            main_window = all_windows[0]
            if len(all_windows) > 1:
                for w in all_windows[1:]:
                    try:
                        driver.switch_to.window(w)
                        time.sleep(2)
                        driver.close()
                    except:
                        pass
                driver.switch_to.window(main_window)
            else:
                driver.back()
                time.sleep(2)
        
        if not clicked:
            logging.info("[CHECKIN] Không tìm thấy nút điểm danh (có thể đã điểm danh rồi)")
            
    except Exception as e:
        logging.warning(f"[CHECKIN] Lỗi: {e}")


def _complete_new_ui(driver):
    """Handle activities for the NEW accordion-based UI.
    
    Uses re-fetch pattern: after each card navigation, re-fetches all cards
    from the DOM to avoid stale element errors.
    """
    logging.info("[ACTIVITIES] === Xử lý UI MỚI ===")
    
    # Step 1: Expand all sections
    _expand_new_ui_sections(driver)
    random_sleep(1, 2)
    
    # Step 2: Get initial card count
    cards = _get_new_ui_task_cards(driver)
    total_cards = len(cards)
    logging.info(f"[ACTIVITIES] Tìm thấy {total_cards} task cards (UI mới)")
    
    if total_cards == 0:
        logging.warning("[ACTIVITIES] Không tìm thấy task cards nào trong UI mới.")
        return
    
    main_window = driver.current_window_handle
    processed_texts = set()  # Track processed cards by text content
    processed_count = 0
    max_iterations = total_cards * 2 + 15  # Safety limit: each card max 2 attempts
    iteration = 0
    no_new_card_streak = 0  # Count consecutive iterations with no new card found
    ACTIVITIES_MAX_TIME = 600  # 10 minutes max for entire activities phase
    start_time = time.time()
    
    while iteration < max_iterations:
        iteration += 1
        
        # Hard timeout: activities không nên mất quá 10 phút
        if time.time() - start_time > ACTIVITIES_MAX_TIME:
            logging.warning(f"[NEW UI] ⏰ Timeout {ACTIVITIES_MAX_TIME}s! Dừng activities sớm. Đã xử lý {processed_count} items.")
            break
        
        # === RE-FETCH cards from DOM every iteration ===
        try:
            cards = _get_new_ui_task_cards(driver)
        except Exception as e:
            logging.warning(f"[NEW UI] Lỗi re-fetch cards: {e}")
            # Try to navigate back and retry
            try:
                driver.get("https://rewards.bing.com/")
                random_sleep(3, 5)
                _expand_new_ui_sections(driver)
                random_sleep(1, 2)
                cards = _get_new_ui_task_cards(driver)
            except:
                logging.error("[NEW UI] Không thể recovery. Dừng xử lý activities.")
                break
        
        if not cards:
            logging.info("[NEW UI] Không còn cards nào. Hoàn tất.")
            break
        
        # Find the next unprocessed, incomplete card
        found_card = False
        for card in cards:
            try:
                card_text = ""
                try:
                    card_text = card.text.replace("\n", " ").strip()[:80]
                except:
                    continue  # Can't read text = skip
                
                # Skip if already processed (by text)
                if card_text in processed_texts or not card_text:
                    continue
                
                # Skip completed cards
                if _is_card_completed_new_ui(card):
                    processed_texts.add(card_text)
                    continue
                
                # === Found an incomplete, unprocessed card ===
                found_card = True
                processed_count += 1
                logging.info(f"[NEW UI] Item {processed_count}/{total_cards}: {card_text[:60]}")
                
                # Scroll to and click the card
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
                time.sleep(random.uniform(0.5, 1))
                
                # For <div> cards, try to find and click a child <a> link first
                click_target = card
                try:
                    if card.tag_name.lower() != 'a':
                        child_links = card.find_elements(By.TAG_NAME, "a")
                        if child_links:
                            click_target = child_links[0]
                except:
                    pass
                
                try:
                    click_target.click()
                except:
                    try:
                        driver.execute_script("arguments[0].click();", click_target)
                    except Exception as click_err:
                        logging.warning(f"[NEW UI] Click failed: {click_err}")
                        processed_texts.add(card_text)
                        break  # Re-fetch and try next
                
                # Mark as processed BEFORE navigating
                processed_texts.add(card_text)
                
                time.sleep(random.uniform(5, 8))
                
                # Handle new tab or same-tab navigation
                all_windows = driver.window_handles
                if len(all_windows) > 1:
                    for window in all_windows:
                        if window != main_window:
                            try:
                                driver.switch_to.window(window)
                                logging.info("   -> Đang xem trang hoạt động...")
                                
                                # Auto-F5 if page loaded with error
                                check_and_recover_oom(driver, "activity tab")
                                
                                solve_potential_quiz(driver)
                                human_scroll(driver)
                                time.sleep(random.uniform(5, 12))
                                
                                try:
                                    driver.execute_script("window.close();")
                                    time.sleep(0.5)
                                except:
                                    try:
                                        driver.close()
                                    except Exception as close_err:
                                        err_msg = str(close_err).split('\n')[0][:80]
                                        logging.warning(f"Window close failed: {err_msg}")
                            except Exception as win_err:
                                logging.warning(f"Lỗi xử lý cửa sổ phụ: {win_err}")
                    try:
                        driver.switch_to.window(main_window)
                    except Exception as switch_err:
                        logging.error(f"Không thể quay lại cửa sổ chính: {switch_err}")
                        try:
                            remaining = driver.window_handles
                            if remaining:
                                driver.switch_to.window(remaining[0])
                                main_window = remaining[0]
                        except:
                            logging.error("Session bị mất hoàn toàn. Dừng.")
                            return
                    
                    # After closing activity tab, ensure we're on rewards page
                    try:
                        if "rewards.bing.com" not in driver.current_url:
                            driver.get("https://rewards.bing.com/")
                            random_sleep(3, 5)
                    except:
                        pass
                    
                    # Re-expand sections for next iteration
                    _expand_new_ui_sections(driver)
                    random_sleep(1, 2)
                else:
                    logging.info("   -> Trang load tại chỗ, quay lại Dashboard sau 5s...")
                    # Auto-F5 if same-tab page loaded with error
                    check_and_recover_oom(driver, "activity same-tab")
                    solve_potential_quiz(driver)
                    time.sleep(5)
                    driver.back()
                    random_sleep(3, 5)
                    # Check rewards page loaded ok after back()
                    check_and_recover_oom(driver, "after back to dashboard")
                    
                    # KIỂM TRA ĐI LẠC (ANTI-LOST): Nếu lệnh back() không đủ để về bờ (do bị dính trang redirect 2-3 lớp)
                    if "rewards.bing.com" not in driver.current_url and "bing.com/rewards" not in driver.current_url:
                        logging.warning("   -> Bị lạc lối (mắc kẹt ở trang khác sau khi Back). Đang ép tải lại Bảng Điều Khiển...")
                        try:
                            # Ưu tiên trang Earn mới nhất của Microsoft
                            driver.get("https://rewards.bing.com/earn")
                            random_sleep(4, 6)
                        except: pass
                    
                    # Re-expand sections after navigating back
                    _expand_new_ui_sections(driver)
                    random_sleep(1, 2)
                
                break  # Break inner for-loop → re-fetch cards in while-loop
                
            except Exception as e:
                logging.error(f"[NEW UI] Lỗi xử lý card '{card_text[:40]}': {e}")
                processed_texts.add(card_text)
                # Try recovery
                try:
                    all_wins = driver.window_handles
                    if main_window not in all_wins:
                        if all_wins:
                            driver.switch_to.window(all_wins[0])
                            main_window = all_wins[0]
                        else:
                            logging.error("Không còn window nào. Dừng.")
                            return
                    else:
                        driver.switch_to.window(main_window)
                    
                    if "rewards.bing.com" not in driver.current_url:
                        driver.get("https://rewards.bing.com/")
                        random_sleep(3, 5)
                    _expand_new_ui_sections(driver)
                    random_sleep(1, 2)
                except:
                    pass
                break  # Re-fetch
        
        if not found_card:
            logging.info(f"[NEW UI] ✅ Đã xử lý xong tất cả cards ({processed_count} items)")
            break
    
    logging.info(f"[NEW UI] Hoàn tất. Đã xử lý {processed_count} activities.")


def _complete_old_ui(driver):
    """Handle activities for the OLD mee-rewards-based UI."""
    logging.info("[ACTIVITIES] === Xử lý UI CŨ ===")
    
    selectors = [
        "mee-rewards-daily-set-item-content",
        "mee-rewards-more-activities-card-item",
        "mee-rewards-banner-card-content"
    ]
    combined_selector = ", ".join(selectors)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, combined_selector)))
    except:
        logging.warning("[ACTIVITIES] Không tìm thấy hoạt động nào (UI cũ).")
        return

    cards = driver.find_elements(By.CSS_SELECTOR, combined_selector)
    total_cards = len(cards)
    logging.info(f"[ACTIVITIES] Tìm thấy tổng cộng {total_cards} thẻ nhiệm vụ (UI cũ).")
    
    main_window = driver.current_window_handle
    
    for index in range(total_cards):
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, combined_selector)
            if index >= len(cards): break
            current_card = cards[index]

            is_completed = False
            try:
                current_card.find_element(By.CSS_SELECTOR, ".mee-icon-SkypeCircleCheck")
                is_completed = True
            except: pass
            
            if is_completed: continue
            
            logging.info(f"Item {index+1}: Chưa hoàn thành, đang thực hiện...")
            
            try:
                link = current_card.find_element(By.TAG_NAME, "a")
            except:
                link = current_card 
            
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
            time.sleep(random.uniform(1, 2))
            
            try:
                link.click()
            except:
                logging.warning(f"   -> Click thường thất bại, thử JS Click cho Item {index+1}...")
                driver.execute_script("arguments[0].click();", link)
                
            time.sleep(random.uniform(5, 8))
            
            all_windows = driver.window_handles
            if len(all_windows) > 1:
                for window in all_windows:
                    if window != main_window:
                        try:
                            driver.switch_to.window(window)
                            logging.info(" -> Đang xem trang hoạt động...")
                            
                            solve_potential_quiz(driver)
                            human_scroll(driver)
                            time.sleep(random.uniform(5, 12))
                            
                            try:
                                driver.execute_script("window.close();")
                                time.sleep(0.5)
                            except:
                                try:
                                    driver.close()
                                except Exception as close_err:
                                    err_msg = str(close_err).split('\n')[0][:80]
                                    logging.warning(f"Window close failed: {err_msg}")
                        except Exception as win_err:
                            logging.warning(f"Lỗi xử lý cửa sổ phụ: {win_err}")
                try:
                    driver.switch_to.window(main_window)
                except Exception as switch_err:
                    logging.error(f"Không thể quay lại cửa sổ chính: {switch_err}")
                    try:
                        remaining = driver.window_handles
                        if remaining:
                            driver.switch_to.window(remaining[0])
                    except:
                        raise Exception("Session bị mất hoàn toàn")
            else:
                logging.info(" -> Trang load tại chỗ, quay lại Dashboard sau 5s...")
                solve_potential_quiz(driver)
                time.sleep(5)
                driver.back()
                random_sleep(3, 5)
            
        except Exception as e:
            logging.error(f"Lỗi khi xử lý item {index+1}: {e}")
            if driver.current_window_handle == main_window and "rewards.bing.com" not in driver.current_url:
                driver.back()
                random_sleep(3, 5)

def _complete_bing_flyout_tasks(driver):
    """Handle tasks embedded in the Bing Search Rewards Flyout (Medal icon)."""
    logging.info("[ACTIVITIES] === Xử lý Khu vực FLYOUT (Menu Bing) ===")
    try:
        current_url = driver.current_url
        driver.get("https://www.bing.com/")
        random_sleep(4, 6)
        
        # 1. Tìm và bấm nút Huy chương (Rewards Medal) ở góc phải
        medal_click = False
        medal_selectors = ["#id_rh", "#id_rc", "#b_rewardsbanner", "[id*='rh_meter']", "span.id_rh"]
        for selector in medal_selectors:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    medal_click = True
                    logging.info(f"[FLYOUT] Đã bấm Menu Rewards bằng selector: {selector}")
                    break
            except:
                pass
                
        if not medal_click:
            logging.warning("[FLYOUT] Không tìm thấy nút Huy Hiệu trên Bing, bỏ qua phần Flyout.")
            return

        time.sleep(random.uniform(4, 6)) # Đợi flyout load
        
        # 2. Tìm iFrame của Flyout và chui vào
        flyout_iframe = None
        for iframe_id in ["b_bapIframe", "b_bap_iframe", "bepfm"]:
            try:
                frame = driver.find_element(By.ID, iframe_id)
                flyout_iframe = frame
                break
            except: pass
            
        if not flyout_iframe:
            try:
                frame = driver.find_element(By.CSS_SELECTOR, "iframe[src*='rewards.bing']")
                flyout_iframe = frame
            except: pass

        if flyout_iframe:
            driver.switch_to.frame(flyout_iframe)
            logging.info("[FLYOUT] Đã lặn vào trong iframe Flyout thành công.")
        else:
            logging.info("[FLYOUT] Không thấy iframe, quét trực tiếp trên giao diện gốc.")
        
        # 3. Dùng chính cỗ máy lọc New UI để quét nhiệm vụ
        for loop_idx in range(3):
            cards = _get_new_ui_task_cards(driver)
            if not cards:
                logging.info("[FLYOUT] Không còn nhiệm vụ nào chưa hoàn thành trên Flyout.")
                break
            
            card = cards[0]
            card_text = (card.text or "").strip()[:40].replace('\n', ' ')
            logging.info(f"[FLYOUT] Phát hiện Item {loop_idx+1}: {card_text}")
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
                time.sleep(1)
                
                click_target = card
                try:
                    if card.tag_name.lower() != 'a':
                        child_links = card.find_elements(By.TAG_NAME, "a")
                        if child_links:
                            click_target = child_links[0]
                except: pass

                try:
                    click_target.click()
                except:
                    driver.execute_script("arguments[0].click();", click_target)
                
                time.sleep(5)
            except Exception as click_err:
                logging.warning(f"[FLYOUT] Lỗi click: {click_err}")
                break

            main_window = driver.window_handles[0]
            all_windows = driver.window_handles
            if len(all_windows) > 1:
                for w in all_windows:
                    if w != main_window:
                        try:
                            driver.switch_to.window(w)
                            time.sleep(2)
                            solve_potential_quiz(driver)
                            human_scroll(driver)
                            time.sleep(random.uniform(5, 8))
                            driver.close()
                        except: pass
                driver.switch_to.window(main_window)
            else:
                solve_potential_quiz(driver)
                time.sleep(3)
                driver.back()

            time.sleep(3)
            
            # Khởi động lại trang Bing vì Flyout có thể bị đóng
            driver.get("https://www.bing.com/")
            time.sleep(3)
            
            for selector in medal_selectors:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        break
                except: pass
            time.sleep(4)
            
            if flyout_iframe:
                driver.switch_to.default_content() 
                for iframe_id in ["b_bapIframe", "b_bap_iframe", "bepfm"]:
                    try:
                        frame = driver.find_element(By.ID, iframe_id)
                        driver.switch_to.frame(frame)
                        break
                    except: pass
                    
    except Exception as e:
        logging.error(f"[FLYOUT] Lỗi tổng quát: {e}")
    finally:
        try:
            driver.switch_to.default_content()
        except: pass


def complete_daily_set_and_activities(driver):
    logging.info("[ACTIVITIES] Đang kiểm tra Daily Set và More Activities...")
    try:
        # Always click daily check-in first
        click_daily_checkin(driver)
        
        try:
            driver.get("https://rewards.bing.com/")
        except Exception as nav_err:
            logging.warning(f"[ACTIVITIES] Lỗi navigation: {nav_err}")
        random_sleep(5, 8)
        
        # Auto-F5 if rewards page loaded with error
        check_and_recover_oom(driver, "activities rewards page")
        
        human_scroll(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep(2, 4)
        driver.execute_script("window.scrollTo(0, 0);")
        random_sleep(1, 2)

        # Auto-detect UI version and use appropriate handler
        try:
            if _is_new_ui(driver):
                _complete_new_ui(driver)
            else:
                _complete_old_ui(driver)
        except Exception as ui_err:
            logging.warning(f"[ACTIVITIES] Cụm handler UI cứng bị lỗi: {ui_err}")
            pass # Cho phép trôi xuống chạy AI
        
        # Chạy thêm giai đoạn vét đáy: Thẻ nhiệm vụ ẩn trên Menu Flyout của trang Bing tìm kiếm
        _complete_bing_flyout_tasks(driver)
        

                
    except Exception as e:
        logging.error(f"[ACTIVITIES] Lỗi chung: {e}")
        take_screenshot(driver, "activities_global_error")
