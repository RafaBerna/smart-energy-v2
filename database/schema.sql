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
-- ║ SOLAREDGE DATA                                                         ║
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


-- ╔════════════════════════════════════════════════════════════╗
-- ║ DATADIS / E-DISTRIBUCIÓN DATA                                          ║
-- ╚════════════════════════════════════════════════════════════╝

-- ──────────────────────────────
-- DATADIS HOURS
-- ──────────────────────────────

CREATE TABLE IF NOT EXISTS datadis_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    cups TEXT NOT NULL,
    date TEXT NOT NULL,
    hour_label TEXT NOT NULL,
    slot_key TEXT NOT NULL,
    hour_index INTEGER NOT NULL,

    grid_consumed_kwh REAL NOT NULL DEFAULT 0,
    feed_in_kwh REAL NOT NULL DEFAULT 0,

    method TEXT,
    is_estimated INTEGER NOT NULL DEFAULT 0,

    source_file TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (cups, date, slot_key)
);

CREATE INDEX IF NOT EXISTS idx_datadis_hours_date
ON datadis_hours (date);

CREATE INDEX IF NOT EXISTS idx_datadis_hours_cups_date
ON datadis_hours (cups, date);


-- ──────────────────────────────
-- DATADIS DAYS
-- ──────────────────────────────

CREATE TABLE IF NOT EXISTS datadis_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    cups TEXT NOT NULL,
    date TEXT NOT NULL,

    grid_consumed_kwh REAL NOT NULL DEFAULT 0,
    feed_in_kwh REAL NOT NULL DEFAULT 0,

    hours_count INTEGER NOT NULL DEFAULT 0,
    expected_hours INTEGER NOT NULL DEFAULT 24,
    real_hours_count INTEGER NOT NULL DEFAULT 0,
    estimated_hours_count INTEGER NOT NULL DEFAULT 0,

    is_complete INTEGER NOT NULL DEFAULT 0,
    data_quality TEXT NOT NULL DEFAULT 'pending',
    quality_note TEXT,

    source_file TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (cups, date)
);

CREATE INDEX IF NOT EXISTS idx_datadis_days_date
ON datadis_days (date DESC);

CREATE INDEX IF NOT EXISTS idx_datadis_days_quality
ON datadis_days (data_quality, is_complete);

-- ╔════════════════════════════════════════════════════════════╗
-- ║ WEATHER DATA                                              ║
-- ╚════════════════════════════════════════════════════════════╝

-- ──────────────────────────────
-- WEATHER HOURS
-- ──────────────────────────────

CREATE TABLE IF NOT EXISTS weather_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    location_code TEXT NOT NULL DEFAULT 'sant_sadurni',
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,

    temperature_c REAL,
    cloud_cover_percent REAL,

    shortwave_radiation REAL,
    direct_radiation REAL,
    diffuse_radiation REAL,
    sunshine_duration_seconds REAL,

    precipitation_mm REAL,
    weather_code INTEGER,

    source TEXT NOT NULL DEFAULT 'open_meteo',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (location_code, date, hour)
);

CREATE INDEX IF NOT EXISTS idx_weather_hours_date
ON weather_hours (date);

CREATE INDEX IF NOT EXISTS idx_weather_hours_location_date
ON weather_hours (location_code, date);


-- ──────────────────────────────
-- WEATHER DAYS
-- ──────────────────────────────

CREATE TABLE IF NOT EXISTS weather_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    location_code TEXT NOT NULL DEFAULT 'sant_sadurni',
    date TEXT NOT NULL,

    temp_min_c REAL,
    temp_max_c REAL,
    temp_avg_c REAL,

    cloud_cover_avg_percent REAL,

    shortwave_radiation_sum REAL,
    direct_radiation_sum REAL,
    diffuse_radiation_sum REAL,
    sunshine_duration_seconds REAL,

    precipitation_sum_mm REAL,

    solar_quality TEXT,
    data_quality TEXT NOT NULL DEFAULT 'pending',

    source TEXT NOT NULL DEFAULT 'open_meteo',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (location_code, date)
);

CREATE INDEX IF NOT EXISTS idx_weather_days_date
ON weather_days (date DESC);

CREATE INDEX IF NOT EXISTS idx_weather_days_location_date
ON weather_days (location_code, date);

CREATE INDEX IF NOT EXISTS idx_weather_days_solar_quality
ON weather_days (solar_quality);