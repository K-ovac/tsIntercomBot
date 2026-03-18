from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from config import SELECT_ACTION, ASK_APARTMENT_LEVEL, ASK_APARTMENT_CALL, ASK_DOOR_CODE
from keyboards import get_action_keyboard, back_keyboard, reply_with_keyboard
from panel_api import (
    measure_linelevel, poll_apartment, check_panel,
    get_current_door_code, CREDS
)
from logger import log_user_action, log_error
import aiohttp


# ========= Apartment status (line level) =========

async def ask_apartment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apt_input = update.message.text.strip()

    if apt_input.lower() == "назад":
        context.user_data['awaiting'] = None
        await update.message.reply_text("Выберите действие:", reply_markup=get_action_keyboard())
        return SELECT_ACTION

    ip = context.user_data.get('selected_ip')
    desc = context.user_data.get('selected_desc')

    apartments = []
    if '-' in apt_input:
        try:
            first, last = map(int, apt_input.split('-'))
            if first > last:
                first, last = last, first
            apartments = list(range(first, last + 1))
        except ValueError:
            await update.message.reply_text(
                "Неверный формат диапазона. Используйте, например: 1-5\nДля отмены нажмите 'Назад'",
                reply_markup=back_keyboard()
            )
            return ASK_APARTMENT_LEVEL
    else:
        try:
            apartments = [int(apt_input)]
        except ValueError:
            await update.message.reply_text(
                "Введите номер квартиры или диапазон через '-'.\nДля отмены нажмите 'Назад'",
                reply_markup=back_keyboard()
            )
            return ASK_APARTMENT_LEVEL

    await update.message.reply_text("Проверяю статус трубок. Подождите...")
    result_msg = f"Проверены уровни для квартир(-ы): {apt_input}\n\n"

    for apt in apartments:
        level = await measure_linelevel(ip, apt)
        if level is None:
            result_msg += f"Кв.{apt}: ошибка получения уровня\n"
        else:
            status_line = "активна" if level < 501 else "не активна"
            result_msg += f"Кв.{apt}: трубка {status_line}. Уровень линии: {level}\n"
            log_user_action(update.effective_user, f"Статус трубки кв.{apt} ({desc}). Уровень={level}")

    await update.message.reply_text(result_msg)
    await reply_with_keyboard(update, f"Панель: {desc}. Выберите действие:")
    return SELECT_ACTION


# ========= Apartment call =========

