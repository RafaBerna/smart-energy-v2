import sqlite3

conn = sqlite3.connect("../database/omie.db")
cursor = conn.cursor()

print("PRICE_DAYS")
for row in cursor.execute("SELECT * FROM price_days"):
    print(row)

print("\nPRICE_HOURS")
for row in cursor.execute("SELECT * FROM price_hours LIMIT 24"):
    print(row)

conn.close()