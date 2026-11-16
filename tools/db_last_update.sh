#!/bin/sh
set -ue

# Help: returns last uploaded point date


exec sqlite3 -readonly ~/fit.db "select date(max(time)) from point;"
