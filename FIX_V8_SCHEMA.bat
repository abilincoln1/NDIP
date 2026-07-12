@echo off
echo ============================================================
echo  NDIP V8 — Schema Fix + Frontend Build
echo ============================================================
echo.
echo [1/4] Deploying corrected scripts...
call fix_daily_snapshot.py.bat
call fix_materialise_v8.py.bat
call fix_v8_migration_fix.py.bat
call fix_layout.tsx.bat
echo.
echo [2/4] Running migration fix...
docker exec agora-backend-1 python scripts/v8_migration_fix.py
echo.
echo [3/4] Running corrected materialisation...
docker exec agora-backend-1 python scripts/materialise_v8.py
echo.
echo [4/4] Running snapshot...
docker exec agora-backend-1 python scripts/daily_snapshot.py
echo.
echo [5/4] Rebuilding frontend...
docker exec agora-frontend-1 npm run build
docker restart agora-frontend-1
echo.
echo ============================================================
echo  Fix complete. Open http://localhost:3000
echo ============================================================
pause
