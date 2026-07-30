import os
import logging
import asyncio
import threading
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
TOKEN = "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **שלום! אני בוט יוצר לינקים לסדרות.**\n\n"
        "שלח לי קישור לתיקיית Google Drive (ציבורית) ואני אחלץ עבורך את כל הפרקים מסודרים לפי עונות.\n\n"
        "🔧 **איך זה עובד?**\n"
        "1. וודא שהתיקייה בדרייב מוגדרת כציבורית.\n"
        "2. שלח את הקישור כאן.\n"
        "3. קבל רשימה מעוצבת של כל הפרקים!"
    )
    keyboard = [[InlineKeyboardButton("עזרה ❓", callback_data='help')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    links = DRIVE_URL_PATTERN.findall(text)
    
    if not links:
        await update.message.reply_text("❌ לא מצאתי קישור תקין של Google Drive. אנא שלח קישור מלא.")
        return

    status_msg = await update.message.reply_text("⏳ **מתחיל בחילוץ...**\nמתחבר ל-Google Drive ומנתח את התוכן.")
    
    extractor = DriveExtractor(use_browser=True)
    results = []
    
    for link in links:
        # Run extraction in a thread to not block the bot
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, extractor.extract_series, link)
        results.append(res)

    await status_msg.delete()

    for res in results:
        if "error" in res:
            await update.message.reply_text(f"❌ **שגיאה בחילוץ:**\n{res['error']}")
            continue
        
        title = res.get('title', 'סדרה ללא שם')
        output = f"🎬 **{title}**\n\n"
        
        data = res.get('data', {})
        for season, episodes in data.items():
            output += f"📂 **{season}:**\n"
            for ep in episodes:
                ep_name = ep['name']
                ep_url = ep['url']
                output += f"• [{ep_name}]({ep_url})\n"
            output += "\n"
        
        # Split long messages if necessary
        if len(output) > 4000:
            parts = [output[i:i+4000] for i in range(0, len(output), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text(output, parse_mode='Markdown', disable_web_page_preview=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ **עזרה:**\n"
        "- התיקייה חייבת להיות ציבורית (Anyone with the link can view).\n"
        "- אם התיקייה מכילה תיקיות משנה (עונות), מומלץ לשלוח קישור ישיר לתיקיית העונה.\n"
        "- הבוט מזהה אוטומטית מספרי פרקים ועונות משם הקובץ."
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode='Markdown')
        await update.callback_query.answer()
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    # Start Flask in background
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Bot
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(help_command, pattern='help'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started...")
    application.run_polling()

if __name__ == '__main__':
    main()
