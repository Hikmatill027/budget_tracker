import sqlite3
from datetime import datetime, timezone, timedelta
DB_FILE = "Finance_Bot.db"


def init_db():
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()


def utc_to_local(utc_timestamp):
    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    utc_dt = datetime.strptime(utc_timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(local_timezone).strftime("%Y-%m-%d %H:%M:%S")


def add_transaction(user_id, entry_type, amount, description):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions (user_id, type, amount, description)
        VALUES (?, ?, ?, ?)
    """, (user_id, entry_type, amount, description))

    conn.commit()
    conn.close()


def get_summary(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            (SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END)) AS total_income,
            (SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END)) AS total_expense
        FROM transactions
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()
    conn.close()

    total_income = result[0] or 0
    total_expense = result[1] or 0

    return total_income, total_expense


def list_transactions(user_id, page=0, items_per_page=5):
    offset = page * items_per_page
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT type, amount, description, timestamp
        FROM transactions
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        OFFSET ?
    """, (user_id, items_per_page, offset))
    rows = cursor.fetchall()
    conn.close()
    rows = [(t_type, amount, desc, utc_to_local(timestamp)) for t_type, amount, desc, timestamp in rows]
    return rows


def get_transaction_count(user_id):
    conn = sqlite3.connect("Finance_Bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE user_id = ?;
    """, (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def search_transactions(user_id, search_key, is_data_query):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        if is_data_query:
            cursor.execute("""
            SELECT type, amount, description, timestamp
            FROM transactions
            WHERE user_id = ? AND DATE(timestamp) = ?
            ORDER BY timestamp DESC
            """,(user_id, search_key))
        else:
            cursor.execute("""
                SELECT type, amount, description, timestamp
                FROM transactions
                WHERE user_id = ? AND LOWER(description) LIKE ?
                ORDER BY timestamp DESC
            """, (user_id, f"%{search_key}%"))

        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def get_total_balance(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            (SUM(CASE WHEN type='income' THEN amount ELSE 0 END)) AS total_income,
            (SUM(CASE WHEN type='expense' THEN amount ELSE 0 END)) AS total_expense
        FROM transactions
        WHERE user_id = ? AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
    """, (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def list_monthly_summary(user_id, year, month):
    conn = sqlite3.connect("Finance_Bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT type, amount, description, timestamp
        FROM transactions
        WHERE user_id = ? 
            AND strftime('%Y', timestamp) = ?
            AND strftime('%m', timestamp) = ?
        ORDER BY timestamp DESC 
    """, (user_id, str(year), f"{int(month):02}"))
    rows = cursor.fetchall()
    conn.close()
    rows = [(t_type, amount, desc, utc_to_local(timestamp)) for t_type, amount, desc, timestamp in rows]
    return rows
