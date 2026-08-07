@echo off
echo ============================================================
echo  NDIP Phase D2.5 - Seed Data and Test Accounts
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0

echo [1/3] Seeding Nigerian geography (37 states + 774 LGAs)...
docker cp "%SCRIPT_DIR%phase_d_00_geography_seed.sql" ndip-db-1:/tmp/phase_d_00_geography_seed.sql
docker exec ndip-db-1 psql -U agora_user -d agora_db -f /tmp/phase_d_00_geography_seed.sql
if %errorlevel% neq 0 (
    echo ERROR: Geography seed failed.
    pause & exit /b 1
)
echo    Geography seeded.
echo.

echo [2/3] Running D2.5 seed (chapter + test accounts + cohort)...
docker cp "%SCRIPT_DIR%seed_d25.sql" ndip-db-1:/tmp/seed_d25.sql
docker exec ndip-db-1 psql -U agora_user -d agora_db -f /tmp/seed_d25.sql
if %errorlevel% neq 0 (
    echo ERROR: D2.5 seed failed.
    pause & exit /b 1
)
echo    Seed complete.
echo.

echo [3/3] Verification summary...
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT 'States' as entity, COUNT(*)::text as count FROM ng_states UNION ALL SELECT 'LGAs', COUNT(*)::text FROM ng_lgas UNION ALL SELECT 'Chapters', COUNT(*)::text FROM chapters WHERE deleted_at IS NULL UNION ALL SELECT 'Test Accounts (active)', COUNT(*)::text FROM members WHERE is_active = TRUE UNION ALL SELECT 'Cohort Members (invited)', COUNT(*)::text FROM members WHERE is_active = FALSE UNION ALL SELECT 'Member Profiles', COUNT(*)::text FROM member_profiles UNION ALL SELECT 'Onboarding States', COUNT(*)::text FROM member_onboarding_state ORDER BY entity;"

echo.
echo ============================================================
echo  D2.5 Seed complete. Paste output above to Claude.
echo ============================================================
pause
