import asyncio
import re
import random
import threading
import time
import requests
from datetime import datetime, timedelta
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
    stealth_async = None

# ==================== 1. הגדרות בסיסיות ====================
TOKEN = "8155459616:AAGJC9uDKbNA9_h9nfSy1xirXrbrMkIQnGQ"
RENDER_URL = "https://booking-bot-nisuy.onrender.com"

app = Flask(__name__)

@app.route('/')
def home():
    return "Booking Bot Advanced v3.0 🚀🤖"

def keep_alive():
    while True:
        time.sleep(600)
        try:
            requests.get(RENDER_URL)
            print("✅ Ping sent successfully!")
        except Exception as e:
            print(f"❌ Ping failed: {e}")

# ==================== 2. מערכת הגנה מתקדמת ====================

# 2.1 סיבוב User-Agent
USER_AGENTS = {
    'windows': [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/126.0"
    ],
    'mac': [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
    ],
    'mobile': [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6312.99 Mobile Safari/537.36"
    ]
}

def get_random_user_agent():
    platform = random.choice(['windows', 'mac', 'mobile'])
    return random.choice(USER_AGENTS[platform]), platform

# 2.2 פרוקסי (אופציונלי - ריק כברירת מחדל)
PROXIES = []  # הוסף פרוקסי אם יש

def get_random_proxy():
    return random.choice(PROXIES) if PROXIES else None

# 2.3 Viewport משתנה
def get_random_viewport():
    if random.random() < 0.3:  # 30% מובייל
        return {'width': random.choice([375, 390, 414]), 'height': random.choice([667, 812, 844, 896])}
    return {'width': random.choice([1366, 1440, 1536, 1920]), 'height': random.choice([768, 900, 1080, 1200])}

# 2.4 כותרות HTTP משתנות
def get_random_headers(platform):
    headers = {
        'Accept-Language': random.choice(['he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7', 'en-US,en;q=0.9,he;q=0.8']),
        'Referer': random.choice(['https://www.google.com/', 'https://www.facebook.com/', 'https://www.youtube.com/']),
        'DNT': random.choice(['1', '0']),
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?1' if platform == 'mobile' else '?0',
        'Sec-Ch-Ua-Platform': '"Windows"' if platform == 'windows' else '"macOS"' if platform == 'mac' else '"iOS"'
    }
    return headers

# 2.5 מוניטור לניטור כשלונות
class BookingScraperMonitor:
    def __init__(self):
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None
        self.failure_patterns = []
        self.total_attempts = 0

    def record_attempt(self, success, error_msg=None):
        self.total_attempts += 1
        if success:
            self.successes += 1
            self.failures = 0
        else:
            self.failures += 1
            self.last_failure_time = datetime.now()
            if error_msg:
                self.failure_patterns.append({
                    'time': datetime.now(),
                    'error': error_msg[:100]
                })
                if len(self.failure_patterns) > 100:
                    self.failure_patterns.pop(0)

    def should_switch_proxy(self):
        return self.failures >= 5

    def get_cooldown(self):
        if self.failures >= 10:
            return 300
        elif self.failures >= 5:
            return 120
        return 60

monitor = BookingScraperMonitor()

# 2.6 פונקציות הגנה
async def human_like_behavior(page):
    # תנועות עכבר
    for _ in range(random.randint(3, 7)):
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.05, 0.2))
    # גלילות
    for _ in range(random.randint(2, 5)):
        scroll_amount = random.randint(100, 500)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.3, 1.0))
    # עצירות אקראיות
    await asyncio.sleep(random.uniform(0.5, 2.0))

async def intelligent_delay():
    hour = datetime.now().hour
    if 2 <= hour <= 5:
        base = random.uniform(3, 8)
    elif 8 <= hour <= 12:
        base = random.uniform(1, 3)
    else:
        base = random.uniform(2, 5)
    await asyncio.sleep(base + random.uniform(0, 1))

