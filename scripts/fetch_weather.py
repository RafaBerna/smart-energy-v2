import argparse
import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests


DB_PATH = os.getenv("DATABASE_PATH", "database/omie.db")

LOCATION_CODE = "sant_sadurni"
LATITUDE = 41.446241
LONGITUDE = 1.779579
TIMEZONE = "Europe/Madrid"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARIABLES = [
    "temperature_2m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "sunshine_duration",
    "precipitation",
    "weather_code",
]


def yesterday_madrid():
    return (datetime.now(ZoneInfo(TIMEZONE)).date() - timedelta(days=1)).isoformat()


def parse_float(value):
    if value is None:
        return None
    return float(value)


def parse_int(value):
    if value is None:
        return None
    return int(value)


def avg(values):
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 3)


def total(values):
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean), 3)


def classify_solar_quality(shortwave_sum, cloud_avg):
    if shortwave_sum is None:
        return "unknown"

    cloud_avg = cloud_avg if cloud_avg is not None else 100

    if shortwave_sum >= 4500 and cloud_avg <= 35:
        return "sunny"

    if shortwave_sum >= 3000 and cloud_avg <= 55:
        return "mostly_sunny"

    if shortwave_sum >= 1500:
        return "mixed"

    return "cloudy"


def get_db_connection():
    db_dir = os.path.dirname(DB_PATH)

    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    with open("database/schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def fetch_weather(start_date, end_date):
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
    }

    response = requests.get(
        OPEN_METEO_ARCHIVE_URL,
        params=params,
        timeout=60,
    )

    response.raise_for_status()
    return response.json()


def normalize_hourly_payload(payload):
    hourly = payload.get("hourly")

    if not hourly:
        raise ValueError("Open-Meteo no devolvió bloque hourly")

    times = hourly.get("time", [])
    rows = []

    for index, time_value in enumerate(times):
        dt = datetime.fromisoformat(time_value)

        # Open-Meteo usa 00:00-23:00.
        # Datadis usa 01:00-24:00 como cierre de periodo.
        # Guardamos 1-24 para alinear mejor con Datadis.
        hour = dt.hour + 1

        rows.append(
            {
                "date": dt.date().isoformat(),
                "hour": hour,
                "temperature_c": parse_float(hourly.get("temperature_2m", [None])[index]),
                "cloud_cover_percent": parse_float(hourly.get("cloud_cover", [None])[index]),
                "shortwave_radiation": parse_float(hourly.get("shortwave_radiation", [None])[index]),
                "direct_radiation": parse_float(hourly.get("direct_radiation", [None])[index]),
                "diffuse_radiation": parse_float(hourly.get("diffuse_radiation", [None])[index]),
                "sunshine_duration_seconds": parse_float(hourly.get("sunshine_duration", [None])[index]),
                "precipitation_mm": parse_float(hourly.get("precipitation", [None])[index]),
                "weather_code": parse_int(hourly.get("weather_code", [None])[index]),
            }
        )

    return rows


