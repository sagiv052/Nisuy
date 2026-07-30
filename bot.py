import os
import logging
import asyncio
import threading
import io
import datetime
import requests
import time
import html
import re
import sys
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from extractor import DriveExtractor, DRIVE_URL_PATTERN

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Flask for Render Health Check
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is alive and kicking! 🚀", 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask server on port {port}...")
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server failed: {e}")

# Improved Keep-Alive Mechanism
def keep_alive():
    url = os.environ.get("BOT_URL")
    if not url:
        logger.warning("BOT_URL not set! Keep-alive might not work on Render Free Tier.")
        return
    
    logger.info(f"Starting keep-alive pings to {url}...")
    while True:
        try:
            r = requests.get(url, timeout=20)
            logger.info(f"Keep-alive ping status: {r.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")
        time.sleep(300)

# Bot Config
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU")

# --- CUSTOM EMOJI CONFIG ---
# To use custom emojis, use the format: <tg-emoji emoji-id="5368324170671202286">🚀</tg-emoji>
# You can get the emoji-id by sending the emoji to a bot like @raw_data_bot
DRUG_EMOJI = '<tg-emoji emoji-id="5368324170671202286">💊</tg-emoji>' # Example ID, replace with real ones from your pack
STAR_EMOJI = '✨'
# ---------------------------

CREDIT_LINE = f"💎 הוכן והועלה על ידי אלון נושם באהבה 👑"

def get_main_menu():
    text = (
        f"{STAR_EMOJI} <b>מערכת חילוץ סדרות מתקדמת v3.2</b> {STAR_EMOJI}\n\n"
        "🚀 <b>ביצועים:</b> סריקה מקבילית (22 Workers)\n"
        "🛡️ <b>חסינות:</b> 22 זהויות דפדפן נפרדות (Multi-Session)\n"
        "📂 <b>תמיכה:</b> תיקיות, תת-תיקיות וקבצים בודדים\n\n"
        "📥 <b>שלחו קישור או קובץ טקסט כדי להתחיל:</b>"
    )
    keyboard = [[
        InlineKeyboardButton("עזרה ❓", callback_data='help'), 
        InlineKeyboardButton("איך להשתמש 🛠️", callback_data='usage')
    ]]
    return f"{text}\n\n{CREDIT_LINE}", InlineKeyboardMarkup(keyboard)

active_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, reply_markup = get_main_menu()
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == 'cancel_all':
        active_tasks[user_id] = False
        await query.edit_message_text("🛑 <b>הפעולה בוטלה.</b>", parse_mode=ParseMode.HTML)
    elif query.data == 'back':
        text, reply_markup = get_main_menu()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif query.data == 'help':
        text = "📖 <b>עזרה</b>\n\nשלחו קישור לתיקיית Google Drive או קובץ טקסט המכיל קישורים. הבוט יחלץ את כל הפרקים ויסדר אותם לפי עונות.\n\n" + CREDIT_LINE
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode=ParseMode.HTML)
    elif query.data == 'usage':
        text = "🛠️ <b>איך להשתמש</b>\n\n1. וודאו שהתיקייה בדרייב ציבורית.\n2. העתיקו את הקישור.\n3. הדביקו כאן בבוט.\n4. המתינו לסיום הסריקה.\n\n" + CREDIT_LINE
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]), parse_mode=ParseMode.HTML)

def format_time(seconds):
    if seconds < 60: return f"{int(seconds)} שניות"
    return f"{int(seconds // 60)} דקות ו-{int(seconds % 60)} שניות"

def get_progress_display(msg, current, total_links, current_link_idx, start_time):
    elapsed = time.time() - start_time
    bar_len = 10
    progress_val = min(current / 50.0, 1.0) if current else 0
    filled = int(bar_len * progress_val)
    bar = '🟢' * filled + '⚪' * (bar_len - filled)
    
    display = (
        f"🔄 <b>מעבד קישור {current_link_idx} מתוך {total_links}</b>\n\n"
        f"📊 <b>סטטוס סריקה:</b>\n"
        f"[{bar}]\n\n"
        f"✅ <b>קבצים שנמצאו:</b> {current if current else 0}\n"
        f"⏱ <b>זמן שעבר:</b> {format_time(elapsed)}\n\n"
        f"⚙️ {msg}"
    )
    return display

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    await process_links(update, context, update.message.text)

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document: return
    if update.message.document.file_name.lower().endswith(".txt"):
        status_msg = await update.message.reply_text("⏳ <b>קורא את הקובץ המצורף...</b>", parse_mode=ParseMode.HTML)
        try:
            f = await context.bot.get_file(update.message.document.file_id)
            c = await f.download_as_bytearray()
            text = c.decode('utf-8', 'ignore')
            await status_msg.delete()
            await process_links(update, context, text)
        except Exception as e:
            logger.error(f"Error handling doc: {e}")
            await status_msg.edit_text("❌ שגיאה בקריאת הקובץ.")

