from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import requests
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOLAREDGE_API_KEY = os.getenv("SOLAREDGE_API_KEY")
SOLAREDGE_SITE_ID = os.getenv("SOLAREDGE_SITE_ID")


# ╔════════════════════════════════════════════════════════════╗
# ║ DATABASE                                                   ║
# ╚════════════════════════════════════════════════════════════╝

def init_db():
    conn = sqlite3.connect("/data/omie.db")
    cursor = conn.cursor()

    with open("database/schema.sql", "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()


init_db()


def get_db_connection():
    conn = sqlite3.connect("/data/omie.db")
    conn.row_factory = sqlite3.Row
    return conn


# ╔════════════════════════════════════════════════════════════╗
# ║ DATES                                                      ║
# ╚════════════════════════════════════════════════════════════╝

def get_today_date():
    return datetime.now().date().isoformat()


def get_tomorrow_date():
    return (datetime.now().date() + timedelta(days=1)).isoformat()


# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE DATA                                                  ║
# ╚════════════════════════════════════════════════════════════╝

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

    best = min(hours, key=lambda x: x["price"])
    worst = max(hours, key=lambda x: x["price"])

    return {
        "date": latest_date,
        "hours": hours,
        "best_hour": best,
        "worst_hour": worst,
    }


# ╔════════════════════════════════════════════════════════════╗
# ║ SOLAREDGE DATA                                             ║
# ╚════════════════════════════════════════════════════════════╝

LOCAL_TZ = ZoneInfo("Europe/Madrid")


def get_local_now():
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def fetch_solaredge(path: str, params: dict | None = None):
    if params is None:
        params = {}

    if not SOLAREDGE_API_KEY or not SOLAREDGE_SITE_ID:
        return {"error": "Faltan SOLAREDGE_API_KEY o SOLAREDGE_SITE_ID"}

    url = f"https://monitoringapi.solaredge.com/site/{SOLAREDGE_SITE_ID}/{path}"

    response = requests.get(
        url,
        params={**params, "api_key": SOLAREDGE_API_KEY},
        timeout=20,
    )

    if response.status_code != 200:
        return {
            "error": "Error al consultar SolarEdge",
            "status_code": response.status_code,
            "detail": response.text,
        }

    return response.json()


def floor_to_quarter(dt: datetime):
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


# 🔥 ACUMULADO DÍA REAL (FIABLE)

def build_solaredge_quarters_today_payload():
    now = get_local_now()
    end_time = floor_to_quarter(now)
    today = end_time.date().isoformat()

    data = fetch_solaredge(
        "energyDetails",
        {
            "timeUnit": "QUARTER_OF_AN_HOUR",
            "startTime": f"{today} 00:00:00",
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "meters": "Production,Consumption,SelfConsumption,FeedIn,Purchased",
        },
    )

    if data.get("error"):
        return data

    meters = data.get("energyDetails", {}).get("meters", [])

    production = 0
    consumption = 0
    self_c = 0
    feed = 0
    purchased = 0

    for meter in meters:
        m_type = meter.get("type")

        total = sum(
            float(v.get("value") or 0)
            for v in meter.get("values", [])
            if v.get("value") is not None
        )

        if m_type == "Production":
            production = total
        elif m_type == "Consumption":
            consumption = total
        elif m_type == "SelfConsumption":
            self_c = total
        elif m_type == "FeedIn":
            feed = total
        elif m_type == "Purchased":
            purchased = total

    return {
        "date": today,
        "from": f"{today} 00:00:00",
        "to": end_time.strftime("%Y-%m-%d %H:%M:%S"),

        "productionKwhUntilNow": round(production / 1000, 3),
        "consumptionKwhUntilNow": round(consumption / 1000, 3),
        "selfConsumptionKwhUntilNow": round(self_c / 1000, 3),
        "feedInKwhUntilNow": round(feed / 1000, 3),

        # 🔥 CONSUMO REAL DE RED
        "purchasedKwhUntilNow": round(purchased / 1000, 3),
    }
# ╔════════════════════════════════════════════════════════════╗
# ║ ENDPOINTS                                                  ║
# ╚════════════════════════════════════════════════════════════╝

@app.get("/solar-edge/quarters-today")
def get_solaredge():
    return build_solaredge_quarters_today_payload()