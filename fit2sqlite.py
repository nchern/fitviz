#!/usr/bin/env python3

import argparse
import sqlite3
import sys

from argparse import Namespace
from pathlib import Path

from fitparse import fetch_pulse, fetch_sleep, fetch_steps, fetch_stress


MIGRATIONS_DIR = Path(__file__).resolve().parent / "db"


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
INSERT INTO point (
    time,
    resolution,
    sleep_hours,
    sleep_score,
    sleep_deep_hours,
    sleep_light_hours,
    sleep_rem_hours,
    sleep_awake_hours
)
VALUES (?, 'day', ?, ?, ?, ?, ?, ?)
ON CONFLICT(time, resolution) DO UPDATE SET
    sleep_hours = excluded.sleep_hours,
    sleep_score = excluded.sleep_score,
    sleep_deep_hours = excluded.sleep_deep_hours,
    sleep_light_hours = excluded.sleep_light_hours,
    sleep_rem_hours = excluded.sleep_rem_hours,
    sleep_awake_hours = excluded.sleep_awake_hours;
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
    parser.add_argument("--schema", action='store_true', required=False, help="Print schema")
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


def _migration_files():
    migrations = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        prefix, separator, name = path.name.partition("_")
        if not separator or len(prefix) != 3 or not prefix.isdigit() or not name:
            raise ValueError(f"invalid migration file name: {path.name}")
        migrations.append((int(prefix), path))

    for expected_version, (version, _) in enumerate(migrations, start=1):
        if version != expected_version:
            raise ValueError(
                f"expected migration {expected_version:03d}, found {version:03d}"
            )
    return migrations


def _migration_script(version, path):
    sql = path.read_text(encoding="utf-8")
    return (
        "BEGIN IMMEDIATE;\n"
        f"{sql}\n"
        f"PRAGMA user_version = {version};\n"
        "COMMIT;"
    )


def _apply_migrations(conn):
    migrations = _migration_files()
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    latest_version = migrations[-1][0] if migrations else 0
    if current_version > latest_version:
        raise ValueError(
            f"database version {current_version} is newer than {latest_version}"
        )

    for version, path in migrations:
        if version <= current_version:
            continue
        try:
            conn.executescript(_migration_script(version, path))
        except sqlite3.Error:
            if conn.in_transaction:
                conn.rollback()
            raise
        current_version = version


def _print_schema():
    for version, path in _migration_files():
        print(_migration_script(version, path))


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
        (
            _format_time(dt, "%Y-%m-%d"),
            sleep_hours,
            sleep_score,
            deep_hours,
            light_hours,
            rem_hours,
            awake_hours,
        )
        for (dt, sleep_hours, sleep_score, deep_hours,
             light_hours, rem_hours, awake_hours) in fetch_sleep(args)
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

    if args.schema:
        _print_schema()
        return

    db_path = Path(args.db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    fit_args = _make_fit_args(args)
    with sqlite3.connect(db_path) as conn:
        _apply_migrations(conn)
        counts = {
            "steps": _import_steps(conn, fit_args),
            "pulse": _import_pulse(conn, fit_args),
            "sleep": _import_sleep(conn, fit_args),
            "stress": _import_stress(conn, fit_args),
        }

    print("Imported " + ", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
