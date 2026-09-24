#!/usr/bin/env python3

import argparse
import sqlite3
import sys

from argparse import Namespace
from pathlib import Path

from fitparse import fetch_pulse, fetch_sleep, fetch_steps, fetch_stress


SCHEMA = """
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
"""


UPSERT_STEPS = """
INSERT INTO point (time, resolution, steps, distance_km, active_calories)
VALUES (?, 'day', ?, ?, ?)
ON CONFLICT(time, resolution) DO UPDATE SET
    steps = excluded.steps,
    distance_km = excluded.distance_km,
    active_calories = excluded.active_calories;
"""


UPSERT_PULSE = """
INSERT INTO point (time, resolution, pulse, activity_type)
VALUES (?, 'minute', ?, ?)
ON CONFLICT(time, resolution) DO UPDATE SET
    pulse = excluded.pulse,
    activity_type = excluded.activity_type;
"""


UPSERT_SLEEP = """
INSERT INTO point (time, resolution, sleep_hours, sleep_score)
VALUES (?, 'day', ?, ?)
ON CONFLICT(time, resolution) DO UPDATE SET
    sleep_hours = excluded.sleep_hours,
    sleep_score = excluded.sleep_score;
"""


UPSERT_STRESS = """
INSERT INTO point (time, resolution, stress)
VALUES (?, 'minute', ?)
ON CONFLICT(time, resolution) DO UPDATE SET
    stress = excluded.stress;
"""


def _parse_args():
    parser = argparse.ArgumentParser(description="Import Garmin FIT data into SQLite")
    parser.add_argument("-b", "--batch", action="store_true",
                        help="Batch mode - read FIT file names from stdin")
    parser.add_argument("--db-path", default="~/fit.db", help="Path to SQLite database")
    parser.add_argument("file_names", nargs="*", help="FIT files to import")
    return parser.parse_args()


def _make_fit_args(args):
    file_names = args.file_names
    if args.batch:
        file_names = [name.strip() for name in sys.stdin if name.strip()]

    return Namespace(
        file_names=file_names,
        batch=False,
        since=None,
        until=None,
    )


def _format_time(val, fmt):
    return val.strftime(fmt)


def _import_steps(conn, args):
    rows = [
        (_format_time(dt, "%Y-%m-%d"), steps, distance_km, active_calories)
        for dt, steps, distance_km, active_calories in fetch_steps(args)
    ]
    conn.executemany(UPSERT_STEPS, rows)
    return len(rows)


def _import_pulse(conn, args):
    rows = [
        (_format_time(dt, "%Y-%m-%dT%H:%M:%S"), pulse, activity_type)
        for dt, pulse, activity_type in fetch_pulse(args)
    ]
    conn.executemany(UPSERT_PULSE, rows)
    return len(rows)


def _import_sleep(conn, args):
    rows = [
        (_format_time(dt, "%Y-%m-%d"), sleep_hours, sleep_score)
        for dt, sleep_hours, sleep_score in fetch_sleep(args)
    ]
    conn.executemany(UPSERT_SLEEP, rows)
    return len(rows)


def _import_stress(conn, args):
    rows = [
        (_format_time(dt, "%Y-%m-%dT%H:%M:%S"), stress)
        for dt, stress in fetch_stress(args)
    ]
    conn.executemany(UPSERT_STRESS, rows)
    return len(rows)


def main():
    args = _parse_args()
    db_path = Path(args.db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    fit_args = _make_fit_args(args)
    with sqlite3.connect(db_path) as conn:
        conn.execute(SCHEMA)
        counts = {
            "steps": _import_steps(conn, fit_args),
            "pulse": _import_pulse(conn, fit_args),
            "sleep": _import_sleep(conn, fit_args),
            "stress": _import_stress(conn, fit_args),
        }

    print("Imported " + ", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
