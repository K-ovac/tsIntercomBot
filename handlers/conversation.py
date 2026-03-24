from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import SELECT_PANEL, SELECT_ACTION, ASK_APARTMENT_LEVEL, ASK_APARTMENT_CALL, ASK_DOOR_CODE, ROLE_PERMISSIONS, DEFAULT_ROLE
from storage import is_allowed, is_admin, get_user_role, load_panels
from keyboards import get_action_keyboard, back_keyboard, reply_with_keyboard
from logger import log_user_action, log_error
from panel_api import (
    toggle_autolearn, toggle_door_code, open_door,
    set_door_magnet, get_dks_du, get_current_door_code,
    get_panel_summary, check_panel
)
from handlers.actions import (
    custom_levels, set_common_levels, ask_apartment_status,
    check_panel_handler
)


async def start(update, context):
    user_id = str(update.effective_user.id)
    if is_allowed(user_id):
        context.user_data['role'] = get_user_role(user_id)
        panels = load_panels()
        context.user_data['panels'] = panels
        await update.message.reply_text("Введите адрес панели")
        return SELECT_PANEL
    else:
        await update.message.reply_text(f"За доступом обратитесь к администратору.\nВаш ID: {user_id}")
        return ConversationHandler.END


async def select_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['panels'] = load_panels()
    panels = context.user_data['panels']
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if text.lower() == "завершить":
        await update.message.reply_text("Операция завершена.")
        return ConversationHandler.END

    if text.lower() == "назад":
        await update.message.reply_text("Введите адрес")
        context.user_data.pop('search_results', None)
        return SELECT_PANEL

    if 'search_results' in context.user_data:
        search_results = context.user_data['search_results']
        if text in search_results:
            ip = search_results[text]
            desc = text
            context.user_data['selected_ip'] = ip
            context.user_data['selected_desc'] = desc

            await update.message.reply_text("⏳ Получаю данные панели...")
            summary = await get_panel_summary(ip, desc)
            if is_admin(user_id):
                summary += f"\n🌐 IP: <code>{ip}</code>"
            await update.message.reply_text(summary, parse_mode="HTML")

            role = context.user_data.get('role', DEFAULT_ROLE)
            await update.message.reply_text("Выберите действие:", reply_markup=get_action_keyboard(role))
            return SELECT_ACTION
        else:
            await update.message.reply_text("Нажмите на одну из кнопок ниже или 'Назад'.")
            return SELECT_PANEL

    user_input = text.lower()
    matches = [(ip, addr) for ip, addr in panels.items() if user_input in addr.lower()]

    if not matches:
        await update.message.reply_text("Панели с таким адресом не найдены. Попробуйте снова.")
        return SELECT_PANEL

    context.user_data['search_results'] = {desc: ip for ip, desc in matches}
    keyboard = [[desc] for _, desc in matches]
    keyboard.append(["Назад"])
    msg = ("Найдена панель. Выберите адрес панели:"
           if len(matches) == 1
           else "Найдено несколько совпадений. Выберите адрес панели:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return SELECT_PANEL


async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text.strip()
    ip = context.user_data.get('selected_ip')
    desc = context.user_data.get('selected_desc')
    role = context.user_data.get('role', DEFAULT_ROLE)

    # --- Назад ---
    if action == "Назад":
        context.user_data['awaiting'] = None
        search_results = context.user_data.get('search_results')
        if search_results:
            keyboard = [[d] for d in search_results.keys()]
            keyboard.append(["Назад"])
            await update.message.reply_text(
                "Выберите адрес панели",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
        else:
            await update.message.reply_text("Введите адрес панели")
        return SELECT_PANEL

    # --- Действия, требующие ввода ---
    if action == "Инд. уровни":
        context.user_data['awaiting'] = "custom_levels"
        await update.message.reply_text(
            "Введите квартиру и три уровня через запятую.\n"
            "Пример: 4, 120 340 500\n"
            "Измерьте уровни через 'Статус трубки' в трёх положениях.\n"
            "Для возврата нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_LEVEL

    if action == "Общие уровни":
        context.user_data['awaiting'] = "set_common_levels"
        await update.message.reply_text(
            "Введите три уровня через пробел (l1 l2 l3).\n"
            "Пример: 120 340 500\nИзмерьте уровни через 'Статус трубки' в трёх положениях.\n"
            "Для возврата нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_LEVEL

    if action == "Статус трубки":
        context.user_data['awaiting'] = "apartment_status"
        await update.message.reply_text(
            "Введите номер квартиры или диапазон через '-'.\nДля возврата нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_LEVEL

    if "Вызов в квартиру" in action:
        context.user_data['awaiting'] = None
        await update.message.reply_text(
            "Введите номер квартиры\nДля возврата нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_CALL

    if action == "Установить код":
        current_code = await get_current_door_code(ip, desc)
        await update.message.reply_text(
            f"Текущий код двери: {current_code}\nВведите новый код (ровно 5 цифр):"
        )
        return ASK_DOOR_CODE

    # --- Если есть ожидающий ввод ---
    awaiting = context.user_data.get("awaiting")
    if awaiting:
        if awaiting == "custom_levels":
            return await custom_levels(update, context)
        if awaiting == "common_levels":
            return await set_common_levels(update, context)
        if awaiting == "apartment_status":
            return await ask_apartment_status(update, context)

    # --- Проверка, что панель выбрана ---
    if not ip or not desc:
        await update.message.reply_text("Панель не выбрана. Введите адрес панели.")
        return SELECT_PANEL

    # --- Проверка прав ---
    allowed = ROLE_PERMISSIONS.get(role, [])
    if "all" not in allowed and action not in allowed:
        await update.message.reply_text("⛔ Недостаточно прав.")
        await update.message.reply_text("Выберите действие:", reply_markup=get_action_keyboard(role))
        return SELECT_ACTION

    # --- Выполнение действия ---
    success = None
    show_keyboard = True  # показывать клавиатуру в конце

    if "Включить" in action:
        success = await toggle_autolearn(ip, True)
    elif "Выключить" in action:
        success = await toggle_autolearn(ip, False)
    elif "Актив код открытия" in action:
        current_code = await get_current_door_code(ip, desc)
        await update.message.reply_text(f"Текущий код двери: {current_code}")
        success = await toggle_door_code(ip, True)
    elif "Деактив код открытия" in action:
        success = await toggle_door_code(ip, False)
    elif action == "Открыть основную дверь":
        await open_door(ip, "maindoor", desc, update)
    elif action == "Открыть доп дверь":
        await open_door(ip, "altdoor", desc, update)
    elif action == "Адресация ККМ":
        await get_dks_du(ip=ip, desc=desc, update=update)
    elif "Ping" in action:
        panel_status = await check_panel(ip)
        await update.message.reply_text(f"{desc}: {panel_status}")
        log_user_action(update.effective_user, f"Ping на {ip} ({desc}) — {panel_status}")
    elif action == "Вкл. магнит осн. двери":
        await set_door_magnet(ip, "MainDoorOpenMode", "off", desc, update)
    elif action == "Выкл. магнит осн. двери":
        await set_door_magnet(ip, "MainDoorOpenMode", "on", desc, update)
    elif action == "Вкл. магнит доп. двери":
        await set_door_magnet(ip, "AltDoorOpenMode", "off", desc, update)
    elif action == "Выкл. магнит доп. двери":
        await set_door_magnet(ip, "AltDoorOpenMode", "on", desc, update)
    else:
        await update.message.reply_text("Неизвестное действие.")
        show_keyboard = False

    # --- Результат для toggle-действий ---
    if success is not None:
        if success:
            await update.message.reply_text(f"✅ Успешно: {action.lower()} на {desc}")
            log_user_action(update.effective_user, f"{action} на {ip} ({desc})")
        else:
            await update.message.reply_text(f"❌ Ошибка: не удалось выполнить {action.lower()} на {desc}")
            log_error(f"{action} на {ip} ({desc})")

    # --- Клавиатура с правильной ролью — всегда в одном месте ---
    if show_keyboard:
        await update.message.reply_text("Выберите действие:", reply_markup=get_action_keyboard(role))

    return SELECT_ACTION


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    panels = load_panels()
    context.user_data['panels'] = panels

    if not panels:
        await update.message.reply_text("Список панелей пуст. Добавьте панели командой /addpanel")
        return ConversationHandler.END

    keyboard = [[desc] for desc in panels.values()]
    await update.message.reply_text(
        "Выберите адрес панели для проверки статуса:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    log_user_action(update.effective_user, "Открыл меню статуса панелей")
    return SELECT_PANEL


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END