async def ask_apartment_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apartment_number = update.message.text.strip()
    ip = context.user_data.get("selected_ip")
    desc = context.user_data.get("selected_desc")

    if apartment_number == "Назад":
        context.user_data['awaiting'] = None
        await reply_with_keyboard(update, "Выберите действие:")
        return SELECT_ACTION

    try:
        apartment_number = int(apartment_number)
    except ValueError:
        await update.message.reply_text(
            "Введите номер квартиры. Для возврата в меню действий нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_CALL

    result = await poll_apartment(ip, "/webs/diag_cgi?action=call", apartment_number)

    if result is None:
        await update.message.reply_text(
            f"❌ Ошибка вызова кв. {apartment_number}: нет ответа от панели",
            reply_markup=get_action_keyboard()
        )
    elif result.strip() == "OK":
        await update.message.reply_text(
            f"✅ Вызов кв. {apartment_number} на {desc} успешно выполнен.",
            reply_markup=get_action_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка вызова квартиры {apartment_number}: {result}",
            reply_markup=get_action_keyboard()
        )

    return SELECT_ACTION


# ========= Individual levels =========

async def custom_levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = context.user_data.get('selected_ip')
    desc = context.user_data.get('selected_desc')
    text = update.message.text.strip()

    if text.lower() == "назад":
        context.user_data['awaiting'] = None
        await reply_with_keyboard(update, "Выберите действие:")
        return SELECT_ACTION

    try:
        apt_part, levels_part = text.split(",", 1)
        apt = int(apt_part.strip())
        levels = list(map(int, levels_part.strip().split()))
        if len(levels) != 3:
            raise ValueError("Неверное количество уровней")
    except ValueError:
        await update.message.reply_text(
            "Неверный формат ввода.\nПример: 4, 120 340 500\nДля возврата нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_LEVEL

    l1, l2, l3 = levels

    if abs(l2 - l1) < 20:
        await update.message.reply_text(
            f"⚠️ Кв.{apt}: уровни трубка висит/поднята слишком близки — проверьте линию"
        )
        await reply_with_keyboard(update, f"Панель: {desc}. Выберите действие:")
        return SELECT_ACTION

    if l3 in (l1, l2) or abs(l3 - l2) < 20:
        await update.message.reply_text(
            f"⚠️ Кв.{apt}: уровень кнопки открытия слишком близко — проверьте линию"
        )
        await reply_with_keyboard(update, f"Панель: {desc}. Выберите действие:")
        return SELECT_ACTION

    a = (l2 - l1) / 2 + l1
    b = l3 - 50
    if b < l2 + 50:
        b -= 25

    url = f"/cgi-bin/apartment_cgi?action=set&Number={apt}&HandsetUpLevel={int(a)}&DoorOpenLevel={int(b)}"
    resp = await poll_apartment(ip, url)

    if resp:
        await update.message.reply_text(
            f"✅ Уровни установлены для кв.{apt} ({desc})\nПоднятия={int(a)}, Открытия={int(b)}"
        )
        log_user_action(update.effective_user, f"Инд. уровни {l1}/{l2}/{l3} → {int(a)}/{int(b)} для кв.{apt} ({ip})")
    else:
        await update.message.reply_text("❌ Ошибка при выставлении уровней")

    context.user_data['awaiting'] = None
    await reply_with_keyboard(update, f"Панель: {desc}. Выберите действие:")
    return SELECT_ACTION


# ========= Common levels =========

async def set_common_levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = context.user_data.get('selected_ip')
    desc = context.user_data.get('selected_desc')
    text = update.message.text.strip()

    if text == "Назад":
        context.user_data['awaiting'] = None
        await reply_with_keyboard(update, f"Панель: {desc}. Выберите действие:")
        return SELECT_ACTION

    parts = text.split()
    if len(parts) != 3:
        await update.message.reply_text(
            "Введите три уровня через пробел, например: 120 340 500\nДля возврата нажмите 'Назад'",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_LEVEL

    try:
        l1, l2, l3 = map(int, parts)
    except ValueError:
        await update.message.reply_text(
            "Неверный формат. Введите три числа через пробел.",
            reply_markup=back_keyboard()
        )
        return ASK_APARTMENT_LEVEL

    if abs(l2 - l1) < 20:
        await update.message.reply_text("⚠️ Уровни l1/l2 слишком близки — проверьте измерения")
        return ASK_APARTMENT_LEVEL

    if l3 in (l1, l2) or abs(l3 - l2) < 20:
        await update.message.reply_text("⚠️ Уровень l3 слишком близко к l2 — проверьте измерения")
        return ASK_APARTMENT_LEVEL

    a = (l2 - l1) / 2 + l1
    b = l3 - 50
    if b < l2 + 20:
        await update.message.reply_text("⚠️ DoorOpenLevel слишком близко к l2 — проверьте измерения")
        return ASK_APARTMENT_LEVEL
    if b < l2 + 50:
        b -= 25

    url = f"/cgi-bin/apartment_cgi?action=levels&HandsetUpLevel={int(a)}&DoorOpenLevel={int(b)}"
    resp = await poll_apartment(ip, url)

    if resp:
        await update.message.reply_text(
            f"✅ Общие уровни установлены на панели {desc}\nПоднятия={int(a)}, Открытия={int(b)}"
        )
        log_user_action(update.effective_user, f"Общие уровни {int(a)}/{int(b)} для панели {ip}")
    else:
        await update.message.reply_text("❌ Ошибка при установке уровней")

    context.user_data['awaiting'] = None
    await reply_with_keyboard(update, f"Панель: {desc}. Выберите действие:")
    return SELECT_ACTION


# ========= Door code input =========

async def ask_door_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = context.user_data.get("selected_ip")
    desc = context.user_data.get("selected_desc")
    code = update.message.text.strip()

    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text("❌ Код должен состоять ровно из 5 цифр. Попробуйте ещё раз.")
        return ASK_DOOR_CODE

    url = f"http://{ip}/cgi-bin/intercom_cgi?action=set&DoorCode={code}"

    for login, password in CREDS:
        auth = aiohttp.BasicAuth(login, password)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url, auth=auth) as resp:
                    text = await resp.text()
                    print(f"Запрос: {url} | Код: {resp.status} | Ответ: {text}")
                    if resp.status == 200:
                        await update.message.reply_text(f"✅ Код двери успешно установлен: {code}")
                        log_user_action(update.effective_user, f"Установил код двери {code} на {ip} ({desc})")
                        break
        except Exception as e:
            log_error(f"Ошибка установки кода на {ip} ({desc}): {e}")
            await update.message.reply_text("⚠ Ошибка подключения к панели. Попробуйте позже.")
            break

    await update.message.reply_text(
        f"Панель: {desc}. Выберите действие:",
        reply_markup=get_action_keyboard()
    )
    return SELECT_ACTION


# ========= Dispatcher for ASK_APARTMENT_LEVEL state =========

async def handle_apartment_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get('awaiting')
    if awaiting == "apartment_status":
        return await ask_apartment_status(update, context)
    elif awaiting == "custom_levels":
        return await custom_levels(update, context)
    elif awaiting == "set_common_levels":
        return await set_common_levels(update, context)
    else:
        await update.message.reply_text("Сначала выберите действие.")
        return SELECT_ACTION


# ========= Ping handler =========

async def check_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = context.user_data.get("selected_ip")
    desc = context.user_data.get("selected_desc")

    await update.message.reply_text("Проверяю панель, подождите...")
    panel_status = await check_panel(ip)
    await update.message.reply_text(f"{desc}: {panel_status}", reply_markup=get_action_keyboard())
    log_user_action(update.effective_user, f"Ping на {ip} ({desc}) — {panel_status}")
    return SELECT_ACTION