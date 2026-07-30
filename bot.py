import os
import logging
import asyncio
import threading
import io
import datetime
import requests
import time
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
    """Pings the bot's own health endpoint to keep it from sleeping on Render."""
    url = os.environ.get("BOT_URL") # User should set this in Render environment variables
    if not url:
        logger.warning("BOT_URL not set. Keep-alive might not work.")
        return
        
    logger.info(f"Starting keep-alive for {url}")
    while True:
        try:
            requests.get(url, timeout=10)
            logger.info("Keep-alive ping successful")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")
        time.sleep(600) # Ping every 10 minutes

# Bot Logic
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU")
CREDIT_LINE = "💎 *הוכן והועלה על ידי אלון נושם באהבה* 👑"

# Main Menu UI
def get_main_menu():
    welcome_text = (
        "🚀 **ברוכים הבאים לבוט הקישורים המשודרג!**\n\n"
        "✨ עכשיו עם תמיכה בתיקיות משנה, זיהוי איכות, וניקוי שמות חכם.\n\n"
        "📥 שלחו קישור (או כמה) ונתחיל בעבודה!"
    )
    keyboard = [
        [InlineKeyboardButton("עזרה ❓", callback_data='help'), InlineKeyboardButton("איך להשתמש? 🛠️", callback_data='usage')]
    ]
    return f"{welcome_text}\n\n{CREDIT_LINE}", InlineKeyboardMarkup(keyboard)

# State for cancellation
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
        help_text = (
            "📖 **מה חדש בבוט?**\n\n"
            "🔍 • סריקה עמוקה של תיקיות משנה.\n"
            "🌟 • זיהוי איכות אוטומטי (4K, 1080p).\n"
            "🧹 • ניקוי שמות חכם (הסרת זבל ופרסומות).\n"
            "📦 • שליחת מספר קישורים בהודעה אחת.\n"
            "📈 • מד התקדמות ויזואלי בזמן אמת."
        )
        await query.edit_message_text(
            f"{help_text}\n\n{CREDIT_LINE}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), 
            parse_mode='Markdown'
        )
    
    elif query.data == 'usage':
        usage_text = (
            "🛠️ **איך להשתמש בבוט?**\n\n"
            "1️⃣ העתיקו קישור לתיקיית Google Drive ציבורית.\n"
            "2️⃣ ניתן לשלוח מספר קישורים בהודעה אחת.\n"
            "3️⃣ הבוט יסרוק את כל הקבצים ותיקיות המשנה.\n"
            "4️⃣ בסיום תקבלו הודעה לכל סדרה וקובץ סיכום אחד לכולן. 📄"
        )
        await query.edit_message_text(
            f"{usage_text}\n\n{CREDIT_LINE}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), 
            parse_mode='Markdown'
        )
        
    elif query.data == 'back':
        text, reply_markup = get_main_menu()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document.file_name.lower().endswith('.txt'):
        try:
            file = await context.bot.get_file(document.file_id)
            content = await file.download_as_bytearray()
            text_content = content.decode('utf-8')
            
            if len(text_content) > 4000:
                for part in [text_content[k:k+4000] for k in range(0, len(text_content), 4000)]:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(text_content)
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text("❌ מצטער, לא הצלחתי לקרוא את תוכן הקובץ. וודא שהקובץ תקין ובקידוד UTF-8.")

