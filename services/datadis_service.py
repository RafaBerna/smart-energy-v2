import os
import time
import requests

DATADIS_LOGIN_URL = "https://datadis.es/nikola-auth/tokens/login"
DATADIS_BASE_URL = "https://datadis.es/api-private/api"

USERNAME = os.getenv("DATADIS_USERNAME", "")
PASSWORD = os.getenv("DATADIS_PASSWORD", "")

COMMON_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


def login():
    if not USERNAME or not PASSWORD:
        print("LOGIN ERROR: faltan DATADIS_USERNAME o DATADIS_PASSWORD")
        return None

    response = requests.post(
        DATADIS_LOGIN_URL,
        data={
            "username": USERNAME,
            "password": PASSWORD,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        },
        timeout=20,
    )

    print("LOGIN STATUS:", response.status_code)

    if response.status_code != 200:
        print("LOGIN RAW:", response.text)
        return None

    token = response.text.strip().strip('"')
    return token


def get_supplies(token, retries=2):
    url = f"{DATADIS_BASE_URL}/get-supplies-v2"

    for attempt in range(retries + 1):
        response = requests.get(
            url,
            headers={
                **COMMON_HEADERS,
                "Authorization": f"Bearer {token}",
            },
            timeout=20,
        )

        print("SUPPLIES STATUS:", response.status_code)
        print("SUPPLIES RAW:", response.text)

        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                return None

        if attempt < retries:
            time.sleep(2)

    return None


def get_consumption(token, cups, distributor_code, point_type, start_month, end_month=None):
    url = f"{DATADIS_BASE_URL}/get-consumption-data-v2"

    if end_month is None:
        end_month = start_month

    params = {
        "cups": cups,
        "distributorCode": distributor_code,
        "startDate": start_month,   # formato YYYY/MM
        "endDate": end_month,       # formato YYYY/MM
        "measurementType": "0",
        "pointType": str(point_type),
    }

    response = requests.get(
        url,
        headers={
            **COMMON_HEADERS,
            "Authorization": f"Bearer {token}",
        },
        params=params,
        timeout=30,
    )

    print("CONSUMPTION STATUS:", response.status_code)
    print("CONSUMPTION RAW:", response.text)

    try:
        return response.json()
    except Exception:
        return None


def filter_consumption_by_day(consumption_data, target_date):
    if not consumption_data:
        return []

    rows = []

    if isinstance(consumption_data, list):
        rows = consumption_data
    elif isinstance(consumption_data, dict):
        if isinstance(consumption_data.get("items"), list):
            rows = consumption_data["items"]
        elif isinstance(consumption_data.get("data"), list):
            rows = consumption_data["data"]
        elif isinstance(consumption_data.get("consumptions"), list):
            rows = consumption_data["consumptions"]

    result = []

    for row in rows:
        row_date = (
            row.get("date")
            or row.get("Date")
            or row.get("datetime")
            or row.get("Datetime")
            or ""
        )

        if isinstance(row_date, str) and target_date in row_date:
            result.append(row)

    return result