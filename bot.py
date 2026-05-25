import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import router
from scheduler import scheduler
from webhook_server import start_webhook_server

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Запускаем планировщик и webhook сервер параллельно
    asyncio.create_task(scheduler(bot))
    asyncio.create_task(start_webhook_server(bot))

    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
