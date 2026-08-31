import asyncio
import re
import random
import threading
import time
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationLogic
)
from playwright.async_api import async_playwright

# --- 1. הגדרות ושרת Keep-Alive ---
TOKEN = "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU"
RENDER_URL = "https://booking-bot-nisuy.onrender.com"  # הקישור המעודכן לשרת הניסוי ב-Render

app = Flask(__name__)

@app.route('/')
def home():
    return "Booking Bot Test Mode Active! 🤖"

def keep_alive():
    while True:
        time.sleep(600)  # פינג כל 10 דקות
        try:
            requests.get(RENDER_URL)
            print("Ping sent successfully! 🚀")
        except Exception as e:
            print(f"Ping failed: {e}")

# --- 2. שכבות הגנה מתקדמות וסריקת בוקינג ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36"
]

async def fetch_booking_price(url: str):
    random_ua = random.choice(USER_AGENTS)
    is_mobile = "Mobile" in random_ua or "iPhone" in random_ua
    viewport = {'width': 390, 'height': 844} if is_mobile else {'width': 1920, 'height': 1080}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security'
            ]
        )
        
        context = await browser.new_context(
            user_agent=random_ua,
            viewport=viewport,
            locale="he-IL",
            timezone_id="Asia/Jerusalem",
            extra_http_headers={
                'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
                'Sec-Ch-Ua-Mobile': '?1' if is_mobile else '?0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none'
            }
        )
        
        page = await context.new_page()

        # שכבת הגנה נוספת: חסימת תמונות ופונטים להאצת הסריקה וחיסכון ב-RAM
        await page.route("**/*.{png,jpg,jpeg,gif,webp,ttf,woff,woff2}", lambda route: route.abort())

        # הסוואת זיהוי ה-Automation של Chromium
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            # הדמיית התנהגות אנושית: הזזת עכבר אקראית
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

            price_element = await page.query_selector('.prco-val-bignum, .bd-price-value, [data-testid="price-and-discounted-price"]')
            if price_element:
                text = await price_element.inner_text()
                clean_price = int(re.sub(r'[^\d]', '', text))
                await browser.close()
                return True, clean_price, None
            else:
                await browser.close()
                return False, None, "לא נמצא אלמנט מחיר בדף (ייתכן שהקישור שגוי או שהופעלה הגנת Captcha)"
        except Exception as e:
            await browser.close()
            return False, None, str(e)

# --- 3. ממשק טלגרם דינמי ומערכת הבדיקה ---
tracked_hotels = {}  # {chat_id: {'url': url, 'target_price': target}}
WAITING_FOR_DATA = 1

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ התחל מעקב חדש", callback_data="btn_track")],
        [InlineKeyboardButton("📊 מצב מעקב נוכחי", callback_data="btn_status")],
        [InlineKeyboardButton("🛑 עצור מעקב", callback_data="btn_stop")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "אהלן! 🤖🏨 מוד ניסוי פעיל (בדיקה כל 1 דקה).\n\n"
        "תוכל להשתמש בכפתורים למטה או בפקודות הישירות:\n"
        "• `/track <URL> <מחיר>` - להתחלת מעקב\n"
        "• `/status` - לבדיקת מצב המעקב\n"
        "• `/stop` - להפסקת המעקב"
    )
    if update.message:
        await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_track":
        await query.message.reply_text(
            "שלח כעת את הקישור לבוקינג יחד עם המחיר הנוכחי בפורמט הזה:\n\n"
            "`<קישור> <מחיר>`\n\n"
            "דוגמה:\n`https://booking.com/... 1200`",
            parse_mode='Markdown'
        )
        return WAITING_FOR_DATA
    elif query.data == "btn_status":
        await status_command(update, context)
    elif query.data == "btn_stop":
        await stop_command(update, context)

