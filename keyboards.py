from telegram import ReplyKeyboardMarkup


def get_action_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["Включить автосбор", "Выключить автосбор"],
        ["Статус трубки", "Вызов в квартиру"],
        ["Инд. уровни", "Общие уровни"],
        ["Адресация ККМ", "Ping"],
        ["Открыть основную дверь", "Открыть доп дверь"],
        ["Актив код открытия", "Деактив код открытия", "Установить код"],
        ["Вкл. магнит осн. двери", "Выкл. магнит осн. двери"],
        ["Вкл. магнит доп. двери", "Выкл. магнит доп. двери"],
        ["Назад"]
    ], one_time_keyboard=True)


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Назад"]], one_time_keyboard=True)


async def reply_with_keyboard(update, text: str, keyboard=None):
    if keyboard is None:
        keyboard = get_action_keyboard()
    await update.message.reply_text(text, reply_markup=keyboard)