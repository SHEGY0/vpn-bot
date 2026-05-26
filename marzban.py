"""
Модуль для работы с Marzban API.
"""

import httpx
from datetime import datetime, timedelta
from config import MARZBAN_URL, MARZBAN_USER, MARZBAN_PASS

_token: str | None = None

async def _get_token() -> str:
    global _token
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{MARZBAN_URL}/api/admin/token",
            data={"username": MARZBAN_USER, "password": MARZBAN_PASS})
        _token = r.json()["access_token"]
        return _token

async def create_vpn_user(telegram_id: int, days: int) -> dict:
    token = await _get_token()
    headers = {"Authorization": f"Bearer {token}"}
    expire_ts = int((datetime.now() + timedelta(days=days)).timestamp())
    username = f"tg_{telegram_id}_{int(datetime.now().timestamp())}"
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{MARZBAN_URL}/api/user", headers=headers, json={
            "username": username,
            "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
            "inbounds": {"vless": ["VLESS TCP REALITY"]},
            "expire": expire_ts,
            "data_limit": 0,
        })
        data = r.json()
        return {
            "vpn_key":    data["links"][0],
            "sub_link":   data["subscription_url"],
            "expires_at": datetime.fromtimestamp(expire_ts).strftime("%Y-%m-%d %H:%M:%S"),
        }

async def delete_vpn_user(username: str):
    token = await _get_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        await client.delete(f"{MARZBAN_URL}/api/user/{username}", headers=headers)
