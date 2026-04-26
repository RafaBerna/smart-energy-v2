from statistics import median
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import requests
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ╔════════════════════════════════════════════════════════════╗
# ║ APP CONFIGURATION                                                      ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# FASTAPI APP
# ──────────────────────────────

app = FastAPI()


# ──────────────────────────────
# CORS
# ──────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────
# ENVIRONMENT VARIABLES
# ──────────────────────────────

SOLAREDGE_API_KEY = os.getenv("SOLAREDGE_API_KEY")
SOLAREDGE_SITE_ID = os.getenv("SOLAREDGE_SITE_ID")


# ╔════════════════════════════════════════════════════════════╗
# ║ GENERAL CONFIGURATION                                                  ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# TIMEZONE
# ──────────────────────────────

LOCAL_TZ = ZoneInfo("Europe/Madrid")


# ──────────────────────────────
# CONTRACT DATES
# ──────────────────────────────

NEXUS_START_DATE = "2026-04-04"


# ╔════════════════════════════════════════════════════════════╗
# ║ DATABASE                                                               ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# CONFIG
# ──────────────────────────────

DB_PATH = os.getenv(
    "DATABASE_PATH",
    "/data/omie.db" if os.path.exists("/data") else "database/omie.db"
)


# ──────────────────────────────
# INITIALIZATION
# ──────────────────────────────

def init_db():
    db_dir = os.path.dirname(DB_PATH)

    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open("database/schema.sql", "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()


init_db()


# ──────────────────────────────
# CONNECTION
# ──────────────────────────────

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE DATA                                                              ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# LATEST DAY ROW
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


# ──────────────────────────────
# DAY PAYLOAD
# ──────────────────────────────

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
# LATEST HOURS PAYLOAD
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


# ──────────────────────────────
# HOURS BY DATE PAYLOAD
# ──────────────────────────────

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
# LATEST PERIODS PAYLOAD
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


# ──────────────────────────────
# PERIODS BY DATE PAYLOAD
# ──────────────────────────────

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
# PRICE DAYS HISTORY PAYLOAD
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


# ╔════════════════════════════════════════════════════════════╗
# ║ SOLAREDGE DATA                                                         ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# TIME HELPERS
# ──────────────────────────────

def get_local_now():
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def floor_to_quarter(dt: datetime):
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0)


# ──────────────────────────────
# SOLAREDGE CLIENT
# ──────────────────────────────

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


# ──────────────────────────────
# CURRENT POWER FLOW
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
# POWER QUARTERS TODAY RAW
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
# DAY ACCUMULATED FROM QUARTERS
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
# CONTRACT ACCUMULATED
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

# ──────────────────────────────
# SOLAREDGE STORAGE
# ──────────────────────────────

