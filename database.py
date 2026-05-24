import sqlite3
from datetime import datetime

DB_PATH = "vpn_bot.db"

def init_db():
    """Создаёт таблицы при первом запуске."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            referred_by  INTEGER DEFAULT NULL,
            balance      REAL DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            plan        TEXT,
            days        INTEGER,
            vpn_key     TEXT,
            sub_link    TEXT,
            expires_at  TEXT,
            paid_rub    REAL,
            paid_usd    REAL,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            invoice_id  TEXT UNIQUE,
            plan        TEXT,
            method      TEXT,
            amount      REAL,
            currency    TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS referral_earnings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id  INTEGER,
            referred_id  INTEGER,
            amount_rub   REAL DEFAULT 0,
            plan         TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, referred_by: int = None):
    conn = sqlite3.connect(DB_PATH)
    if referred_by:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
            (user_id, username or "", referred_by)
        )
    else:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username or "")
        )
    conn.commit()
    conn.close()

def get_user(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, referred_by, balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1], "referred_by": row[2], "balance": row[3]}
    return None

def get_referral_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_referral_earnings(user_id: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(amount_rub),0) FROM referral_earnings WHERE referrer_id=?", (user_id,))
    total = c.fetchone()[0]
    conn.close()
    return total

def add_referral_bonus(referrer_id: int, referred_id: int, amount_rub: float, plan: str):
    """Начисляет 30% реферального бонуса на баланс."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO referral_earnings (referrer_id, referred_id, amount_rub, plan) VALUES (?,?,?,?)",
        (referrer_id, referred_id, amount_rub, plan)
    )
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount_rub, referrer_id)
    )
    conn.commit()
    conn.close()

def get_balance(user_id: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def deduct_balance(user_id: int, amount: float) -> bool:
    """Списывает баланс. Возвращает True если хватило средств."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return False
    conn.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return True

def save_payment(user_id: int, invoice_id: str, plan: str, method: str, amount: float, currency: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO payments (user_id, invoice_id, plan, method, amount, currency) VALUES (?,?,?,?,?,?)",
        (user_id, invoice_id, plan, method, amount, currency)
    )
    conn.commit()
    conn.close()

def confirm_payment(invoice_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE payments SET status='paid' WHERE invoice_id=?", (invoice_id,))
    conn.commit()
    c.execute("SELECT user_id, plan FROM payments WHERE invoice_id=?", (invoice_id,))
    row = c.fetchone()
    conn.close()
    return {"user_id": row[0], "plan": row[1]} if row else None

def save_subscription(user_id: int, plan: str, days: int, vpn_key: str, sub_link: str, expires_at: str, paid_rub: float = 0, paid_usd: float = 0):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO subscriptions (user_id,plan,days,vpn_key,sub_link,expires_at,paid_rub,paid_usd) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, plan, days, vpn_key, sub_link, expires_at, paid_rub, paid_usd)
    )
    conn.commit()
    conn.close()

def get_active_subscription(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT plan, expires_at, vpn_key, sub_link
        FROM subscriptions
        WHERE user_id=? AND expires_at > datetime('now')
        ORDER BY expires_at DESC LIMIT 1
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"plan": row[0], "expires_at": row[1], "vpn_key": row[2], "sub_link": row[3]}
    return None

def get_all_users() -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE expires_at > datetime('now')")
    active_subs = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(paid_rub),0) FROM subscriptions")
    total_rub = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount_rub),0) FROM referral_earnings")
    total_ref = c.fetchone()[0]
    conn.close()
    return {"total_users": total_users, "active_subs": active_subs, "total_rub": total_rub, "total_ref_paid": total_ref}
