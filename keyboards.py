from telegram import ReplyKeyboardMarkup
from config import ROLE_PERMISSIONS, DEFAULT_ROLE


def get_action_keyboard(role: str = DEFAULT_ROLE) -> ReplyKeyboardMarkup:
    allowed = ROLE_PERMISSIONS.get(role, [])
    all_rows = [
        ["Включить автосбор", "Выключить автосбор"],
        ["Статус трубки", "Вызов в квартиру"],
        ["Инд. уровни", "Общие уровни"],
        ["Адресация ККМ", "Ping"],
        ["Открыть основную дверь", "Открыть доп дверь"],
        ["Актив код открытия", "Деактив код открытия", "Установить код"],
        ["Вкл. магнит осн. двери", "Выкл. магнит осн. двери"],
        ["Вкл. магнит доп. двери", "Выкл. магнит доп. двери"],
    ]

    if "all" in allowed:
        filtered = all_rows
    else:
        filtered = [
            [btn for btn in row if btn in allowed]
            for row in all_rows
        ]
        filtered = [row for row in filtered if row]

    filtered.append(["Назад"])
    return ReplyKeyboardMarkup(filtered, one_time_keyboard=True)


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Назад"]], one_time_keyboard=True)


async def reply_with_keyboard(update, text: str, keyboard=None, role: str = DEFAULT_ROLE):
    if keyboard is None:
        keyboard = get_action_keyboard(role)
    await update.message.reply_text(text, reply_markup=keyboard)