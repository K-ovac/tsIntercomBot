import json
import os
from logger import log_error
from config import USERS_FILE, PANELS_FILE

USERS_FILE = "data/users.json"

# ========= Users =========
_users_cache: dict = {}

def load_users() -> dict:
    global _users_cache
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            _users_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _users_cache = {"admins": [], "roles": {}}
    return _users_cache


def save_users(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_admins() -> list:
    return _users_cache.get("admins", [])

def is_admin(user_id: str) -> bool:
    return user_id in get_admins()

def is_allowed(user_id: str) -> bool:
    return user_id in _users_cache.get("roles", {}) or is_admin(user_id)

def get_user_role(user_id: str) -> str:
    if is_admin(user_id):
        return "admin"
    user = _users_cache.get("roles", {}).get(user_id)
    if user:
        return user.get("group", "oao_service")
    return None


# ========= Panels =========

def load_panels() -> dict:
    if not os.path.exists(PANELS_FILE):
        log_error(f"{PANELS_FILE} не найден. Создан пустой файл.")
        save_panels({})
        return {}
    try:
        with open(PANELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        log_error(f"{PANELS_FILE} поврежден или имеет неверный формат. Создан пустой файл.")
        save_panels({})
        return {}


def save_panels(panels: dict):
    with open(PANELS_FILE, "w", encoding="utf-8") as f:
        json.dump(panels, f, ensure_ascii=False, indent=2)


# ========= Credentials =========

def load_creds(filename="data/creds.json") -> list[tuple[str, str]]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            creds = json.load(f)
            if isinstance(creds, list):
                return [(item["login"], item["password"]) for item in creds]
    except Exception as e:
        log_error(f"Ошибка загрузки учетных данных: {e}")
    return []


# Глобальные объекты — инициализируются один раз при импорте
users: dict = load_users()
CREDS: list[tuple[str, str]] = load_creds()