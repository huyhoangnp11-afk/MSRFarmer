"""
farm/profiles.py - Shared profile discovery for GUI, CLI, and tray app.
"""
import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
EDGE_USER_DATA = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Microsoft",
    "Edge",
    "User Data",
)
DEFAULT_PROFILE_NAME = "Farming_Profile"
MAX_PROFILES = 6
RESERVED_WORKSPACE_PROFILES = {"zalo_web_agent"}


def _build_profile_id(source, folder_name):
    return f"{source}:{folder_name}"


def ensure_workspace_profiles_dir():
    os.makedirs(WORKSPACE_PROFILES_DIR, exist_ok=True)
    return WORKSPACE_PROFILES_DIR


def create_workspace_profile(name):
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Profile name is required")

    ensure_workspace_profiles_dir()
    profile_path = os.path.join(WORKSPACE_PROFILES_DIR, clean_name)
    os.makedirs(profile_path, exist_ok=True)
    
    # Tạo dummy file "First Run" để đánh lừa Edge rằng đã khởi tạo rồi, 
    # tránh hiện bảng chào mừng và tự động Sign-in acc Windows.
    try:
        first_run_file = os.path.join(profile_path, "First Run")
        if not os.path.exists(first_run_file):
            with open(first_run_file, "w") as f:
                pass
    except: pass
    
    return profile_path


def ensure_default_workspace_profile():
    return create_workspace_profile(DEFAULT_PROFILE_NAME)


def _discover_edge_profiles():
    profiles = []
    local_state_path = os.path.join(EDGE_USER_DATA, "Local State")

    try:
        if not os.path.exists(local_state_path):
            return []

        with open(local_state_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        info_cache = data.get("profile", {}).get("info_cache", {})
        for folder_name, info in info_cache.items():
            if folder_name in {"System Profile", "Guest Profile"}:
                continue

            profile_path = os.path.join(EDGE_USER_DATA, folder_name)
            if not os.path.isdir(profile_path):
                continue

            display_name = (info.get("name") or folder_name).strip()
            if display_name == folder_name:
                label = f"{folder_name} [Edge]"
            else:
                label = f"{display_name} ({folder_name}) [Edge]"

            profiles.append(
                {
                    "id": _build_profile_id("edge", folder_name),
                    "history_id": folder_name,
                    "label": label,
                    "name": display_name,
                    "folder": folder_name,
                    "path": profile_path,
                    "source": "edge",
                }
            )
    except Exception:
        return []

    profiles.sort(key=lambda item: item["label"].lower())
    return profiles


def _discover_workspace_profiles():
    ensure_workspace_profiles_dir()
    profiles = []

    try:
        for folder_name in os.listdir(WORKSPACE_PROFILES_DIR):
            profile_path = os.path.join(WORKSPACE_PROFILES_DIR, folder_name)
            if not os.path.isdir(profile_path) or folder_name.startswith("."):
                continue
            if folder_name in RESERVED_WORKSPACE_PROFILES:
                continue

            label = f"{folder_name} [Local]"
            profiles.append(
                {
                    "id": _build_profile_id("local", folder_name),
                    "history_id": folder_name,
                    "label": label,
                    "name": folder_name,
                    "folder": folder_name,
                    "path": profile_path,
                    "source": "local",
                }
            )
    except Exception:
        return []

    profiles.sort(key=lambda item: item["label"].lower())
    return profiles


def discover_profiles(mode="auto", limit=MAX_PROFILES):
    """
    mode:
      - auto: prefer Edge profiles, fallback to local workspace profiles
      - edge: only Edge profiles
      - local: only workspace profiles
      - all: include both sources
    """
    edge_profiles = _discover_edge_profiles()
    local_profiles = _discover_workspace_profiles()

    if mode == "edge":
        profiles = edge_profiles
    elif mode == "local":
        profiles = local_profiles
    elif mode == "all":
        profiles = edge_profiles + local_profiles
    else:
        profiles = edge_profiles or local_profiles

    if limit is not None:
        return profiles[:limit]
    return profiles


def build_profile_mapping(profiles):
    return {profile["id"]: profile for profile in profiles}
