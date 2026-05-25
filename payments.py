"""
Модуль оплаты: @CryptoBot (крипта) и ЮKassa (рубли).
"""

import httpx
from config import CRYPTOBOT_TOKEN, YUKASSA_SHOP_ID, YUKASSA_SECRET, PLANS
import uuid
import base64

CRYPTOBOT_API = "https://pay.crypt.bot/api"


# ── CryptoBot ───────────────────────────────────────────────

async def create_crypto_invoice(plan_key: str, user_id: int) -> dict:
    """
    Создаёт инвойс в @CryptoBot.
    Возвращает: {"invoice_id": str, "pay_url": str}
    """
    plan = PLANS[plan_key]
    amount = plan["price_usd"]

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{CRYPTOBOT_API}/createInvoice",
            headers={"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN},
            json={
                "asset": "USDT",
                "amount": str(amount),
                "description": f"VPN подписка {plan['name']}",
                "payload": f"{user_id}:{plan_key}",
                "expires_in": 3600,
            }
        )
        data = r.json()["result"]
        return {"invoice_id": str(data["invoice_id"]), "pay_url": data["pay_url"]}


async def check_crypto_invoice(invoice_id: str) -> bool:
    """Проверяет оплачен ли инвойс."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{CRYPTOBOT_API}/getInvoices",
            headers={"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN},
            params={"invoice_ids": invoice_id}
        )
        items = r.json()["result"]["items"]
        return items[0]["status"] == "paid" if items else False


# ── ЮKassa ──────────────────────────────────────────────────

def _yukassa_headers() -> dict:
    creds = base64.b64encode(f"{YUKASSA_SHOP_ID}:{YUKASSA_SECRET}".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4()),
    }


async def create_yookassa_payment(plan_key: str, user_id: int) -> dict:
    """
    Создаёт платёж в ЮKassa.
    Возвращает: {"invoice_id": str, "pay_url": str}
    """
    plan = PLANS[plan_key]
    amount = plan["price_rub"]

    # ── Заглушка (ЮKassa пока не подключена) ────────────────
    return {
        "invoice_id": f"YOOKASSA_STUB_{user_id}_{plan_key}",
        "pay_url":    "https://yookassa.ru/STUB_PAYMENT_URL",
    }


# ── Freekassa ───────────────────────────────────────────────

import hashlib
import os

FREEKASSA_SHOP_ID = os.environ.get("FREEKASSA_SHOP_ID", "")
FREEKASSA_SECRET1 = os.environ.get("FREEKASSA_SECRET1", "")


async def create_freekassa_payment(plan_key: str, user_id: int) -> dict:
    """
    Создаёт ссылку для оплаты через Freekassa.
    Возвращает: {"invoice_id": str, "pay_url": str}
    """
    from config import PLANS
    plan = PLANS[plan_key]
    amount = plan["price_rub"]
    invoice_id = f"FK_{user_id}_{plan_key}_{int(__import__('time').time())}"

    sign = hashlib.md5(
        f"{FREEKASSA_SHOP_ID}:{amount}:{FREEKASSA_SECRET1}:{invoice_id}".encode()
    ).hexdigest()

    pay_url = (
        f"https://pay.freekassa.com/"
        f"?m={FREEKASSA_SHOP_ID}"
        f"&oa={amount}"
        f"&o={invoice_id}"
        f"&s={sign}"
        f"&currency=RUB"
        f"&lang=ru"
    )

    return {"invoice_id": invoice_id, "pay_url": pay_url}
