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
# ║ SOLAREDGE DATA                                             ║
# ╚════════════════════════════════════════════════════════════╝

NEXUS_START_DATE = "2026-04-04"
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
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0)


# ──────────────────────────────
# TIEMPO REAL
# ──────────────────────────────

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

    excess_kw = max(production_kw - consumption_kw, 0)

    return {
        "productionPowerW": round(production_kw * 1000, 2),
        "consumptionPowerW": round(consumption_kw * 1000, 2),
        "excessPowerW": round(excess_kw * 1000, 2),
        "balancePowerW": round((production_kw - consumption_kw) * 1000, 2),
        "gridPowerW": round(grid_kw * 1000, 2),
        "storagePowerW": round(storage_kw * 1000, 2),
        "raw": flow,
    }


# ──────────────────────────────
# CUARTOS HOY (RAW)
# ──────────────────────────────

def build_solaredge_power_quarters_today_payload():
    now = get_local_now()
    end_time = floor_to_quarter(now)
    today = end_time.date().isoformat()

    data = fetch_solaredge(
        "powerDetails",
        {
            "timeUnit": "QUARTER_OF_AN_HOUR",
            "startTime": f"{today} 00:00:00",
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "meters": "Production,Consumption,SelfConsumption,FeedIn,Purchased",
        },
    )

    if data.get("error"):
        return data

    meters = data.get("powerDetails", {}).get("meters", [])
    quarters = {}

    for meter in meters:
        meter_type = meter.get("type")

        for item in meter.get("values", []):
            date = item.get("date")
            value = item.get("value")

            if not date:
                continue

            if date not in quarters:
                quarters[date] = {
                    "date": date,
                    "productionWh": 0,
                    "consumptionWh": 0,
                    "selfConsumptionWh": 0,
                    "feedInWh": 0,
                    "purchasedWh": 0,
                }

            if value is None:
                continue

            value = float(value)

            if meter_type == "Production":
                quarters[date]["productionWh"] = value
            elif meter_type == "Consumption":
                quarters[date]["consumptionWh"] = value
            elif meter_type == "SelfConsumption":
                quarters[date]["selfConsumptionWh"] = value
            elif meter_type == "FeedIn":
                quarters[date]["feedInWh"] = value
            elif meter_type == "Purchased":
                quarters[date]["purchasedWh"] = value

    return {
        "date": today,
        "from": f"{today} 00:00:00",
        "to": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "quarters": list(quarters.values()),
    }


# ──────────────────────────────
# ACUMULADO DÍA
# ──────────────────────────────

def build_solaredge_quarters_today_payload():
    power_data = build_solaredge_power_quarters_today_payload()

    if power_data.get("error"):
        return power_data

    quarters = power_data.get("quarters", [])

    result = {
        "production": 0,
        "consumption": 0,
        "self": 0,
        "feed": 0,
        "purchased": 0,
    }

    for q in quarters:
        result["production"] += q["productionWh"] / 1000
        result["consumption"] += q["consumptionWh"] / 1000
        result["self"] += q["selfConsumptionWh"] / 1000
        result["feed"] += q["feedInWh"] / 1000
        result["purchased"] += q["purchasedWh"] / 1000

    return {
        "date": power_data["date"],
        "from": power_data["from"],
        "to": power_data["to"],
        "productionKwhUntilNow": round(result["production"], 3),
        "consumptionKwhUntilNow": round(result["consumption"], 3),
        "selfConsumptionKwhUntilNow": round(result["self"], 3),
        "feedInKwhUntilNow": round(result["feed"], 3),
        "purchasedKwhUntilNow": round(result["purchased"], 3),
        "intervalsCount": len(quarters),
    }


# ──────────────────────────────
# ACUMULADO DESDE CONTRATO (FIABLE)
# ──────────────────────────────

def build_solaredge_month_payload():
    now = get_local_now()
    end_date = now.date()
    start_date = datetime.strptime(NEXUS_START_DATE, "%Y-%m-%d").date()

    result = {
        "production": 0,
        "consumption": 0,
        "self": 0,
        "feed": 0,
        "purchased": 0,
    }

    current = start_date

    while current <= end_date:
        day_str = current.isoformat()

        data = fetch_solaredge(
            "powerDetails",
            {
                "timeUnit": "QUARTER_OF_AN_HOUR",
                "startTime": f"{day_str} 00:00:00",
                "endTime": f"{day_str} 23:59:59",
                "meters": "Production,Consumption,SelfConsumption,FeedIn,Purchased",
            },
        )

        if data.get("error"):
            current += timedelta(days=1)
            continue

        meters = data.get("powerDetails", {}).get("meters", [])

        for meter in meters:
            mtype = meter.get("type")

            for item in meter.get("values", []):
                value = item.get("value")
                if value is None:
                    continue

                kwh = float(value) / 1000

                if mtype == "Production":
                    result["production"] += kwh
                elif mtype == "Consumption":
                    result["consumption"] += kwh
                elif mtype == "SelfConsumption":
                    result["self"] += kwh
                elif mtype == "FeedIn":
                    result["feed"] += kwh
                elif mtype == "Purchased":
                    result["purchased"] += kwh

        current += timedelta(days=1)

    return {
        "from": f"{NEXUS_START_DATE} 00:00:00",
        "to": now.strftime("%Y-%m-%d %H:%M:%S"),
        "label": "Desde inicio contrato",
        "productionKwh": round(result["production"], 3),
        "consumptionKwh": round(result["consumption"], 3),
        "selfConsumptionKwh": round(result["self"], 3),
        "feedInKwh": round(result["feed"], 3),
        "purchasedKwh": round(result["purchased"], 3),
    }


# ──────────────────────────────
# METERS RAW
# ──────────────────────────────

def build_solaredge_meters_payload():
    now = get_local_now()
    today = now.date().isoformat()

    return fetch_solaredge(
        "meters",
        {
            "timeUnit": "QUARTER_OF_AN_HOUR",
            "startTime": f"{today} 00:00:00",
            "endTime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "meters": "Production,Consumption,FeedIn,Purchased",
        },
    )
# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE ENDPOINTS                                             ║
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
# ║ SOLAREDGE ENDPOINTS                                        ║
# ╚════════════════════════════════════════════════════════════╝

@app.get("/solar-edge/current")
def get_solaredge_current():
    return build_solaredge_current_payload()


@app.get("/solar-edge/quarters-today")
def get_solaredge_quarters_today():
    return build_solaredge_quarters_today_payload()


@app.get("/solar-edge/month")
def get_solaredge_month():
    return build_solaredge_month_payload()


@app.get("/solar-edge/power-quarters-today")
def get_solaredge_power_quarters_today():
    return build_solaredge_power_quarters_today_payload()


@app.get("/solar-edge/meters")
def get_solar_edge_meters():
    return build_solaredge_meters_payload()


# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE IMPORT ENDPOINTS                                      ║
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