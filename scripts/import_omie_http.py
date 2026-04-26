import os
import sys
import urllib.request


# ╔════════════════════════════════════════════════════════════╗
# ║ CONFIGURATION                                              ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# IMPORT URL
# ──────────────────────────────

OMIE_IMPORT_URL = os.getenv(
    "OMIE_IMPORT_URL",
    "https://cooperative-insight-production-a160.up.railway.app/import-omie",
)


# ╔════════════════════════════════════════════════════════════╗
# ║ HTTP IMPORT                                                ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# CALL IMPORT ENDPOINT
# ──────────────────────────────

def call_import_endpoint():
    print(f"Llamando a: {OMIE_IMPORT_URL}")

    try:
        with urllib.request.urlopen(OMIE_IMPORT_URL, timeout=60) as response:
            status_code = response.status
            body = response.read().decode("utf-8")

        print(f"Status code: {status_code}")
        print(f"Response: {body}")

        if status_code < 200 or status_code >= 300:
            return False

        return True

    except Exception as error:
        print(f"Error llamando a import OMIE: {error}")
        return False


# ╔════════════════════════════════════════════════════════════╗
# ║ CLI EXECUTION                                              ║
# ╚════════════════════════════════════════════════════════════╝

# ──────────────────────────────
# MAIN
# ──────────────────────────────

if __name__ == "__main__":
    ok = call_import_endpoint()

    if not ok:
        sys.exit(1)

    sys.exit(0)