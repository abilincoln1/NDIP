@echo off
echo ============================================================
echo  NDIP Phase D4 - System Acceptance Testing (Fixed)
echo  Date: 2026-08-02
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0

REM ── PRE-SAT 1: Rotate SECRET_KEY via Docker env override ──────────────
echo [PRE-SAT 1/5] Rotating SECRET_KEY...
REM Generate a secure key inside the container and write it to .env
docker exec ndip-backend-1 python3 -c "import secrets,re; key=secrets.token_hex(32); content=open('/app/.env').read(); new=re.sub(r'SECRET_KEY=.*', f'SECRET_KEY={key}', content); open('/app/.env','w').write(new); print(f'NEW KEY: {key[:16]}...')"
echo.

REM ── PRE-SAT 2: Restart backend to apply new key ────────────────────────
echo [PRE-SAT 2/5] Restarting backend with new key...
docker restart ndip-backend-1
timeout /t 12 /nobreak > nul

REM ── PRE-SAT 3: Confirm new key active ─────────────────────────────────
echo [PRE-SAT 3/5] Verifying new key active...
docker exec ndip-backend-1 python3 -c "import os; from dotenv import load_dotenv; load_dotenv('/app/.env',override=True); key=os.environ.get('SECRET_KEY',''); print('Key rotated:', key != 'Agora-RTIFN-Observatory-2024-SecureKey-XYZ'); print('Key length:', len(key)); print('Key prefix:', key[:16]+'...')"
echo.

REM ── PRE-SAT 4: Verify backend responding ─────────────────────────────
echo [PRE-SAT 4/5] Verifying backend health...
Invoke-RestMethod -Uri http://localhost:8000/health
echo.

REM ── PRE-SAT 5: Create DB baseline ─────────────────────────────────────
echo [PRE-SAT 5/5] Creating NDIP_D25_BASELINE database snapshot...
docker exec ndip-db-1 pg_dump -U agora_user -d agora_db -f /tmp/NDIP_D25_BASELINE.sql
docker cp ndip-db-1:/tmp/NDIP_D25_BASELINE.sql "%SCRIPT_DIR%NDIP_D25_BASELINE.sql"
if exist "%SCRIPT_DIR%NDIP_D25_BASELINE.sql" (
    echo Baseline created successfully
) else (
    echo WARNING: Baseline not found
)
echo.

REM ── SAT: Install httpx on Windows if needed ────────────────────────────
echo Installing test dependency (httpx)...
pip install httpx -q 2>nul || python -m pip install httpx -q
echo.

REM ── SAT: Run test suite from host ─────────────────────────────────────
echo ============================================================
echo  EXECUTING SAT TEST SUITE (13 Areas, ~85 tests)
echo ============================================================
echo.
python "%SCRIPT_DIR%sat_host_runner.py"
echo.

REM ── POST-SAT: DB state ────────────────────────────────────────────────
echo ============================================================
echo  POST-SAT DATABASE STATE
echo ============================================================
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT metric, value FROM (SELECT 'audit_log entries' as metric, COUNT(*)::text as value FROM audit_log UNION ALL SELECT 'reports created', COUNT(*)::text FROM engagement_reports UNION ALL SELECT 'projects created', COUNT(*)::text FROM platform_projects UNION ALL SELECT 'sponsorships', COUNT(*)::text FROM ward_sponsorships UNION ALL SELECT 'verifications', COUNT(*)::text FROM verification_submissions UNION ALL SELECT 'impact scores', COUNT(*)::text FROM diaspora_impact_scores UNION ALL SELECT 'scheduler jobs', COUNT(*)::text FROM scheduler_job_log UNION ALL SELECT 'notifications', COUNT(*)::text FROM notifications) t ORDER BY metric;"

echo.
echo ============================================================
echo  SAT Complete. Paste ALL output above to Claude.
echo ============================================================
pause