def upsert_weather_hours(conn, rows):
    for row in rows:
        conn.execute(
            """
            INSERT INTO weather_hours (
                location_code,
                date,
                hour,
                temperature_c,
                cloud_cover_percent,
                shortwave_radiation,
                direct_radiation,
                diffuse_radiation,
                sunshine_duration_seconds,
                precipitation_mm,
                weather_code,
                source,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open_meteo', CURRENT_TIMESTAMP)
            ON CONFLICT(location_code, date, hour)
            DO UPDATE SET
                temperature_c = excluded.temperature_c,
                cloud_cover_percent = excluded.cloud_cover_percent,
                shortwave_radiation = excluded.shortwave_radiation,
                direct_radiation = excluded.direct_radiation,
                diffuse_radiation = excluded.diffuse_radiation,
                sunshine_duration_seconds = excluded.sunshine_duration_seconds,
                precipitation_mm = excluded.precipitation_mm,
                weather_code = excluded.weather_code,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                LOCATION_CODE,
                row["date"],
                row["hour"],
                row["temperature_c"],
                row["cloud_cover_percent"],
                row["shortwave_radiation"],
                row["direct_radiation"],
                row["diffuse_radiation"],
                row["sunshine_duration_seconds"],
                row["precipitation_mm"],
                row["weather_code"],
            ),
        )


def build_daily_summaries(rows):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["date"]].append(row)

    summaries = []

    for day, day_rows in grouped.items():
        temperatures = [r["temperature_c"] for r in day_rows]
        clouds = [r["cloud_cover_percent"] for r in day_rows]
        shortwave = [r["shortwave_radiation"] for r in day_rows]
        direct = [r["direct_radiation"] for r in day_rows]
        diffuse = [r["diffuse_radiation"] for r in day_rows]
        sunshine = [r["sunshine_duration_seconds"] for r in day_rows]
        precipitation = [r["precipitation_mm"] for r in day_rows]

        temp_values = [v for v in temperatures if v is not None]

        shortwave_sum = total(shortwave)
        cloud_avg = avg(clouds)

        summaries.append(
            {
                "date": day,
                "temp_min_c": round(min(temp_values), 3) if temp_values else None,
                "temp_max_c": round(max(temp_values), 3) if temp_values else None,
                "temp_avg_c": avg(temperatures),
                "cloud_cover_avg_percent": cloud_avg,
                "shortwave_radiation_sum": shortwave_sum,
                "direct_radiation_sum": total(direct),
                "diffuse_radiation_sum": total(diffuse),
                "sunshine_duration_seconds": total(sunshine),
                "precipitation_sum_mm": total(precipitation),
                "solar_quality": classify_solar_quality(shortwave_sum, cloud_avg),
                "data_quality": "complete" if len(day_rows) >= 23 else "incomplete",
            }
        )

    return summaries


def upsert_weather_days(conn, summaries):
    for row in summaries:
        conn.execute(
            """
            INSERT INTO weather_days (
                location_code,
                date,
                temp_min_c,
                temp_max_c,
                temp_avg_c,
                cloud_cover_avg_percent,
                shortwave_radiation_sum,
                direct_radiation_sum,
                diffuse_radiation_sum,
                sunshine_duration_seconds,
                precipitation_sum_mm,
                solar_quality,
                data_quality,
                source,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open_meteo', CURRENT_TIMESTAMP)
            ON CONFLICT(location_code, date)
            DO UPDATE SET
                temp_min_c = excluded.temp_min_c,
                temp_max_c = excluded.temp_max_c,
                temp_avg_c = excluded.temp_avg_c,
                cloud_cover_avg_percent = excluded.cloud_cover_avg_percent,
                shortwave_radiation_sum = excluded.shortwave_radiation_sum,
                direct_radiation_sum = excluded.direct_radiation_sum,
                diffuse_radiation_sum = excluded.diffuse_radiation_sum,
                sunshine_duration_seconds = excluded.sunshine_duration_seconds,
                precipitation_sum_mm = excluded.precipitation_sum_mm,
                solar_quality = excluded.solar_quality,
                data_quality = excluded.data_quality,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                LOCATION_CODE,
                row["date"],
                row["temp_min_c"],
                row["temp_max_c"],
                row["temp_avg_c"],
                row["cloud_cover_avg_percent"],
                row["shortwave_radiation_sum"],
                row["direct_radiation_sum"],
                row["diffuse_radiation_sum"],
                row["sunshine_duration_seconds"],
                row["precipitation_sum_mm"],
                row["solar_quality"],
                row["data_quality"],
            ),
        )


def main():
    parser = argparse.ArgumentParser(
        description="Importa clima horario Open-Meteo para Sant Sadurní"
    )

    parser.add_argument(
        "--start",
        default="2026-01-01",
        help="Fecha inicio YYYY-MM-DD",
    )

    parser.add_argument(
        "--end",
        default=yesterday_madrid(),
        help="Fecha fin YYYY-MM-DD. Por defecto: ayer",
    )

    args = parser.parse_args()

    print("Descargando clima Open-Meteo")
    print(f"Ubicación: {LOCATION_CODE}")
    print(f"Coordenadas: {LATITUDE}, {LONGITUDE}")
    print(f"Rango: {args.start} → {args.end}")

    payload = fetch_weather(args.start, args.end)
    rows = normalize_hourly_payload(payload)
    summaries = build_daily_summaries(rows)

    conn = get_db_connection()

    try:
        init_db(conn)
        upsert_weather_hours(conn, rows)
        upsert_weather_days(conn, summaries)
        conn.commit()

    finally:
        conn.close()

    print("Importación weather OK")
    print(f"Horas importadas: {len(rows)}")
    print(f"Días resumidos: {len(summaries)}")


if __name__ == "__main__":
    main()