async def enhanced_stealth(page):
    await page.add_init_script("""
        // הסתרת WebDriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        // הסתרת Chrome Automation
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        // זיוף window.chrome
        window.chrome = { runtime: {} };
        // זיוף שפות
        Object.defineProperty(navigator, 'languages', { get: () => ['he-IL', 'he', 'en-US', 'en'] });
        // הסתרת headless
        Object.defineProperty(navigator, 'headless', { get: () => false });
        // זיוף screen
        Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
        Object.defineProperty(screen, 'availHeight', { get: () => 1080 });
        // WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter(parameter);
        };
    """)

async def detect_block(page):
    try:
        status_text = await page.inner_text('body')
        block_keywords = ['blocked', 'access denied', 'forbidden', 'unavailable', 'נחסם', 'ip', 'security']
        if any(keyword in status_text.lower() for keyword in block_keywords):
            return True
        return False
    except:
        return False

async def detect_captcha(page):
    captcha_selectors = ['#captcha', '.captcha', '[aria-label*="captcha"]', 'iframe[src*="recaptcha"]', 'iframe[src*="hcaptcha"]']
    for selector in captcha_selectors:
        if await page.query_selector(selector):
            return True
    body = await page.inner_text('body')
    if any(k in body.lower() for k in ['captcha', 'robot', 'verify', 'אימות', 'בוט']):
        return True
    return False

async def manage_cookies(context):
    await context.add_cookies([{
        'name': 'lang',
        'value': 'he',
        'domain': '.booking.com',
        'path': '/'
    }, {
        'name': 'currency',
        'value': 'ILS',
        'domain': '.booking.com',
        'path': '/'
    }])

# ==================== 3. פונקציית הסריקה הראשית ====================

