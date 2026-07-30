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
        "✨ **ברוכים הבאים למערכת חילוץ הקישורים המתקדמת!** ✨\n\n"
        "🚀 **מהירות שיא:** סריקה מקבילית עם 10 'עובדים' בו-זמנית.\n"
        "🛡️ **חסינות:** שימוש ב-20+ זהויות דפדפן למניעת חסימות.\n"
        "📂 **תמיכה מלאה:** תיקיות, תת-תיקיות וקבצים בודדים.\n\n"
        "📥 **שלחו קישור לדרייב או קובץ טקסט כדי להתחיל:**"
    )
    keyboard = [
        [InlineKeyboardButton("עזרה ומידע ❓", callback_data='help'), InlineKeyboardButton("איך זה עובד? 🛠️", callback_data='usage')]
    ]
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
        help_text = (
            "📖 **מרכז מידע**\n\n"
            "🔍 **סריקה עמוקה:** הבוט נכנס לתוך כל התיקיות ומחלץ את כל הקבצים.\n"
            "🌟 **זיהוי איכות:** מזהה אוטומטית 4K, 1080p, 720p.\n"
            "🧹 **ניקוי שמות:** מסיר פרסומות וג'אנק משמות הקבצים.\n"
            "⚡ **מהירות:** סריקה מהירה פי 10 מהגרסאות הקודמות.\n\n"
            f"{CREDIT_LINE}"
        )
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode='Markdown')
    elif query.data == 'usage':
        usage_text = (
            "🛠️ **מדריך שימוש**\n\n"
            "1️⃣ העתיקו קישור ציבורי מ-Google Drive.\n"
            "2️⃣ הדביקו כאן או שלחו קובץ .txt עם רשימת קישורים.\n"
            "3️⃣ הבוט יבצע סריקה מקבילית וישלח לכם דוח וקובץ מוכן.\n\n"
            f"{CREDIT_LINE}"
        )
        await query.edit_message_text(usage_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode='Markdown')
    elif query.data == 'back':
        text, reply_markup = get_main_menu()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def format_time(seconds):
    if seconds < 60: return f"{int(seconds)} שניות"
    return f"{int(seconds // 60)} דקות ו-{int(seconds % 60)} שניות"

