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
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except ImportError:
    # אם אין playwright_stealth - נדלג
    stealth_async = None

# --- 1. הגדרות ושרת Keep-Alive ---
TOKEN = "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU"
RENDER_URL = "https://booking-bot-nisuy.onrender.com"  

app = Flask(__name__)

@app.route('/')
def home():
    return "Booking Bot Test Mode Active & Stealthy! 🤖🥷"

def keep_alive():
    while True:
        time.sleep(600)  
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
                '--disable-web-security',
                '--window-size=1920,1080'
            ]
        )
        
        context = await browser.new_context(
            user_agent=random_ua,
            viewport=viewport,
            locale="he-IL",
            timezone_id="Asia/Jerusalem",
            extra_http_headers={
                'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.google.com/',
                'Sec-Ch-Ua-Mobile': '?1' if is_mobile else '?0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site'
            }
        )
        
        page = await context.new_page()

        # הפעלת Stealth אם קיים
        if stealth_async:
            try:
                await stealth_async(page)
            except Exception:
                pass

        # חסימת מדיה להאצה
        await page.route("**/*.{png,jpg,jpeg,gif,webp,ttf,woff,woff2,css}", lambda route: route.abort())

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(random.randint(2500, 5000))
            
            # הדמיית התנהגות אנושית
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await page.mouse.wheel(0, random.randint(300, 800))
            await page.wait_for_timeout(random.randint(1000, 2000))

            # ניסיון למצוא מחיר במספר סלקטורים
            price_selectors = [
                '.prco-val-bignum', 
                '.bd-price-value', 
                '[data-testid="price-and-discounted-price"]',
                '.bui-price-display__value',
                '.prco-inner',
                '.xp__price',
                '.bui-price-display__value.prco-inline-block'
            ]
            
            price_element = None
            for selector in price_selectors:
                price_element = await page.query_selector(selector)
                if price_element:
                    break
            
            if price_element:
                text = await price_element.inner_text()
                clean_price = re.sub(r'[^\d]', '', text)
                if clean_price:
                    clean_price = int(clean_price)
                    await browser.close()
                    return True, clean_price, None
                else:
                    await browser.close()
                    return False, None, "לא נמצא מחיר תקין"
            else:
                # ניסיון למצוא מחיר בדף
                body_text = await page.inner_text('body')
                prices = re.findall(r'₪\s*([\d,]+)', body_text)
                if prices:
                    clean_price = int(re.sub(r'[^\d]', '', prices[0]))
                    await browser.close()
                    return True, clean_price, None
                
                await browser.close()
                return False, None, "לא נמצא מחיר (ייתכן שבוקינג ביקש קאפצ'ה או שהקישור שגוי)"
        except Exception as e:
            await browser.close()
            return False, None, str(e)

# --- 3. ממשק טלגרם דינמי ומערכת הבדיקה ---
tracked_hotels = {}
WAITING_FOR_DATA = 1

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ התחל מעקב חדש", callback_data="btn_track")],
        [InlineKeyboardButton("📊 מצב מעקב נוכחי", callback_data="btn_status")],
        [InlineKeyboardButton("🛑 עצור מעקב", callback_data="btn_stop")]
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "אהלן! 🤖🏨 הבוט החשאי מוכן (בדיקה כל דקה).\n\n"
        "• `/track <URL> <מחיר>` - להתחלת מעקב\n"
        "• `/status` - לבדיקת מצב\n"
        "• `/stop` - לעצירה\n\n"
        "לחלופין, לחץ על הכפתורים למטה:"
    )
    target = update.message or update.callback_query.message
    await target.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_track":
        await query.message.reply_text(
            "שלח כעת את הקישור יחד עם המחיר הנוכחי:\n\n`<קישור> <מחיר>`\n\nלדוגמה:\n`https://www.booking.com/hotel/il/example 500`",
            parse_mode='Markdown'
        )
        return WAITING_FOR_DATA
    elif query.data == "btn_status":
        await status_command(update, context)
    elif query.data == "btn_stop":
        await stop_command(update, context)
    return ConversationHandler.END