async def fetch_booking_price(url: str):
    # 3.1 דיליי חכם
    await intelligent_delay()
    
    # 3.2 בחירת User-Agent
    ua, platform = get_random_user_agent()
    viewport = get_random_viewport()
    headers = get_random_headers(platform)
    is_mobile = platform == 'mobile'
    
    # 3.3 פרוקסי
    proxy = get_random_proxy()
    
    async with async_playwright() as p:
        # 3.4 הגדרות דפדפן
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )
        
        context = await browser.new_context(
            user_agent=ua,
            viewport=viewport,
            locale='he-IL',
            timezone_id='Asia/Jerusalem',
            extra_http_headers=headers,
            proxy=proxy
        )
        
        # 3.5 Cookies
        await manage_cookies(context)
        
        page = await context.new_page()
        
        # 3.6 Stealth
        await enhanced_stealth(page)
        if stealth_async:
            try:
                await stealth_async(page)
            except:
                pass
        
        # 3.7 חסימת מדיה
        await page.route("**/*.{png,jpg,jpeg,gif,webp,ttf,woff,woff2,css,svg,ico}", lambda route: route.abort())
        
        try:
            # 3.8 ניווט
            response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # 3.9 התנהגות אנושית
            await human_like_behavior(page)
            
            # 3.10 בדיקת חסימה
            if await detect_block(page):
                monitor.record_attempt(False, 'Block detected')
                await browser.close()
                return False, None, 'האתר חסם את הבקשה', False, {}
            
            # 3.11 בדיקת CAPTCHA
            if await detect_captcha(page):
                monitor.record_attempt(False, 'CAPTCHA detected')
                await browser.close()
                return False, None, 'זוהתה CAPTCHA - מנסה שוב מאוחר יותר', False, {}
            
            # ==================== 4. חילוץ נתונים ====================
            data = {}
            
            # 4.1 שם מלון
            hotel_name_elem = await page.query_selector('.hp__hotel-name, .d2fee87262, .pp-header__title, .bui-u-text-ellipsis--2')
            if hotel_name_elem:
                data['hotel_name'] = (await hotel_name_elem.inner_text()).strip()
            else:
                data['hotel_name'] = 'מלון לא מזוהה'
            
            # 4.2 דירוג
            rating_elem = await page.query_selector('.bui-review-score__badge, .review-score-badge, .a3b8729ab1')
            if rating_elem:
                data['hotel_rating'] = (await rating_elem.inner_text()).strip()
            else:
                data['hotel_rating'] = 'N/A'
            
            # 4.3 גוף דף לחיפוש טקסט
            body_text = await page.inner_text('body')
            
            # 4.4 זיהוי ביטול חינם
            data['free_cancellation'] = False
            if 'ביטול חינם' in body_text or 'free cancellation' in body_text.lower():
                data['free_cancellation'] = True
                cancel_match = re.search(r'ביטול חינם עד (\d{1,2}/\d{1,2}/\d{4})', body_text)
                if cancel_match:
                    data['cancellation_deadline'] = cancel_match.group(1)
                else:
                    data['cancellation_deadline'] = None
            
            # 4.5 ארוחת בוקר
            data['includes_breakfast'] = 'ארוחת בוקר' in body_text or 'breakfast' in body_text.lower()
            
            # 4.6 זיהוי מבצע
            sale_keywords = ['מבצע', 'הנחה', 'סייל', 'sale', 'discount', 'save', 'חיסכון']
            data['sale_detected'] = any(k in body_text.lower() for k in sale_keywords)
            
            # 4.7 זיהוי ביקוש (צופים)
            viewers_elem = await page.query_selector('.hp-rt-people-viewing, [data-testid="people-viewing"]')
            data['viewers'] = 0
            if viewers_elem:
                viewers_text = await viewers_elem.inner_text()
                viewers_match = re.search(r'(\d+)', viewers_text)
                if viewers_match:
                    data['viewers'] = int(viewers_match.group(1))
            
            # 4.8 זמינות נמוכה
            data['low_availability'] = False
            rooms_left_elem = await page.query_selector('.room-last-booked, [data-testid="last-rooms"]')
            if rooms_left_elem:
                left_text = await rooms_left_elem.inner_text()
                rooms_match = re.search(r'(\d+)', left_text)
                if rooms_match and int(rooms_match.group(1)) <= 3:
                    data['low_availability'] = True
            
            # 4.9 חילוץ מחיר
            price_selectors = [
                '.prco-val-bignum',
                '.bd-price-value',
                '[data-testid="price-and-discounted-price"]',
                '.bui-price-display__value',
                '.prco-inner',
                '.xp__price',
                '.bui-price-display__value.prco-inline-block'
            ]
            
            price_elem = None
            for selector in price_selectors:
                price_elem = await page.query_selector(selector)
                if price_elem:
                    break
            
            if price_elem:
                price_text = await price_elem.inner_text()
                clean_price = re.sub(r'[^\d]', '', price_text)
                if clean_price:
                    clean_price = int(clean_price)
                    data['price'] = clean_price
                    monitor.record_attempt(True)
                    await browser.close()
                    return True, clean_price, None, data['sale_detected'], data
            
            # 4.10 ניסיון חלופי - חיפוש כללי
            prices = re.findall(r'₪\s*([\d,]+)', body_text)
            if prices:
                clean_price = int(re.sub(r'[^\d]', '', prices[0]))
                data['price'] = clean_price
                monitor.record_attempt(True)
                await browser.close()
                return True, clean_price, None, data['sale_detected'], data
            
            # 4.11 כשל
            monitor.record_attempt(False, 'No price found')
            await browser.close()
            return False, None, 'לא נמצא מחיר', False, data
            
        except Exception as e:
            monitor.record_attempt(False, str(e))
            await browser.close()
            return False, None, str(e), False, {}

# ==================== 5. מבני נתונים וממשק ====================
tracked_hotels = {}
WAITING_FOR_DATA = 1
WAITING_FOR_DATES = 2

