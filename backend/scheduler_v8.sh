#!/bin/sh
# NDIP V8 — Scheduler entrypoint
# Runs daily ingest at 06:00 UTC then snapshot + materialisation immediately after
# Runs snapshot again at 23:59 UTC to capture end-of-day state

echo "NDIP V8 Scheduler starting..."

run_daily_cycle() {
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Starting daily ingest cycle..."
    cd /app
    python scripts/daily_ingest.py
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Ingest complete. Running materialisation..."
    python scripts/materialise_v8.py
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Materialisation complete. Taking snapshot..."
    python scripts/daily_snapshot.py
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Daily cycle complete."
}

run_eod_snapshot() {
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Running end-of-day snapshot..."
    cd /app
    python scripts/daily_snapshot.py
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] End-of-day snapshot complete."
}

while true; do
    HOUR=$(date -u '+%H')
    MIN=$(date -u '+%M')

    # 06:00 UTC — full daily cycle
    if [ "$HOUR" = "06" ] && [ "$MIN" = "00" ]; then
        run_daily_cycle
        sleep 61
    # 23:59 UTC — end of day snapshot
    elif [ "$HOUR" = "23" ] && [ "$MIN" = "59" ]; then
        run_eod_snapshot
        sleep 61
    else
        sleep 30
    fi
done
