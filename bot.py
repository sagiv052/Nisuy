import os
import logging
import asyncio
import threading
import io
import datetime
import requests
import time
import html
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
def health(): return "Bot is running! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Keep-Alive Mechanism for Render
def keep_alive():
    url = os.environ.get("BOT_URL")
    if not url: return
    while True:
        try:
            requests.get(url, timeout=10)
        except: pass
        time.sleep(600)

# Bot Logic
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU")
CREDIT_LINE = "💎 הוכן והועלה על ידי אלון נושם באהבה 👑"

def get_main_menu():
    welcome_text = (
        "🚀 **ברוכים הבאים לבוט הקישורים המשודרג!**\n\n"
        "✨ עכשיו עם תמיכה בתיקיות משנה, זיהוי איכות, וניקוי שמות חכם.\n\n"
        "📥 שלחו קישור (או כמה) ונתחיל בעבודה!"
    )
    keyboard = [[InlineKeyboardButton("עזרה ❓", callback_data='help'), InlineKeyboardButton("איך להשתמש? 🛠️", callback_data='usage')]]
    return f"{welcome_text}\n\n{CREDIT_LINE}", InlineKeyboardMarkup(keyboard)

active_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, reply_markup = get_main_menu()
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == 'cancel_all':
        active_tasks[user_id] = False
        await query.edit_message_text("🛑 **הפעולה בוטלה על ידי המשתמש.**")
        await asyncio.sleep(2)
        text, reply_markup = get_main_menu()
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == 'help':
        await query.edit_message_text(f"📖 **מה חדש?**\n\n🔍 סריקה עמוקה.\n🌟 זיהוי איכות.\n🧹 ניקוי שמות.\n📦 תמיכה במאות סדרות.\n📈 מד זמן ו-ETA.\n\n{CREDIT_LINE}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode='Markdown')
    elif query.data == 'usage':
        await query.edit_message_text(f"🛠️ **איך להשתמש?**\n\n1️⃣ שלחו קישור לדרייב ציבורי.\n2️⃣ הבוט יסרוק הכל.\n3️⃣ תקבלו דוח וקובץ בסיום.\n\n{CREDIT_LINE}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode='Markdown')
    elif query.data == 'back':
        text, reply_markup = get_main_menu()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def format_time(seconds):
    if seconds < 60: return f"{int(seconds)} שניות"
    return f"{int(seconds // 60)} דקות ו-{int(seconds % 60)} שניות"

def get_progress_bar(current, total, start_time):
    percentage = (current / total) * 100
    filled = int(15 * current // total)
    bar = '█' * filled + '░' * (15 - filled)
    elapsed = time.time() - start_time
    if current > 0:
        remaining = (elapsed / current) * total - elapsed
        time_info = f"\n⏱ **זמן שעבר:** {format_time(elapsed)}\n⏳ **זמן משוער לסיום:** {format_time(remaining)}"
    else:
        time_info = f"\n⏱ **זמן שעבר:** {format_time(elapsed)}\n⏳ **מחשב זמן...**"
    return f"|{bar}| {percentage:.1f}%{time_info}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_links(update, context, update.message.text)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document.file_name.lower().endswith(".txt"):
        status_msg = await update.message.reply_text("⏳ **קורא את הקובץ המצורף...**")
        try:
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            text = file_content.decode('utf-8', errors='ignore')
            await status_msg.delete()
            await process_links(update, context, text)
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await status_msg.edit_text("❌ **שגיאה בקריאת הקובץ.**")

async def process_links(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    if not text: return
    user_id = update.message.from_user.id
    links = DRIVE_URL_PATTERN.findall(text)
    if not links:
        if update.message.document: # If it was a file but no links found
            await update.message.reply_text("❌ **לא נמצאו קישורי Google Drive בקובץ.**")
        return

    active_tasks[user_id] = True
    status_msg = await update.message.reply_text(f"⏳ **זיהיתי {len(links)} קישורים. מתחיל...**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
    
    success_count, fail_count, total_episodes_all = 0, 0, 0
    consolidated_content, series_details, all_series_messages = "", [], []
    total_msg_length = 0
    process_start_time = time.time()
    loop = asyncio.get_event_loop()

    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        last_update = [0]
        def progress(msg, current=None, total=None):
            if time.time() - last_update[0] < 3.0 and current is not None: return
            last_update[0] = time.time()
            try:
                display = f"🔄 **מעבד {i}/{len(links)}...**\n{msg}"
                if current and total: display += f"\n\n{get_progress_bar(current, total, process_start_time)}"
                asyncio.run_coroutine_threadsafe(status_msg.edit_text(display, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]])), loop)
            except: pass

        extractor = DriveExtractor(progress_callback=progress)
        results = await loop.run_in_executor(None, extractor.extract_series, link)
        
        for res in results:
            if "error" in res:
                fail_count += 1
                series_details.append(f"❌ • • {res.get('title', 'סדרה לא ידועה')}: שגיאה ({res['error']})")
                continue
            success_count += 1
            title, data, stats = res['title'], res['data'], res['stats']
            total_episodes_all += stats['total_episodes']
            series_details.append(f"✅ • • {title}: {stats['total_episodes']} פרקים")
            consolidated_content += f"🎬 סדרה: {title}\n"
            msg_output = f"🎥 **{title}**\n\n"
            for season, episodes in data.items():
                msg_output += f"📂 **{season}**\n"
                consolidated_content += f"{season}\n"
                for ep in episodes:
                    line = f"פרק {ep['episode'] if ep['episode'] is not None else 'כללי'}\n{ep['url']}\n"
                    msg_output += line
                    consolidated_content += line
                msg_output += "\n"
                consolidated_content += "\n"
            consolidated_content += "-"*20 + "\n\n"
            all_series_messages.append(msg_output)
            total_msg_length += len(msg_output) + 50

    # Prepare final delivery
    base_summary = f"🎊 <b>העבודה הסתיימה בהצלחה!</b> 🏁\n\n✅ סדרות שחולצו: {success_count}\n❌ סדרות שנכשלו: {fail_count}\n📦 סה\"כ פרקים: {total_episodes_all}\n\n"
    details_text = "📝 <b>פירוט:</b>\n" + "\n".join(series_details) + "\n\n"
    credit_html = html.escape(CREDIT_LINE).replace("💎", "💎").replace("👑", "👑")
    full_report = base_summary + details_text + credit_html
    
    if len(full_report) > 4000:
        summary_to_send = base_summary + "⚠️ <b>פירוט הסדרות ארוך מדי להודעה, הוא נמצא בתוך הקובץ המצורף.</b> 📄\n\n" + credit_html
        consolidated_content = "=== דוח סיכום ===\n" + "\n".join(series_details) + "\n\n" + "="*30 + "\n\n" + consolidated_content
    else:
        summary_to_send = full_report

    # DELIVERY PHASE - Using a safe try-except to ensure we don't "disappear"
    try:
        # 1. Send summary first
        await update.message.reply_text(summary_to_send, parse_mode='HTML')
        
        # 2. Delete progress message only after successful summary
        try: await status_msg.delete()
        except: pass

        # 3. Send individual messages if they fit
        if success_count > 0 and total_msg_length <= 4000:
            combined_msg = "\n".join(all_series_messages) + f"\n{CREDIT_LINE}"
            try: await update.message.reply_text(combined_msg, parse_mode='Markdown')
            except: await update.message.reply_text(combined_msg.replace('*', '').replace('_', ''))

        # 4. Send document
        if success_count > 0:
            file_stream = io.BytesIO(consolidated_content.encode('utf-8'))
            file_stream.name = f"Summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            await update.message.reply_document(document=file_stream, caption=f"📄 <b>קובץ הקישורים והדוח המלא</b> ✨\n\n{credit_html}", parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Final delivery failed: {e}")
        await update.message.reply_text(f"🎊 העבודה הסתיימה! הצלחנו לחלץ {success_count} סדרות.\n(חלק מההודעות היו ארוכות מדי או הכילו תווים בעייתיים, בדוק את הקובץ המצורף אם נשלח).")
    
    text, reply_markup = get_main_menu()
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    active_tasks.pop(user_id, None)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_document))
    logger.info("Bot started...")
    application.run_polling()

if __name__ == '__main__':
    main()
