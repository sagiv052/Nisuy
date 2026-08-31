import random

# מאגר זהויות של מכשירים שונים 🎭
USER_AGENTS = [
    # Windows - Chrome & Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # macOS - Safari & Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # iPhone - Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/605.1.15",
    # Android - Chrome
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36"
]

async def fetch_booking_price(url: str):
    async with async_playwright() as p:
        # בחירת זהות אקראית לכל ריצה 🎲
        random_ua = random.choice(USER_AGENTS)
        
        # הגדרת viewport בהתאם לסוג המכשיר (נייד או מחשב) 📐
        is_mobile = "Mobile" in random_ua or "iPhone" in random_ua
        viewport = {'width': 390, 'height': 844} if is_mobile else {'width': 1920, 'height': 1080}

        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled', # ביטול דגל ה-Bot 🚫
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        context = await browser.new_context(
            user_agent=random_ua,
            viewport=viewport,
            locale="he-IL",
            timezone_id="Asia/Jerusalem"
        )
        
        page = await context.new_page()
        
        # הזרקת קוד שמסתיר את השדה navigator.webdriver 🕵️‍♂️
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            # גלישה לעמוד המלון
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(random.randint(3000, 5000)) # המתנה אקראית ⏱️
            
            # איתור המחיר בדף (תומך במגוון אלמנטים)
            price_element = await page.query_selector('.prco-val-bignum, .bd-price-value, [data-testid="price-and-discounted-price"]')
            if price_element:
                text = await price_element.inner_text()
                clean_price = int(re.sub(r'[^\d]', '', text))
                await browser.close()
                return clean_price
        except Exception as e:
            print(f"Scraping error with UA ({random_ua[:30]}...): {e}")
        
        await browser.close()
        return None
