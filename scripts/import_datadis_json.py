import json
import sqlite3
from pathlib import Path

DB_PATH = "database/omie.db"
DATA_PATH = Path("data/datadis")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

files = list(DATA_PATH.rglob("*.json"))

print(f"Encontrados {len(files)} archivos")

inserted = 0
skipped = 0


def to_float(value):
    if value in (None, "", " "):
        return 0.0
    return float(value.replace(",", "."))


for file in files:
    print(f"Importando {file}")

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for row in data:

        fecha = row.get("Fecha")
        hora = row.get("Hora")

        if not fecha or not hora:
            skipped += 1
            continue

        dt = f"{fecha} {hora}"

        consumption = to_float(row.get("Consumo_kWh"))
        generation = to_float(row.get("Energia_generada_kWh"))
        self_consumption = to_float(row.get("Energia_autoconsumida_kWh"))
        surplus = to_float(row.get("Energia_vertida_kWh"))

        cursor.execute("""
            INSERT OR IGNORE INTO datadis_curves
            (datetime, consumption, generation, self_consumption, surplus)
            VALUES (?, ?, ?, ?, ?)
        """, (
            dt,
            consumption,
            generation,
            self_consumption,
            surplus,
        ))

        inserted += 1

conn.commit()
conn.close()

print(f"IMPORT DONE - insertados: {inserted}, saltados: {skipped}")