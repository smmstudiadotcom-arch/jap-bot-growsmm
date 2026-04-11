import requests
import random
import time
import os
import re
from datetime import datetime

JAP_API_KEY    = "ec2fb6c8f5a4ea7ba6cf532e87a09895"
JAP_API_URL    = "https://justanotherpanel.com/api/v2"
JAP_SERVICE    = 7400
QUANTITY_MIN   = 1400
QUANTITY_MAX   = 1600
TG_CHANNEL     = "growsmm"
CHECK_INTERVAL = 60
STATE_FILE     = "last_post_id.txt"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def load_last_post_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val.isdigit() else 0
    return 0

def save_last_post_id(post_id):
    with open(STATE_FILE, "w") as f:
        f.write(str(post_id))

def get_latest_post():
    url = f"https://t.me/s/{TG_CHANNEL}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            log(f"⚠️  Telegram вернул статус {resp.status_code}")
            return None, None
        pattern = rf'https://t\.me/{TG_CHANNEL}/(\d+)'
        matches = re.findall(pattern, resp.text)
        if not matches:
            log("⚠️  Посты не найдены")
            return None, None
        latest_id = max(int(m) for m in matches)
        post_url  = f"https://t.me/{TG_CHANNEL}/{latest_id}"
        return latest_id, post_url
    except Exception as e:
        log(f"❌ Ошибка Telegram: {e}")
        return None, None

def create_jap_order(post_url):
    quantity = random.randint(QUANTITY_MIN, QUANTITY_MAX)
    payload  = {
        "key":      JAP_API_KEY,
        "action":   "add",
        "service":  JAP_SERVICE,
        "link":     post_url,
        "quantity": quantity,
    }
    try:
        log(f"📤 Отправляю заказ: service={JAP_SERVICE}, link={post_url}, quantity={quantity}")
        resp = requests.post(JAP_API_URL, data=payload, timeout=15)
        log(f"📥 Ответ JAP (raw): {resp.status_code} | {repr(resp.text[:300])}")
        if not resp.text.strip():
            log("❌ Пустой ответ — проверьте API ключ или баланс")
            return
        data = resp.json()
        if "order" in data:
            log(f"✅ Заказ создан! ID: {data['order']} | Кол-во: {quantity} | {post_url}")
        elif "error" in data:
            log(f"❌ Ошибка: {data['error']}")
        else:
            log(f"⚠️  Неизвестный ответ: {data}")
    except Exception as e:
        log(f"❌ Ошибка заказа: {e}")

def check_balance():
    try:
        resp = requests.post(JAP_API_URL, data={"key": JAP_API_KEY, "action": "balance"}, timeout=10)
        log(f"📥 Баланс (raw): {resp.status_code} | {repr(resp.text[:200])}")
        if resp.text.strip():
            data = resp.json()
            if "balance" in data:
                log(f"💰 Баланс: ${data['balance']} {data.get('currency','')}")
    except Exception as e:
        log(f"❌ Ошибка баланса: {e}")

def main():
    log("🚀 Бот запущен!")
    log(f"📡 Канал: @{TG_CHANNEL} | Услуга: {JAP_SERVICE} | Кол-во: {QUANTITY_MIN}–{QUANTITY_MAX}")
    check_balance()
    last_id = load_last_post_id()
    if last_id == 0:
        latest_id, _ = get_latest_post()
        if latest_id:
            save_last_post_id(latest_id)
            last_id = latest_id
            log(f"📌 Первый запуск. Последний пост: #{latest_id}. Жду новые...")
    while True:
        try:
            latest_id, post_url = get_latest_post()
            if latest_id and latest_id > last_id:
                for new_id in range(last_id + 1, latest_id + 1):
                    new_url = f"https://t.me/{TG_CHANNEL}/{new_id}"
                    log(f"🆕 Новый пост: {new_url}")
                    create_jap_order(new_url)
                    time.sleep(2)
                save_last_post_id(latest_id)
                last_id = latest_id
            else:
                log(f"🔍 Нет новых постов (последний: #{last_id})")
        except Exception as e:
            log(f"❌ Ошибка: {e}")
        time.sleep(CHECK_INTERVAL)

main()
