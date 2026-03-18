import logging
import os
import requests

# Импортируем TOKEN и CHAT_ID через геттер, чтобы избежать circular import
# (config загружает токен позже, после check_required_files)
def _get_token():
    from config import TOKEN
    return TOKEN

def _get_chat_id():
    from config import CHAT_ID
    return CHAT_ID


class TelegramLogsHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{_get_token()}/sendMessage",
                data={"chat_id": _get_chat_id(), "text": log_entry[:4000]},
                timeout=5
            )
            if resp.status_code != 200 or not resp.json().get("ok", False):
                print("Ошибка Telegram API:", resp.text)
        except Exception as e:
            print("Ошибка отправки лога в Telegram:", e)


def setup_loggers():
    os.makedirs("logs", exist_ok=True)

    # --- Panel logger ---
    panel_logger = logging.getLogger("panel_logger")
    panel_logger.setLevel(logging.INFO)

    panel_handler = logging.FileHandler("logs/action.log", encoding="utf-8")
    panel_handler.setLevel(logging.INFO)
    panel_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]"
    ))
    panel_logger.addHandler(panel_handler)

    tg_panel_handler = TelegramLogsHandler()
    tg_panel_handler.setLevel(logging.INFO)
    tg_panel_handler.setFormatter(logging.Formatter(
        "📒 ACTION\n%(asctime)s - %(levelname)s:\n%(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]"
    ))
    panel_logger.addHandler(tg_panel_handler)

    # --- Error logger ---
    error_logger = logging.getLogger("error_logger")
    error_logger.setLevel(logging.WARNING)

    error_handler = logging.FileHandler("logs/errors.log", encoding="utf-8")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]"
    ))
    error_logger.addHandler(error_handler)

    tg_error_handler = TelegramLogsHandler()
    tg_error_handler.setLevel(logging.WARNING)
    tg_error_handler.setFormatter(logging.Formatter(
        "❌ ERROR\n%(asctime)s - %(levelname)s:\n%(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]"
    ))
    error_logger.addHandler(tg_error_handler)


def get_panel_logger():
    return logging.getLogger("panel_logger")


def get_error_logger():
    return logging.getLogger("error_logger")


def log_user_action(user, action: str):
    username = getattr(user, "username", None) or "unknown"
    get_panel_logger().info(f"@{username} ({user.id}): {action}")


def log_error(message: str, exc=None):
    if exc:
        get_error_logger().error(message, exc_info=True)
    else:
        get_error_logger().error(message)