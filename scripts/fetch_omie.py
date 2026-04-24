import sys
import requests
import sqlite3
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin


OMIE_BASE_URL = "https://www.omie.es"
OMIE_LIST_URL = (
    "https://www.omie.es/es/file-access-list?"
    "parents=Mercado%20Diario/1.%20Precios&dir=Precios%20horarios%20del%20mercado%20diario%20en%20Espa%C3%B1a"
    "&realdir=marginalpdbc"
)
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_date_from_offset(days_offset=0):
    target = datetime.now() - timedelta(days=days_offset)
    return target.strftime("%Y-%m-%d"), target.strftime("%Y%m%d")


def get_date_range(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")

    current = start
    dates = []

    while current <= end:
        dates.append((current.strftime("%Y-%m-%d"), current.strftime("%Y%m%d")))
        current += timedelta(days=1)

    return dates


def build_filename(date_compact, version=1):
    return f"marginalpdbc_{date_compact}.{version}"


def fetch_list_page():
    response = requests.get(OMIE_LIST_URL, headers=HEADERS, timeout=20)
    if response.status_code != 200:
        print("Error listado OMIE:", response.status_code)
        return None
    return response.text


def find_download_url(filename, html):
    soup = BeautifulSoup(html, "html.parser")

    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        href = link["href"]

        if filename in text or filename in href:
            return urljoin(OMIE_BASE_URL, href)

    return None


def find_download_url_for_date(date_compact, html):
    for version in range(1, 6):
        filename = build_filename(date_compact, version)
        download_url = find_download_url(filename, html)

        if download_url:
            print(f"Encontrado: {filename}")
            return download_url

    return None


def fetch_omie_file(download_url):
    print(f"Descargando: {download_url}")

    response = requests.get(download_url, headers=HEADERS, timeout=20)
    if response.status_code != 200:
        print("Error descarga:", response.status_code)
        return None

    return response.text


def parse_omie_periods(text):
    lines = text.splitlines()
    period_prices = []

    for line in lines:
        if line.startswith("MARGINALPDBC") or not line.strip():
            continue

        parts = line.split(";")

        if len(parts) < 6:
            continue

        try:
            period = int(parts[3])
            price = float(parts[4])
        except ValueError:
            continue

        if 1 <= period <= 96:
            period_prices.append((period, price))

    period_prices.sort(key=lambda x: x[0])
    return period_prices


def build_hour_rows(period_prices):
    only_prices = [price for _, price in period_prices]

    if len(only_prices) == 96:
        hour_rows = []
        for i in range(0, 96, 4):
            block = only_prices[i:i + 4]
            hour = (i // 4) + 1
            avg_price = sum(block) / 4
            hour_rows.append((hour, avg_price))
        return hour_rows

    if len(only_prices) == 24:
        return [(i + 1, price) for i, price in enumerate(only_prices)]

    raise ValueError(f"Unexpected number of periods: {len(only_prices)}")


def save_to_db(date_iso, period_prices, hour_rows):
    conn = sqlite3.connect("database/omie.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            avg_price REAL,
            min_price REAL,
            max_price REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price_day_id INTEGER,
            hour INTEGER,
            price REAL,
            UNIQUE(price_day_id, hour)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price_day_id INTEGER,
            period INTEGER,
            price REAL,
            UNIQUE(price_day_id, period)
        )
    """)

    cursor.execute("SELECT id FROM price_days WHERE date = ?", (date_iso,))
    existing = cursor.fetchone()

    if existing:
        print(f"Ya existe {date_iso}, se sobrescribe")
        day_id = existing[0]
        cursor.execute("DELETE FROM price_hours WHERE price_day_id = ?", (day_id,))
        cursor.execute("DELETE FROM price_periods WHERE price_day_id = ?", (day_id,))
        cursor.execute("DELETE FROM price_days WHERE id = ?", (day_id,))

    prices = [p for _, p in hour_rows]
    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)

    cursor.execute("""
        INSERT INTO price_days (date, avg_price, min_price, max_price)
        VALUES (?, ?, ?, ?)
    """, (date_iso, avg_price, min_price, max_price))

    cursor.execute("SELECT id FROM price_days WHERE date = ?", (date_iso,))
    price_day_id = cursor.fetchone()[0]

    for period, price in period_prices:
        cursor.execute("""
            INSERT INTO price_periods (price_day_id, period, price)
            VALUES (?, ?, ?)
        """, (price_day_id, period, price))

    for hour, price in hour_rows:
        cursor.execute("""
            INSERT INTO price_hours (price_day_id, hour, price)
            VALUES (?, ?, ?)
        """, (price_day_id, hour, price))

    conn.commit()
    conn.close()

    print(f"✔ Guardado {date_iso}")


def process_date(date_iso, date_compact, html):
    print(f"\n--- Procesando {date_iso} ---")

    download_url = find_download_url_for_date(date_compact, html)

    if not download_url:
        print(f"No encontrado: {date_iso}")
        return False

    data = fetch_omie_file(download_url)
    if not data:
        return False

    period_prices = parse_omie_periods(data)
    hour_rows = build_hour_rows(period_prices)

    if len(hour_rows) != 24:
        print("Error generando horas")
        return False

    save_to_db(date_iso, period_prices, hour_rows)
    return True


def process_latest_available(html):
    # Primero intenta hoy
    today_iso, today_compact = get_date_from_offset(0)
    if process_date(today_iso, today_compact, html):
        return

    print("\nNo hay datos de hoy. Se intenta con ayer...")

    # Si hoy no existe, prueba ayer
    yesterday_iso, yesterday_compact = get_date_from_offset(1)
    if process_date(yesterday_iso, yesterday_compact, html):
        return

    print("\nNo se encontraron datos ni para hoy ni para ayer.")


if __name__ == "__main__":

    if len(sys.argv) == 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]

        print(f"Cargando histórico: {start_date} → {end_date}")

        html = fetch_list_page()
        if not html:
            sys.exit(1)

        dates = get_date_range(start_date, end_date)

        for date_iso, date_compact in dates:
            process_date(date_iso, date_compact, html)

        sys.exit(0)

    html = fetch_list_page()
    if not html:
        sys.exit(1)

    if len(sys.argv) == 2:
        days_offset = int(sys.argv[1])
        date_iso, date_compact = get_date_from_offset(days_offset)
        process_date(date_iso, date_compact, html)
        sys.exit(0)

    # Sin argumentos: intenta el último disponible
    process_latest_available(html)