async def handle_input_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_parts = update.message.text.strip().split()
    if len(text_parts) >= 2:
        url = text_parts[0]
        try:
            price = int(text_parts[1])
            tracked_hotels[update.effective_chat.id] = {'url': url, 'target_price': price}
            await update.message.reply_text(
                f"✅ **המעקב הוגדר בהצלחה!**\n💰 **מחיר יעד:** ₪{price}\n⏱️ **בדיקה תתבצע כל 1 דקה.**\n\nלחץ על 'מצב מעקב נוכחי' לפרטים נוספים.",
                reply_markup=get_main_keyboard(), parse_mode='Markdown'
            )
            return ConversationHandler.END
        except ValueError:
            await update.message.reply_text("❌ המחיר חייב להיות מספר! נסה שוב.", reply_markup=get_main_keyboard())
            return WAITING_FOR_DATA
    else:
        await update.message.reply_text("❌ פורמט לא תקין. שלח: `<קישור> <מחיר>`\nלדוגמה: `https://www.booking.com/hotel/il/example 500`", reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return WAITING_FOR_DATA

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url, price = context.args[0], int(context.args[1])
        tracked_hotels[update.effective_chat.id] = {'url': url, 'target_price': price}
        await update.message.reply_text(
            f"✅ **מעקב הוגדר!**\n💰 **יעד:** ₪{price}\n⏱️ **בדיקה כל דקה**",
            reply_markup=get_main_keyboard(), 
            parse_mode='Markdown'
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ פורמט לא תקין: `/track <קישור> <מחיר>`\nלדוגמה: `/track https://www.booking.com/hotel/il/example 500`",
            parse_mode='Markdown'
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if chat_id in tracked_hotels:
        data = tracked_hotels[chat_id]
        await target.reply_text(
            f"📊 **מצב מעקב:** פעיל\n💰 **יעד:** ₪{data['target_price']}\n🔗 [קישור למלון]({data['url']})\n\n⏱️ **תדירות בדיקה:** כל 1 דקה",
            reply_markup=get_main_keyboard(), 
            parse_mode='Markdown', 
            disable_web_page_preview=True
        )
    else:
        await target.reply_text("ℹ️ אין מעקב פעיל כרגע.", reply_markup=get_main_keyboard())

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if tracked_hotels.pop(chat_id, None):
        await target.reply_text("🛑 המעקב הופסק בהצלחה!", reply_markup=get_main_keyboard())
    else:
        await target.reply_text("ℹ️ אין מעקב פעיל.", reply_markup=get_main_keyboard())

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """בטל את השיחה הנוכחית"""
    await update.message.reply_text(
        "❌ ביטלת את הפעולה.", 
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# --- 4. לולאת בדיקת מחירים בלייב ---
async def test_check_prices_loop(app_telegram):
    while True:
        await asyncio.sleep(60)  
        if not tracked_hotels:
            continue
            
        print(f"Running price check for {len(tracked_hotels)} hotels...")
        
        for chat_id, data in list(tracked_hotels.items()):
            try:
                success, new_price, error_msg = await fetch_booking_price(data['url'])
                
                if success and new_price:
                    if new_price < data['target_price']:
                        msg = f"🎉 **יש ירידת מחיר!** 📉\n\n💰 **מחיר קודם:** ₪{data['target_price']}\n🔥 **חדש:** ₪{new_price}\n🔗 [לחץ להזמנה]({data['url']})\n\n⚠️ **שים לב:** המחיר התעדכן והיעד עודכן אוטומטית!"
                        data['target_price'] = new_price 
                    else:
                        msg = f"ℹ️ **סריקה תקופתית** ✅\n💰 **יעד שלך:** ₪{data['target_price']}\n🔍 **מחיר נוכחי:** ₪{new_price}"
                    
                    await app_telegram.bot.send_message(
                        chat_id=chat_id, 
                        text=msg, 
                        parse_mode='Markdown', 
                        reply_markup=get_main_keyboard(), 
                        disable_web_page_preview=True
                    )
                else:
                    msg = f"⚠️ **שגיאה בסריקה!**\n`{error_msg or 'שגיאה לא ידועה'}`"
                    await app_telegram.bot.send_message(
                        chat_id=chat_id, 
                        text=msg, 
                        parse_mode='Markdown', 
                        reply_markup=get_main_keyboard()
                    )
            except Exception as e:
                print(f"Error checking price for chat {chat_id}: {e}")
                try:
                    await app_telegram.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **שגיאה בסריקה:**\n`{str(e)}`",
                        parse_mode='Markdown',
                        reply_markup=get_main_keyboard()
                    )
                except:
                    pass

# --- 5. הפעלת השרת והבוט ---
async def main():
    # הפעלת שרת Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False), daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()

    # יצירת אפליקציית Telegram
    tg_app = Application.builder().token(TOKEN).build()
    
    # הוספת handlers
    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(CommandHandler("track", track_command))
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("stop", stop_command))
    tg_app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_click, pattern="^btn_track$")],
        states={
            WAITING_FOR_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(button_click, pattern="^btn_stop$"),
        ]
    )
    tg_app.add_handler(conv_handler)
    
    # CallbackQueryHandler לכל הכפתורים
    tg_app.add_handler(CallbackQueryHandler(button_click))
    
    # Message handler
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message))

    # הפעלת לולאת הבדיקה
    asyncio.create_task(test_check_prices_loop(tg_app))
    
    print("🚀 Stealth Bot Started! Waiting for commands...")
    print(f"🤖 Bot token: {TOKEN[:10]}...")
    print(f"🌐 Web server running on port 8080")

    # הפעלת הבוט
    try:
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # שמירה על הבוט פועל
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Error: {e}")