def get_progress_display(msg, current, total, start_time, header=""):
    elapsed = time.time() - start_time
    
    # Advanced Progress Bar
    bar_length = 12
    if current is not None and total is not None and total > 0:
        progress = current / total
        filled = int(bar_length * progress)
        bar = '🟢' * filled + '⚪' * (bar_length - filled)
        percent = int(progress * 100)
        
        remaining = (elapsed / current) * (total - current) if current > 0 else 0
        eta = format_time(remaining) if current > 0 else "מחשב..."
        
        display = (
            f"{header}\n\n"
            f"📊 **התקדמות:** {percent}%\n"
            f"[{bar}]\n\n"
            f"✅ **הושלמו:** {current} מתוך {total}\n"
            f"⏱ **זמן שעבר:** {format_time(elapsed)}\n"
            f"⏳ **זמן נותר משוער:** {eta}\n\n"
            f"⚙️ {msg}"
        )
    else:
        display = (
            f"{header}\n\n"
            f"⏳ **מעבד נתונים...**\n"
            f"⏱ **זמן שעבר:** {format_time(elapsed)}\n\n"
            f"⚙️ {msg}"
        )
    return display

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
        if update.message.document:
            await update.message.reply_text("❌ **לא נמצאו קישורי Google Drive בקובץ.**")
        return

    active_tasks[user_id] = True
    status_msg = await update.message.reply_text(
        f"🔍 **זיהיתי {len(links)} קישורים.**\n🚀 מתחיל סריקה מקבילית...", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]])
    )
    
    process_start_time = time.time()
    loop = asyncio.get_event_loop()
    
    # Phase 1: Pre-scan to get all folder IDs
    all_targets = []
    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        
        def pre_scan_progress(msg, current=None, total=None):
            try:
                display = f"📡 **מתחבר לקישור {i}/{len(links)}...**\n{msg}"
                asyncio.run_coroutine_threadsafe(status_msg.edit_text(display, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]])), loop)
            except: pass

        extractor = DriveExtractor(progress_callback=pre_scan_progress)
        series_list = await loop.run_in_executor(None, extractor.get_series_list, link)
        if isinstance(series_list, list):
            for item in series_list:
                if isinstance(item, str) and "error" not in item: all_targets.append(item)
                elif isinstance(item, dict) and "error" not in item: all_targets.append(item.get('id', link))
        else: all_targets.append(link)

    # Phase 2: Extraction
    total_targets = len(all_targets)
    all_results = []
    
    for idx, target in enumerate(all_targets, 1):
        if not active_tasks.get(user_id, True): break
        
        last_update = [0]
        def progress(msg, current=None, total=None):
            if time.time() - last_update[0] < 1.5: return
            last_update[0] = time.time()
            try:
                header = f"🔄 **סריקה פעילה: {idx}/{total_targets}**"
                display = get_progress_display(msg, current, total, process_start_time, header)
                asyncio.run_coroutine_threadsafe(
                    status_msg.edit_text(display, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול פעולה 🛑", callback_data='cancel_all')]])), 
                    loop
                )
            except: pass

        extractor = DriveExtractor(progress_callback=progress)
        results = await loop.run_in_executor(None, extractor.extract_series, target)
        all_results.extend(results)

    # Consolidate results by title to avoid duplicates
    consolidated = {}
    success_count, fail_count, total_episodes = 0, 0, 0
    series_details = []

    for res in all_results:
        if "error" in res:
            fail_count += 1
            series_details.append(f"❌ • {res.get('title', 'לא ידוע')}: {res['error']}")
            continue
        
        title = res['title']
        if title not in consolidated:
            consolidated[title] = {"data": {}, "stats": {"total_episodes": 0, "total_seasons": 0}}
        
        # Merge seasons and episodes
        for season, episodes in res['data'].items():
            if season not in consolidated[title]['data']:
                consolidated[title]['data'][season] = []
            
            # Avoid duplicate episodes in same season
            existing_urls = {e['url'] for e in consolidated[title]['data'][season]}
            for ep in episodes:
                if ep['url'] not in existing_urls:
                    consolidated[title]['data'][season].append(ep)
                    consolidated[title]['stats']['total_episodes'] += 1
        
        consolidated[title]['stats']['total_seasons'] = len(consolidated[title]['data'])

    # Prepare final output
    final_content = ""
    all_series_messages = []
    
    for title, info in consolidated.items():
        success_count += 1
        total_episodes += info['stats']['total_episodes']
        series_details.append(f"✅ • {title}: {info['stats']['total_episodes']} פרקים")
        
        msg_output = f"🎥 **{title}**\n\n"
        final_content += f"🎬 סדרה: {title}\n"
        
        # Sort seasons
        sorted_seasons = sorted(info['data'].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999)
        
        for season in sorted_seasons:
            episodes = info['data'][season]
            episodes.sort(key=lambda x: x['episode'] if x['episode'] is not None else 999)
            
            msg_output += f"📂 **{season}**\n"
            final_content += f"{season}\n"
            
            for ep in episodes:
                line = f"פרק {ep['episode'] if ep['episode'] is not None else 'כללי'}\n{ep['url']}\n"
                msg_output += line
                final_content += line
            msg_output += "\n"
            final_content += "\n"
        
        final_content += "-"*25 + "\n\n"
        all_series_messages.append(msg_output)

    # Final Delivery UI
    summary_header = (
        f"🎊 **העבודה הושלמה בהצלחה!** 🏁\n\n"
        f"✅ **סדרות שחולצו:** {success_count}\n"
        f"❌ **נכשלו:** {fail_count}\n"
        f"📦 **סה\"כ פרקים:** {total_episodes}\n\n"
        f"📝 **פירוט:**\n" + "\n".join(series_details) + "\n\n"
        f"{CREDIT_LINE}"
    )

    try:
        await status_msg.delete()
        await update.message.reply_text(summary_header, parse_mode='Markdown')
        
        if success_count > 0:
            # Send messages in chunks if needed
            current_msg = ""
            for msg in all_series_messages:
                if len(current_msg) + len(msg) > 3800:
                    await update.message.reply_text(current_msg + f"\n{CREDIT_LINE}", parse_mode='Markdown')
                    current_msg = msg
                else:
                    current_msg += msg
            
            if current_msg:
                try:
                    await update.message.reply_text(current_msg + f"\n{CREDIT_LINE}", parse_mode='Markdown')
                except:
                    await update.message.reply_text(current_msg.replace('*', '').replace('_', '') + f"\n{CREDIT_LINE}")

            # Send full file
            file_stream = io.BytesIO(final_content.encode('utf-8'))
            file_stream.name = f"Results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            await update.message.reply_document(
                document=file_stream, 
                caption=f"📄 **קובץ הקישורים המלא** ✨\n\n{CREDIT_LINE}", 
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Final delivery failed: {e}")
        await update.message.reply_text("🎊 העבודה הסתיימה! בדוק את ההודעות והקבצים שנשלחו.")
    
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
