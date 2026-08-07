@echo off
echo ============================================================
echo  NDIP Phase D5 - Founder Pilot Database Baseline
echo  Date: 2026-08-03
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0

REM ── Create D5 pilot baseline snapshot ──────────────────────────────────
echo [1/2] Creating NDIP_D5_PILOT_BASELINE database snapshot...
docker exec ndip-db-1 pg_dump -U agora_user -d agora_db -f /tmp/NDIP_D5_PILOT_BASELINE.sql
docker cp ndip-db-1:/tmp/NDIP_D5_PILOT_BASELINE.sql "%SCRIPT_DIR%NDIP_D5_PILOT_BASELINE.sql"
if exist "%SCRIPT_DIR%NDIP_D5_PILOT_BASELINE.sql" (
    echo Baseline created successfully at %SCRIPT_DIR%NDIP_D5_PILOT_BASELINE.sql
) else (
    echo WARNING: Baseline not found
)
echo.

REM ── Record baseline metadata (row counts, size) for the backup report ──
echo [2/2] Recording baseline metadata...
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT 'members' AS table_name, COUNT(*) FROM members UNION ALL SELECT 'chapters', COUNT(*) FROM chapters UNION ALL SELECT 'ng_states', COUNT(*) FROM ng_states UNION ALL SELECT 'ng_lgas', COUNT(*) FROM ng_lgas UNION ALL SELECT 'audit_log', COUNT(*) FROM audit_log;" > "%SCRIPT_DIR%NDIP_D5_PILOT_BASELINE_METADATA.txt"
for %%A in ("%SCRIPT_DIR%NDIP_D5_PILOT_BASELINE.sql") do echo File size: %%~zA bytes >> "%SCRIPT_DIR%NDIP_D5_PILOT_BASELINE_METADATA.txt"
echo Metadata written to %SCRIPT_DIR%NDIP_D5_PILOT_BASELINE_METADATA.txt
echo.

echo ============================================================
echo  D5 Baseline complete.
echo ============================================================