async def handle_input_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_parts = update.message.text.strip().split()
    if len(text_parts) >= 2:
        url = text_parts[0]
        try:
            price = int(text_parts[1])
            chat_id = update.effective_chat.id
            tracked_hotels[chat_id] = {'url': url, 'target_price': price}
            await update.message.reply_text(
                f"✅ **המעקב הוגדר בהצלחה!**\n\n"
                f"🔗 **URL:** {url[:35]}...\n"
                f"💰 **מחיר יעד:** ₪{price}\n\n"
                f"⏱️ **מצב ניסוי:** הבוט ייסרוק עכשיו את האתר **כל 1 דקה** וידווח תוצאה!",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
            return ConversationLogic.END
        except ValueError:
            await update.message.reply_text("❌ המחיר חייב להיות במספר בלבד! נסה שוב.", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("❌ פורמט לא תקין. שלח: `<קישור> <מחיר>`", reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = context.args[0]
        price = int(context.args[1])
        chat_id = update.effective_chat.id
        tracked_hotels[chat_id] = {'url': url, 'target_price': price}
        await update.message.reply_text(
            f"✅ **המעקב הוגדר בהצלחה (דרך פקודה)!**\n\n"
            f"💰 **מחיר יעד:** ₪{price}\n"
            f"⏱️ **בדיקה תתבצע כל 1 דקה.**",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ פורמט לא תקין. שלח: `/track <קישור> <מחיר>`", parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message if update.message else update.callback_query.message
    if chat_id in tracked_hotels:
        data = tracked_hotels[chat_id]
        await target.reply_text(
            f"📊 **מצב מעקב פעיל:**\n\n"
            f"💰 **מחיר יעד מוגדר:** ₪{data['target_price']}\n"
            f"🔗 **קישור:** [לחץ מעבר]({data['url']})\n"
            f"⏱️ **תדירות בדיקה:** כל דקה אחת.",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await target.reply_text("ℹ️ אין כרגע מעקב פעיל. לחץ על 'התחל מעקב חדש' כדי להגדיר!", reply_markup=get_main_keyboard())

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message if update.message else update.callback_query.message
    if chat_id in tracked_hotels:
        del tracked_hotels[chat_id]
        await target.reply_text("🛑 המעקב הופסק בהצלחה!", reply_markup=get_main_keyboard())
    else:
        await target.reply_text("ℹ️ אין מעקב פעיל להפסיק.", reply_markup=get_main_keyboard())

# --- 4. לולאת בדיקת מחירים בלייב (כל 1 דקה לניסוי) ---
async def test_check_prices_loop(app_telegram):
    while True:
        await asyncio.sleep(60)  # ניסוי: בדיקה כל 60 שניות (1 דקה)
        for chat_id, data in list(tracked_hotels.items()):
            success, new_price, error_msg = await fetch_booking_price(data['url'])
            
            if success:
                if new_price < data['target_price']:
                    msg = (
                        f"🎉 **יש שינוי - עבר בהצלחה!** 📉\n\n"
                        f"💰 **מחיר נוכחי (שלך):** ₪{data['target_price']}\n"
                        f"🔥 **מחיר חדש שנמצא:** ₪{new_price}\n\n"
                        f"🔗 [לחץ כאן למעבר להזמנה]({data['url']})"
                    )
                    data['target_price'] = new_price  # עדכון המחיר היעד
                else:
                    msg = (
                        f"ℹ️ **אין שינוי - עבר בהצלחה!** ✅\n\n"
                        f"💰 **מחיר שהוגדר:** ₪{data['target_price']}\n"
                        f"🔍 **מחיר שניסרק עכשיו:** ₪{new_price}"
                    )
            else:
                msg = f"⚠️ **ERROR בדיקת המחיר נכשלה!**\n\n**סיבה:** `{error_msg}`"

            await app_telegram.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown', reply_markup=get_main_keyboard())

# --- 5. הפעלת השרת והבוט באופן מתואם ---
async def main():
    # הפעלת Flask בשרשור נפרד
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # הפעלת Pinger
    threading.Thread(target=keep_alive, daemon=True).start()

    # אתחול אפליקציית הטלגרם
    tg_app = Application.builder().token(TOKEN).build()
    
    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(CommandHandler("track", track_command))
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("stop", stop_command))
    tg_app.add_handler(CallbackQueryHandler(button_click))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message))

    # הפעלת לולאת המעקב ברקע
    asyncio.create_task(test_check_prices_loop(tg_app))

    print("Test Bot Started Successfully! 🚀")

    # הרצת הבוט בצורה אסינכרונית יציבה
    async with tg_app:
        await tg_app.start()
        await tg_app.updater.start_polling()
        # שמירה על השרת פעיל
        await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
