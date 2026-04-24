import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.datadis_service import (
    login,
    get_supplies,
    get_consumption,
    filter_consumption_by_day,
)

TARGET_MONTH = "2026/04"
TARGET_DAY = "2026/04/22"


token = login()
print("TOKEN OK:", bool(token))

if not token:
    raise SystemExit("No token")

supplies = get_supplies(token)
print("SUPPLIES:", supplies)

if not supplies or not supplies.get("supplies"):
    raise SystemExit("No supplies found")

s = supplies["supplies"][0]

consumption = get_consumption(
    token,
    s["cups"],
    s["distributorCode"],
    s["pointType"],
    TARGET_MONTH,
)

print("CONSUMPTION TYPE:", type(consumption).__name__)

day_rows = filter_consumption_by_day(consumption, TARGET_DAY)
print("ROWS FOR DAY:", len(day_rows))
print("DAY DATA:", day_rows)