def get_progress_bar(current, total):
    percentage = (current / total) * 100
    filled_length = int(15 * current // total)
    bar = '█' * filled_length + '░' * (15 - filled_length)
    return f"|{bar}| {percentage:.1f}%"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    links = DRIVE_URL_PATTERN.findall(text)
    
    if not links: return

    active_tasks[user_id] = True
    total_links = len(links)
    status_msg = await update.message.reply_text(f"⏳ **זיהיתי {total_links} קישורים. מתחיל בעבודה...** ⚙️", 
                                               reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
    
    success_count = 0
    fail_count = 0
    total_episodes_all = 0
    consolidated_content = ""
    series_details = []
    loop = asyncio.get_event_loop()

    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        
        await status_msg.edit_text(f"🔄 **מעבד סדרה {i}/{total_links}...**\n📡 מתחבר לשרת...", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
        
        last_update_time = [0] # Use list for closure modification
        def progress(msg, current=None, total=None):
            # Throttle updates to Telegram (max 1 update per 2 seconds) to avoid Rate Limits
            current_time = time.time()
            if current_time - last_update_time[0] < 2.0 and current is not None:
                return
            
            last_update_time[0] = current_time
            try:
                display_msg = f"🔄 **מעבד {i}/{total_links}...**\n{msg}"
                if current is not None and total is not None:
                    bar = get_progress_bar(current, total)
                    display_msg += f"\n\n{bar}"
                
                coro = status_msg.edit_text(display_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
                asyncio.run_coroutine_threadsafe(coro, loop)
            except Exception as e:
                logger.debug(f"Progress update skipped: {e}")

        extractor = DriveExtractor(progress_callback=progress)
        results = await loop.run_in_executor(None, extractor.extract_series, link)
        
        for res in results:
            if "error" in res:
                fail_count += 1
                series_details.append(f"❌ שגיאה: {res['error']}")
                continue
            
            success_count += 1
            title = res['title']
            data = res['data']
            stats = res['stats']
            total_episodes_all += stats['total_episodes']
            
            series_details.append(f"✅ {title}: {stats['total_episodes']} פרקים")
            consolidated_content += f"🎬 סדרה: {title}\n"
            
            # Individual message for this series
            msg_output = f"🎬 **{title}**\n\n"
            for season, episodes in data.items():
                msg_output += f"📂 **{season}:**\n"
                consolidated_content += f"{season}\n"
                for ep in episodes:
                    ep_num = ep['episode'] if ep['episode'] is not None else "כללי"
                    line = f"• פרק {ep_num}: {ep['url']}"
                    msg_output += f"{line}\n"
                    consolidated_content += f"{line}\n"
                msg_output += "\n"
                consolidated_content += "\n"
            
            consolidated_content += "-"*20 + "\n\n"
            msg_output += f"\n{CREDIT_LINE}"
            
            # Send individual message
            try:
                if len(msg_output) > 4000:
                    for part in [msg_output[k:k+4000] for k in range(0, len(msg_output), 4000)]:
                        await update.message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=False)
                else:
                    await update.message.reply_text(msg_output, parse_mode='Markdown', disable_web_page_preview=False)
            except Exception as e:
                logger.error(f"Error sending series message: {e}")

    # Final summary
    summary_text = "🎊 **העבודה הסתיימה בהצלחה!** 🏁\n\n"
    summary_text += f"✅ סדרות שחולצו: {success_count}\n"
    if fail_count > 0:
        summary_text += f"⚠️ קישורים שנכשלו: {fail_count}\n"
    summary_text += f"📦 סה\"כ פרקים: {total_episodes_all}\n\n"
    summary_text += "📝 **פירוט:**\n" + "\n".join(series_details) + "\n\n"
    summary_text += CREDIT_LINE
    
    # Send final summary as a NEW message to avoid collisions with progress bar
    try:
        # Try to delete the progress message to clean up, then send summary
        await status_msg.delete()
    except: pass
    
    await update.message.reply_text(summary_text, parse_mode='Markdown')
    
    # Send consolidated file
    if success_count > 0:
        file_stream = io.BytesIO(consolidated_content.encode('utf-8'))
        file_stream.name = f"Summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        await update.message.reply_document(
            document=file_stream, 
            caption=f"📄 **קובץ הקישורים המאוחד** ✨\n\n{CREDIT_LINE}", 
            parse_mode='Markdown'
        )
    
    # Send main menu again for convenience
    text, reply_markup = get_main_menu()
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    active_tasks.pop(user_id, None)

def main():
    # Start Flask server
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Keep-Alive thread
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
