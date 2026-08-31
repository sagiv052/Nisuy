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
    return "Booking Bot Advanced v4.0 🚀🤖"

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

# 2.2 Viewport משתנה
def get_random_viewport():
    if random.random() < 0.3:
        return {'width': random.choice([375, 390, 414]), 'height': random.choice([667, 812, 844, 896])}
    return {'width': random.choice([1366, 1440, 1536, 1920]), 'height': random.choice([768, 900, 1080, 1200])}

# 2.3 כותרות HTTP משתנות
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

# 2.4 מוניטור לניטור כשלונות
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

# 2.5 פונקציות הגנה
async def human_like_behavior(page):
    for _ in range(random.randint(3, 7)):
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.05, 0.2))
    for _ in range(random.randint(2, 5)):
        scroll_amount = random.randint(100, 500)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.3, 1.0))
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
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['he-IL', 'he', 'en-US', 'en'] });
        Object.defineProperty(navigator, 'headless', { get: () => false });
        Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
        Object.defineProperty(screen, 'availHeight', { get: () => 1080 });
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
    await intelligent_delay()
    
    ua, platform = get_random_user_agent()
    viewport = get_random_viewport()
    headers = get_random_headers(platform)
    
    async with async_playwright() as p:
        # 🔥 תיקון - הוספת נתיב מדויק לדפדפן
        try:
            browser = await p.chromium.launch(
                headless=True,
                executable_path='/opt/render/.cache/ms-playwright/chromium-1155/chrome-linux/chrome',
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
        except:
            # אם הנתיב לא עובד - נסה בלי נתיב
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
            extra_http_headers=headers
        )
        
        await manage_cookies(context)
        page = await context.new_page()
        
        await enhanced_stealth(page)
        if stealth_async:
            try:
                await stealth_async(page)
            except:
                pass
        
        await page.route("**/*.{png,jpg,jpeg,gif,webp,ttf,woff,woff2,css,svg,ico}", lambda route: route.abort())
        
        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            await human_like_behavior(page)
            
            if await detect_block(page):
                monitor.record_attempt(False, 'Block detected')
                await browser.close()
                return False, None, 'האתר חסם את הבקשה', False, {}
            
            if await detect_captcha(page):
                monitor.record_attempt(False, 'CAPTCHA detected')
                await browser.close()
                return False, None, 'זוהתה CAPTCHA - מנסה שוב מאוחר יותר', False, {}
            
            data = {}
            
            # שם מלון
            hotel_name_elem = await page.query_selector('.hp__hotel-name, .d2fee87262, .pp-header__title, .bui-u-text-ellipsis--2')
            if hotel_name_elem:
                data['hotel_name'] = (await hotel_name_elem.inner_text()).strip()
            else:
                data['hotel_name'] = 'מלון לא מזוהה'
            
            # דירוג
            rating_elem = await page.query_selector('.bui-review-score__badge, .review-score-badge, .a3b8729ab1')
            if rating_elem:
                data['hotel_rating'] = (await rating_elem.inner_text()).strip()
            else:
                data['hotel_rating'] = 'N/A'
            
            body_text = await page.inner_text('body')
            
            # ביטול חינם
            data['free_cancellation'] = False
            if 'ביטול חינם' in body_text or 'free cancellation' in body_text.lower():
                data['free_cancellation'] = True
                cancel_match = re.search(r'ביטול חינם עד (\d{1,2}/\d{1,2}/\d{4})', body_text)
                if cancel_match:
                    data['cancellation_deadline'] = cancel_match.group(1)
                else:
                    data['cancellation_deadline'] = None
            
            # ארוחת בוקר
            data['includes_breakfast'] = 'ארוחת בוקר' in body_text or 'breakfast' in body_text.lower()
            
            # זיהוי מבצע
            sale_keywords = ['מבצע', 'הנחה', 'סייל', 'sale', 'discount', 'save', 'חיסכון']
            data['sale_detected'] = any(k in body_text.lower() for k in sale_keywords)
            
            # צופים
            viewers_elem = await page.query_selector('.hp-rt-people-viewing, [data-testid="people-viewing"]')
            data['viewers'] = 0
            if viewers_elem:
                viewers_text = await viewers_elem.inner_text()
                viewers_match = re.search(r'(\d+)', viewers_text)
                if viewers_match:
                    data['viewers'] = int(viewers_match.group(1))
            
            # זמינות נמוכה
            data['low_availability'] = False
            rooms_left_elem = await page.query_selector('.room-last-booked, [data-testid="last-rooms"]')
            if rooms_left_elem:
                left_text = await rooms_left_elem.inner_text()
                rooms_match = re.search(r'(\d+)', left_text)
                if rooms_match and int(rooms_match.group(1)) <= 3:
                    data['low_availability'] = True
            
            # חילוץ מחיר
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
            
            # ניסיון חלופי
            prices = re.findall(r'₪\s*([\d,]+)', body_text)
            if prices:
                clean_price = int(re.sub(r'[^\d]', '', prices[0]))
                data['price'] = clean_price
                monitor.record_attempt(True)
                await browser.close()
                return True, clean_price, None, data['sale_detected'], data
            
            monitor.record_attempt(False, 'No price found')
            await browser.close()
            return False, None, 'לא נמצא מחיר', False, data
            
        except Exception as e:
            monitor.record_attempt(False, str(e))
            await browser.close()
            return False, None, str(e), False, {}

