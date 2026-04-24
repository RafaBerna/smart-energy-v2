import sqlite3
from datetime import datetime, timedelta


def get_dates():
    today = datetime.now() - timedelta(days=1)
    yesterday = today - timedelta(days=1)

    return today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")


def compare_days():
    conn = sqlite3.connect("../database/omie.db")
    cursor = conn.cursor()

    today, yesterday = get_dates()

    print(f"Comparing {today} vs {yesterday}")

    cursor.execute("""
        SELECT avg_price, min_price, max_price
        FROM price_days
        WHERE date = ?
    """, (today,))
    today_data = cursor.fetchone()

    cursor.execute("""
        SELECT avg_price, min_price, max_price
        FROM price_days
        WHERE date = ?
    """, (yesterday,))
    yesterday_data = cursor.fetchone()

    if not today_data or not yesterday_data:
        print("Missing data for comparison")
        conn.close()
        return

    avg_diff = today_data[0] - yesterday_data[0]
    min_diff = today_data[1] - yesterday_data[1]
    max_diff = today_data[2] - yesterday_data[2]

    print("")
    print("RESULT")
    print(f"Avg diff: {avg_diff:.2f}")
    print(f"Min diff: {min_diff:.2f}")
    print(f"Max diff: {max_diff:.2f}")

    conn.close()


if __name__ == "__main__":
    compare_days()