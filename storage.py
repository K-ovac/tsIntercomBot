import json
import os
from logger import log_error
from config import ADMINS_FILE, USERS_FILE, PANELS_FILE


# ========= Admins =========

def load_admins() -> list:
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ========= Users =========

def load_users() -> dict:
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_users(user_dict: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_dict, f, ensure_ascii=False, indent=4)


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
admins: list = load_admins()
users: dict = load_users()
CREDS: list[tuple[str, str]] = load_creds()