def get_solar_period_from_measurement_time(measurement_time: str):
    dt = datetime.strptime(measurement_time, "%Y-%m-%d %H:%M:%S")
    return (dt.hour * 4) + (dt.minute // 15) + 1


def build_solaredge_power_quarters_by_date_payload(target_date: str):
    data = fetch_solaredge(
        "powerDetails",
        {
            "timeUnit": "QUARTER_OF_AN_HOUR",
            "startTime": f"{target_date} 00:00:00",
            "endTime": f"{target_date} 23:59:59",
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
                    "feedInWh": 0,
                    "purchasedWh": 0,
                }

            if value is None:
                continue

            value = float(value)

            if meter_type == "FeedIn":
                quarters[date]["feedInWh"] = value
            elif meter_type == "Purchased":
                quarters[date]["purchasedWh"] = value

    return {
        "date": target_date,
        "from": f"{target_date} 00:00:00",
        "to": f"{target_date} 23:59:59",
        "quarters": list(quarters.values()),
    }


def save_solaredge_power_day_to_db(power_data, is_complete: int = 0):
    if power_data.get("error"):
        return power_data

    date = power_data.get("date")
    quarters = power_data.get("quarters", [])

    if not date or not quarters:
        return {
            "status": "empty",
            "date": date,
            "message": "No hay datos SolarEdge para guardar",
        }

    quarters = sorted(quarters, key=lambda q: q["date"])

    conn = get_db_connection()
    cursor = conn.cursor()

    grid_consumed_total_raw = 0
    feed_in_total_raw = 0
    last_measurement_at = None

    for quarter in quarters:
        measurement_time = quarter["date"]
        period = get_solar_period_from_measurement_time(measurement_time)

        grid_consumed_raw = float(quarter.get("purchasedWh", 0) or 0)
        feed_in_raw = float(quarter.get("feedInWh", 0) or 0)

        grid_consumed_total_raw += grid_consumed_raw
        feed_in_total_raw += feed_in_raw
        last_measurement_at = measurement_time

        cursor.execute("""
            INSERT INTO solar_quarters (
                date,
                period,
                measurement_time,
                grid_consumed_raw,
                feed_in_raw,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(date, period)
            DO UPDATE SET
                measurement_time = excluded.measurement_time,
                grid_consumed_raw = excluded.grid_consumed_raw,
                feed_in_raw = excluded.feed_in_raw,
                updated_at = CURRENT_TIMESTAMP
        """, (
            date,
            period,
            measurement_time,
            grid_consumed_raw,
            feed_in_raw,
        ))

    grid_consumed_kwh = grid_consumed_total_raw / 1000
    feed_in_kwh = feed_in_total_raw / 1000
    intervals_count = len(quarters)

    cursor.execute("""
        INSERT INTO solar_days (
            date,
            grid_consumed_kwh,
            feed_in_kwh,
            intervals_count,
            last_measurement_at,
            is_complete,
            source,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'solaredge_power', CURRENT_TIMESTAMP)
        ON CONFLICT(date)
        DO UPDATE SET
            grid_consumed_kwh = excluded.grid_consumed_kwh,
            feed_in_kwh = excluded.feed_in_kwh,
            intervals_count = excluded.intervals_count,
            last_measurement_at = excluded.last_measurement_at,
            is_complete = excluded.is_complete,
            source = excluded.source,
            updated_at = CURRENT_TIMESTAMP
    """, (
        date,
        grid_consumed_kwh,
        feed_in_kwh,
        intervals_count,
        last_measurement_at,
        is_complete,
    ))

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "date": date,
        "gridConsumedKwh": round(grid_consumed_kwh, 3),
        "feedInKwh": round(feed_in_kwh, 3),
        "intervalsCount": intervals_count,
        "lastMeasurementAt": last_measurement_at,
        "isComplete": bool(is_complete),
        "source": "solaredge_power",
    }


def build_solaredge_update_today_payload():
    power_data = build_solaredge_power_quarters_today_payload()
    return save_solaredge_power_day_to_db(power_data, is_complete=0)


def build_solaredge_update_date_payload(target_date: str):
    today = get_local_now().date().isoformat()
    is_complete = 0 if target_date == today else 1

    power_data = build_solaredge_power_quarters_by_date_payload(target_date)
    return save_solaredge_power_day_to_db(power_data, is_complete=is_complete)


def build_solaredge_update_range_payload(start: str, end: str):
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return {
            "status": "error",
            "message": "Formato de fecha inválido. Usa YYYY-MM-DD",
        }

    if start_date > end_date:
        return {
            "status": "error",
            "message": "La fecha inicial no puede ser posterior a la fecha final",
        }

    today = get_local_now().date()

    if end_date > today:
        return {
            "status": "error",
            "message": "No se pueden importar fechas futuras",
        }

    current = start_date
    imported = 0
    failed = []
    results = []

    while current <= end_date:
        date_iso = current.isoformat()

        result = build_solaredge_update_date_payload(date_iso)
        results.append(result)

        if result.get("status") == "ok":
            imported += 1
        else:
            failed.append({
                "date": date_iso,
                "status": result.get("status"),
                "message": result.get("message") or result.get("error"),
            })

        current += timedelta(days=1)

    return {
        "status": "ok",
        "start": start,
        "end": end,
        "imported": imported,
        "failed": failed,
        "results": results,
    }
# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE ENDPOINTS                                                         ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# LATEST
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


# ──────────────────────────────
# BY DATE
# ──────────────────────────────

@app.get("/price-hours/by-date")
def get_price_hours_by_date(date: str):
    return build_hours_payload_by_date(date)


@app.get("/price-periods/by-date")
def get_price_periods_by_date(date: str):
    return build_periods_payload_by_date(date)


# ──────────────────────────────
# HISTORY
# ──────────────────────────────

@app.get("/price-days/history")
def get_price_days_history(limit: int = 30):
    return build_price_days_history_payload(limit)


# ╔════════════════════════════════════════════════════════════╗
# ║ SOLAREDGE ENDPOINTS                                                    ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# CURRENT
# ──────────────────────────────

@app.get("/solar-edge/current")
def get_solaredge_current():
    return build_solaredge_current_payload()


# ──────────────────────────────
# TODAY
# ──────────────────────────────

@app.get("/solar-edge/quarters-today")
def get_solaredge_quarters_today():
    return build_solaredge_quarters_today_payload()


@app.get("/solar-edge/power-quarters-today")
def get_solaredge_power_quarters_today():
    return build_solaredge_power_quarters_today_payload()


# ──────────────────────────────
# ACCUMULATED
# ──────────────────────────────

@app.get("/solar-edge/month")
def get_solaredge_month():
    return build_solaredge_month_payload()


# ──────────────────────────────
# RAW / DEBUG
# ──────────────────────────────

@app.get("/solar-edge/meters")
def get_solar_edge_meters():
    return build_solaredge_meters_payload()

# ──────────────────────────────
# STORAGE
# ──────────────────────────────

@app.get("/solar-edge/update-today")
def update_solaredge_today():
    return build_solaredge_update_today_payload()


@app.get("/solar-edge/update-date")
def update_solaredge_date(date: str):
    return build_solaredge_update_date_payload(date)


@app.get("/solar-edge/update-range")
def update_solaredge_range(start: str, end: str):
    return build_solaredge_update_range_payload(start, end)

# ╔════════════════════════════════════════════════════════════╗
# ║ OMIE IMPORT ENDPOINTS                                                  ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# IMPORT LATEST AVAILABLE
# ──────────────────────────────

@app.get("/import-omie")
def import_omie():
    from scripts.fetch_omie import fetch_list_page, process_latest_available

    html = fetch_list_page()

    if not html:
        return {"status": "error", "message": "No se pudo cargar listado OMIE"}

    process_latest_available(html)

    return {"status": "ok"}


# ──────────────────────────────
# IMPORT RANGE
# ──────────────────────────────

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

# ╔════════════════════════════════════════════════════════════╗
# ║ DATADIS / E-DISTRIBUCIÓN DATA                                          ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# DATADIS DAYS
# ──────────────────────────────

@app.get("/datadis-days/latest")
def get_latest_datadis_day():
    conn = get_db_connection()
    cursor = conn.cursor()

    row = cursor.execute("""
        SELECT
            date,
            grid_consumed_kwh,
            feed_in_kwh,
            hours_count,
            expected_hours,
            real_hours_count,
            estimated_hours_count,
            is_complete,
            data_quality,
            quality_note,
            source_file,
            updated_at
        FROM datadis_days
        WHERE is_complete = 1
        ORDER BY date DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    if row is None:
        return {
            "status": "empty",
            "message": "No Datadis data found"
        }

    return {
        "status": "ok",
        "date": row["date"],
        "gridConsumedKwh": row["grid_consumed_kwh"],
        "feedInKwh": row["feed_in_kwh"],
        "hoursCount": row["hours_count"],
        "expectedHours": row["expected_hours"],
        "realHoursCount": row["real_hours_count"],
        "estimatedHoursCount": row["estimated_hours_count"],
        "isComplete": bool(row["is_complete"]),
        "dataQuality": row["data_quality"],
        "qualityNote": row["quality_note"],
        "sourceFile": row["source_file"],
        "updatedAt": row["updated_at"],
        "source": "datadis"
    }


@app.get("/datadis-days/period")
def get_datadis_period(start: str = NEXUS_START_DATE, end: str | None = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    params = [start]

    end_filter = ""
    if end:
        end_filter = "AND date <= ?"
        params.append(end)

    summary = cursor.execute(f"""
        SELECT
            ROUND(SUM(grid_consumed_kwh), 3) AS grid_consumed_kwh,
            ROUND(SUM(feed_in_kwh), 3) AS feed_in_kwh,
            COUNT(*) AS days_count,
            MIN(date) AS first_date,
            MAX(date) AS last_date
        FROM datadis_days
        WHERE date >= ?
          AND is_complete = 1
          {end_filter}
    """, params).fetchone()

    incomplete_days = cursor.execute(f"""
        SELECT
            date,
            hours_count,
            expected_hours,
            data_quality,
            quality_note
        FROM datadis_days
        WHERE date >= ?
          AND is_complete = 0
          {end_filter}
        ORDER BY date
    """, params).fetchall()

    conn.close()

    return {
        "status": "ok",
        "startDate": start,
        "endDate": end,
        "firstAvailableDate": summary["first_date"],
        "lastAvailableDate": summary["last_date"],
        "daysCount": summary["days_count"],
        "gridConsumedKwh": summary["grid_consumed_kwh"] or 0,
        "feedInKwh": summary["feed_in_kwh"] or 0,
        "excludedDays": [
            {
                "date": row["date"],
                "hoursCount": row["hours_count"],
                "expectedHours": row["expected_hours"],
                "dataQuality": row["data_quality"],
                "qualityNote": row["quality_note"],
            }
            for row in incomplete_days
        ],
        "source": "datadis"
    }

# ╔════════════════════════════════════════════════════════════╗
# ║ ENERGY INTELLIGENCE                                                    ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# DAILY FINGERPRINTS
# ──────────────────────────────

@app.get("/energy-intelligence/daily-fingerprints")
def get_daily_energy_fingerprints(
    start: str = "2026-03-01",
    end: str | None = None,
    includeEstimated: bool = False
):
    conn = get_db_connection()
    cursor = conn.cursor()

    params = [start]

    end_filter = ""
    if end:
        end_filter = "AND d.date <= ?"
        params.append(end)

    datadis_quality_filter = "AND d.data_quality = 'complete_real'"

    if includeEstimated:
        datadis_quality_filter = "AND d.data_quality IN ('complete_real', 'complete_mixed')"

    rows = cursor.execute(f"""
        SELECT
            d.date,
            d.grid_consumed_kwh,
            d.feed_in_kwh,
            d.is_complete,
            d.data_quality AS datadis_quality,

            w.temp_avg_c,
            w.temp_max_c,
            w.cloud_cover_avg_percent,
            w.shortwave_radiation_sum,
            w.direct_radiation_sum,
            w.sunshine_duration_seconds,
            w.precipitation_sum_mm,
            w.solar_quality,
            w.data_quality AS weather_quality
        FROM datadis_days d
        JOIN weather_days w
          ON d.date = w.date
        WHERE d.date >= ?
          AND d.is_complete = 1
          {datadis_quality_filter}
          AND w.data_quality = 'complete'
          {end_filter}
        ORDER BY d.date
    """, params).fetchall()

    conn.close()

    base = []

    for row in rows:
        radiation = row["shortwave_radiation_sum"] or 0
        feed_in = row["feed_in_kwh"] or 0
        grid = row["grid_consumed_kwh"] or 0

        feed_in_per_radiation = None
        grid_per_radiation = None

        if radiation > 0:
            feed_in_per_radiation = feed_in / radiation
            grid_per_radiation = grid / radiation

        base.append({
            "date": row["date"],
            "gridConsumedKwh": grid,
            "feedInKwh": feed_in,
            "tempAvgC": row["temp_avg_c"],
            "tempMaxC": row["temp_max_c"],
            "cloudCoverAvgPercent": row["cloud_cover_avg_percent"],
            "shortwaveRadiationSum": radiation,
            "directRadiationSum": row["direct_radiation_sum"],
            "sunshineDurationSeconds": row["sunshine_duration_seconds"],
            "precipitationSumMm": row["precipitation_sum_mm"],
            "solarQuality": row["solar_quality"],
            "feedInPerRadiation": feed_in_per_radiation,
            "gridPerRadiation": grid_per_radiation,
            "datadisQuality": row["datadis_quality"],
            "weatherQuality": row["weather_quality"],
        })

    valid_ratios = [
        item["feedInPerRadiation"]
        for item in base
        if item["feedInPerRadiation"] is not None
        and item["solarQuality"] in ("sunny", "mostly_sunny")
        and item["datadisQuality"] == "complete_real"
    ]

    reference_ratio = median(valid_ratios) if valid_ratios else None

    fingerprints = []

    for item in base:
        ratio = item["feedInPerRadiation"]
        solar_quality = item["solarQuality"]

        hidden_consumption_signal = "unknown"
        day_type = "unknown"
        interpretation = "Datos insuficientes para clasificar"

        if reference_ratio and ratio is not None:
            if solar_quality in ("sunny", "mostly_sunny"):
                if ratio < reference_ratio * 0.80:
                    hidden_consumption_signal = "high"
                    day_type = "sunny_low_export"
                    interpretation = "Día con buen sol pero vertido bajo: probable consumo interno fuerte cubierto por solar"
                elif ratio < reference_ratio * 0.92:
                    hidden_consumption_signal = "medium"
                    day_type = "sunny_moderate_export"
                    interpretation = "Día con buen sol y vertido algo inferior al patrón"
                else:
                    hidden_consumption_signal = "low"
                    day_type = "sunny_clean_export"
                    interpretation = "Día soleado con vertido normal o alto"
            elif solar_quality == "mixed":
                hidden_consumption_signal = "medium"
                day_type = "mixed_solar"
                interpretation = "Día mixto: la bajada de vertido puede venir de nubes o consumo"
            else:
                hidden_consumption_signal = "low"
                day_type = "cloudy_low_solar"
                interpretation = "Día con baja calidad solar: menor vertido probablemente por clima"

        fingerprints.append({
            **item,
            "referenceFeedInPerRadiation": reference_ratio,
            "hiddenConsumptionSignal": hidden_consumption_signal,
            "dayType": day_type,
            "interpretation": interpretation,
        })

    return {
        "status": "ok",
        "startDate": start,
        "endDate": end,
        "includeEstimated": includeEstimated,
        "qualityMode": "real_and_estimated" if includeEstimated else "real_only",
        "daysCount": len(fingerprints),
        "referenceFeedInPerRadiation": reference_ratio,
        "items": fingerprints,
        "source": "datadis_weather"
    }

# ──────────────────────────────
# DAILY SUMMARY
# ──────────────────────────────

@app.get("/energy-intelligence/daily-summary")
def get_daily_energy_summary(
    start: str = "2026-03-01",
    end: str | None = None,
    days: int = 10,
    includeEstimated: bool = False
):
    fingerprints_response = get_daily_energy_fingerprints(
        start=start,
        end=end,
        includeEstimated=includeEstimated
    )

    items = fingerprints_response["items"]

    latest_items = list(reversed(items[-days:]))

    return {
        "status": "ok",
        "startDate": start,
        "endDate": end,
        "daysRequested": days,
        "daysReturned": len(latest_items),
        "includeEstimated": includeEstimated,
        "qualityMode": fingerprints_response["qualityMode"],
        "referenceFeedInPerRadiation": fingerprints_response["referenceFeedInPerRadiation"],
        "items": [
            {
                "date": item["date"],
                "gridConsumedKwh": item["gridConsumedKwh"],
                "feedInKwh": item["feedInKwh"],
                "solarQuality": item["solarQuality"],
                "tempAvgC": item["tempAvgC"],
                "tempMaxC": item["tempMaxC"],
                "cloudCoverAvgPercent": item["cloudCoverAvgPercent"],
                "shortwaveRadiationSum": item["shortwaveRadiationSum"],
                "feedInPerRadiation": item["feedInPerRadiation"],
                "hiddenConsumptionSignal": item["hiddenConsumptionSignal"],
                "dayType": item["dayType"],
                "interpretation": item["interpretation"],
                "datadisQuality": item["datadisQuality"],
            }
            for item in latest_items
        ],
        "source": "datadis_weather"
    }