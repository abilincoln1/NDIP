# ============================================================
# NDIP Docker End-of-Day Procedure
# ============================================================

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " NDIP DOCKER END-OF-DAY PROCEDURE" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$NDIP = "C:\Projects\NDIP"
Set-Location $NDIP

# 1. Verify containers are running before we do anything
Write-Host "[1/7] Checking NDIP container state..." -ForegroundColor Yellow

$containers = docker compose ps --format json 2>$null
docker compose ps

# 2. Generate WhatsApp Intelligence Brief
Write-Host ""
Write-Host "[2/7] Generating WhatsApp Intelligence Brief..." -ForegroundColor Yellow

try {
    docker cp d3_install\whatsapp_brief.py ndip-backend-1:/tmp/whatsapp_brief.py 2>$null
    Write-Host ""
    Write-Host "--- COPY THIS INTO WHATSAPP ---" -ForegroundColor Cyan
    docker exec ndip-backend-1 python3 /tmp/whatsapp_brief.py
    Write-Host "--- END OF WHATSAPP BRIEF ---" -ForegroundColor Cyan
    Write-Host ""
}
catch {
    Write-Host "WhatsApp brief generation skipped (backend may be down)." -ForegroundColor Yellow
}

# 3. Save database baseline
Write-Host "[3/7] Saving database baseline..." -ForegroundColor Yellow

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = "d3_install\NDIP_EOD_BACKUP_$timestamp.sql"

docker exec ndip-db-1 pg_dump -U agora_user -d agora_db -f /tmp/ndip_eod_backup.sql

if ($LASTEXITCODE -eq 0) {
    docker cp ndip-db-1:/tmp/ndip_eod_backup.sql $backupFile
    Write-Host "Database backup saved: $backupFile" -ForegroundColor Green
} else {
    Write-Host "Database backup FAILED — proceeding with shutdown anyway." -ForegroundColor Red
}

# 4. Copy any modified backend files to Windows
Write-Host ""
Write-Host "[4/7] Syncing backend files to Windows..." -ForegroundColor Yellow

$filesToSync = @(
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/api/routes/auth_v3.py";         WindowsPath = "backend\app\api\routes\auth_v3.py" },
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/api/routes/activities_v3.py";    WindowsPath = "backend\app\api\routes\activities_v3.py" },
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/api/routes/projects_v3.py";      WindowsPath = "backend\app\api\routes\projects_v3.py" },
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/api/routes/donations_comms_v3.py"; WindowsPath = "backend\app\api\routes\donations_comms_v3.py" },
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/services/normalisation.py";      WindowsPath = "backend\app\services\normalisation.py" },
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/connectors/nigeria/__init__.py"; WindowsPath = "backend\app\connectors\nigeria\__init__.py" },
    @{ Container = "ndip-backend-1"; ContainerPath = "/app/app/health_check_retry.py";          WindowsPath = "backend\app\health_check_retry.py" },
    @{ Container = "ndip-frontend-1"; ContainerPath = "/app/src/lib/api.ts";                    WindowsPath = "frontend\src\lib\api.ts" },
    @{ Container = "ndip-frontend-1"; ContainerPath = "/app/src/app/login/page.tsx";            WindowsPath = "frontend\src\app\login\page.tsx" },
    @{ Container = "ndip-frontend-1"; ContainerPath = "/app/src/components/layout/Sidebar.tsx"; WindowsPath = "frontend\src\components\layout\Sidebar.tsx" },
    @{ Container = "ndip-frontend-1"; ContainerPath = "/app/src/app/activities/page.tsx";       WindowsPath = "frontend\src\app\activities\page.tsx" },
    @{ Container = "ndip-frontend-1"; ContainerPath = "/app/src/app/volunteers/page.tsx";       WindowsPath = "frontend\src\app\volunteers\page.tsx" },
    @{ Container = "ndip-frontend-1"; ContainerPath = "/app/src/app/projects/page.tsx";         WindowsPath = "frontend\src\app\projects\page.tsx" }
)

foreach ($file in $filesToSync) {
    docker cp "$($file.Container):$($file.ContainerPath)" $file.WindowsPath 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Synced: $($file.WindowsPath)" -ForegroundColor Green
    }
}

# 5. Record counts summary
Write-Host ""
Write-Host "[5/7] End-of-day record summary..." -ForegroundColor Yellow

docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT 'activities' as table_name, COUNT(*) as records FROM activities WHERE is_archived=FALSE UNION ALL SELECT 'volunteer_records', COUNT(*) FROM volunteer_records WHERE is_archived=FALSE UNION ALL SELECT 'projects', COUNT(*) FROM projects WHERE is_archived=FALSE UNION ALL SELECT 'donations', COUNT(*) FROM donations WHERE is_archived=FALSE UNION ALL SELECT 'communications', COUNT(*) FROM communications WHERE is_archived=FALSE UNION ALL SELECT 'normalised_posts', COUNT(*) FROM normalised_posts UNION ALL SELECT 'narrative_trends', COUNT(*) FROM narrative_trends ORDER BY table_name;"

# 6. Stop NDIP containers
Write-Host ""
Write-Host "[6/7] Stopping NDIP containers..." -ForegroundColor Yellow

docker compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host "NDIP containers stopped cleanly." -ForegroundColor Green
} else {
    Write-Host "Warning: containers may not have stopped cleanly." -ForegroundColor Yellow
}

# 7. Final confirmation
Write-Host ""
Write-Host "[7/7] End-of-day summary..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path $backupFile) {
    $size = (Get-Item $backupFile).Length / 1MB
    Write-Host "  Database backup: $backupFile ($([math]::Round($size,1)) MB)" -ForegroundColor Green
} else {
    Write-Host "  Database backup: NOT SAVED" -ForegroundColor Red
}

Write-Host "  Containers: stopped" -ForegroundColor Green
Write-Host "  Files synced to Windows: $($filesToSync.Count) files" -ForegroundColor Green
Write-Host ""
Write-Host "REMINDER: If you made changes today, run:" -ForegroundColor Yellow
Write-Host "  git add -A" -ForegroundColor White
Write-Host "  git commit -m 'EOD: [brief description]'" -ForegroundColor White
Write-Host "  git push origin main" -ForegroundColor White
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " NDIP END-OF-DAY COMPLETE" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
