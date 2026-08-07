@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo  NDIP Phase D.3 — Platform Readiness Installation
echo  Date: 2026-08-02
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0

REM ── Step 1: Run DB migration ────────────────────────────────────────────
echo [1/9] Running D3.1 database migration...
docker cp "%SCRIPT_DIR%phase_d3_migration.sql" ndip-db-1:/tmp/phase_d3_migration.sql
docker exec ndip-db-1 psql -U agora_user -d agora_db -f /tmp/phase_d3_migration.sql
if %errorlevel% neq 0 (
    echo ERROR: Migration failed. Aborting.
    pause & exit /b 1
)
echo    Migration complete.
echo.

REM ── Step 2: Create directory structure ────────────────────────────────
echo [2/9] Creating backend directory structure...
docker exec ndip-backend-1 mkdir -p /app/app/scheduler
docker exec ndip-backend-1 sh -c "touch /app/app/scheduler/__init__.py"
docker exec ndip-backend-1 mkdir -p /app/app/api/middleware
docker exec ndip-scheduler-1 mkdir -p /app/app/scheduler
docker exec ndip-scheduler-1 sh -c "touch /app/app/scheduler/__init__.py"
echo    Directories created.
echo.

REM ── Step 3: Deploy backend services ───────────────────────────────────
echo [3/9] Deploying D3.3 auth_service.py...
docker cp "%SCRIPT_DIR%auth_service.py" ndip-backend-1:/app/app/services/auth_service.py
docker cp "%SCRIPT_DIR%auth_service.py" ndip-scheduler-1:/app/app/services/auth_service.py

echo [3/9] Deploying D3.7 notification_service.py...
docker cp "%SCRIPT_DIR%notification_service.py" ndip-backend-1:/app/app/services/notification_service.py
docker cp "%SCRIPT_DIR%notification_service.py" ndip-scheduler-1:/app/app/services/notification_service.py

echo [3/9] Deploying D3.5 storage_service.py...
docker cp "%SCRIPT_DIR%storage_service.py" ndip-backend-1:/app/app/services/storage_service.py

echo [3/9] Deploying D3.6 scheduler jobs...
docker cp "%SCRIPT_DIR%scheduler_jobs.py" ndip-backend-1:/app/app/scheduler/d3_jobs.py
docker cp "%SCRIPT_DIR%scheduler_jobs.py" ndip-scheduler-1:/app/app/scheduler/d3_jobs.py

echo    Services deployed.
echo.

REM ── Step 4: Deploy API routes ─────────────────────────────────────────
echo [4/9] Deploying D3.2 API routes...
docker cp "%SCRIPT_DIR%auth_v2.py"       ndip-backend-1:/app/app/api/routes/auth_v2.py
docker cp "%SCRIPT_DIR%reports_v2.py"    ndip-backend-1:/app/app/api/routes/reports_v2.py
docker cp "%SCRIPT_DIR%platform_routes.py" ndip-backend-1:/app/app/api/routes/platform_routes.py
echo    API routes deployed.
echo.

REM ── Step 5: Deploy middleware ─────────────────────────────────────────
echo [5/9] Deploying D3.8/D3.9 middleware...
docker cp "%SCRIPT_DIR%observability.py" ndip-backend-1:/app/app/api/middleware/observability.py
docker cp "%SCRIPT_DIR%health_v2.py"     ndip-backend-1:/app/app/api/routes/health_v2.py
REM Ensure middleware __init__.py exists
docker exec ndip-backend-1 sh -c "test -f /app/app/api/middleware/__init__.py || touch /app/app/api/middleware/__init__.py"
echo    Middleware deployed.
echo.

REM ── Step 6: Deploy scheduler v2 ──────────────────────────────────────
echo [6/9] Deploying D3.6 scheduler_v2.py...
docker cp "%SCRIPT_DIR%scheduler_v2.py" ndip-scheduler-1:/app/scheduler_v2.py
echo    Scheduler deployed.
echo.

REM ── Step 7: Deploy frontend pages ────────────────────────────────────
echo [7/9] Deploying D3.10 onboarding page...
docker exec ndip-frontend-1 mkdir -p /app/src/app/onboarding
docker cp "%SCRIPT_DIR%onboarding_page.tsx" ndip-frontend-1:/app/src/app/onboarding/page.tsx

echo [7/9] Deploying D3.11 dashboard page...
docker exec ndip-frontend-1 mkdir -p /app/src/app/dashboard
docker cp "%SCRIPT_DIR%dashboard_page.tsx" ndip-frontend-1:/app/src/app/dashboard/page.tsx
echo    Frontend pages deployed.
echo.

REM ── Step 8: Patch main.py ─────────────────────────────────────────────
echo [8/9] Patching main.py to register D3 routers...
docker cp "%SCRIPT_DIR%main_new.py" ndip-backend-1:/app/app/main.py
echo    main.py patched.
echo.

REM ── Step 9: Restart backend ───────────────────────────────────────────
echo [9/9] Restarting backend container...
docker restart ndip-backend-1
timeout /t 8 /nobreak > nul

REM ── Verify backend health ────────────────────────────────────────────
echo.
echo Verifying backend health...
curl -s http://localhost:8000/health
echo.
echo Verifying readiness...
curl -s http://localhost:8000/readiness
echo.

REM ── Verify new routes registered ─────────────────────────────────────
echo.
echo Verifying D3 routes (checking OpenAPI)...
curl -s http://localhost:8000/openapi.json | python -c "import sys,json; d=json.load(sys.stdin); paths=[p for p in d['paths'] if '/api/v2/' in p]; print(f'D3 API routes registered: {len(paths)}'); [print(f'  {p}') for p in sorted(paths)]"

echo.
echo ============================================================
echo  D3 Installation complete.
echo  Paste full output above to Claude for verification.
echo ============================================================
pause
