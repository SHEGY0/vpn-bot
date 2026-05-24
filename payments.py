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

    # ── Заглушка (убрать после получения токена CryptoBot) ──
    return {
        "invoice_id": f"CRYPTO_STUB_{user_id}_{plan_key}",
        "pay_url":    "https://t.me/CryptoBot?start=STUB_INVOICE",
    }

    # ── Реальный код ────────────────────────────────────────
    # async with httpx.AsyncClient() as client:
    #     r = await client.post(
    #         f"{CRYPTOBOT_API}/createInvoice",
    #         headers={"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN},
    #         json={
    #             "asset": "USDT",
    #             "amount": str(amount),
    #             "description": f"VPN подписка {plan['name']}",
    #             "payload": f"{user_id}:{plan_key}",
    #             "expires_in": 3600,
    #         }
    #     )
    #     data = r.json()["result"]
    #     return {"invoice_id": str(data["invoice_id"]), "pay_url": data["pay_url"]}


async def check_crypto_invoice(invoice_id: str) -> bool:
    """Проверяет оплачен ли инвойс."""
    # Заглушка — всегда False (не оплачено)
    return False
    # async with httpx.AsyncClient() as client:
    #     r = await client.get(
    #         f"{CRYPTOBOT_API}/getInvoices",
    #         headers={"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN},
    #         params={"invoice_ids": invoice_id}
    #     )
    #     items = r.json()["result"]["items"]
    #     return items[0]["status"] == "paid" if items else False


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

    # ── Заглушка ────────────────────────────────────────────
    return {
        "invoice_id": f"YOOKASSA_STUB_{user_id}_{plan_key}",
        "pay_url":    "https://yookassa.ru/STUB_PAYMENT_URL",
    }

    # ── Реальный код ────────────────────────────────────────
    # async with httpx.AsyncClient() as client:
    #     r = await client.post(
    #         "https://api.yookassa.ru/v3/payments",
    #         headers=_yukassa_headers(),
    #         json={
    #             "amount": {"value": str(amount), "currency": "RUB"},
    #             "confirmation": {"type": "redirect", "return_url": "https://t.me/ВАШ_БОТ"},
    #             "description": f"VPN {plan['name']} | user {user_id}",
    #             "metadata": {"user_id": user_id, "plan": plan_key},
    #             "capture": True,
    #         }
    #     )
    #     data = r.json()
    #     return {
    #         "invoice_id": data["id"],
    #         "pay_url":    data["confirmation"]["confirmation_url"],
    #     }
