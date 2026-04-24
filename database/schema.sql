CREATE TABLE markets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(10) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE price_days (
    id SERIAL PRIMARY KEY,
    market_id INT NOT NULL,
    date DATE NOT NULL,
    avg_price DECIMAL(10,4),
    min_price DECIMAL(10,4),
    max_price DECIMAL(10,4),
   

    base_load_price DECIMAL(10,4),
    peak_load_price DECIMAL(10,4),
    hours_count INT,
    import_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    source_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_price_days_market
        FOREIGN KEY (market_id) REFERENCES markets(id),
    CONSTRAINT uq_price_days_market_date
        UNIQUE (market_id, date)
);

CREATE TABLE price_hours (
    id SERIAL PRIMARY KEY,
    price_day_id INT NOT NULL,
    hour_index INT NOT NULL,
    hour_start TIMESTAMP,
    hour_end TIMESTAMP,
    price DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_price_hours_day
        FOREIGN KEY (price_day_id) REFERENCES price_days(id),
    CONSTRAINT uq_price_hours_day_hour
        UNIQUE (price_day_id, hour_index)
);

CREATE TABLE day_comparisons (
    id SERIAL PRIMARY KEY,
    market_id INT NOT NULL,
    date DATE NOT NULL,
    previous_date DATE,
    avg_diff DECIMAL(10,4),
    avg_diff_pct DECIMAL(10,4),
    min_diff DECIMAL(10,4),
    max_diff DECIMAL(10,4),
    cheapest_hour_today INT,
    cheapest_hour_yesterday INT,
    most_expensive_hour_today INT,
    most_expensive_hour_yesterday INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_day_comparisons_market
        FOREIGN KEY (market_id) REFERENCES markets(id),
    CONSTRAINT uq_day_comparisons_market_date
        UNIQUE (market_id, date)
);

-- price_days
CREATE INDEX idx_price_days_market_date
ON price_days (market_id, date DESC);

-- price_hours
CREATE INDEX idx_price_hours_day
ON price_hours (price_day_id);

-- day_comparisons
CREATE INDEX idx_day_comparisons_market_date
ON day_comparisons (market_id, date DESC);

ALTER TABLE price_hours
ADD CONSTRAINT chk_hour_index
CHECK (hour_index >= 1 AND hour_index <= 24);

