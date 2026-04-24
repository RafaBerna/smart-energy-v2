from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import requests
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


# ╔════════════════════════════════════════════════════════════╗
# ║ DATABASE                                                  ║
# ╚════════════════════════════════════════════════════════════╝

def init_db():
    conn = sqlite3.connect("database/omie.db")
    cursor = conn.cursor()

    with open("database/schema.sql", "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()


init_db()

def get_db_connection():
    conn = sqlite3.connect("database/omie.db")
    conn.row_factory = sqlite3.Row
    return conn


# ╔════════════════════════════════════════════════════════════╗
# ║ DATES                                                     ║
# ╚════════════════════════════════════════════════════════════╝

def get_today_date():
    return datetime.now().date().isoformat()


def get_tomorrow_date():
    return (datetime.now().date() + timedelta(days=1)).isoformat()


# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE DATA                                                 ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# DAY HELPERS
# ──────────────────────────────

def get_latest_day_row():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date, avg_price, min_price, max_price
        FROM price_days
        ORDER BY date DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()
    return row


def build_day_payload(day):
    if day is None:
        return {"error": "No data"}

    return {
        "date": day["date"],
        "avg_price": round(day["avg_price"] / 1000, 5),
        "min_price": round(day["min_price"] / 1000, 5),
        "max_price": round(day["max_price"] / 1000, 5),
    }


# ──────────────────────────────
# HOURS HELPERS
# ──────────────────────────────

def build_latest_hours_payload():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ph.hour, ph.price, pd.date
        FROM price_hours ph
        JOIN price_days pd ON ph.price_day_id = pd.id
        ORDER BY pd.date DESC, ph.hour ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"error": "No hourly data"}

    latest_date = rows[0]["date"]

    hours = [
        {
            "hour": row["hour"],
            "price": round(row["price"] / 1000, 5),
        }
        for row in rows
        if row["date"] == latest_date
    ]

    if not hours:
        return {"error": "No hourly data"}

    best = min(hours, key=lambda x: x["price"])
    worst = max(hours, key=lambda x: x["price"])

    return {
        "date": latest_date,
        "hours": hours,
        "best_hour": best,
        "worst_hour": worst,
    }


def build_hours_payload_by_date(target_date: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ph.hour, ph.price, pd.date
        FROM price_hours ph
        JOIN price_days pd ON ph.price_day_id = pd.id
        WHERE pd.date = ?
        ORDER BY ph.hour ASC
    """, (target_date,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "date": target_date,
            "hours": [],
            "best_hour": None,
            "worst_hour": None,
        }

    hours = [
        {
            "hour": row["hour"],
            "price": round(row["price"] / 1000, 5),
        }
        for row in rows
    ]

    best = min(hours, key=lambda x: x["price"])
    worst = max(hours, key=lambda x: x["price"])

    return {
        "date": target_date,
        "hours": hours,
        "best_hour": best,
        "worst_hour": worst,
    }


# ──────────────────────────────
# PERIODS HELPERS
# ──────────────────────────────

def build_latest_periods_payload():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date
        FROM price_days
        ORDER BY date DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {"date": None, "periods": []}

    price_day_id = row["id"]
    date = row["date"]

    cursor.execute("""
        SELECT period, price
        FROM price_periods
        WHERE price_day_id = ?
        ORDER BY period ASC
    """, (price_day_id,))

    periods = cursor.fetchall()
    conn.close()

    return {
        "date": date,
        "periods": [
            {
                "period": p["period"],
                "price": round(p["price"] / 1000, 5),
            }
            for p in periods
        ],
    }


def build_periods_payload_by_date(target_date: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pp.period, pp.price, pd.date
        FROM price_periods pp
        JOIN price_days pd ON pp.price_day_id = pd.id
        WHERE pd.date = ?
        ORDER BY pp.period ASC
    """, (target_date,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "date": target_date,
            "periods": [],
        }

    return {
        "date": target_date,
        "periods": [
            {
                "period": row["period"],
                "price": round(row["price"] / 1000, 5),
            }
            for row in rows
        ],
    }


# ──────────────────────────────
# HISTORY HELPERS
# ──────────────────────────────

def build_price_days_history_payload(limit: int = 30):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, avg_price, min_price, max_price
        FROM price_days
        ORDER BY date DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return {
        "days": [
            {
                "date": row["date"],
                "avg_price": round(row["avg_price"] / 1000, 5),
                "min_price": round(row["min_price"] / 1000, 5),
                "max_price": round(row["max_price"] / 1000, 5),
            }
            for row in rows
        ]
    }


# ──────────────────────────────
# OMIE ENDPOINTS
# ──────────────────────────────

@app.get("/price-day/latest")
def get_latest_price_day():
    return build_day_payload(get_latest_day_row())


@app.get("/price-hours/latest")
def get_latest_price_hours():
    return build_latest_hours_payload()


@app.get("/price-periods/latest")
def get_latest_periods():
    return build_latest_periods_payload()


@app.get("/price-hours/by-date")
def get_price_hours_by_date(date: str):
    return build_hours_payload_by_date(date)


@app.get("/price-periods/by-date")
def get_price_periods_by_date(date: str):
    return build_periods_payload_by_date(date)


@app.get("/price-days/history")
def get_price_days_history(limit: int = 30):
    return build_price_days_history_payload(limit)


# ╔════════════════════════════════════════════════════════════╗
# ║ WEATHER                                                   ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# GEOCODING HELPERS
# ──────────────────────────────

def geocode_location(location: str):
    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params={
            "name": location,
            "count": 1,
            "language": "es",
            "format": "json",
        },
        timeout=20,
    )

    if response.status_code != 200:
        return None

    data = response.json()
    results = data.get("results") or []

    if not results:
        return None

    result = results[0]

    return {
        "name": result.get("name"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone"),
    }


# ──────────────────────────────
# FORECAST HELPERS
# ──────────────────────────────

def fetch_weather_for_coordinates(lat, lon, timezone="auto"):
    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
            "current": "cloud_cover,shortwave_radiation",
        },
        timeout=20,
    )

    if response.status_code != 200:
        return None

    return response.json()


def build_weather_payload(location):
    geo = geocode_location(location)

    if not geo:
        return {"error": "Localidad no encontrada"}

    weather = fetch_weather_for_coordinates(
        geo["latitude"],
        geo["longitude"],
        geo["timezone"]
    )

    if not weather:
        return {"error": "Error meteo"}

    current = weather.get("current", {})

    return {
        "location": geo,
        "current": current
    }


# ──────────────────────────────
# WEATHER ENDPOINTS
# ──────────────────────────────

@app.get("/weather/by-location")
def get_weather_by_location(location: str):
    return build_weather_payload(location)

@app.get("/import-omie")
def import_omie():
    from scripts.fetch_omie import fetch_and_store

    fetch_and_store(0)  # hoy
    return {"status": "ok"}