# ==================== 4. מבני נתונים וממשק ====================
tracked_hotels = {}
WAITING_FOR_URL = 1
WAITING_FOR_DATES = 2
WAITING_FOR_YEAR = 3
WAITING_FOR_PRICE = 4

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 בדיקת קישור", callback_data="btn_test")],
        [InlineKeyboardButton("➕ מעקב חדש", callback_data="btn_track")],
        [InlineKeyboardButton("📊 מצב מעקב", callback_data="btn_status")],
        [InlineKeyboardButton("🛑 עצור מעקב", callback_data="btn_stop")]
    ])

# ==================== 5. פקודות טלגרם ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎯 **ברוכים הבאים לבוט מעקב המחירים החכם!**\n\n"
        "📌 **איך זה עובד:**\n"
        "1️⃣ שלח קישור למלון\n"
        "2️⃣ בחר תאריכים\n"
        "3️⃣ הזן מחיר שמצאת (או דלג)\n"
        "4️⃣ הבוט יעקוב ויתריע על ירידות!\n\n"
        "🔽 לחץ על '➕ מעקב חדש' להתחלה!"
    )
    await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == "btn_track":
        # איפוס state
        context.user_data['state'] = None
        context.user_data['temp_dates'] = None
        
        if chat_id in tracked_hotels:
            await query.message.reply_text(
                "⚠️ כבר יש לך מעקב פעיל!\n"
                "אם תרצה להתחיל מחדש - עצור את המעקב הקודם.",
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        tracked_hotels[chat_id] = {
            'url': None,
            'check_in': None,
            'check_out': None,
            'user_price': None,
            'best_price': None,
            'last_price': None,
            'history': [],
            'hotel_name': 'ממתין להגדרה',
            'free_cancellation': False,
            'includes_breakfast': False,
            'hotel_rating': 'N/A'
        }
        
        await query.message.reply_text(
            "📤 **שלח קישור למלון**\n\n"
            "לחץ על 'שתף' באפליקציית Booking.com והדבק כאן.\n"
            "לדוגמה:\n"
            "`https://www.booking.com/Share-ALqQ48w`\n\n"
            "או קישור רגיל:\n"
            "`https://www.booking.com/hotel/il/x`",
            parse_mode='Markdown'
        )
        context.user_data['state'] = WAITING_FOR_URL
        return WAITING_FOR_URL

    elif query.data == "btn_test":
        context.user_data['state'] = None
        await query.message.reply_text(
            "🧪 **שלח קישור לבדיקה**\n\n"
            "הבוט יסרוק את המלון ויציג את כל הנתונים\n"
            "בלי להתחיל מעקב.\n\n"
            "לדוגמה:\n"
            "`https://www.booking.com/Share-ALqQ48w`",
            parse_mode='Markdown'
        )
        context.user_data['state'] = WAITING_FOR_URL
        return WAITING_FOR_URL

    elif query.data == "btn_status":
        await status_command(update, context)
        return ConversationHandler.END

    elif query.data == "btn_stop":
        await stop_command(update, context)
        return ConversationHandler.END

    return ConversationHandler.END

def parse_dates(text: str):
    """פונקציה שמנתחת תאריכים ממחרוזת"""
    current_year = datetime.now().year
    
    patterns = [
        # 2.8-2.9 (שנה נוכחית)
        (r'(\d{1,2})\.(\d{1,2})\s*[-–—]\s*(\d{1,2})\.(\d{1,2})', 
         lambda m: (datetime(current_year, int(m[2]), int(m[1])),
                   datetime(current_year, int(m[4]), int(m[3])))),
        # 2.8.2027-2.9.2027 (עם שנה)
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s*[-–—]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
         lambda m: (datetime(int(m[3]), int(m[2]), int(m[1])),
                   datetime(int(m[6]), int(m[5]), int(m[4])))),
        # 2/8-2/9
        (r'(\d{1,2})/(\d{1,2})\s*[-–—]\s*(\d{1,2})/(\d{1,2})',
         lambda m: (datetime(current_year, int(m[2]), int(m[1])),
                   datetime(current_year, int(m[4]), int(m[3])))),
        # 2.8 עד 2.9
        (r'(\d{1,2})\.(\d{1,2})\s*עד\s*(\d{1,2})\.(\d{1,2})',
         lambda m: (datetime(current_year, int(m[2]), int(m[1])),
                   datetime(current_year, int(m[4]), int(m[3])))),
        # 2.8.2027 עד 2.9.2027
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s*עד\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
         lambda m: (datetime(int(m[3]), int(m[2]), int(m[1])),
                   datetime(int(m[6]), int(m[5]), int(m[4])))),
    ]
    
    for pattern, func in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return func(match.groups())
            except:
                continue
    
    # ניסיון חלופי - חיפוש תאריכים בודדים
    date_pattern = r'(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?'
    dates = re.findall(date_pattern, text)
    if len(dates) >= 2:
        try:
            if dates[0][2]:
                d1 = datetime(int(dates[0][2]), int(dates[0][1]), int(dates[0][0]))
            else:
                d1 = datetime(current_year, int(dates[0][1]), int(dates[0][0]))
            
            if dates[1][2]:
                d2 = datetime(int(dates[1][2]), int(dates[1][1]), int(dates[1][0]))
            else:
                d2 = datetime(current_year, int(dates[1][1]), int(dates[1][0]))
            
            if d1 and d2 and d2 > d1:
                return (d1, d2)
        except:
            pass
    
    return None

