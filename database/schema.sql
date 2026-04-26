CREATE TABLE IF NOT EXISTS price_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    avg_price REAL,
    min_price REAL,
    max_price REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_day_id INTEGER NOT NULL,
    period INTEGER NOT NULL,
    price REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_day_id) REFERENCES price_days(id),
    UNIQUE (price_day_id, period)
);

CREATE TABLE IF NOT EXISTS price_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_day_id INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    price REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_day_id) REFERENCES price_days(id),
    UNIQUE (price_day_id, hour)
);

CREATE INDEX IF NOT EXISTS idx_price_days_date
ON price_days (date DESC);

CREATE INDEX IF NOT EXISTS idx_price_periods_day
ON price_periods (price_day_id);

CREATE INDEX IF NOT EXISTS idx_price_hours_day
ON price_hours (price_day_id);

-- ╔════════════════════════════════════════════════════════════╗
-- ║ SOLAREDGE DATA                                            ║
-- ╚════════════════════════════════════════════════════════════╝

-- ──────────────────────────────
-- SOLAR QUARTERS
-- ──────────────────────────────

CREATE TABLE IF NOT EXISTS solar_quarters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    period INTEGER NOT NULL,
    measurement_time TEXT NOT NULL,
    grid_consumed_raw REAL NOT NULL DEFAULT 0,
    feed_in_raw REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (date, period)
);

CREATE INDEX IF NOT EXISTS idx_solar_quarters_date
ON solar_quarters (date);

CREATE INDEX IF NOT EXISTS idx_solar_quarters_measurement_time
ON solar_quarters (measurement_time);


-- ──────────────────────────────
-- SOLAR DAYS
-- ──────────────────────────────

CREATE TABLE IF NOT EXISTS solar_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    grid_consumed_kwh REAL NOT NULL DEFAULT 0,
    feed_in_kwh REAL NOT NULL DEFAULT 0,
    intervals_count INTEGER NOT NULL DEFAULT 0,
    last_measurement_at TEXT,
    is_complete INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'solaredge_power',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_solar_days_date
ON solar_days (date DESC);