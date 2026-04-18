"""
farm/decision.py - Smart Decision Engine cho Microsoft Rewards farming

Cung cấp các kỹ thuật ra quyết định thông minh:
  1. EarlyStopDetector  - Dừng sớm khi search không còn kiếm điểm
  2. adaptive_batch     - Tính batch size tối ưu theo quota còn lại
  3. auto_speed_config  - Tự chọn tốc độ search theo thời gian còn lại
"""
import time
import logging


# ─────────────────────────────────────────────
# 1. EARLY STOP DETECTOR
# ─────────────────────────────────────────────
class EarlyStopDetector:
    """Phát hiện khi search không còn kiếm điểm → dừng sớm để tiết kiệm thời gian.

    Cách dùng:
        detector = EarlyStopDetector()
        for batch in ...:
            # sau mỗi batch lấy điểm hiện tại
            if detector.update(current_points) and detector.should_stop():
                log("Quota đã đạt! Dừng sớm.")
                break
    """

    def __init__(self, zero_threshold: int = 3, min_samples: int = 3):
        """
        Args:
            zero_threshold: số batch liên tiếp không kiếm được điểm trước khi dừng
            min_samples:    số lần check tối thiểu trước khi cho phép dừng sớm
        """
        self.zero_threshold = zero_threshold
        self.min_samples = min_samples
        self._last_points = None
        self._zero_streak = 0
        self._sample_count = 0
        self._stop_flagged = False

    def update(self, current_points) -> bool:
        """Cập nhật với điểm hiện tại. Trả về True nếu đọc được điểm hợp lệ."""
        if not isinstance(current_points, int) or current_points <= 0:
            return False  # Không đọc được điểm — bỏ qua

        if self._last_points is None:
            self._last_points = current_points
            return True

        delta = current_points - self._last_points
        self._last_points = current_points
        self._sample_count += 1

        if delta <= 0:
            self._zero_streak += 1
            logging.debug(f"[DECISION] Zero-delta streak: {self._zero_streak}/{self.zero_threshold}")
        else:
            self._zero_streak = 0  # Reset nếu vừa kiếm được điểm
            logging.debug(f"[DECISION] +{delta} pts. Streak reset.")

        return True

    def should_stop(self) -> bool:
        """Trả về True nếu nên dừng search sớm."""
        if self._sample_count < self.min_samples:
            return False  # Chưa đủ dữ liệu để quyết định
        if self._zero_streak >= self.zero_threshold:
            if not self._stop_flagged:
                self._stop_flagged = True
                logging.info(
                    f"[DECISION] 🛑 EarlyStop: {self._zero_streak} batches liên tiếp không kiếm điểm. "
                    f"Quota đã đạt thực tế!"
                )
            return True
        return False

    def reset(self):
        """Reset cho profile hoặc phase mới."""
        self._last_points = None
        self._zero_streak = 0
        self._sample_count = 0
        self._stop_flagged = False


# ─────────────────────────────────────────────
# 2. ADAPTIVE BATCH SIZE
# ─────────────────────────────────────────────
def adaptive_batch(done: int, needed: int, base: int = 3) -> int:
    """Tính batch size tối ưu dựa trên tiến độ.

    Logic:
      - Giai đoạn đầu (< 30% xong): batch lớn hơn để nhanh
      - Giai đoạn giữa (30-80%):    batch bình thường
      - Giai đoạn cuối (> 80% xong): batch nhỏ hơn để chính xác

    Args:
        done:  số searches đã làm
        needed: tổng số searches cần làm
        base:  batch size cơ bản

    Returns:
        batch size (min 1, max 5)
    """
    remaining = needed - done
    if remaining <= 0:
        return 1

    if needed <= 0:
        return base

    progress = done / needed

    if progress < 0.30:
        # Giai đoạn đầu: tăng tốc (batch +2)
        batch = min(base + 2, remaining, 5)
    elif progress < 0.80:
        # Giai đoạn giữa: bình thường
        batch = min(base, remaining, 5)
    else:
        # Giai đoạn cuối: thận trọng (batch 1-2)
        batch = min(2, remaining)

    batch = max(1, batch)
    logging.debug(f"[DECISION] adaptive_batch: done={done}/{needed} ({progress:.0%}) → batch={batch}")
    return batch


