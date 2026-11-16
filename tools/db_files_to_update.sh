#!/bin/sh
set -ue

# Help: loads FIT data to db from files newer than last point in db

last_update_date() {
    sqlite3 -readonly ~/fit.db "select date(max(time)) from point;"
}

SMARTWATCH_ROOT="$HOME/Smartwatch"


exec find "$SMARTWATCH_ROOT/Monitor/" "$SMARTWATCH_ROOT/Sleep/"  -type f -newermt "$(last_update_date)"