async def process_links(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.message.from_user.id
    links = DRIVE_URL_PATTERN.findall(text)
    if not links: return

    active_tasks[user_id] = True
    status_msg = await update.message.reply_text("📡 <b>מתחבר למערכת...</b>", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול 🛑", callback_data='cancel_all')]]),
                                                parse_mode=ParseMode.HTML)
    
    process_start_time = time.time()
    loop = asyncio.get_event_loop()
    
    all_targets = []
    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        try:
            await status_msg.edit_text(f"🔍 <b>מנתח קישור {i}/{len(links)}...</b>", parse_mode=ParseMode.HTML)
            extractor = DriveExtractor()
            targets = await loop.run_in_executor(None, extractor.get_series_list, link)
            all_targets.extend(targets)
        except Exception as e:
            logger.error(f"Pre-scan error: {e}")
            all_targets.append(link)

    all_results = []
    total_targets = len(all_targets)
    for idx, target in enumerate(all_targets, 1):
        if not active_tasks.get(user_id, True): break
        
        last_upd = [0]
        def progress(msg, current=None, total=None):
            if time.time() - last_upd[0] < 2.0: return
            last_upd[0] = time.time()
            try:
                display = get_progress_display(msg, current, total_targets, idx, process_start_time)
                asyncio.run_coroutine_threadsafe(status_msg.edit_text(display, 
                                                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול 🛑", callback_data='cancel_all')]]),
                                                                   parse_mode=ParseMode.HTML), loop)
            except: pass

        try:
            extractor = DriveExtractor(progress_callback=progress)
            res = await loop.run_in_executor(None, extractor.extract_series, target)
            all_results.extend(res)
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            all_results.append({"error": str(e), "title": "שגיאה"})

    consolidated = {}
    success, fail, total_eps = 0, 0, 0
    details = []
    for res in all_results:
        if not res or "error" in res:
            fail += 1
            details.append(f"❌ • {res.get('title', 'לא ידוע') if res else 'לא ידוע'}: {res.get('error', 'שגיאה לא ידועה') if res else 'שגיאה'}")
            continue
        title = res['title']
        if title not in consolidated: consolidated[title] = {"data": {}, "eps": 0}
        for s, eps in res['data'].items():
            if s not in consolidated[title]['data']: consolidated[title]['data'][s] = []
            urls = {e['url'] for e in consolidated[title]['data'][s]}
            for e in eps:
                if e['url'] not in urls:
                    consolidated[title]['data'][s].append(e)
                    consolidated[title]['eps'] += 1
    
    report = f"🎊 <b>העבודה הושלמה!</b> 🏁\n\n"
    final_txt = ""
    series_msgs = []
    for title, info in consolidated.items():
        success += 1
        total_eps += info['eps']
        details.append(f"✅ • {title}: {info['eps']} פרקים")
        msg = f"🎥 <b>{title}</b>\n\n"
        final_txt += f"🎬 סדרה: {title}\n"
        for s in sorted(info['data'].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999):
            msg += f"📂 <b>{s}</b>\n"
            final_txt += f"{s}\n"
            for e in sorted(info['data'][s], key=lambda x: x['episode'] if x['episode'] is not None else 999):
                line = f"פרק {e['episode'] if e['episode'] is not None else 'כללי'}\n{e['url']}\n"
                msg += line
                final_txt += line
            msg += "\n"
            final_txt += "\n"
        final_txt += "="*25 + "\n\n"
        series_msgs.append(msg)

    report += f"✅ סדרות: {success}\n❌ נכשלו: {fail}\n📦 פרקים: {total_eps}\n\n📝 <b>פירוט:</b>\n" + "\n".join(details)
    
    try:
        await status_msg.delete()
        # 1. Send the summary report
        await update.message.reply_text(report + f"\n\n{CREDIT_LINE}", parse_mode=ParseMode.HTML)
        
        # 2. Send the TXT file IMMEDIATELY after the report
        if success > 0 or final_txt.strip():
            try:
                f = io.BytesIO(final_txt.encode('utf-8'))
                f.name = f"Results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                await update.message.reply_document(f, caption=f"📄 <b>דוח מלא (קובץ טקסט)</b>\n\n{CREDIT_LINE}", parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to send document: {e}")
        
        # 3. Send preview messages with rate-limit protection
        # Threshold: If more than 10 series, skip individual messages to avoid flooding
        if len(series_msgs) > 10:
            await update.message.reply_text(f"⚠️ <b>נמצאו {len(series_msgs)} סדרות.</b>\nבשל הכמות הגדולה, הפירוט המלא מופיע בקובץ הטקסט המצורף בלבד כדי למנוע חסימות.", parse_mode=ParseMode.HTML)
        else:
            for m in series_msgs:
                try:
                    if len(m) > 4000:
                        parts = [m[i:i+4000] for i in range(0, len(m), 4000)]
                        for p in parts:
                            await update.message.reply_text(p, parse_mode=ParseMode.HTML)
                            await asyncio.sleep(0.5)
                    else:
                        await update.message.reply_text(m + f"\n{CREDIT_LINE}", parse_mode=ParseMode.HTML)
                    
                    await asyncio.sleep(0.8)
                except Exception as e:
                    logger.error(f"Error sending series preview: {e}")
                
    except Exception as e:
        logger.error(f"Final delivery error: {e}")
    
    active_tasks.pop(user_id, None)

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    try:
        logger.info("Initializing Telegram Bot...")
        app_tg = Application.builder().token(TOKEN).build()
        app_tg.add_handler(CommandHandler("start", start))
        app_tg.add_handler(CallbackQueryHandler(handle_callback))
        app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app_tg.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
        
        logger.info("Bot is starting polling...")
        app_tg.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
