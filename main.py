# main.py

import logging
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Impor fungsi handler Anda
from handlers.start import start
from handlers.token_select import token_prompt, token_select
from handlers.timeframe_select import timeframe_select
from handlers.analysis import start_analysis_callback
from utils.db import init_db
# Impor 'load_coin_list' sudah tidak diperlukan lagi, jadi kita hapus.

# Definisikan state untuk ConversationHandler
SELECTING_ACTION, SELECTING_TOKEN, SELECTING_TIMEFRAME = range(3)

async def post_init_setup(application):
    """
    Fungsi ini akan dijalankan setelah Application dibuat,
    tapi sebelum polling dimulai. Tempat yang sempurna untuk async setup.
    """
    await application.bot.set_my_commands([
        BotCommand("start", "🚀 Kembali ke Menu Utama")
    ])

def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    
    # Fungsi load_coin_list() sudah dihapus dari sini.
    init_db()
    
    app = (
        ApplicationBuilder()
        .token("7207657126:AAF53TTiNB_VIQcl_8bk5DfYKgZ6laX8izU")
        .post_init(post_init_setup)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex('^Pilih Token Lain$'), token_prompt)
        ],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.Regex('^▶️ Mulai$'), token_prompt)
            ],
            SELECTING_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, token_select)
            ],
            SELECTING_TIMEFRAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, timeframe_select)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(start_analysis_callback, pattern="start_analysis"))
    
    print("Bot is running...")
    
    app.run_polling()

if __name__ == '__main__':
    main()