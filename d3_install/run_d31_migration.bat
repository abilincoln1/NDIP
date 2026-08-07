@echo off
echo ========================================
echo  NDIP D3.1 - Database Hardening Migration
echo ========================================

REM Copy migration into container
docker cp "%~dp0phase_d3_migration.sql" ndip-db-1:/tmp/phase_d3_migration.sql

REM Run migration
docker exec ndip-db-1 psql -U agora_user -d agora_db -f /tmp/phase_d3_migration.sql

echo.
echo ========================================
echo  Verifying table count after migration
echo ========================================
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "\dt" 2>&1 | find /c "table"

echo.
echo ========================================
echo  Confirming new D3 tables present
echo ========================================
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('audit_log','notifications','engagement_reports','ward_sponsorships','ward_executives','platform_projects','verification_submissions','diaspora_impact_scores','intelligence_nodes','intelligence_edges','member_onboarding_state','scheduler_job_log','media_assets','email_verification_tokens','password_reset_tokens','login_attempts') ORDER BY table_name;"

echo.
echo D3.1 migration complete. Paste the output above back to Claude.
pause
