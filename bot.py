import os
import logging
import asyncio
import threading
import io
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from extractor import DriveExtractor, DRIVE_URL_PATTERN

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask for Render Health Check
app = Flask(__name__)
@app.route('/')
def health(): return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Bot Logic
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU")
CREDIT_LINE = "❤️ *הוכן והועלה על ידי אלון נושם באהבה*"

# State for cancellation
active_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **ברוכים הבאים לבוט הקישורים המשודרג!**\n\n"
        "עכשיו עם תמיכה בתיקיות משנה, זיהוי איכות, וניקוי שמות חכם.\n\n"
        "שלחו קישור (או כמה) ונתחיל!"
    )
    keyboard = [[InlineKeyboardButton("עזרה ❓", callback_data='help')], [InlineKeyboardButton("איך להשתמש? 🛠️", callback_data='usage')]]
    await update.message.reply_text(f"{welcome_text}\n\n{CREDIT_LINE}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == 'cancel_all':
        active_tasks[user_id] = False
        await query.edit_message_text("🛑 **הפעולה בוטלה על ידי המשתמש.**")
    elif query.data == 'help':
        help_text = "📖 **מה חדש?**\n• סריקה עמוקה של תיקיות.\n• זיהוי איכות (4K, 1080p).\n• ניקוי שמות אוטומטי.\n• שליחת מספר קישורים במכה."
        await query.edit_message_text(f"{help_text}\n\n{CREDIT_LINE}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode='Markdown')
    elif query.data == 'back':
        await start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    links = DRIVE_URL_PATTERN.findall(text)
    
    if not links: return

    active_tasks[user_id] = True
    total = len(links)
    status_msg = await update.message.reply_text(f"⏳ **זיהיתי {total} קישורים. מתחיל בעבודה...**", 
                                               reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
    
    success_count = 0
    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        
        await status_msg.edit_text(f"🔄 **מעבד {i}/{total}...**\nסורק תיקיות וקבצים (זה עשוי לקחת זמן)", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
        
        def progress(msg):
            # Silent progress updates
            try: asyncio.run_coroutine_threadsafe(status_msg.edit_text(f"🔄 **מעבד {i}/{total}...**\n{msg}"), asyncio.get_event_loop())
            except: pass

        extractor = DriveExtractor(progress_callback=progress)
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, extractor.extract_series, link)
        
        if "error" in res:
            await update.message.reply_text(f"❌ **שגיאה בקישור {i}:** {res['error']}")
            continue
        
        success_count += 1
        title = res['title']
        data = res['data']
        stats = res['stats']
        
        msg_output = f"🎬 **{title}**\n\n"
        file_content = f"--- {title} ---\nסה\"כ: {stats['total_episodes']} פרקים\n\n"
        
        for season, episodes in data.items():
            msg_output += f"📂 **{season}:**\n"
            file_content += f"[{season}]\n"
            for ep in episodes:
                msg_output += f"• [{ep['name']}]({ep['url']})\n"
                file_content += f"{ep['name']}: {ep['url']}\n"
            msg_output += "\n"
            file_content += "\n"
        
        msg_output += f"\n{CREDIT_LINE}"
        
        if len(msg_output) > 4000:
            for part in [msg_output[i:i+4000] for i in range(0, len(msg_output), 4000)]:
                await update.message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text(msg_output, parse_mode='Markdown', disable_web_page_preview=True)
        
        file_stream = io.BytesIO(file_content.encode('utf-8'))
        file_stream.name = f"{title.replace(' ', '_')}.txt"
        await update.message.reply_document(document=file_stream, caption=f"📄 {title}\n{CREDIT_LINE}", parse_mode='Markdown')

    final_text = f"🏁 **העבודה הסתיימה!**\n✅ הצלחנו לחלץ {success_count} סדרות.\n\n{CREDIT_LINE}"
    await status_msg.edit_text(final_text, parse_mode='Markdown')
    active_tasks.pop(user_id, None)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
