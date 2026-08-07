@echo off
echo ============================================================
echo  NDIP Phase D4 - System Acceptance Testing
echo  Date: 2026-08-02
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0

REM ── Pre-SAT: Secret key rotation + config ─────────────────────────────
echo [PRE-SAT 1/4] Rotating SECRET_KEY...
docker cp "%SCRIPT_DIR%presat_setup.py" ndip-backend-1:/tmp/presat_setup.py
docker exec ndip-backend-1 python3 /tmp/presat_setup.py
echo.

echo [PRE-SAT 2/4] Restarting backend with new SECRET_KEY...
docker restart ndip-backend-1
timeout /t 10 /nobreak > nul

echo [PRE-SAT 3/4] Verifying backend health...
docker exec ndip-backend-1 python3 -c "from app.core.config import get_settings; s=get_settings(); key_ok = s.secret_key != 'Agora-RTIFN-Observatory-2024-SecureKey-XYZ' and len(s.secret_key) >= 32; print('SECRET_KEY rotated:', key_ok); print('Key prefix:', s.secret_key[:12]+'...')"
echo.

echo [PRE-SAT 4/4] Creating D25 baseline backup...
docker exec ndip-db-1 pg_dump -U agora_user -d agora_db -f /tmp/NDIP_D25_BASELINE.sql
docker cp ndip-db-1:/tmp/NDIP_D25_BASELINE.sql "%SCRIPT_DIR%NDIP_D25_BASELINE.sql"
echo Baseline created at: %SCRIPT_DIR%NDIP_D25_BASELINE.sql
echo.

REM ── Install httpx in backend container (needed by SAT runner) ──────────
echo Installing test dependencies...
docker exec ndip-backend-1 pip install httpx --quiet --break-system-packages
echo.

REM ── SAT Test Execution ─────────────────────────────────────────────────
echo ============================================================
echo  EXECUTING SAT TEST SUITE (13 Test Areas)
echo ============================================================
docker cp "%SCRIPT_DIR%sat_runner.py" ndip-backend-1:/tmp/sat_runner.py
docker exec ndip-backend-1 python3 /tmp/sat_runner.py
echo.

REM ── Retrieve results ───────────────────────────────────────────────────
echo Retrieving results...
docker cp ndip-backend-1:/tmp/sat_results.json "%SCRIPT_DIR%sat_results.json" 2>nul
if exist "%SCRIPT_DIR%sat_results.json" (
    echo SAT results saved: %SCRIPT_DIR%sat_results.json
)

REM ── Post-SAT verification ──────────────────────────────────────────────
echo.
echo ============================================================
echo  POST-SAT DATABASE STATE
echo ============================================================
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT 'audit_log entries' as metric, COUNT(*)::text as value FROM audit_log UNION ALL SELECT 'scheduler jobs run', COUNT(*)::text FROM scheduler_job_log UNION ALL SELECT 'notifications', COUNT(*)::text FROM notifications UNION ALL SELECT 'reports created', COUNT(*)::text FROM engagement_reports UNION ALL SELECT 'projects created', COUNT(*)::text FROM platform_projects UNION ALL SELECT 'sponsorships', COUNT(*)::text FROM ward_sponsorships UNION ALL SELECT 'verifications', COUNT(*)::text FROM verification_submissions UNION ALL SELECT 'impact scores', COUNT(*)::text FROM diaspora_impact_scores ORDER BY metric;"

echo.
echo ============================================================
echo  D4 SAT execution complete.
echo  Copy FULL output above and paste to Claude.
echo ============================================================
pause
