from telegram import Update
from telegram.ext import ContextTypes

from storage import is_admin, load_users, save_users, load_panels, save_panels
from logger import log_user_action, log_error


# ========= User management =========

async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = str(update.effective_user.id)
    if not is_admin(admin_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Использование: /adduser <user_id> <group> [Имя]")
        return

    new_user_id = context.args[0]
    group = context.args[1] if len(context.args) > 1 else "oao_service"
    name = " ".join(context.args[2:]) if len(context.args) > 2 else None

    if not name:
        try:
            chat = await context.bot.get_chat(int(new_user_id))
            name = chat.full_name
        except Exception:
            name = "Неизвестный пользователь"

    data = load_users()
    if new_user_id in data.get("roles", {}):
        await update.message.reply_text("Пользователь уже есть в списке.")
        return

    data.setdefault("roles", {})[new_user_id] = {"name": name, "group": group}
    save_users(data)
    await update.message.reply_text(f"Пользователь {name} ({new_user_id}) добавлен в группу {group}.")
    log_user_action(update.effective_user, f"Добавил пользователя {name} ({new_user_id}) → {group}")


async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    data = load_users()
    roles = data.get("roles", {})
    admins = data.get("admins", [])

    if not roles and not admins:
        await update.message.reply_text("Список пользователей пуст.")
        return

    msg = "Список пользователей:\n"
    for uid, info in roles.items():
        is_adm = "👑 " if uid in admins else ""
        name = info.get("name", "—") if isinstance(info, dict) else info
        group = info.get("group", "—") if isinstance(info, dict) else "—"
        msg += f"{is_adm}{name} (ID: {uid}) — {group}\n"

    await update.message.reply_text(msg)
    log_user_action(update.effective_user, "Запросил список пользователей")


async def deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = str(update.effective_user.id)
    if not is_admin(admin_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /deluser <user_id>")
        return

    target_id = context.args[0]
    data = load_users()

    if target_id not in data.get("roles", {}):
        await update.message.reply_text(f"Пользователь с ID {target_id} не найден.")
        return

    deleted = data["roles"].pop(target_id)
    deleted_name = deleted.get("name", target_id) if isinstance(deleted, dict) else deleted
    if target_id in data.get("admins", []):
        data["admins"].remove(target_id)

    save_users(data)
    await update.message.reply_text(f"Пользователь {deleted_name} (ID {target_id}) удалён.")
    log_user_action(update.effective_user, f"Удалил пользователя {deleted_name} ({target_id})")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = str(update.effective_user.id)
    if not is_admin(admin_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Использование: /broadcast <текст сообщения>")
        return

    data = load_users()
    count = 0
    for uid, info in data.get("roles", {}).items():
        name = info.get("name", uid) if isinstance(info, dict) else info
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            count += 1
        except Exception as e:
            log_error(f"Ошибка при отправке {name} ({uid}): {e}")

    await update.message.reply_text(f"Отправлено уведомление {count} пользователям.")
    log_user_action(update.effective_user, f"Рассылка: '{message}' ({count} получателей)")


# ========= Panel management =========

async def addpanel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Использование: /addpanel <ip> <адрес>")
        return

    ip = context.args[0]
    address = " ".join(context.args[1:])

    panels = load_panels()
    if ip in panels:
        await update.message.reply_text(f"Панель с IP {ip} уже существует.")
        return

    panels[ip] = address
    save_panels(panels)
    await update.message.reply_text(f"Панель с IP {ip} добавлена: {address}")
    log_user_action(update.effective_user, f"Добавил панель {ip} → {address}")


async def editpanel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("Использование: /editpanel <старый_ip> <новый_ip> <новый_адрес>")
        return

    old_ip, new_ip = context.args[0], context.args[1]
    new_address = " ".join(context.args[2:])

    panels = load_panels()
    if old_ip not in panels:
        await update.message.reply_text(f"Панель с IP {old_ip} не найдена.")
        return

    if new_ip in panels and new_ip != old_ip:
        await update.message.reply_text(f"Панель с IP {new_ip} уже существует. Выберите другой IP.")
        return

    del panels[old_ip]
    panels[new_ip] = new_address
    save_panels(panels)
    await update.message.reply_text(f"Панель обновлена: {new_ip} -> {new_address}")
    log_user_action(update.effective_user, f"Изменил панель {old_ip} → {new_ip}, {new_address}")


async def delpanel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /delpanel <ip>")
        return

    ip = context.args[0]
    panels = load_panels()
    if ip not in panels:
        await update.message.reply_text(f"Панель с IP {ip} не найдена.")
        return

    del panels[ip]
    save_panels(panels)
    await update.message.reply_text(f"Панель с IP {ip} удалена.")
    log_user_action(update.effective_user, f"Удалил панель {ip}")