async def handle_input_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    # === מצב: מחכה לקישור ===
    if context.user_data.get('state') == WAITING_FOR_URL:
        url = text.split()[0] if text.split() else text
        
        if 'booking.com' not in url.lower():
            await update.message.reply_text(
                "❌ **קישור לא תקין**\n\n"
                "שלח קישור מ-Booking.com בלבד.\n"
                "למשל: `https://www.booking.com/Share-ALqQ48w`",
                parse_mode='Markdown'
            )
            context.user_data['state'] = WAITING_FOR_URL
            return WAITING_FOR_URL
        
        if chat_id not in tracked_hotels:
            tracked_hotels[chat_id] = {
                'url': None,
                'check_in': None,
                'check_out': None,
                'user_price': None,
                'best_price': None,
                'last_price': None,
                'history': [],
                'hotel_name': 'ממתין להגדרה',
                'free_cancellation': False,
                'includes_breakfast': False,
                'hotel_rating': 'N/A'
            }
        
        tracked_hotels[chat_id]['url'] = url
        
        await update.message.reply_text("🔍 **בודק קישור...**")
        
        try:
            # הוספת Timeout של 30 שניות
            success, price, error, sale, info = await asyncio.wait_for(
                fetch_booking_price(url),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            await update.message.reply_text(
                "⏰ **הסריקה ארכה יותר מדי זמן**\n\n"
                "יכול להיות שהאתר עמוס או שיש בעיה.\n"
                "נסה שוב בעוד כמה דקות.",
                reply_markup=get_main_keyboard()
            )
            context.user_data['state'] = None
            return ConversationHandler.END
        
        if success and price:
            tracked_hotels[chat_id]['hotel_name'] = info.get('hotel_name', 'מלון')
            tracked_hotels[chat_id]['last_price'] = price
            tracked_hotels[chat_id]['best_price'] = price
            tracked_hotels[chat_id]['free_cancellation'] = info.get('free_cancellation', False)
            tracked_hotels[chat_id]['includes_breakfast'] = info.get('includes_breakfast', False)
            tracked_hotels[chat_id]['hotel_rating'] = info.get('hotel_rating', 'N/A')
            
            msg = f"✅ **קישור נקלט בהצלחה!**\n\n"
            msg += f"🏨 **מלון:** {info.get('hotel_name', 'לא ידוע')}\n"
            msg += f"💰 **מחיר נוכחי:** ₪{price}\n"
            msg += f"⭐ **דירוג:** {info.get('hotel_rating', 'N/A')}\n"
            msg += f"🔄 **ביטול חינם:** {'✅' if info.get('free_cancellation') else '❌'}\n"
            msg += f"🍳 **ארוחת בוקר:** {'✅' if info.get('includes_breakfast') else '❌'}\n\n"
            msg += f"📅 **עכשיו שלח תאריכים:**\n"
            msg += f"(למשל: `2.8-2.9` או `2.8.2027-2.9.2027`)"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            context.user_data['state'] = WAITING_FOR_DATES
            return WAITING_FOR_DATES
        else:
            await update.message.reply_text(
                f"❌ **הקישור לא נקלט**\n\n"
                f"שגיאה: {error}\n\n"
                "🔧 נסה שוב עם קישור אחר.",
                reply_markup=get_main_keyboard()
            )
            context.user_data['state'] = None
            return ConversationHandler.END
    
    # === מצב: מחכה לתאריכים ===
    elif context.user_data.get('state') == WAITING_FOR_DATES:
        dates = parse_dates(text)
        
        if not dates:
            await update.message.reply_text(
                "❌ **פורמט לא תקין**\n\n"
                "שלח תאריכים באחד מהפורמטים:\n"
                "• `2.8-2.9` (אותה שנה)\n"
                "• `2.8.2027-2.9.2027`\n"
                "• `2/8-2/9`\n"
                "• `2.8 עד 2.9`",
                parse_mode='Markdown'
            )
            return WAITING_FOR_DATES
        
        check_in, check_out = dates
        
        if check_in.year == 1900 or check_out.year == 1900:
            await update.message.reply_text(
                "📅 **איזו שנה?**\n\n"
                "לא זיהיתי שנה, אנא בחר:\n"
                "שלח `2026`, `2027` או שנה אחרת",
                parse_mode='Markdown'
            )
            context.user_data['temp_dates'] = (check_in, check_out)
            context.user_data['state'] = WAITING_FOR_YEAR
            return WAITING_FOR_YEAR
        
        if chat_id in tracked_hotels:
            tracked_hotels[chat_id]['check_in'] = check_in.strftime('%Y-%m-%d')
            tracked_hotels[chat_id]['check_out'] = check_out.strftime('%Y-%m-%d')
            
            await update.message.reply_text(
                f"✅ **תאריכים נקלטו!**\n"
                f"📅 {check_in.strftime('%d/%m/%Y')} → {check_out.strftime('%d/%m/%Y')}\n\n"
                f"💰 **עכשיו שלח מחיר שמצאת** (או שלח `דלג`):\n"
                f"אם יש לך מחיר ממקור אחר - שלח אותו,\n"
                f"אחרת הבוט ישתמש במחיר הנוכחי.",
                parse_mode='Markdown'
            )
            context.user_data['state'] = WAITING_FOR_PRICE
            return WAITING_FOR_PRICE
        
        context.user_data['state'] = None
        return ConversationHandler.END
    
    # === מצב: מחכה לשנה ===
    elif context.user_data.get('state') == WAITING_FOR_YEAR:
        try:
            year = int(text.strip())
            if year < 2020 or year > 2030:
                await update.message.reply_text("❌ שנה לא תקינה. שלח 2020-2030")
                return WAITING_FOR_YEAR
            
            check_in, check_out = context.user_data.get('temp_dates', (None, None))
            if check_in and check_out:
                check_in = check_in.replace(year=year)
                check_out = check_out.replace(year=year)
                
                if chat_id in tracked_hotels:
                    tracked_hotels[chat_id]['check_in'] = check_in.strftime('%Y-%m-%d')
                    tracked_hotels[chat_id]['check_out'] = check_out.strftime('%Y-%m-%d')
                    
                    await update.message.reply_text(
                        f"✅ **תאריכים נקלטו!**\n"
                        f"📅 {check_in.strftime('%d/%m/%Y')} → {check_out.strftime('%d/%m/%Y')}\n\n"
                        f"💰 **עכשיו שלח מחיר שמצאת** (או שלח `דלג`):",
                        parse_mode='Markdown'
                    )
                    context.user_data['state'] = WAITING_FOR_PRICE
                    return WAITING_FOR_PRICE
        except:
            await update.message.reply_text("❌ שלח שנה תקינה (למשל: 2027)")
            return WAITING_FOR_YEAR
        
        context.user_data['state'] = None
        return ConversationHandler.END
    
    # === מצב: מחכה למחיר ===
    elif context.user_data.get('state') == WAITING_FOR_PRICE:
        if text.lower() == 'דלג' or text.lower() == 'skip':
            if chat_id in tracked_hotels:
                data = tracked_hotels[chat_id]
                
                await update.message.reply_text("🔍 **מבצע סריקה ראשונית...**")
                
                try:
                    success, price, error, sale, info = await asyncio.wait_for(
                        fetch_booking_price(data['url']),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    await update.message.reply_text(
                        "⏰ **הסריקה ארכה יותר מדי זמן**\n\n"
                        "נסה שוב בעוד כמה דקות.",
                        reply_markup=get_main_keyboard()
                    )
                    context.user_data['state'] = None
                    return ConversationHandler.END
                
                if success and price:
                    data['last_price'] = price
                    if not data['best_price']:
                        data['best_price'] = price
                    if info.get('hotel_name'):
                        data['hotel_name'] = info['hotel_name']
                    
                    msg = "✅ **המעקב הוגדר בהצלחה!**\n\n"
                    msg += f"🏨 **מלון:** {data['hotel_name']}\n"
                    msg += f"🔥 **מחיר נוכחי:** ₪{price}\n"
                    msg += f"📅 **תאריכים:** {data['check_in']} → {data['check_out']}\n\n"
                    msg += "💡 הבוט יעקוב ויתריע על ירידות!"
                    
                    await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
                    
                    data['history'].append({
                        'date': datetime.now(),
                        'price': price,
                        'sale': sale,
                        'user_price': data.get('user_price')
                    })
                    
                    context.user_data['state'] = None
                    return ConversationHandler.END
                else:
                    await update.message.reply_text(
                        f"❌ **שגיאה בסריקה:**\n{error}\n\n"
                        "🔧 נסה שוב או בדוק את הקישור.",
                        reply_markup=get_main_keyboard()
                    )
                    context.user_data['state'] = None
                    return ConversationHandler.END
        else:
            try:
                price = int(re.sub(r'[^\d]', '', text))
                if price <= 0:
                    await update.message.reply_text("❌ שלח מחיר חיובי")
                    return WAITING_FOR_PRICE
                
                if chat_id in tracked_hotels:
                    data = tracked_hotels[chat_id]
                    data['user_price'] = price
                    
                    await update.message.reply_text("🔍 **מבצע סריקה ראשונית...**")
                    
                    try:
                        success, new_price, error, sale, info = await asyncio.wait_for(
                            fetch_booking_price(data['url']),
                            timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        await update.message.reply_text(
                            "⏰ **הסריקה ארכה יותר מדי זמן**\n\n"
                            "נסה שוב בעוד כמה דקות.",
                            reply_markup=get_main_keyboard()
                        )
                        context.user_data['state'] = None
                        return ConversationHandler.END
                    
                    if success and new_price:
                        data['last_price'] = new_price
                        if not data['best_price']:
                            data['best_price'] = new_price
                        if info.get('hotel_name'):
                            data['hotel_name'] = info['hotel_name']
                        
                        msg = "✅ **המעקב הוגדר בהצלחה!**\n\n"
                        msg += f"🏨 **מלון:** {data['hotel_name']}\n"
                        msg += f"💰 **המחיר שמצאת:** ₪{price}\n"
                        msg += f"🔥 **מחיר נוכחי:** ₪{new_price}\n"
                        
                        if new_price < price:
                            savings = price - new_price
                            percent = (savings / price) * 100
                            msg += f"🎉 **חיסכון:** ₪{savings} ({percent:.1f}%)\n"
                            msg += f"✅ **כבר שווה!**\n"
                        elif new_price > price:
                            msg += f"⚠️ **המחיר גבוה יותר** ממה שמצאת\n"
                            msg += f"💡 הבוט יעקוב ויתריע על ירידות\n"
                        else:
                            msg += f"💡 המחיר זהה למה שמצאת\n"
                        
                        msg += f"\n📅 **תאריכים:** {data['check_in']} → {data['check_out']}"
                        
                        await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
                        
                        data['history'].append({
                            'date': datetime.now(),
                            'price': new_price,
                            'sale': sale,
                            'user_price': price
                        })
                        
                        context.user_data['state'] = None
                        return ConversationHandler.END
                    else:
                        await update.message.reply_text(
                            f"❌ **שגיאה בסריקה:**\n{error}\n\n"
                            "🔧 נסה שוב או בדוק את הקישור.",
                            reply_markup=get_main_keyboard()
                        )
                        context.user_data['state'] = None
                        return ConversationHandler.END
            except:
                await update.message.reply_text("❌ שלח מספר תקין או 'דלג'")
                return WAITING_FOR_PRICE
        
        context.user_data['state'] = None
        return ConversationHandler.END
    
    await update.message.reply_text(
        "❓ לא הבנתי.\n"
        "לחץ על כפתור '➕ מעקב חדש' להתחלה.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# ==================== 6. פקודות מעקב ====================

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🧪 **בדיקת קישור**\n\n"
            "שלח: `/test <קישור>`\n"
            "למשל: `/test https://www.booking.com/Share-ALqQ48w`",
            parse_mode='Markdown'
        )
        return
    
    url = context.args[0]
    msg = await update.message.reply_text("⏳ **בודק...** זה יכול לקחת 10-20 שניות")
    
    try:
        success, price, error, sale, info = await asyncio.wait_for(
            fetch_booking_price(url),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        await msg.edit_text(
            "⏰ **הסריקה ארכה יותר מדי זמן**\n\n"
            "נסה שוב בעוד כמה דקות.",
            reply_markup=get_main_keyboard()
        )
        return
    
    if success:
        result = (
            "🧪 **תוצאות הבדיקה:**\n\n"
            f"🏨 **מלון:** {info.get('hotel_name', 'לא ידוע')}\n"
            f"💰 **מחיר:** ₪{price}\n"
            f"⭐ **דירוג:** {info.get('hotel_rating', 'N/A')}\n"
            f"🔄 **ביטול חינם:** {'✅' if info.get('free_cancellation') else '❌'}\n"
            f"🍳 **ארוחת בוקר:** {'✅' if info.get('includes_breakfast') else '❌'}\n"
            f"🔥 **מבצע:** {'✅' if sale else '❌'}\n"
            f"👀 **צופים:** {info.get('viewers', 0)}\n"
            f"⚠️ **כמעט אזל:** {'✅' if info.get('low_availability') else '❌'}\n\n"
            "✅ **הסריקה עבדה בהצלחה!**\n"
            "לחץ על '➕ מעקב חדש' כדי להתחיל לעקוב."
        )
        await msg.edit_text(result, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        await msg.edit_text(
            f"❌ **שגיאה בבדיקה:**\n{error}\n\n"
            "🔧 **טיפים:**\n"
            "• ודא שהקישור תקין\n"
            "• המתן 30 שניות ונסה שוב",
            reply_markup=get_main_keyboard()
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    
    if chat_id not in tracked_hotels:
        await target.reply_text("ℹ️ אין מעקב פעיל", reply_markup=get_main_keyboard())
        return
    
    data = tracked_hotels[chat_id]
    
    msg = f"📊 **מצב מעקב**\n"
    msg += f"🏨 {data.get('hotel_name', 'לא ידוע')}\n"
    
    if data.get('user_price'):
        msg += f"💰 **המחיר שמצאת:** ₪{data['user_price']}\n"
    if data.get('best_price'):
        msg += f"🔥 **המחיר הזול ביותר:** ₪{data['best_price']}\n"
        if data.get('user_price') and data['user_price'] > data['best_price']:
            savings = data['user_price'] - data['best_price']
            msg += f"🎉 **חיסכון:** ₪{savings} ({savings/data['user_price']*100:.1f}%)\n"
    
    msg += f"📅 {data.get('check_in', 'N/A')} → {data.get('check_out', 'N/A')}\n"
    msg += f"🔄 ביטול חינם: {'✅' if data.get('free_cancellation') else '❌'}\n"
    msg += f"🍳 ארוחת בוקר: {'✅' if data.get('includes_breakfast') else '❌'}\n"
    msg += f"⭐ דירוג: {data.get('hotel_rating', 'N/A')}\n"
    msg += f"📊 היסטוריה: {len(data.get('history', []))} בדיקות"
    
    await target.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = update.message or update.callback_query.message
    
    if tracked_hotels.pop(chat_id, None):
        await target.reply_text("🛑 **המעקב הופסק**\n\nניתן להתחיל מעקב חדש בכל עת.", reply_markup=get_main_keyboard())
    else:
        await target.reply_text("ℹ️ אין מעקב פעיל", reply_markup=get_main_keyboard())

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = None
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
                url = data['url']
                if data.get('check_in') and data.get('check_out'):
                    url += f"&checkin={data['check_in']}&checkout={data['check_out']}"
                
                success, new_price, error, sale, info = await fetch_booking_price(url)
                
                if success and new_price:
                    if info.get('hotel_name'):
                        data['hotel_name'] = info['hotel_name']
                    if info.get('free_cancellation'):
                        data['free_cancellation'] = True
                    if info.get('includes_breakfast'):
                        data['includes_breakfast'] = True
                    if info.get('hotel_rating'):
                        data['hotel_rating'] = info['hotel_rating']
                    
                    data['history'].append({
                        'date': datetime.now(),
                        'price': new_price,
                        'sale': sale,
                        'user_price': data.get('user_price')
                    })
                    
                    if not data['best_price'] or new_price < data['best_price']:
                        data['best_price'] = new_price
                    
                    # בדיקת ירידה לעומת מחיר המשתמש
                    if data.get('user_price') and new_price < data['user_price']:
                        savings = data['user_price'] - new_price
                        percent = (savings / data['user_price']) * 100
                        
                        alert = f"🎉 **ירידת מחיר!** 📉\n\n"
                        alert += f"💰 **המחיר שמצאת:** ₪{data['user_price']}\n"
                        alert += f"🔥 **מחיר עכשיו:** ₪{new_price}\n"
                        alert += f"🎉 **חיסכון:** ₪{savings} ({percent:.1f}%)\n"
                        
                        if sale:
                            alert += "\n🔥 **מבצע פעיל!**\n"
                        if data.get('free_cancellation'):
                            alert += "\n🔄 ביטול חינם ✅\n"
                        if data.get('includes_breakfast'):
                            alert += "\n🍳 ארוחת בוקר כלולה\n"
                        
                        alert += f"\n🔗 [לחץ להזמנה]({data['url']})"
                        
                        await app_telegram.bot.send_message(
                            chat_id=chat_id,
                            text=alert,
                            parse_mode='Markdown',
                            reply_markup=get_main_keyboard(),
                            disable_web_page_preview=True
                        )
                        
                        data['user_price'] = new_price
                    
                    # בדיקת ירידה מול המחיר האחרון
                    elif data['last_price'] and new_price < data['last_price']:
                        drop = ((data['last_price'] - new_price) / data['last_price']) * 100
                        if drop >= 10:
                            alert = f"📉 **ירידת מחיר!**\n"
                            alert += f"💰 ₪{data['last_price']} → ₪{new_price}\n"
                            alert += f"📉 {drop:.1f}% ירידה"
                            if sale:
                                alert += "\n🔥 מבצע!"
                            alert += f"\n🔗 [להזמנה]({data['url']})"
                            
                            await app_telegram.bot.send_message(
                                chat_id=chat_id,
                                text=alert,
                                parse_mode='Markdown',
                                reply_markup=get_main_keyboard(),
                                disable_web_page_preview=True
                            )
                    
                    data['last_price'] = new_price
                    
                else:
                    await app_telegram.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **שגיאה בסריקה:**\n{error or 'לא ידוע'}",
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
    tg_app.add_handler(CommandHandler("test", test_command))
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("stop", stop_command))
    tg_app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Conversation handler
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_click, pattern="^btn_track$"),
            CallbackQueryHandler(button_click, pattern="^btn_test$")
        ],
        states={
            WAITING_FOR_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)],
            WAITING_FOR_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)],
            WAITING_FOR_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)],
            WAITING_FOR_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_message)]
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
    
    print("🚀 Advanced Booking Bot v4.0 Started!")
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
