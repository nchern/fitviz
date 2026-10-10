#!/bin/sh
set -ue

. tests/lib.sh

_db=.fitviz-test.db
trap 'rm -f "$_db"; printf "\n"' EXIT

begin "Test fit2sqlite file args"
rm -f "$_db"
./fit2sqlite.py --db-path "$_db" testdata/Monitor/* testdata/Sleep/* >/dev/null
test "$(sqlite3 "$_db" "select count(*) from point;")" = "2718"
test "$(sqlite3 "$_db" "select time, resolution, pulse, activity_type, stress from point where time = '2025-10-12T00:02:00' and resolution = 'minute';")" = "2025-10-12T00:02:00|minute|58|0|1"
test "$(sqlite3 "$_db" "select user_version from pragma_user_version;")" = "2"
test "$(sqlite3 "$_db" "select time, sleep_hours, sleep_score, sleep_deep_hours, sleep_light_hours, sleep_rem_hours, sleep_awake_hours from point where time = '2025-10-15' and resolution = 'day';")" = "2025-10-15|6.45|87|1.72|3.11|1.63|0.0"
end 0 "expected imported sqlite data"

begin "Test fit2sqlite batch args"
rm -f "$_db"
printf '%s\n' testdata/Monitor/* testdata/Sleep/* | ./fit2sqlite.py -b --db-path "$_db" >/dev/null
test "$(sqlite3 "$_db" "select count(*) from point;")" = "2718"
end 0 "expected imported sqlite data from stdin"

begin "Test incremental database migrations"
rm -f "$_db"
sqlite3 "$_db" < db/001_create_point.sql
sqlite3 "$_db" "insert into point (time, resolution, sleep_hours) values ('2025-01-01', 'day', 7.5);"
./fit2sqlite.py --db-path "$_db" >/dev/null
./fit2sqlite.py --db-path "$_db" >/dev/null
test "$(sqlite3 "$_db" "select user_version from pragma_user_version;")" = "2"
test "$(sqlite3 "$_db" "select count(*) from pragma_table_info('point') where name in ('sleep_deep_hours', 'sleep_light_hours', 'sleep_rem_hours', 'sleep_awake_hours');")" = "4"
test "$(sqlite3 "$_db" "select time, sleep_hours from point;")" = "2025-01-01|7.5"
end 0 "expected ordered idempotent migrations"
