# ============================================================
#  НАСТРОЙКИ — все секреты берутся из переменных окружения
#  (Railway → Variables, или локально из .env файла)
# ============================================================

import os

# Токен вашего Telegram бота
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ID администратора
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ── Marzban ────────────────────────────────────────────────
MARZBAN_URL   = os.environ.get("MARZBAN_URL", "http://localhost:7777")
MARZBAN_USER  = os.environ.get("MARZBAN_USER", "admin")
MARZBAN_PASS  = os.environ.get("MARZBAN_PASS", "")

# ── Оплата криптой через @CryptoBot ───────────────────────
CRYPTOBOT_TOKEN = os.environ.get("CRYPTOBOT_TOKEN", "")

# ── Оплата рублями через ЮKassa ───────────────────────────
YUKASSA_SHOP_ID  = os.environ.get("YUKASSA_SHOP_ID", "")
YUKASSA_SECRET   = os.environ.get("YUKASSA_SECRET", "")

# ============================================================
#  ТАРИФЫ
# ============================================================
PLANS = {
    "1m": {
        "name":      "1 месяц",
        "days":      30,
        "price_rub": 149,
        "price_usd": 1.5,
    },
    "3m": {
        "name":      "3 месяца",
        "days":      90,
        "price_rub": 399,
        "price_usd": 4.0,
    },
    "6m": {
        "name":      "6 месяцев",
        "days":      180,
        "price_rub": 699,
        "price_usd": 7.0,
    },
}
