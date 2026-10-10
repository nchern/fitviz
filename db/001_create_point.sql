CREATE TABLE IF NOT EXISTS point (
    time            TEXT NOT NULL,
    resolution      TEXT NOT NULL CHECK (resolution IN ('day', 'minute')),
    steps           INTEGER,
    distance_km     REAL,
    active_calories INTEGER,
    pulse           INTEGER,
    activity_type   INTEGER,
    sleep_hours     REAL,
    sleep_score     INTEGER,
    stress          INTEGER,

    PRIMARY KEY (time, resolution)
);