ROOM_TYPES = {
    'double': {'name': 'חדר זוגי', 'emoji': '🛏️'},
    'standard': {'name': 'חדר רגיל', 'emoji': '🛏️'},
    'premium': {'name': 'חדר פרימיום', 'emoji': '⭐'},
    'basic': {'name': 'חדר סטנדרט', 'emoji': '🏠'}
}

# 5.1 מקלדות
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ מעקב חדש", callback_data="btn_track")],
        [InlineKeyboardButton("📊 מצב מעקב", callback_data="btn_status")],
        [InlineKeyboardButton("⚙️ הגדרות", callback_data="advanced_settings")],
        [InlineKeyboardButton("🛑 עצור מעקב", callback_data="btn_stop")]
    ])

def get_advanced_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛏️ סוג חדר", callback_data="change_room"),
         InlineKeyboardButton("📅 מועדים", callback_data="change_dates")],
        [InlineKeyboardButton("🔄 ביטול חינם", callback_data="toggle_cancellation"),
         InlineKeyboardButton("📊 היסטוריה", callback_data="show_history")],
        [InlineKeyboardButton("⚙️ תדירות", callback_data="change_frequency"),
         InlineKeyboardButton("🔔 התראות", callback_data="alert_settings")],
        [InlineKeyboardButton("📋 רשימת מעקבים", callback_data="list_tracking"),
         InlineKeyboardButton("📤 ייצוא", callback_data="export_data")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="back_to_main")]
    ])

def get_room_keyboard():
    buttons = []
    for k, v in ROOM_TYPES.items():
        buttons.append([InlineKeyboardButton(f"{v['emoji']} {v['name']}", callback_data=f"room_{k}")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)

def get_frequency_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱️ 1 דקה", callback_data="freq_1"),
         InlineKeyboardButton("⏱️ 5 דקות", callback_data="freq_5")],
        [InlineKeyboardButton("⏱️ 15 דקות", callback_data="freq_15"),
         InlineKeyboardButton("⏱️ 60 דקות", callback_data="freq_60")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="back_to_main")]
    ])

def get_alert_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📉 5% ירידה", callback_data="alert_5"),
         InlineKeyboardButton("📉 10% ירידה", callback_data="alert_10")],
        [InlineKeyboardButton("📉 20% ירידה", callback_data="alert_20"),
         InlineKeyboardButton("📈 עליית מחיר", callback_data="alert_up")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="back_to_main")]
    ])

