import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


DB_PATH = os.getenv("DATABASE_PATH", "database/omie.db")
DEFAULT_INPUT_DIR = Path("data/datadis/2026")


def parse_decimal(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip().replace(",", ".")
    if value == "":
        return 0.0
    return float(value)


def parse_date(value):
    return datetime.strptime(value, "%Y/%m/%d").date().isoformat()


def parse_hour_index(hour_label):
    # Datadis viene como "01:00" ... "24:00"
    return int(hour_label.split(":")[0])


def expected_hours_for_day(day_iso):
    """
    España peninsular:
    - último domingo de marzo: 23 horas
    - último domingo de octubre: 25 horas
    - resto: 24 horas
    """
    d = date.fromisoformat(day_iso)

    if d.month == 3 and d.weekday() == 6 and 25 <= d.day <= 31:
        return 23

    if d.month == 10 and d.weekday() == 6 and 25 <= d.day <= 31:
        return 25

    return 24


def load_records(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"El JSON no es una lista: {path}")

    return data


def iter_input_files(input_path):
    path = Path(input_path)

    if path.is_file():
        return [path]

    if path.is_dir():
        return sorted(path.glob("*.json"))

    raise FileNotFoundError(f"No existe: {input_path}")


def init_db(conn):
    with open("database/schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def import_file(conn, file_path):
    records = load_records(file_path)
    days = defaultdict(list)

    for row in records:
        cups = row["cups"]
        day = parse_date(row["fecha"])
        hour_label = row["hora"]
        hour_index = parse_hour_index(hour_label)

        grid_consumed_kwh = parse_decimal(row.get("consumo_kWh"))
        feed_in_kwh = parse_decimal(row.get("energiaVertida_kWh"))

        method = row.get("metodoObtencion")
        is_estimated = 1 if str(method).strip().lower() == "estimada" else 0

        slot_key = hour_label

        conn.execute(
            """
            INSERT INTO datadis_hours (
                cups,
                date,
                hour_label,
                slot_key,
                hour_index,
                grid_consumed_kwh,
                feed_in_kwh,
                method,
                is_estimated,
                source_file,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(cups, date, slot_key)
            DO UPDATE SET
                hour_label = excluded.hour_label,
                hour_index = excluded.hour_index,
                grid_consumed_kwh = excluded.grid_consumed_kwh,
                feed_in_kwh = excluded.feed_in_kwh,
                method = excluded.method,
                is_estimated = excluded.is_estimated,
                source_file = excluded.source_file,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                cups,
                day,
                hour_label,
                slot_key,
                hour_index,
                grid_consumed_kwh,
                feed_in_kwh,
                method,
                is_estimated,
                file_path.name,
            ),
        )

        days[(cups, day)].append(
            {
                "grid": grid_consumed_kwh,
                "feed": feed_in_kwh,
                "method": method,
                "is_estimated": is_estimated,
                "hour_index": hour_index,
            }
        )

    for (cups, day), rows in days.items():
        hours_count = len(rows)
        expected_hours = expected_hours_for_day(day)
        real_hours_count = sum(1 for r in rows if not r["is_estimated"])
        estimated_hours_count = sum(1 for r in rows if r["is_estimated"])

        grid_total = round(sum(r["grid"] for r in rows), 3)
        feed_total = round(sum(r["feed"] for r in rows), 3)

        is_complete = 1 if hours_count == expected_hours else 0

        if is_complete and estimated_hours_count == 0:
            data_quality = "complete_real"
            quality_note = None
        elif is_complete and estimated_hours_count > 0:
            data_quality = "complete_mixed"
            quality_note = f"{estimated_hours_count} horas estimadas"
        elif hours_count < expected_hours:
            data_quality = "incomplete"
            missing = expected_hours - hours_count
            quality_note = f"Faltan {missing} horas"
        else:
            data_quality = "unexpected"
            quality_note = f"{hours_count} horas para un día de {expected_hours}"

        conn.execute(
            """
            INSERT INTO datadis_days (
                cups,
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(cups, date)
            DO UPDATE SET
                grid_consumed_kwh = excluded.grid_consumed_kwh,
                feed_in_kwh = excluded.feed_in_kwh,
                hours_count = excluded.hours_count,
                expected_hours = excluded.expected_hours,
                real_hours_count = excluded.real_hours_count,
                estimated_hours_count = excluded.estimated_hours_count,
                is_complete = excluded.is_complete,
                data_quality = excluded.data_quality,
                quality_note = excluded.quality_note,
                source_file = excluded.source_file,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                cups,
                day,
                grid_total,
                feed_total,
                hours_count,
                expected_hours,
                real_hours_count,
                estimated_hours_count,
                is_complete,
                data_quality,
                quality_note,
                file_path.name,
            ),
        )

    return {
        "file": file_path.name,
        "records": len(records),
        "days": len(days),
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT_DIR

    files = iter_input_files(input_path)

    if not files:
        print(f"No hay JSON en {input_path}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        init_db(conn)

        results = []
        for file_path in files:
            result = import_file(conn, file_path)
            results.append(result)

        conn.commit()

        print("Importación Datadis OK")
        print(f"DB: {DB_PATH}")
        print(f"Archivos: {len(results)}")

        for r in results:
            print(f"- {r['file']}: {r['records']} registros, {r['days']} días")

    finally:
        conn.close()


if __name__ == "__main__":
    main()