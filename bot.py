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

# Keep-Alive Mechanism
def keep_alive():
    url = os.environ.get("BOT_URL")
    if not url: return
    while True:
        try: requests.get(url, timeout=10)
        except: pass
        time.sleep(600)

# Bot Config
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU")
CREDIT_LINE = "💎 הוכן והועלה על ידי אלון נושם באהבה 👑"

def get_main_menu():
    text = (
        "✨ **מערכת חילוץ סדרות מתקדמת v3.0** ✨\n\n"
        "🚀 **ביצועים:** סריקה מקבילית (10 Workers)\n"
        "🛡️ **חסינות:** 22 זהויות דפדפן משתנות\n"
        "📂 **תמיכה:** תיקיות, תת-תיקיות וקבצים בודדים\n\n"
        "📥 **שלחו קישור או קובץ טקסט כדי להתחיל:**"
    )
    keyboard = [[InlineKeyboardButton("עזרה ❓", callback_data='help'), InlineKeyboardButton("איך להשתמש 🛠️", callback_data='usage')]]
    return f"{text}\n\n{CREDIT_LINE}", InlineKeyboardMarkup(keyboard)

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
        await query.edit_message_text("🛑 **הפעולה בוטלה.**")
    elif query.data == 'back':
        text, reply_markup = get_main_menu()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.edit_message_text("⚙️ פונקציה זו תתווסף בקרוב.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("חזרה 🏠", callback_data='back')]]))

def format_time(seconds):
    if seconds < 60: return f"{int(seconds)} שניות"
    return f"{int(seconds // 60)} דקות ו-{int(seconds % 60)} שניות"

def get_progress_display(msg, current, total_links, current_link_idx, start_time):
    elapsed = time.time() - start_time
    bar_len = 10
    
    # Estimate progress based on found files (arbitrary total of 50 for bar if unknown)
    progress_val = min(current / 50.0, 1.0) if current else 0
    filled = int(bar_len * progress_val)
    bar = '🟢' * filled + '⚪' * (bar_len - filled)
    
    display = (
        f"🔄 **מעבד קישור {current_link_idx} מתוך {total_links}**\n\n"
        f"📊 **סטטוס סריקה:**\n"
        f"[{bar}]\n\n"
        f"✅ **קבצים שנמצאו:** {current if current else 0}\n"
        f"⏱ **זמן שעבר:** {format_time(elapsed)}\n\n"
        f"⚙️ {msg}"
    )
    return display

async def process_links(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    if not text: return
    user_id = update.message.from_user.id
    links = DRIVE_URL_PATTERN.findall(text)
    if not links: return

    active_tasks[user_id] = True
    status_msg = await update.message.reply_text("📡 **מתחבר למערכת...**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול 🛑", callback_data='cancel_all')]]))
    
    process_start_time = time.time()
    loop = asyncio.get_event_loop()
    
    # Phase 1: Pre-scan
    all_targets = []
    for i, link in enumerate(links, 1):
        if not active_tasks.get(user_id, True): break
        await status_msg.edit_text(f"🔍 **מנתח קישור {i}/{len(links)}...**")
        extractor = DriveExtractor()
        targets = await loop.run_in_executor(None, extractor.get_series_list, link)
        all_targets.extend(targets)

    # Phase 2: Extract
    all_results = []
    total_targets = len(all_targets)
    for idx, target in enumerate(all_targets, 1):
        if not active_tasks.get(user_id, True): break
        
        last_upd = [0]
        def progress(msg, current=None, total=None):
            if time.time() - last_upd[0] < 1.5: return
            last_upd[0] = time.time()
            try:
                display = get_progress_display(msg, current, total_targets, idx, process_start_time)
                asyncio.run_coroutine_threadsafe(status_msg.edit_text(display, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ביטול 🛑", callback_data='cancel_all')]])), loop)
            except: pass

        extractor = DriveExtractor(progress_callback=progress)
        res = await loop.run_in_executor(None, extractor.extract_series, target)
        all_results.extend(res)

    # Consolidation
    consolidated = {}
    success, fail, total_eps = 0, 0, 0
    details = []
    for res in all_results:
        if "error" in res:
            fail += 1
            details.append(f"❌ • {res.get('title', 'לא ידוע')}: {res['error']}")
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
    
    # Final Output
    report = f"🎊 **העבודה הושלמה!** 🏁\n\n"
    final_txt = ""
    series_msgs = []
    for title, info in consolidated.items():
        success += 1
        total_eps += info['eps']
        details.append(f"✅ • {title}: {info['eps']} פרקים")
        msg = f"🎥 **{title}**\n\n"
        final_txt += f"🎬 סדרה: {title}\n"
        for s in sorted(info['data'].keys()):
            msg += f"📂 **{s}**\n"
            final_txt += f"{s}\n"
            for e in sorted(info['data'][s], key=lambda x: x['episode'] if x['episode'] is not None else 999):
                line = f"פרק {e['episode'] if e['episode'] is not None else 'כללי'}\n{e['url']}\n"
                msg += line
                final_txt += line
            msg += "\n"
            final_txt += "\n"
        final_txt += "="*20 + "\n\n"
        series_msgs.append(msg)

    report += f"✅ סדרות: {success}\n❌ נכשלו: {fail}\n📦 פרקים: {total_eps}\n\n📝 **פירוט:**\n" + "\n".join(details)
    
    try:
        await status_msg.delete()
        await update.message.reply_text(report + f"\n\n{CREDIT_LINE}", parse_mode='Markdown')
        for m in series_msgs:
            try: await update.message.reply_text(m + f"\n{CREDIT_LINE}", parse_mode='Markdown')
            except: await update.message.reply_text(m.replace('*','').replace('_','') + f"\n{CREDIT_LINE}")
        if success > 0:
            f = io.BytesIO(final_txt.encode('utf-8'))
            f.name = f"Results_{datetime.datetime.now().strftime('%H%M')}.txt"
            await update.message.reply_document(f, caption=f"📄 **דוח מלא**\n\n{CREDIT_LINE}", parse_mode='Markdown')
    except: pass
    active_tasks.pop(user_id, None)

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document.file_name.lower().endswith(".txt"):
        f = await context.bot.get_file(update.message.document.file_id)
        c = await f.download_as_bytearray()
        await process_links(update, context, c.decode('utf-8', 'ignore'))

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    app_tg = Application.builder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CallbackQueryHandler(handle_callback))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_links))
    app_tg.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app_tg.run_polling()

if __name__ == '__main__': main()