# ==================== 6. פקודות טלגרם ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎯 **ברוכים הבאים לבוט מעקב המחירים החכם!**\n\n"
        "📌 **פקודות:**\n"
        "• `/track <URL> <מחיר>` - מעקב מהיר\n"
        "• `/status` - מצב נוכחי\n"
        "• `/stop` - עצירת מעקב\n"
        "• `/history` - היסטוריה\n"
        "• `/list` - רשימת מעקבים\n\n"
        "🔽 לחץ על הכפתורים למטה!"
    )
    await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == "btn_track":
        await query.message.reply_text(
            "📝 שלח קישור ומחיר:\n`<קישור> <מחיר>`\nלמשל:\n`https://www.booking.com/hotel/il/x 500`",
            parse_mode='Markdown'
        )
        return WAITING_FOR_DATA

    elif query.data.startswith("room_"):
        room_key = query.data.split("_")[1]
        if chat_id in tracked_hotels:
            tracked_hotels[chat_id]['room_type'] = room_key
            await query.message.reply_text(
                f"✅ סוג חדר: {ROOM_TYPES[room_key]['emoji']} {ROOM_TYPES[room_key]['name']}",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.message.reply_text("⚠️ אין מעקב פעיל.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    elif query.data == "change_dates":
        await query.message.reply_text(
            "📅 שלח תאריכים: `YYYY-MM-DD YYYY-MM-DD`\nלמשל: `2026-09-01 2026-09-05`",
            parse_mode='Markdown'
        )
        return WAITING_FOR_DATES

    elif query.data == "toggle_cancellation":
        if chat_id in tracked_hotels:
            tracked_hotels[chat_id]['free_cancellation'] = not tracked_hotels[chat_id].get('free_cancellation', False)
            status = "✅ פעיל" if tracked_hotels[chat_id]['free_cancellation'] else "❌ לא פעיל"
            await query.message.reply_text(f"🔄 ביטול חינם: {status}", reply_markup=get_main_keyboard())
        else:
            await query.message.reply_text("⚠️ אין מעקב פעיל.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    elif query.data == "show_history":
        await show_history(update, context)
        return ConversationHandler.END

    elif query.data == "list_tracking":
        await list_tracking(update, context)
        return ConversationHandler.END

    elif query.data == "export_data":
        await export_data(update, context)
        return ConversationHandler.END

    elif query.data.startswith("alert_"):
        threshold = query.data.split("_")[1]
        if chat_id in tracked_hotels:
            tracked_hotels[chat_id]['alert_threshold'] = int(threshold)
            await query.message.reply_text(f"🔔 התראה הוגדרה ל-{threshold}% ירידה", reply_markup=get_main_keyboard())
        else:
            await query.message.reply_text("⚠️ אין מעקב פעיל.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    elif query.data == "alert_up":
        if chat_id in tracked_hotels:
            tracked_hotels[chat_id]['alert_on_up'] = not tracked_hotels[chat_id].get('alert_on_up', False)
            status = "✅ פעיל" if tracked_hotels[chat_id]['alert_on_up'] else "❌ לא פעיל"
            await query.message.reply_text(f"📈 התראות עלייה: {status}", reply_markup=get_main_keyboard())
        else:
            await query.message.reply_text("⚠️ אין מעקב פעיל.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    elif query.data.startswith("freq_"):
        freq = int(query.data.split("_")[1])
        if chat_id in tracked_hotels:
            tracked_hotels[chat_id]['check_frequency'] = freq
            await query.message.reply_text(f"⏱️ תדירות: כל {freq} דקות", reply_markup=get_main_keyboard())
        else:
            await query.message.reply_text("⚠️ אין מעקב פעיל.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    elif query.data == "advanced_settings":
        await query.message.reply_text("⚙️ **הגדרות מתקדמות**", reply_markup=get_advanced_keyboard())
        return ConversationHandler.END

    elif query.data == "change_room":
        await query.message.reply_text("🛏️ **בחר סוג חדר:**", reply_markup=get_room_keyboard())
        return ConversationHandler.END

    elif query.data == "change_frequency":
        await query.message.reply_text("⏱️ **בחר תדירות:**", reply_markup=get_frequency_keyboard())
        return ConversationHandler.END

    elif query.data == "alert_settings":
        await query.message.reply_text("🔔 **הגדרות התראות:**", reply_markup=get_alert_keyboard())
        return ConversationHandler.END

    elif query.data == "back_to_main":
        await query.message.reply_text("🏠 חזרה", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    elif query.data == "btn_status":
        await status_command(update, context)
        return ConversationHandler.END

    elif query.data == "btn_stop":
        await stop_command(update, context)
        return ConversationHandler.END

    return ConversationHandler.END

async def handle_input_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    parts = text.split()

    # בדיקת תאריכים
    if len(parts) == 2 and re.match(r'\d{4}-\d{2}-\d{2}', parts[0]):
        try:
            check_in = datetime.strptime(parts[0], '%Y-%m-%d')
            check_out = datetime.strptime(parts[1], '%Y-%m-%d')
            if check_in < datetime.now():
                await update.message.reply_text("❌ תאריך כניסה חייב להיות בעתיד")
                return WAITING_FOR_DATES
            if check_out <= check_in:
                await update.message.reply_text("❌ תאריך יציאה חייב להיות אחרי כניסה")
                return WAITING_FOR_DATES
            if chat_id in tracked_hotels:
                tracked_hotels[chat_id]['check_in'] = parts[0]
                tracked_hotels[chat_id]['check_out'] = parts[1]
                await update.message.reply_text(f"✅ מועדים: {parts[0]} → {parts[1]}", reply_markup=get_main_keyboard())
                return ConversationHandler.END
            else:
                await update.message.reply_text("⚠️ אין מעקב פעיל", reply_markup=get_main_keyboard())
                return ConversationHandler.END
        except:
            await update.message.reply_text("❌ פורמט לא תקין. נסה: YYYY-MM-DD YYYY-MM-DD")
            return WAITING_FOR_DATES

    # קישור + מחיר
    if len(parts) >= 2:
        url = parts[0]
        try:
            price = int(parts[1])
            tracked_hotels[chat_id] = {
                'url': url,
                'target_price': price,
                'room_type': 'standard',
                'free_cancellation': False,
                'cancellation_deadline': None,
                'includes_breakfast': False,
                'hotel_rating': 'N/A',
                'viewers': 0,
                'low_availability': False,
                'check_in': None,
                'check_out': None,
                'guests': 2,
                'rooms': 1,
                'history': [],
                'alert_threshold': 10,
                'alert_on_up': False,
                'check_frequency': 60,
                'last_check': datetime.now(),
                'sale_detected': False,
                'hotel_name': 'ממתין לבדיקה'
            }
            await update.message.reply_text(
                f"✅ **מעקב הוגדר!**\n💰 מחיר יעד: ₪{price}\n⏱️ בדיקה כל 1 דקה",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        except:
            await update.message.reply_text("❌ המחיר חייב להיות מספר", reply_markup=get_main_keyboard())
            return WAITING_FOR_DATA

    await update.message.reply_text("❌ פורמט לא תקין. שלח: `<קישור> <מחיר>`", parse_mode='Markdown')
    return WAITING_FOR_DATA

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url, price = context.args[0], int(context.args[1])
        chat_id = update.effective_chat.id
        tracked_hotels[chat_id] = {
            'url': url, 'target_price': price, 'room_type': 'standard',
            'free_cancellation': False, 'cancellation_deadline': None,
            'includes_breakfast': False, 'hotel_rating': 'N/A',
            'viewers': 0, 'low_availability': False,
            'check_in': None, 'check_out': None,
            'guests': 2, 'rooms': 1,
            'history': [], 'alert_threshold': 10,
            'alert_on_up': False, 'check_frequency': 60,
            'last_check': datetime.now(), 'sale_detected': False,
            'hotel_name': 'ממתין לבדיקה'
        }
        await update.message.reply_text(
            f"✅ מעקב הוגדר! יעד: ₪{price}", reply_markup=get_main_keyboard()
        )
    except:
        await update.message.reply_text("❌ /track <URL> <מחיר>")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if chat_id not in tracked_hotels:
        await target.reply_text("ℹ️ אין מעקב פעיל", reply_markup=get_main_keyboard())
        return
    d = tracked_hotels[chat_id]
    room_name = ROOM_TYPES.get(d.get('room_type', 'standard'), {}).get('name', 'סטנדרט')
    msg = (
        f"📊 **מצב מעקב**\n"
        f"🏨 {d.get('hotel_name', 'לא ידוע')}\n"
        f"💰 יעד: ₪{d['target_price']}\n"
        f"🛏️ {room_name}\n"
        f"🔄 ביטול: {'✅' if d.get('free_cancellation') else '❌'}\n"
        f"⏱️ תדירות: {d.get('check_frequency', 60)} דקות\n"
        f"📊 היסטוריה: {len(d.get('history', []))} בדיקות"
    )
    if d.get('check_in') and d.get('check_out'):
        msg += f"\n📅 {d['check_in']} → {d['check_out']}"
    if d.get('hotel_rating') and d['hotel_rating'] != 'N/A':
        msg += f"\n⭐ {d['hotel_rating']}"
    if d.get('viewers', 0) > 10:
        msg += f"\n👀 {d['viewers']} צופים"
    if d.get('low_availability'):
        msg += "\n⚠️ **כמעט אזל!**"
    await target.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if tracked_hotels.pop(chat_id, None):
        await target.reply_text("🛑 המעקב הופסק", reply_markup=get_main_keyboard())
    else:
        await target.reply_text("ℹ️ אין מעקב פעיל", reply_markup=get_main_keyboard())

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if chat_id not in tracked_hotels:
        await target.reply_text("⚠️ אין מעקב", reply_markup=get_main_keyboard())
        return
    history = tracked_hotels[chat_id].get('history', [])
    if not history:
        await target.reply_text("📊 אין היסטוריה", reply_markup=get_main_keyboard())
        return
    recent = history[-10:]
    msg = "📊 **היסטוריה (10 אחרונות):**\n"
    for i, entry in enumerate(reversed(recent), 1):
        dt = entry.get('date', datetime.now()).strftime('%d/%m %H:%M')
        p = entry.get('price', '?')
        msg += f"{i}. {dt} - ₪{p}"
        if entry.get('sale'):
            msg += " 🔥"
        msg += "\n"
    await target.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def list_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if chat_id not in tracked_hotels:
        await target.reply_text("⚠️ אין מעקבים", reply_markup=get_main_keyboard())
        return
    d = tracked_hotels[chat_id]
    msg = f"📋 **המעקב שלך**\n🏨 {d.get('hotel_name', 'לא ידוע')}\n💰 ₪{d['target_price']}\n📊 {len(d.get('history', []))} בדיקות"
    await target.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    if chat_id not in tracked_hotels:
        await target.reply_text("⚠️ אין נתונים", reply_markup=get_main_keyboard())
        return
    history = tracked_hotels[chat_id].get('history', [])
    if not history:
        await target.reply_text("📊 אין נתונים לייצוא", reply_markup=get_main_keyboard())
        return
    csv = "תאריך,מחיר,מבצע\n"
    for e in history:
        dt = e.get('date', datetime.now()).strftime('%Y-%m-%d %H:%M')
        p = e.get('price', '')
        s = 'כן' if e.get('sale') else 'לא'
        csv += f"{dt},{p},{s}\n"
    await target.reply_text(
        f"📤 **ייצוא נתונים**\n{csv[:500]}...",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ בוטל", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# ==================== 7. לולאת בדיקות ====================
async def check_prices_loop(app_telegram):
    while True:
        await asyncio.sleep(60)
        if not tracked_hotels:
            continue
        print(f"🔄 בודק {len(tracked_hotels)} מלונות...")
        for chat_id, data in list(tracked_hotels.items()):
            try:
                # בנה URL עם פרמטרים
                url = data['url']
                if data.get('check_in') and data.get('check_out'):
                    url += f"&checkin={data['check_in']}&checkout={data['check_out']}"
                if data.get('guests'):
                    url += f"&group_adults={data.get('guests', 2)}&no_rooms={data.get('rooms', 1)}"
                
                success, new_price, error, sale, info = await fetch_booking_price(url)
                
                if success and new_price:
                    # עדכון פרטי המלון
                    if info.get('hotel_name'):
                        data['hotel_name'] = info['hotel_name']
                    if info.get('hotel_rating'):
                        data['hotel_rating'] = info['hotel_rating']
                    if info.get('free_cancellation'):
                        data['free_cancellation'] = True
                    if info.get('cancellation_deadline'):
                        data['cancellation_deadline'] = info['cancellation_deadline']
                    if info.get('includes_breakfast'):
                        data['includes_breakfast'] = True
                    if info.get('viewers', 0) > data.get('viewers', 0):
                        data['viewers'] = info.get('viewers', 0)
                    if info.get('low_availability'):
                        data['low_availability'] = True
                    
                    # שמירת היסטוריה
                    if 'history' not in data:
                        data['history'] = []
                    data['history'].append({
                        'date': datetime.now(),
                        'price': new_price,
                        'sale': sale
                    })
                    data['last_check'] = datetime.now()
                    if info.get('sale_detected'):
                        data['sale_detected'] = True
                    
                    # בדיקת ירידת מחיר
                    if new_price < data['target_price']:
                        drop = ((data['target_price'] - new_price) / data['target_price']) * 100
                        alert = f"🎉 **ירידת מחיר!** 📉\n💰 ₪{data['target_price']} → ₪{new_price}\n📉 {drop:.1f}%"
                        if sale:
                            alert += "\n🔥 **מבצע פעיל!**"
                        if data.get('free_cancellation'):
                            alert += "\n🔄 ביטול חינם ✅"
                        if data.get('includes_breakfast'):
                            alert += "\n🍳 ארוחת בוקר כלולה"
                        alert += f"\n🔗 [להזמנה]({data['url']})"
                        data['target_price'] = new_price
                        await app_telegram.bot.send_message(
                            chat_id=chat_id,
                            text=alert,
                            parse_mode='Markdown',
                            reply_markup=get_main_keyboard(),
                            disable_web_page_preview=True
                        )
                    elif data.get('alert_on_up') and new_price > data['target_price']:
                        await app_telegram.bot.send_message(
                            chat_id=chat_id,
                            text=f"📈 **עליית מחיר!**\n💰 ₪{data['target_price']} → ₪{new_price}",
                            reply_markup=get_main_keyboard()
                        )
                    
                    # התראת ביקוש גבוה
                    if data.get('viewers', 0) > 10:
                        await app_telegram.bot.send_message(
                            chat_id=chat_id,
                            text=f"👀 **ביקוש גבוה!** {data['viewers']} אנשים צופים עכשיו",
                            reply_markup=get_main_keyboard()
                        )
                    
                    # התראת כמעט אזל
                    if data.get('low_availability'):
                        await app_telegram.bot.send_message(
                            chat_id=chat_id,
                            text="⚠️ **כמעט אזל!** נשארו חדרים בודדים - מהרו להזמין!",
                            reply_markup=get_main_keyboard()
                        )
                    
                else:
                    await app_telegram.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **שגיאה:** {error or 'לא ידוע'}",
                        reply_markup=get_main_keyboard()
                    )
            except Exception as e:
                print(f"❌ שגיאה: {e}")
                try:
                    await app_telegram.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ שגיאה: {str(e)[:100]}",
                        reply_markup=get_main_keyboard()
                    )
                except:
                    pass

# ==================== 8. הפעלה ====================
async def main():
    # Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False), daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()

    # Telegram
    tg_app = Application.builder().token(TOKEN).build()
    await tg_app.bot.delete_webhook(drop_pending_updates=True)

    # Handlers
    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(CommandHandler("track", track_command))
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("stop", stop_command))
    tg_app.add_handler(CommandHandler("history", show_history))
    tg_app.add_handler(CommandHandler("list", list_tracking))
    tg_app.add_handler(CommandHandler("cancel", cancel_command))

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_click, pattern="^btn_track$")],
        states={
            WAITING_FOR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)],
            WAITING_FOR_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(button_click, pattern="^back_to_main$")
        ]
    )
    tg_app.add_handler(conv)
    tg_app.add_handler(CallbackQueryHandler(button_click))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message))

    # לולאה
    asyncio.create_task(check_prices_loop(tg_app))

    print("🚀 Advanced Booking Bot v3.0 Started!")
    print(f"🤖 Token: {TOKEN[:10]}...")
    print("🌐 Web: http://0.0.0.0:8080")

    try:
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("🛑 Stopping...")
    finally:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Bye!")
    except Exception as e:
        print(f"❌ Error: {e}")
