"""
Модуль для работы с Marzban API.
Сейчас возвращает заглушки — после покупки сервера
замените MARZBAN_URL, MARZBAN_USER, MARZBAN_PASS в config.py
и раскомментируйте реальные вызовы.
"""

import httpx
from datetime import datetime, timedelta
from config import MARZBAN_URL, MARZBAN_USER, MARZBAN_PASS

# Кэш токена авторизации
_token: str | None = None

async def _get_token() -> str:
    """Получает JWT-токен от Marzban."""
    global _token
    # ── Заглушка (убрать после настройки сервера) ──────────
    _token = "STUB_TOKEN"
    return _token
    # ── Реальный код (раскомментировать после сервера) ──────
    # async with httpx.AsyncClient() as client:
    #     r = await client.post(f"{MARZBAN_URL}/api/admin/token",
    #         data={"username": MARZBAN_USER, "password": MARZBAN_PASS})
    #     _token = r.json()["access_token"]
    #     return _token

async def create_vpn_user(telegram_id: int, days: int) -> dict:
    """
    Создаёт пользователя в Marzban и возвращает:
    - vpn_key  : ссылка vless://...
    - sub_link : subscription link (автообновление)
    - expires_at: дата окончания (строка)
    """
    # ── Заглушка ────────────────────────────────────────────
    expires = datetime.now() + timedelta(days=days)
    stub_key = f"vless://STUB-UUID@YOUR_SERVER_IP:443?type=tcp&security=reality&STUB_PARAMS#{telegram_id}"
    stub_sub = f"{MARZBAN_URL}/sub/user_{telegram_id}"
    return {
        "vpn_key":    stub_key,
        "sub_link":   stub_sub,
        "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S"),
    }
    # ── Реальный код ─────────────────────────────────────────
    # token = await _get_token()
    # headers = {"Authorization": f"Bearer {token}"}
    # expire_ts = int((datetime.now() + timedelta(days=days)).timestamp())
    # username = f"tg_{telegram_id}_{int(datetime.now().timestamp())}"
    # async with httpx.AsyncClient() as client:
    #     r = await client.post(f"{MARZBAN_URL}/api/user", headers=headers, json={
    #         "username": username,
    #         "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
    #         "inbounds": {"vless": ["VLESS TCP REALITY"]},
    #         "expire": expire_ts,
    #         "data_limit": 0,
    #     })
    #     data = r.json()
    #     return {
    #         "vpn_key":    data["links"][0],
    #         "sub_link":   data["subscription_url"],
    #         "expires_at": datetime.fromtimestamp(expire_ts).strftime("%Y-%m-%d %H:%M:%S"),
    #     }

async def delete_vpn_user(telegram_id: int, username: str):
    """Удаляет пользователя из Marzban (при отмене подписки)."""
    pass
    # token = await _get_token()
    # headers = {"Authorization": f"Bearer {token}"}
    # async with httpx.AsyncClient() as client:
    #     await client.delete(f"{MARZBAN_URL}/api/user/{username}", headers=headers)