# ─────────────────────────────────────────────
# 3. AUTO SPEED CONFIG
# ─────────────────────────────────────────────
_SPEED_PRESETS = {
    "safe":   {'wait': (10, 18), 'post': (5, 10)},
    "medium": {'wait': (5, 10),  'post': (3, 6)},
    "fast":   {'wait': (3, 6),   'post': (2, 4)},
    "turbo":  {'wait': (2, 4),   'post': (1, 2)},
}

def auto_speed_config(
    remaining_searches: int,
    elapsed_seconds: float,
    timeout_seconds: float = 1500,
    user_speed: str = "auto"
) -> dict:
    """Tự chọn speed config tối ưu để hoàn thành quota trong thời gian cho phép.

    Args:
        remaining_searches: số searches còn lại
        elapsed_seconds:    thời gian đã dùng (giây)
        timeout_seconds:    giới hạn thời gian tổng cộng (giây)
        user_speed:         speed do user chọn ("auto" = để system quyết định)

    Returns:
        speed config dict với keys 'wait' và 'post'
    """
    # Nếu user đã chọn speed cụ thể, dùng theo user
    normalized_speed = (user_speed or "").strip().lower()
    if normalized_speed and "auto" not in normalized_speed:
        if "turbo" in normalized_speed:
            key = "turbo"
        elif "fast" in normalized_speed:
            key = "fast"
        elif "safe" in normalized_speed:
            key = "safe"
        else:
            key = "medium"
        return _SPEED_PRESETS[key]

    time_left = timeout_seconds - elapsed_seconds

    if remaining_searches <= 0 or time_left <= 0:
        return _SPEED_PRESETS["turbo"]

    # Thời gian trung bình mỗi search ở từng mode (giây):
    # safe≈18s, medium≈10s, fast≈6s, turbo≈4s
    avg_time_per_search = {
        "safe": 18, "medium": 10, "fast": 6, "turbo": 4
    }

    # Chọn speed chậm nhất mà vẫn kịp hoàn thành
    chosen = "turbo"
    for speed in ["safe", "medium", "fast", "turbo"]:
        estimated = remaining_searches * avg_time_per_search[speed]
        if estimated <= time_left * 0.85:  # 85% thời gian còn lại = buffer
            chosen = speed
            break

    cfg = _SPEED_PRESETS[chosen]
    logging.info(
        f"[DECISION] 🚦 auto_speed → '{chosen}' "
        f"({remaining_searches} searches, {time_left:.0f}s left)"
    )
    return cfg


# ─────────────────────────────────────────────
# 4. QUOTA CONFIDENCE
# ─────────────────────────────────────────────
def log_quota_confidence(quota: dict, profile: str):
    """Log mức độ tin cậy của quota data và đề xuất hành động."""
    if quota is None:
        logging.warning(f"[DECISION] [{profile}] ⚠️ Không có quota data — dùng fallback")
        return

    inferred = quota.get('inferred', False)
    pc_rem   = quota.get('pc_remaining_searches', 0)
    mob_rem  = quota.get('mobile_remaining_searches', 0)

    confidence = "🟢 Chính xác (API)" if not inferred else "🟡 Ước tính (inferred)"
    efficiency = "tối ưu" if not inferred else "có thể lệch ±20%"

    logging.info(
        f"[DECISION] [{profile}] Quota confidence: {confidence} | "
        f"PC cần ~{pc_rem} searches, Mobile ~{mob_rem} searches | "
        f"Độ chính xác {efficiency}"
    )

    if inferred and pc_rem == 30:
        logging.info(
            f"[DECISION] [{profile}] 💡 Hint: Re-read quota sau activities để có data chính xác hơn"
        )
