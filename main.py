# main.py
import config

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters
)

from config import (
    SELECT_PANEL, SELECT_ACTION,
    ASK_APARTMENT_LEVEL, ASK_APARTMENT_CALL, ASK_DOOR_CODE,
    check_required_files, load_token_and_chat_id, TOKEN
)
from logger import setup_loggers

from handlers.conversation import start, select_panel, select_action, status, cancel
from handlers.actions import handle_apartment_level, ask_apartment_call, ask_door_code
from handlers.admin import adduser, deluser, listusers, broadcast, addpanel, editpanel, delpanel


def main():
    check_required_files()
    load_token_and_chat_id()
    setup_loggers()

    app = ApplicationBuilder().token(config.TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(r"^\s*(Старт|старт)\s*$"), start)
        ],
        states={
            SELECT_PANEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_panel)
            ],
            SELECT_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_action)
            ],
            ASK_APARTMENT_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_apartment_level)
            ],
            ASK_APARTMENT_CALL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_apartment_call)
            ],
            ASK_DOOR_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_door_code)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex(r"^\s*(Отмена|отмена)\s*$"), cancel)
        ],
        allow_reentry=True
    )

    app.add_handler(conv_handler)

    # Admin commands (outside conversation)
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("deluser", deluser))
    app.add_handler(CommandHandler("listusers", listusers))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("addpanel", addpanel))
    app.add_handler(CommandHandler("editpanel", editpanel))
    app.add_handler(CommandHandler("delpanel", delpanel))
    app.add_handler(CommandHandler("status", status))

    print("Бот запущен.")
    app.run_polling()


if __name__ == '__main__':
    main()
