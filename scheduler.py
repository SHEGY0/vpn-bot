"""
Планировщик задач — уведомления об истекающих подписках.
Запускается автоматически вместе с ботом.
"""

import asyncio
import logging
from datetime import datetime, timedelta
import sqlite3

from database import DB_PATH

logger = logging.getLogger(__name__)


def get_expiring_subscriptions(days: int) -> list:
    """Возвращает подписки которые истекают через N дней."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    target = now + timedelta(days=days)
    # Ищем подписки в окне: от (days-1) до (days) дней
    from_dt = (now + timedelta(days=days-1)).strftime("%Y-%m-%d %H:%M:%S")
    to_dt = target.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        SELECT DISTINCT user_id, expires_at FROM subscriptions
        WHERE expires_at BETWEEN ? AND ?
        AND expires_at > datetime('now')
    """, (from_dt, to_dt))
    rows = c.fetchall()
    conn.close()
    return rows


async def send_expiry_notifications(bot):
    """Отправляет уведомления пользователям у кого подписка истекает."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    renew_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Продлить подписку", callback_data="back:plans")]
    ])

    # Уведомление за 3 дня
    for user_id, expires_at in get_expiring_subscriptions(3):
        try:
            await bot.send_message(
                user_id,
                f"⏰ <b>Ваша подписка истекает через 3 дня!</b>\n\n"
                f"📅 Дата окончания: <b>{expires_at[:10]}</b>\n\n"
                f"Не забудьте продлить чтобы не потерять доступ к VPN.",
                parse_mode="HTML",
                reply_markup=renew_kb
            )
            logger.info(f"Sent 3-day expiry notice to {user_id}")
        except Exception as e:
            logger.warning(f"Failed to notify {user_id}: {e}")

    # Уведомление за 1 день
    for user_id, expires_at in get_expiring_subscriptions(1):
        try:
            await bot.send_message(
                user_id,
                f"🚨 <b>Ваша подписка истекает завтра!</b>\n\n"
                f"📅 Дата окончания: <b>{expires_at[:10]}</b>\n\n"
                f"Продлите прямо сейчас чтобы не потерять доступ к VPN.",
                parse_mode="HTML",
                reply_markup=renew_kb
            )
            logger.info(f"Sent 1-day expiry notice to {user_id}")
        except Exception as e:
            logger.warning(f"Failed to notify {user_id}: {e}")


async def scheduler(bot):
    """Основной цикл планировщика — запускается каждый день в 10:00."""
    logger.info("Scheduler started")
    while True:
        now = datetime.now()
        # Следующий запуск в 10:00
        next_run = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"Next notification check in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)
        await send_expiry_notifications(bot)
