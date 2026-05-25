"""
Веб-сервер для приёма webhook от Freekassa.
Запускается параллельно с ботом на порту 8080.
"""

import hashlib
import logging
from aiohttp import web
import os

from config import PLANS
from database import confirm_payment, save_subscription, get_user, add_referral_bonus
from marzban import create_vpn_user

logger = logging.getLogger(__name__)

FREEKASSA_SHOP_ID = os.environ.get("FREEKASSA_SHOP_ID", "")
FREEKASSA_SECRET2 = os.environ.get("FREEKASSA_SECRET2", "")


def check_freekassa_sign(data: dict) -> bool:
    """Проверяет подпись от Freekassa."""
    sign_str = f"{FREEKASSA_SHOP_ID}:{data['AMOUNT']}:{FREEKASSA_SECRET2}:{data['MERCHANT_ORDER_ID']}"
    expected = hashlib.md5(sign_str.encode()).hexdigest()
    return expected == data.get("SIGN", "")


async def freekassa_webhook(request: web.Request) -> web.Response:
    """Обработчик webhook от Freekassa."""
    try:
        data = await request.post()
        data = dict(data)
        logger.info(f"Freekassa webhook: {data}")

        # Проверяем подпись
        if not check_freekassa_sign(data):
            logger.warning("Invalid Freekassa signature")
            return web.Response(text="invalid sign", status=400)

        invoice_id = data.get("MERCHANT_ORDER_ID", "")
        payment = confirm_payment(invoice_id)
        if not payment:
            logger.warning(f"Payment not found: {invoice_id}")
            return web.Response(text="YES")  # Freekassa требует YES в ответ

        plan = PLANS[payment["plan"]]
        vpn = await create_vpn_user(payment["user_id"], plan["days"])

        save_subscription(
            user_id=payment["user_id"],
            plan=payment["plan"],
            days=plan["days"],
            vpn_key=vpn["vpn_key"],
            sub_link=vpn["sub_link"],
            expires_at=vpn["expires_at"],
            paid_rub=plan["price_rub"],
        )

        # Реферальный бонус
        from handlers import REFERRAL_PERCENT
        user = get_user(payment["user_id"])
        if user and user["referred_by"]:
            bonus = round(plan["price_rub"] * REFERRAL_PERCENT, 2)
            add_referral_bonus(user["referred_by"], payment["user_id"], bonus, payment["plan"])
            try:
                await request.app["bot"].send_message(
                    user["referred_by"],
                    f"💰 <b>Реферальный бонус!</b>\n\n"
                    f"Ваш реферал купил «{plan['name']}»\n"
                    f"Начислено: <b>{bonus}₽</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        # Отправляем ключ пользователю
        try:
            await request.app["bot"].send_message(
                payment["user_id"],
                f"✅ <b>Оплата прошла! Ваш VPN готов.</b>\n\n"
                f"📅 Действует до: <b>{vpn['expires_at'][:10]}</b>\n\n"
                f"🔑 <b>Ваш ключ:</b>\n<code>{vpn['vpn_key']}</code>\n\n"
                f"🔗 <b>Subscription link:</b>\n<code>{vpn['sub_link']}</code>\n\n"
                "📲 Нажмите «Инструкция» чтобы узнать как подключиться.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send key to user: {e}")

        return web.Response(text="YES")

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="YES")


async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="OK")


def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/freekassa/webhook", freekassa_webhook)
    app.router.add_get("/", healthcheck)
    return app


async def start_webhook_server(bot):
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Webhook server started on port 8080")
