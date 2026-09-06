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
end 0 "expected imported sqlite data"

begin "Test fit2sqlite batch args"
rm -f "$_db"
printf '%s\n' testdata/Monitor/* testdata/Sleep/* | ./fit2sqlite.py -b --db-path "$_db" >/dev/null
test "$(sqlite3 "$_db" "select count(*) from point;")" = "2718"
end 0 "expected imported sqlite data from stdin"
