"""
farm_rewards.py - Microsoft Rewards Farmer CLI Wrapper
======================================================
Runs the centralized FarmOrchestrator against a shared profile list.
"""
import logging
import argparse

from farm.utils import setup_logging
from farm.orchestrator import FarmOrchestrator
from farm.profiles import (
    discover_profiles,
    build_profile_mapping,
    ensure_workspace_profiles_dir,
    ensure_default_workspace_profile,
)


def main():
    parser = argparse.ArgumentParser(description="Microsoft Rewards Farmer CLI")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--pc", type=int, default=30, help="Default PC searches when auto quota is unavailable")
    parser.add_argument("--mobile", type=int, default=20, help="Default mobile searches when auto quota is unavailable")
    parser.add_argument(
        "--source",
        choices=["auto", "edge", "local", "all"],
        default="auto",
        help="Profile source: auto prefers Edge, local uses profiles/, all includes both",
    )
    parser.add_argument(
        "--profile-id",
        action="append",
        default=[],
        help="Run only the specified stable profile id. Can be passed multiple times.",
    )
    args = parser.parse_args()
    setup_logging()

    headless_mode = not args.visible
    mode_str = "HEADLESS" if headless_mode else "VISIBLE"

    logging.info("=== AUTO MICROSOFT REWARDS CLI ===")
    logging.info(f"=== MODE: {mode_str} | PC: {args.pc} | Mobile: {args.mobile} | Source: {args.source} ===")

    ensure_workspace_profiles_dir()
    available_profiles = discover_profiles(mode=args.source)
    if args.profile_id:
        selected_ids = set(args.profile_id)
        available_profiles = [profile for profile in available_profiles if profile["id"] in selected_ids]
        logging.info(f"Filtered profile ids: {sorted(selected_ids)}")
    if not available_profiles:
        if args.profile_id:
            logging.info("No matching profiles found for the requested tray selection.")
        else:
            ensure_default_workspace_profile()
            logging.info("No profiles found. Created 'Farming_Profile [Local]'.")
            logging.info("Open the GUI or run visible mode to sign into the new profile before farming.")
        return

    profiles = [profile["id"] for profile in available_profiles]
    profile_mapping = build_profile_mapping(available_profiles)
    logging.info(f"Found {len(profiles)} profiles: {[profile['label'] for profile in available_profiles]}")

    callbacks = {
        "log": logging.info,
        "progress": lambda percent: logging.info(f"[Progress] {percent:.1f}%"),
        "status": lambda status: logging.info(f"[Status] {status}"),
        "eta": lambda eta: logging.info(f"[ETA] {eta}"),
        "points": lambda: None,
        "is_running": lambda: True,
    }

    config = {
        "pc_count": args.pc,
        "mobile_count": args.mobile,
        "delay_min": 0,
        "speed_mode": "🤖 Auto (Smart)",
        "debug_mode": not headless_mode,
        "auto_quota": True,
    }

    orchestrator = FarmOrchestrator(callbacks)
    orchestrator.farm_profiles(profiles, config, profile_mapping)

    logging.info("=== ALL PROFILES COMPLETED ===")


if __name__ == "__main__":
    main()
