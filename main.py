import asyncio
import re
import threading
import time
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

TOKEN = "8155459616:AAFPWhdETkxBtEiaKZ-fJU--O2NHwJ3BYvU"
RENDER_URL = "https://YOUR-APP-NAME.onrender.com"  # להחליף ל-URL של Render!

app = Flask(__name__)

@app.route('/')
def home():
    return "Booking Bot is Alive! 🤖"

def keep_alive():
    while True:
        time.sleep(600)
        try:
            requests.get(RENDER_URL)
            print("Ping sent successfully! 🚀")
        except Exception as e:
            print(f"Ping failed: {e}")

async def fetch_booking_price(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            price_element = await page.query_selector('.prco-val-bignum, .bd-price-value, [data-testid="price-and-discounted-price"]')
            if price_element:
                text = await price_element.inner_text()
                clean_price = int(re.sub(r'[^\d]', '', text))
                await browser.close()
                return clean_price
        except Exception as e:
            print(f"Scraping error: {e}")
        await browser.close()
        return None

tracked_hotels = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "אהלן! 🤖🏨
למעקב שלח:
`/track <קישור> <מחיר_נוכחי>`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        url = context.args[0]
        current_price = int(context.args[1])
        tracked_hotels[chat_id] = {'url': url, 'target_price': current_price}
        await update.message.reply_text(f"התחלתי מעקב! אשלח הודעה ברגע שהמחיר יורד מ-₪{current_price} 📉✨")
    except (IndexError, ValueError):
        await update.message.reply_text("פורמט לא תקין. שלח: `/track <URL> <מחיר>`", parse_mode='Markdown')

async def check_prices_loop(app_telegram):
    while True:
        await asyncio.sleep(1200) # כל 20 דקות
        for chat_id, data in list(tracked_hotels.items()):
            new_price = await fetch_booking_price(data['url'])
            if new_price and new_price < data['target_price']:
                msg = f"🚨 **ירידת מחיר!** 🚨\n\nהמחיר ירד ל-**₪{new_price}**! 🎉\n[לחץ להזמנה]({data['url']})"
                await app_telegram.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                data['target_price'] = new_price

if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

    tg_app = Application.builder().token(TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("track", track))

    loop = asyncio.get_event_loop()
    loop.create_task(check_prices_loop(tg_app))
    
    print("Bot started! 🚀")
    tg_app.run_polling()
