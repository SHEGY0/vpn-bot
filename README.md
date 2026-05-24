# VPN Telegram Bot

## Структура файлов
```
vpn_bot/
├── bot.py          — запуск бота
├── config.py       — ВСЕ настройки (токены, тарифы)
├── handlers.py     — логика бота (кнопки, команды)
├── database.py     — база данных SQLite
├── marzban.py      — подключение к VPN панели
├── payments.py     — оплата (CryptoBot + ЮKassa)
└── requirements.txt
```

## Быстрый старт

### 1. Установите зависимости
```bash
pip install -r requirements.txt
```

### 2. Настройте config.py
Откройте `config.py` и заполните:
- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_ID` — ваш Telegram ID (узнать у @userinfobot)

### 3. Запустите бота
```bash
python bot.py
```

---

## После покупки сервера Aeza

Откройте `config.py` и заполните:
```python
MARZBAN_URL   = "http://ВАШ_IP:7777"
MARZBAN_USER  = "admin"
MARZBAN_PASS  = "ВАШ_ПАРОЛЬ"
```

Затем откройте `marzban.py` — там закомментированные блоки
с пометкой "Реальный код". Раскомментируйте их и удалите заглушки.

---

## Подключение оплаты

### CryptoBot (крипта)
1. Напишите @CryptoBot → API → Create App
2. Скопируйте токен в `config.py` → `CRYPTOBOT_TOKEN`
3. В `payments.py` раскомментируйте реальный код в `create_crypto_invoice`

### ЮKassa (рубли)
1. Зарегистрируйтесь на yookassa.ru
2. Получите Shop ID и Secret Key
3. Заполните `YUKASSA_SHOP_ID` и `YUKASSA_SECRET` в `config.py`
4. Настройте webhook: https://ВАШ_ДОМЕН/yookassa/webhook
5. В `payments.py` раскомментируйте реальный код

---

## Админ-команды в боте
- `/admin` — статистика (пользователи, подписки, выручка)
- `/confirm INVOICE_ID` — вручную выдать подписку
- `/broadcast Текст` — рассылка всем пользователям
