# telegram_bot.py — Sürücü GPS Botu
# Sürücü məkanını göndərir → Supabase-ə yazılır → Admin xəritədə görür

import logging
import requests
from datetime import datetime

# ── Konfiqurasiya ─────────────────────────────────────────────────────────────
BOT_TOKEN    = "8791790844:AAEVZk_gcFmfkuRQHlDmu29SfPkIfp-zj9U"
SUPABASE_URL = "https://vsbxbqklsvtmvuxoenut.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzYnhicWtsc3Z0bXZ1eG9lbnV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgwOTExMTEsImV4cCI6MjA5MzY2NzExMX0.XTuQD6W4AhJ5s6tlhYrZmNirMNskS_lNBkzrG4prt04"
API_URL      = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# Sürücü məlumatları — ölkə və kortej xəritəsi
# Format: telegram_user_id → {country, convoy, driver_name}
# Admin istifadəçiləri qeydiyyatdan keçirəcək
DRIVERS = {}  # dynamic - filled from /start command

# ── Supabase əməliyyatları ────────────────────────────────────────────────────
def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

def save_gps(vehicle_id, country, driver_name, lat, lon, speed=0):
    now  = datetime.utcnow().isoformat()
    data = {"vehicle_id": vehicle_id, "country": country,
            "driver_name": driver_name, "lat": lat, "lon": lon,
            "speed_kmh": speed, "updated_at": now}
    # Check exists
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/gps_tracking?vehicle_id=eq.{vehicle_id}",
        headers=supabase_headers())
    if r.json():
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/gps_tracking?vehicle_id=eq.{vehicle_id}",
            json=data, headers=supabase_headers())
    else:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/gps_tracking",
            json=data, headers=supabase_headers())
    log.info(f"GPS saved: {country} {lat},{lon}")

# ── Telegram API ──────────────────────────────────────────────────────────────
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

def request_location(chat_id):
    """Məkan paylaşma düyməsi göndər"""
    keyboard = {
        "keyboard": [[{"text": "📍 Məkanımı Göndər", "request_location": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_message(chat_id,
        "📍 Aşağıdakı düyməni bas — məkanın avtomatik göndəriləcək:",
        reply_markup=keyboard)

def get_updates(offset=None):
    params = {"timeout": 30, "offset": offset}
    try:
        r = requests.get(f"{API_URL}/getUpdates", params=params, timeout=35)
        return r.json().get("result", [])
    except:
        return []

# ── Mesaj emalı ───────────────────────────────────────────────────────────────
def handle_update(update):
    msg      = update.get("message", {})
    chat_id  = msg.get("chat", {}).get("id")
    text     = msg.get("text", "")
    location = msg.get("location")
    user     = msg.get("from", {})
    username = user.get("username", str(chat_id))
    fname    = user.get("first_name", "Sürücü")

    if not chat_id:
        return

    # /start əmri
    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1:
            # /start Kenya__DYP formatında
            param = parts[1]
            p     = param.split("__")
            country = p[0] if len(p) > 0 else ""
            convoy  = p[1] if len(p) > 1 else "DYP"
            DRIVERS[chat_id] = {
                "country":     country,
                "convoy":      convoy,
                "driver_name": fname,
                "vehicle_id":  f"{country}__{convoy}"
            }
            send_message(chat_id,
                f"👋 Salam <b>{fname}</b>!\n\n"
                f"🌍 Ölkə: <b>{country}</b>\n"
                f"🚗 Kortej: <b>{convoy}</b>\n\n"
                f"Aşağıdakı düyməni basaraq məkanını göndər.")
            request_location(chat_id)
        else:
            send_message(chat_id,
                "👋 Salam! Bu bot Protokol Xidməti GPS sistemidir.\n"
                "Admin sizə xüsusi link göndərəcək.")

    # /konum əmri
    elif text in ["/konum", "/gps", "/location"]:
        if chat_id in DRIVERS:
            request_location(chat_id)
        else:
            send_message(chat_id, "⚠️ Əvvəlcə admin tərəfindən göndərilən linki açın.")

    # Məkan mesajı
    elif location:
        lat   = location["latitude"]
        lon   = location["longitude"]
        speed = location.get("speed", 0) or 0
        speed = round(speed * 3.6, 1) if speed else 0

        if chat_id in DRIVERS:
            d = DRIVERS[chat_id]
            save_gps(d["vehicle_id"], d["country"], d["driver_name"], lat, lon, speed)
            send_message(chat_id,
                f"✅ GPS göndərildi!\n"
                f"📍 {lat:.6f}, {lon:.6f}\n"
                f"🚗 {speed} km/h\n\n"
                f"Hər dəfə məkanın dəyişəndə yenidən göndər.")
        else:
            send_message(chat_id,
                "⚠️ Qeydiyyatınız tapılmadı. Admin tərəfindən göndərilən linki açın.")

    # Digər mesajlar
    elif text:
        if chat_id in DRIVERS:
            request_location(chat_id)
        else:
            send_message(chat_id,
                "Admin tərəfindən göndərilən Telegram linkini açın.")

# ── Əsas döngü ────────────────────────────────────────────────────────────────
def main():
    log.info("🤖 Protokol GPS Botu başladı...")
    
    # Bot məlumatını yoxla
    r = requests.get(f"{API_URL}/getMe")
    if r.status_code == 200:
        bot_info = r.json()["result"]
        log.info(f"Bot: @{bot_info['username']}")
    else:
        log.error("Bot token xətalıdır!")
        return

    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            try:
                handle_update(update)
            except Exception as e:
                log.error(f"Xəta: {e}")
            offset = update["update_id"] + 1

if __name__ == "__main__":
    main()
