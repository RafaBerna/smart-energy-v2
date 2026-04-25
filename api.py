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
# ║ DATABASE                                                                     ║
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
# ║ DATES                                                                        ║
# ╚════════════════════════════════════════════════════════════╝

def get_today_date():
    return datetime.now().date().isoformat()


def get_tomorrow_date():
    return (datetime.now().date() + timedelta(days=1)).isoformat()


# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE DATA                                                                    ║
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

# ╔════════════════════════════════════════════════════════════╗
# ║ SOLAREDGE DATA                                                         ║
# ╚════════════════════════════════════════════════════════════╝

def fetch_solaredge(path: str, params: dict | None = None):
    if params is None:
        params = {}

    if not SOLAREDGE_API_KEY or not SOLAREDGE_SITE_ID:
        return {
            "error": "Faltan SOLAREDGE_API_KEY o SOLAREDGE_SITE_ID"
        }

    url = f"https://monitoringapi.solaredge.com/site/{SOLAREDGE_SITE_ID}/{path}"

    request_params = {
        **params,
        "api_key": SOLAREDGE_API_KEY,
    }

    response = requests.get(url, params=request_params, timeout=20)

    if response.status_code != 200:
        return {
            "error": "Error al consultar SolarEdge",
            "status_code": response.status_code,
            "detail": response.text,
        }

    return response.json()


def build_solaredge_current_payload():
    data = fetch_solaredge("currentPowerFlow")

    if data.get("error"):
        return data

    flow = data.get("siteCurrentPowerFlow", {})

    pv = flow.get("PV", {})
    load = flow.get("LOAD", {})
    grid = flow.get("GRID", {})
    storage = flow.get("STORAGE", {})

    production_kw = float(pv.get("currentPower", 0) or 0)
    consumption_kw = float(load.get("currentPower", 0) or 0)
    grid_kw = float(grid.get("currentPower", 0) or 0)
    storage_kw = float(storage.get("currentPower", 0) or 0)

    return {
        "productionPowerW": round(production_kw * 1000, 2),
        "consumptionPowerW": round(consumption_kw * 1000, 2),
        "balancePowerW": round((production_kw - consumption_kw) * 1000, 2),
        "gridPowerW": round(grid_kw * 1000, 2),
        "storagePowerW": round(storage_kw * 1000, 2),
        "raw": flow,
    }


def build_solaredge_today_payload():
    today = get_today_date()

    data = fetch_solaredge(
        "energyDetails",
        {
            "timeUnit": "DAY",
            "startTime": f"{today} 00:00:00",
            "endTime": f"{today} 23:59:59",
            "meters": "Production,Consumption,SelfConsumption,FeedIn,Purchased",
        },
    )

    if data.get("error"):
        return data

    meters = data.get("energyDetails", {}).get("meters", [])

    result = {
        "date": today,
        "productionKwh": 0,
        "consumptionKwh": 0,
        "selfConsumptionKwh": 0,
        "feedInKwh": 0,
        "purchasedKwh": 0,
    }

    mapping = {
        "Production": "productionKwh",
        "Consumption": "consumptionKwh",
        "SelfConsumption": "selfConsumptionKwh",
        "FeedIn": "feedInKwh",
        "Purchased": "purchasedKwh",
    }

    for meter in meters:
        meter_type = meter.get("type")
        key = mapping.get(meter_type)

        if not key:
            continue

        values = meter.get("values", [])

        total_wh = sum(
            float(item.get("value") or 0)
            for item in values
            if item.get("value") is not None
        )

        result[key] = round(total_wh / 1000, 3)

    return result


def floor_to_quarter(dt: datetime):
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0)


def build_solaredge_quarters_today_payload():
    now = datetime.now()
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

    result = {
        "date": today,
        "from": f"{today} 00:00:00",
        "to": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "productionKwhUntilNow": 0,
        "consumptionKwhUntilNow": 0,
        "selfConsumptionKwhUntilNow": 0,
        "feedInKwhUntilNow": 0,
        "purchasedKwhUntilNow": 0,
        "intervalsCount": 0,
    }

    mapping = {
        "Production": "productionKwhUntilNow",
        "Consumption": "consumptionKwhUntilNow",
        "SelfConsumption": "selfConsumptionKwhUntilNow",
        "FeedIn": "feedInKwhUntilNow",
        "Purchased": "purchasedKwhUntilNow",
    }

    max_intervals = 0

    for meter in meters:
        meter_type = meter.get("type")
        key = mapping.get(meter_type)

        if not key:
            continue

        values = meter.get("values", [])
        max_intervals = max(max_intervals, len(values))

        total_wh = sum(
            float(item.get("value") or 0)
            for item in values
            if item.get("value") is not None
        )

        result[key] = round(total_wh / 1000, 3)

    result["intervalsCount"] = max_intervals

    return result

# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE ENDPOINTS                                                         ║
# ╚════════════════════════════════════════════════════════════╝

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
# ║ SOLAREDGE ENDPOINTS                                                    ║
# ╚════════════════════════════════════════════════════════════╝

@app.get("/solar-edge/current")
def get_solaredge_current():
    return build_solaredge_current_payload()


@app.get("/solar-edge/today")
def get_solaredge_today():
    return build_solaredge_today_payload()

@app.get("/solar-edge/quarters-today")
def get_solaredge_quarters_today():
    return build_solaredge_quarters_today_payload()

# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE IMPORT ENDPOINTS                                                  ║
# ╚════════════════════════════════════════════════════════════╝

@app.get("/import-omie")
def import_omie():
    from scripts.fetch_omie import fetch_list_page, process_latest_available

    html = fetch_list_page()

    if not html:
        return {"status": "error", "message": "No se pudo cargar listado OMIE"}

    process_latest_available(html)

    return {"status": "ok"}


@app.get("/import-omie-range")
def import_omie_range(start: str, end: str):
    from scripts.fetch_omie import fetch_list_page, process_date

    html = fetch_list_page()

    if not html:
        return {"status": "error", "message": "No se pudo cargar listado OMIE"}

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return {
            "status": "error",
            "message": "Formato de fecha inválido. Usa YYYY-MM-DD",
        }

    current = start_date
    imported = 0
    failed = []

    while current <= end_date:
        date_iso = current.strftime("%Y-%m-%d")
        date_compact = current.strftime("%Y%m%d")

        ok = process_date(date_iso, date_compact, html)

        if ok:
            imported += 1
        else:
            failed.append(date_iso)

        current += timedelta(days=1)

    return {
        "status": "ok",
        "imported": imported,
        "failed": failed,
    }