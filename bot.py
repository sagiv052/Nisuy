import os
import logging
import asyncio
import threading
import io
import datetime
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
        [InlineKeyboardButton("עזרה ❓", callback_data='help')],
        [InlineKeyboardButton("איך להשתמש? 🛠️", callback_data='usage')]
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
    
    elif query.data == 'help':
        help_text = (
            "📖 **מה חדש בבוט?**\n\n"
            "🔍 • סריקה עמוקה של תיקיות משנה.\n"
            "🌟 • זיהוי איכות אוטומטי (4K, 1080p).\n"
            "🧹 • ניקוי שמות חכם (הסרת זבל ופרסומות).\n"
            "📦 • שליחת מספר קישורים בהודעה אחת.\n"
            "📊 • דוח סיכום מאוחד לכל הקישורים."
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
            await update.message.reply_text("❌ מצטער, לא הצלחתי לקרוא את תוכן הקובץ.")

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
    
    consolidated_content = f"📊 דוח סיכום חילוץ - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    consolidated_content += "="*40 + "\n\n"
    
    series_details = []
    loop = asyncio.get_event_loop()

    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        
        await status_msg.edit_text(f"🔄 **מעבד סדרה {i}/{total_links}...**\n📡 מתחבר לשרת...", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
        
        def progress(msg):
            # Safer progress update using the captured loop
            try:
                coro = status_msg.edit_text(f"🔄 **מעבד {i}/{total_links}...**\n{msg}", 
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]]))
                asyncio.run_coroutine_threadsafe(coro, loop)
            except Exception as e:
                logger.error(f"Progress update error: {e}")

        extractor = DriveExtractor(progress_callback=progress)
        res = await loop.run_in_executor(None, extractor.extract_series, link)
        
        if "error" in res:
            fail_count += 1
            series_details.append(f"❌ קישור {i}: שגיאה - {res['error']}")
            consolidated_content += f"❌ סדרה {i} (נכשל):\n🔗 קישור: {link}\n⚠️ שגיאה: {res['error']}\n\n"
            consolidated_content += "-"*20 + "\n\n"
            continue
        
        success_count += 1
        title = res['title']
        data = res['data']
        stats = res['stats']
        total_episodes_all += stats['total_episodes']
        
        series_details.append(f"✅ {title}: {stats['total_episodes']} פרקים")
        
        # Add to consolidated file
        consolidated_content += f"🎬 סדרה: {title}\n"
        consolidated_content += f"🔗 קישור מקור: {link}\n"
        consolidated_content += f"📦 סה\"כ פרקים: {stats['total_episodes']}\n\n"
        
        # Individual message for this series
        msg_output = f"🎬 **{title}**\n\n"
        for season, episodes in data.items():
            msg_output += f"📂 **{season}:**\n"
            consolidated_content += f"[{season}]\n"
            for ep in episodes:
                ep_num = ep['episode'] if ep['episode'] is not None else "כללי"
                line = f"פרק {ep_num}: {ep['url']}"
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

    # Prepare final summary
    summary_text = "🎊 **העבודה הסתיימה בהצלחה!** 🏁\n\n"
    summary_text += f"✅ סדרות שחולצו: {success_count}\n"
    if fail_count > 0:
        summary_text += f"⚠️ קישורים שנכשלו: {fail_count}\n"
    summary_text += f"📦 סה\"כ פרקים בכל הסדרות: {total_episodes_all}\n\n"
    
    summary_text += "📝 **פירוט:**\n" + "\n".join(series_details) + "\n\n"
    summary_text += CREDIT_LINE
    
    # Update status message to final summary
    try:
        await status_msg.edit_text(summary_text, parse_mode='Markdown')
    except:
        await update.message.reply_text(summary_text, parse_mode='Markdown')
    
    # Send consolidated file if there was at least one success
    if success_count > 0 or fail_count > 0:
        summary_header = f"--- סיכום כללי ---\n"
        summary_header += f"סדרות בהצלחה: {success_count}\n"
        summary_header += f"סדרות שנכשלו: {fail_count}\n"
        summary_header += f"סה\"כ פרקים: {total_episodes_all}\n"
        summary_header += "="*40 + "\n\n"
        
        final_file_content = summary_header + consolidated_content
        file_stream = io.BytesIO(final_file_content.encode('utf-8'))
        file_stream.name = f"Summary_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        
        await update.message.reply_document(
            document=file_stream, 
            caption=f"📄 **דוח סיכום מאוחד**\nמכיל את כל הקישורים והפרקים שחולצו. ✨\n\n{CREDIT_LINE}", 
            parse_mode='Markdown'
        )

        # שליחת תוכן הקובץ גם כהודעת טקסט
        try:
            if len(final_file_content) > 4000:
                for part in [final_file_content[k:k+4000] for k in range(0, len(final_file_content), 4000)]:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(final_file_content)
        except Exception as e:
            logger.error(f"Error sending consolidated text message: {e}")
    
    active_tasks.pop(user_id, None)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_document))
    application.run_polling()

if __name__ == '__main__':
    main()
