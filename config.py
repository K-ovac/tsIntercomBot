import sys
import json
import os

SELECT_PANEL, SELECT_ACTION, ASK_APARTMENT_LEVEL, ASK_APARTMENT_CALL, ASK_DOOR_CODE = range(5)

USERS_FILE = "data/users.json"
PANELS_FILE = "data/panels.json"
UNAUTHORIZED_LOG = "data/unauthorized.log"

REQUIRED_FILES = [
    "data/bot_token.txt",
    "data/panels.json",
    "data/creds.json",
    "data/users.json",
    "data/chat_id.txt"
]

PROXY = "socks5://[::1]:10811"
TOKEN: str = ""
CHAT_ID: str = ""

PANEL_INFO_FIELDS = [
    {
        #основные настройки
        "url": "/cgi-bin/intercom_cgi?action=get",
        "keys": {
            "DoorCode":       ("🔑 Код двери",     "code",    lambda v: f"<code>{v}</code>"),
            "DoorCodeActive": ("🔒 Код открытия",  "active",  lambda v: "✅ активен" if v.lower() == "on" else "❌ неактивен"),
        }
    },
{
        #ключи
        "url": "/cgi-bin/mifare_cgi?action=get",
        "keys": {
            "ScanCode": ("🔖 Код сканирования ключей", "code", lambda v: f"<code>{v}</code>"),
            "ScanModeActive": ("📝 Автосбор", "active", lambda v: "✅ активен" if v.lower() == "on" else "❌ неактивен"),
            "AutoExtRfidSync":          ("♾️ Синхронизация с внешней таблицей",   "autosync",   lambda v: "✅ активна" if v.lower() == "on" else "❌ неактивна"),
        }
    },
    {
        #системная информация
        "url": "/cgi-bin/systeminfo_cgi?action=get",
        "keys": {
            "DeviceID": ("🛠 Серийный номер", "deviceid", lambda v: v),
            "UpTime":          ("⏱ Аптайм",   "uptime",   lambda v: v),
        }
    },
]

DEFAULT_ROLE = "ooo_service"

ROLE_PERMISSIONS = {
    "admin":       ["all"],
    "ooo_service": ["all"],
    "oao_service": [
        "Открыть основную дверь", "Открыть доп дверь"
    ],
}

def load_token_and_chat_id():
    global TOKEN, CHAT_ID
    with open("data/bot_token.txt", "r", encoding="utf-8") as f:
        TOKEN = f.read().strip()
    with open("data/chat_id.txt", "r", encoding="utf-8") as f:
        CHAT_ID = f.read().strip()


def check_required_files():
    missing = []
    for f_req in REQUIRED_FILES:
        if not os.path.exists(f_req):
            missing.append(f_req)
        else:
            if f_req.endswith(".json"):
                try:
                    with open(f_req, "r", encoding="utf-8") as file:
                        json.load(file)
                except json.JSONDecodeError:
                    print(f"[ERROR] Файл {f_req} поврежден или не является корректным JSON.")
                    sys.exit(1)
    if missing:
        print(f"[ERROR] Отсутствуют необходимые файлы: {', '.join(missing)}")
        sys.exit(1)
    print("Все необходимые файлы найдены и корректны.")