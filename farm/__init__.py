"""
farm/ - MS Rewards Farming Package
Re-exports all public APIs for backward compatibility.
"""
from .config import (
    PC_SEARCH_COUNT, MOBILE_SEARCH_COUNT, MAX_WORKERS,
    PROFILE_DIRECTORY, LOG_DIR, SCREENSHOT_DIR,
    VOCAB, MOBILE_DEVICES
)
from .query import QueryGenerator, query_gen
from .utils import (
    setup_logging, take_screenshot, random_sleep,
    simulate_typing, simulate_reading_interaction,
    human_scroll, human_hover_and_click, human_bezier_move,
    apply_mobile_emulation, bezier_curve_points,
    check_and_recover_oom
)
from .driver import (
    setup_driver, get_driver, clone_edge_profile,
    safe_driver_quit, is_driver_alive, get_edge_version,
    cleanup_clone_profiles, cleanup_automation_processes
)
from .points import get_current_points, get_points_from_search_page
from .search import (
    interact_with_results, do_one_search, do_one_news_read,
    perform_searches, perform_mobile_news_reads, farm_parallel
)
from .activities import complete_daily_set_and_activities, solve_potential_quiz
from .profiles import (
    discover_profiles, build_profile_mapping,
    ensure_workspace_profiles_dir, ensure_default_workspace_profile,
    create_workspace_profile
)
from .decision import (
    EarlyStopDetector, adaptive_batch, auto_speed_config, log_quota_confidence
)

__all__ = [
    'setup_driver', 'safe_driver_quit', 'get_current_points',
    'complete_daily_set_and_activities', 'query_gen',
    'simulate_typing', 'human_scroll', 'interact_with_results',
    'random_sleep', 'setup_logging', 'perform_searches',
    'farm_parallel', 'get_edge_version', 'clone_edge_profile',
    'EarlyStopDetector', 'adaptive_batch', 'auto_speed_config', 'log_quota_confidence',
    'discover_profiles', 'build_profile_mapping', 'ensure_workspace_profiles_dir',
    'ensure_default_workspace_profile', 'create_workspace_profile',
    'cleanup_automation_processes',
]
