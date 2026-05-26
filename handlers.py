import sqlite3
"""
Все хендлеры Telegram бота.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import PLANS, ADMIN_ID
from database import (
    add_user, get_user, save_payment, confirm_payment,
    save_subscription, get_active_subscription, get_all_users, get_stats,
    get_referral_count, get_referral_earnings, add_referral_bonus,
    get_balance, deduct_balance
)
from marzban import create_vpn_user
from payments import create_crypto_invoice, create_yookassa_payment, check_crypto_invoice, create_freekassa_payment

REFERRAL_PERCENT = 0.30  # 30%

router = Router()


# ── Клавиатуры ───────────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Купить подписку")],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="📋 Инструкция")],
        [KeyboardButton(text="👥 Реферальная программа"), KeyboardButton(text="💬 Поддержка")],
    ], resize_keyboard=True)


def plans_keyboard(show_balance_pay: bool = False, balance: float = 0) -> InlineKeyboardMarkup:
    buttons = []
    for key, plan in PLANS.items():
        label = f"{plan['name']} — {plan['price_rub']}₽ / ${plan['price_usd']}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"plan:{key}")])
    if show_balance_pay:
        buttons.append([InlineKeyboardButton(
            text=f"💰 Оплатить с баланса ({balance:.0f}₽)",
            callback_data="pay:balance"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_keyboard(plan_key: str, balance: float = 0) -> InlineKeyboardMarkup:
    plan = PLANS[plan_key]
    buttons = [
        [InlineKeyboardButton(text="💎 Крипта (USDT)", callback_data=f"pay:crypto:{plan_key}")],
        [InlineKeyboardButton(text="💳 Рубли (Freekassa)", callback_data=f"pay:fk:{plan_key}")],
    ]
    if balance >= plan["price_rub"]:
        buttons.append([InlineKeyboardButton(
            text=f"💰 С баланса ({balance:.0f}₽)",
            callback_data=f"pay:balance:{plan_key}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back:plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def check_payment_keyboard(invoice_id: str, method: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check:{method}:{invoice_id}")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="back:plans")],
    ])


# ── /start ───────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    # Проверяем реферальный параметр
    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].replace("ref_", ""))
            if ref_id != message.from_user.id:
                referred_by = ref_id
        except ValueError:
            pass

    # Сохраняем пользователя (если новый — с реферером)
    user = get_user(message.from_user.id)
    if not user:
        add_user(message.from_user.id, message.from_user.username, referred_by)
        # Уведомляем реферера о новом приглашённом
        if referred_by:
            try:
                await message.bot.send_message(
                    referred_by,
                    f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
                    f"Вы получите <b>30%</b> от его первой покупки.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        add_user(message.from_user.id, message.from_user.username)

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "🔐 <b>Быстрый и надёжный VPN</b>\n\n"
        "• Несколько серверов по всему миру 🌍\n"
        "• Работает на iOS, Android, Windows, Mac\n"
        "• Подписка активируется автоматически\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ── Покупка ──────────────────────────────────────────────────

@router.message(F.text == "🛒 Купить подписку")
async def buy_subscription(message: Message):
    balance = get_balance(message.from_user.id)
    await message.answer(
        "📦 <b>Выберите тариф:</b>",
        parse_mode="HTML",
        reply_markup=plans_keyboard()
    )


@router.callback_query(F.data == "back:plans")
async def back_to_plans(cb: CallbackQuery):
    await cb.message.edit_text(
        "📦 <b>Выберите тариф:</b>",
        parse_mode="HTML",
        reply_markup=plans_keyboard()
    )


@router.callback_query(F.data.startswith("plan:"))
async def select_plan(cb: CallbackQuery):
    plan_key = cb.data.split(":")[1]
    plan = PLANS[plan_key]
    balance = get_balance(cb.from_user.id)
    text = (
        f"✅ Тариф: <b>{plan['name']}</b>\n"
        f"💰 Цена: <b>{plan['price_rub']}₽</b> / <b>${plan['price_usd']}</b>\n\n"
        "Выберите способ оплаты:"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=payment_keyboard(plan_key, balance))


# ── Оплата с баланса ─────────────────────────────────────────

@router.callback_query(F.data.startswith("pay:balance:"))
async def pay_with_balance(cb: CallbackQuery, bot: Bot):
    plan_key = cb.data.split(":")[2]
    plan = PLANS[plan_key]
    balance = get_balance(cb.from_user.id)

    if balance < plan["price_rub"]:
        await cb.answer("❌ Недостаточно средств на балансе", show_alert=True)
        return

    success = deduct_balance(cb.from_user.id, plan["price_rub"])
    if not success:
        await cb.answer("❌ Ошибка списания. Попробуйте ещё раз.", show_alert=True)
        return

    vpn = await create_vpn_user(cb.from_user.id, plan["days"])
    save_subscription(
        user_id=cb.from_user.id,
        plan=plan_key,
        days=plan["days"],
        vpn_key=vpn["vpn_key"],
        sub_link=vpn["sub_link"],
        expires_at=vpn["expires_at"],
        paid_rub=plan["price_rub"],
    )

    await cb.message.edit_text(
        f"✅ <b>Оплачено с баланса! Ваш VPN готов.</b>\n\n"
        f"📅 Действует до: <b>{vpn['expires_at'][:10]}</b>\n\n"
        f"🔑 <b>Ваш ключ:</b>\n<code>{vpn['vpn_key']}</code>\n\n"
        f"🔗 <b>Subscription link:</b>\n<code>{vpn['sub_link']}</code>\n\n"
        "📲 Нажмите «Инструкция» чтобы узнать как подключиться.",
        parse_mode="HTML"
    )


# ── Оплата крипта ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay:crypto:"))
async def pay_crypto(cb: CallbackQuery):
    plan_key = cb.data.split(":")[2]
    plan = PLANS[plan_key]

    invoice = await create_crypto_invoice(plan_key, cb.from_user.id)
    save_payment(cb.from_user.id, invoice["invoice_id"], plan_key, "crypto", plan["price_usd"], "USDT")

    text = (
        f"💎 <b>Оплата криптовалютой</b>\n\n"
        f"Сумма: <b>${plan['price_usd']} USDT</b>\n"
        f"Тариф: <b>{plan['name']}</b>\n\n"
        f"👉 <a href='{invoice['pay_url']}'>Нажмите для оплаты</a>\n\n"
        "После оплаты нажмите кнопку ниже:"
    )
    await cb.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=check_payment_keyboard(invoice["invoice_id"], "crypto"),
        disable_web_page_preview=True
    )


# ── Оплата рубли ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay:rub:"))
async def pay_rub(cb: CallbackQuery):
    plan_key = cb.data.split(":")[2]
    plan = PLANS[plan_key]

    invoice = await create_yookassa_payment(plan_key, cb.from_user.id)
    save_payment(cb.from_user.id, invoice["invoice_id"], plan_key, "yookassa", plan["price_rub"], "RUB")

    text = (
        f"💳 <b>Оплата рублями</b>\n\n"
        f"Сумма: <b>{plan['price_rub']}₽</b>\n"
        f"Тариф: <b>{plan['name']}</b>\n\n"
        f"👉 <a href='{invoice['pay_url']}'>Нажмите для оплаты</a>\n\n"
        "После оплаты нажмите кнопку ниже:"
    )
    await cb.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=check_payment_keyboard(invoice["invoice_id"], "rub"),
        disable_web_page_preview=True
    )


# ── Проверка оплаты ───────────────────────────────────────────

async def _activate_subscription(cb_or_msg, bot: Bot, user_id: int, plan_key: str, method: str):
    """Создаёт подписку и начисляет реферальный бонус."""
    plan = PLANS[plan_key]
    vpn = await create_vpn_user(user_id, plan["days"])

    save_subscription(
        user_id=user_id,
        plan=plan_key,
        days=plan["days"],
        vpn_key=vpn["vpn_key"],
        sub_link=vpn["sub_link"],
        expires_at=vpn["expires_at"],
        paid_rub=plan["price_rub"] if method in ("rub", "balance") else 0,
        paid_usd=plan["price_usd"] if method == "crypto" else 0,
    )

    # Реферальный бонус
    user = get_user(user_id)
    if user and user["referred_by"]:
        bonus = round(plan["price_rub"] * REFERRAL_PERCENT, 2)
        add_referral_bonus(user["referred_by"], user_id, bonus, plan_key)
        try:
            await bot.send_message(
                user["referred_by"],
                f"💰 <b>Реферальный бонус!</b>\n\n"
                f"Ваш реферал купил подписку «{plan['name']}»\n"
                f"Вам начислено: <b>{bonus}₽</b> (30%)\n"
                f"Используйте баланс для оплаты своей подписки!",
                parse_mode="HTML"
            )
        except Exception:
            pass

    return vpn


@router.callback_query(F.data.startswith("check:"))
async def check_payment(cb: CallbackQuery, bot: Bot):
    _, method, invoice_id = cb.data.split(":", 2)

    paid = False
    if method == "crypto":
        paid = await check_crypto_invoice(invoice_id)
    else:
        paid = False

    if not paid:
        await cb.answer(
            "⏳ Оплата ещё не поступила. Подождите немного и попробуйте снова.",
            show_alert=True
        )
        return

    payment = confirm_payment(invoice_id)
    if not payment:
        await cb.answer("Ошибка. Обратитесь в поддержку.", show_alert=True)
        return

    vpn = await _activate_subscription(cb, bot, payment["user_id"], payment["plan"], method)

    await cb.message.edit_text(
        f"✅ <b>Оплата прошла! Ваш VPN готов.</b>\n\n"
        f"📅 Действует до: <b>{vpn['expires_at'][:10]}</b>\n\n"
        f"🔑 <b>Ваш ключ:</b>\n<code>{vpn['vpn_key']}</code>\n\n"
        f"🔗 <b>Subscription link:</b>\n<code>{vpn['sub_link']}</code>\n\n"
        "📲 Нажмите «Инструкция» чтобы узнать как подключиться.",
        parse_mode="HTML"
    )

    plan = PLANS[payment["plan"]]
    await bot.send_message(
        ADMIN_ID,
        f"💰 Новая оплата!\n"
        f"👤 @{cb.from_user.username} (id: {cb.from_user.id})\n"
        f"📦 Тариф: {plan['name']}\n"
        f"💳 Метод: {method}"
    )


# ── Реферальная программа ─────────────────────────────────────

@router.message(F.text == "👥 Реферальная программа")
async def referral_program(message: Message):
    user_id = message.from_user.id
    ref_count = get_referral_count(user_id)
    total_earned = get_referral_earnings(user_id)
    balance = get_balance(user_id)

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    await message.answer(
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте <b>30%</b> от каждой их покупки на свой баланс!\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Приглашено друзей: <b>{ref_count}</b>\n"
        f"• Всего заработано: <b>{total_earned:.0f}₽</b>\n"
        f"• Баланс: <b>{balance:.0f}₽</b>\n\n"
        f"💡 Баланс можно потратить при покупке подписки — кнопка «С баланса» появится автоматически.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ── Профиль ───────────────────────────────────────────────────

@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message):
    sub = get_active_subscription(message.from_user.id)
    balance = get_balance(message.from_user.id)

    if not sub:
        await message.answer(
            f"😔 У вас нет активной подписки.\n\n"
            f"💰 Баланс: <b>{balance:.0f}₽</b>\n\n"
            "Нажмите «🛒 Купить подписку» чтобы начать.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        return

    plan = PLANS.get(sub["plan"], {})
    await message.answer(
        f"👤 <b>Ваша подписка</b>\n\n"
        f"📦 Тариф: <b>{plan.get('name', sub['plan'])}</b>\n"
        f"📅 Действует до: <b>{sub['expires_at'][:10]}</b>\n"
        f"💰 Баланс: <b>{balance:.0f}₽</b>\n\n"
        f"🔑 <b>Ключ:</b>\n<code>{sub['vpn_key']}</code>\n\n"
        f"🔗 <b>Subscription link:</b>\n<code>{sub['sub_link']}</code>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ── Инструкция ────────────────────────────────────────────────

@router.message(F.text == "📋 Инструкция")
async def instruction(message: Message):
    await message.answer(
        "📲 <b>Как подключиться к VPN</b>\n\n"
        "<b>1. Скачайте приложение Hiddify</b>\n"
        "• iPhone/iPad: App Store → «Hiddify»\n"
        "• Android: Play Store → «Hiddify»\n"
        "• Windows/Mac: hiddify.com\n\n"
        "<b>2. Добавьте подписку</b>\n"
        "• Откройте Hiddify\n"
        "• Нажмите «+» → «Добавить из буфера обмена»\n"
        "• Вставьте ваш Subscription link\n\n"
        "<b>3. Нажмите «Подключить»</b> ✅\n\n"
        "💡 Subscription link обновляется автоматически — менять его не нужно.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ── Поддержка ─────────────────────────────────────────────────

@router.message(F.text == "💬 Поддержка")
async def support(message: Message):
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Если у вас возникли проблемы — напишите нам:\n"
        "👉 @pl0pa\n\n"
        "Обычно отвечаем в течение 1 часа.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ── Админ-панель ──────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = get_stats()
    await message.answer(
        f"👨‍💼 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"✅ Активных подписок: <b>{stats['active_subs']}</b>\n"
        f"💰 Выручка (₽): <b>{stats['total_rub']:.0f}₽</b>\n"
        f"🤝 Выплачено рефералам: <b>{stats['total_ref_paid']:.0f}₽</b>",
        parse_mode="HTML"
    )


@router.message(Command("broadcast"))
async def broadcast(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Использование: /broadcast Ваш текст")
        return
    users = get_all_users()
    sent, failed = 0, 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


@router.message(Command("confirm"))
async def manual_confirm(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /confirm INVOICE_ID")
        return
    invoice_id = parts[1]
    payment = confirm_payment(invoice_id)
    if not payment:
        await message.answer("❌ Инвойс не найден")
        return

    vpn = await _activate_subscription(message, bot, payment["user_id"], payment["plan"], "manual")
    plan = PLANS[payment["plan"]]
    await bot.send_message(
        payment["user_id"],
        f"✅ <b>Оплата подтверждена! Ваш VPN готов.</b>\n\n"
        f"📅 Действует до: <b>{vpn['expires_at'][:10]}</b>\n\n"
        f"🔑 <b>Ключ:</b>\n<code>{vpn['vpn_key']}</code>\n\n"
        f"🔗 <b>Subscription link:</b>\n<code>{vpn['sub_link']}</code>\n\n"
        "📲 Нажмите «Инструкция» чтобы узнать как подключиться.",
        parse_mode="HTML"
    )
    await message.answer(f"✅ Подписка выдана пользователю {payment['user_id']}")


# ── Доп. админ команды ────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("vpn_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, created_at FROM users ORDER BY created_at DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.answer("Пользователей пока нет.")
        return
    lines = []
    for uid, uname, created in rows:
        uname_str = f"@{uname}" if uname else f"id:{uid}"
        lines.append(f"• {uname_str} — {created[:10]}")
    await message.answer("👥 <b>Последние 10 пользователей:</b>\n\n" + "\n".join(lines), parse_mode="HTML")
    return


@router.message(Command("sub"))
async def cmd_sub(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /sub USER_ID")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный USER_ID")
        return
    sub = get_active_subscription(uid)
    if not sub:
        await message.answer(f"❌ У пользователя {uid} нет активной подписки.")
        return
    plan = PLANS.get(sub["plan"], {})
    await message.answer(
        f"👤 Пользователь: <b>{uid}</b>\n"
        f"📦 Тариф: <b>{plan.get('name', sub['plan'])}</b>\n"
        f"📅 До: <b>{sub['expires_at'][:10]}</b>\n"
        f"🔑 Ключ:\n<code>{sub['vpn_key']}</code>",
        parse_mode="HTML"
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /ban USER_ID")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный USER_ID")
        return
    conn = sqlite3.connect("vpn_bot.db")
    conn.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM subscriptions WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    try:
        await bot.send_message(uid, "❌ Ваш аккаунт заблокирован. Обратитесь в поддержку.")
    except Exception:
        pass
    await message.answer(f"✅ Пользователь {uid} заблокирован и удалён.")


@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /addbalance USER_ID СУММА")
        return
    try:
        uid = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer("❌ Неверные параметры")
        return
    conn = sqlite3.connect("vpn_bot.db")
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()
    try:
        await bot.send_message(uid, f"💰 Вам начислено <b>{amount:.0f}₽</b> на баланс!", parse_mode="HTML")
    except Exception:
        pass
    await message.answer(f"✅ Пользователю {uid} начислено {amount:.0f}₽")


@router.message(Command("notify"))
async def cmd_notify(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    from scheduler import send_expiry_notifications
    await message.answer("⏳ Запускаю проверку истекающих подписок...")
    await send_expiry_notifications(bot)
    await message.answer("✅ Проверка завершена!")


@router.message(Command("givekey"))
async def cmd_givekey(message: Message, bot: Bot):
    """
    Выдать ключ пользователю бесплатно.
    Использование: /givekey USER_ID ПЛАН
    Планы: 1m / 3m / 6m
    Пример: /givekey 6477447974 1m
    """
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "Использование: /givekey USER_ID ПЛАН\n"
            "Планы: 1m / 3m / 6m\n"
            "Пример: /givekey 6477447974 1m"
        )
        return
    try:
        uid = int(parts[1])
        plan_key = parts[2]
    except ValueError:
        await message.answer("❌ Неверные параметры")
        return
    if plan_key not in PLANS:
        await message.answer(f"❌ Неверный тариф. Доступны: {', '.join(PLANS.keys())}")
        return

    plan = PLANS[plan_key]
    vpn = await create_vpn_user(uid, plan["days"])
    save_subscription(
        user_id=uid,
        plan=plan_key,
        days=plan["days"],
        vpn_key=vpn["vpn_key"],
        sub_link=vpn["sub_link"],
        expires_at=vpn["expires_at"],
        paid_rub=0,
    )
    try:
        await bot.send_message(
            uid,
            f"🎁 <b>Вам выдан бесплатный VPN!</b>\n\n"
            f"📦 Тариф: <b>{plan['name']}</b>\n"
            f"📅 Действует до: <b>{vpn['expires_at'][:10]}</b>\n\n"
            f"🔑 <b>Ваш ключ:</b>\n<code>{vpn['vpn_key']}</code>\n\n"
            f"🔗 <b>Subscription link:</b>\n<code>{vpn['sub_link']}</code>\n\n"
            "📲 Нажмите «Инструкция» чтобы узнать как подключиться.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить сообщение пользователю: {e}")
        return
    await message.answer(f"✅ Ключ на {plan['name']} выдан пользователю {uid}")
