# NDIP Daily Ingest Health Check
# Run from C:\Projects\NDIP
# Exit 0 = all clear, 1 = hard failure, 2 = warnings only

$DB_USER = "agora_user"
$DB_NAME = "agora_db"
$TODAY   = (Get-Date).ToString("yyyy-MM-dd")
$WARN    = 0
$FAIL    = 0

function q($sql) {
    $r = docker exec ndip-db-1 psql -U $DB_USER -d $DB_NAME -t -c $sql 2>&1
    return ($r | Out-String).Trim()
}
function OK($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }
function WARN($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow; $script:WARN++ }
function FAIL($m) { Write-Host "[FAIL] $m" -ForegroundColor Red;    $script:FAIL++ }
function INFO($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }

INFO "NDIP Ingest Health Check -- $TODAY"
INFO "------------------------------------"

# Preflight: bail immediately if the DB container is not running
$dbRunning = docker inspect --format="{{.State.Running}}" ndip-db-1 2>$null
if ($dbRunning -ne "true") {
    FAIL "Stack is not running. Start it first: docker compose up -d"
    exit 1
}

$raw       = q "SELECT COUNT(*) FROM social_posts;"
$norm      = q "SELECT COUNT(*) FROM normalised_posts;"

INFO "Total raw posts      : $raw"
INFO "Total normalised     : $norm"

if ([int]$raw -eq 0)  { FAIL "social_posts is empty" }
if ([int]$norm -eq 0) { FAIL "normalised_posts is empty" }

$today_raw = q "SELECT COUNT(*) FROM social_posts WHERE fetched_at::date = '$TODAY';"
INFO "Posts ingested today : $today_raw"
if ([int]$today_raw -eq 0) { WARN "No posts ingested today" }

$pending   = q "SELECT COUNT(*) FROM social_posts sp WHERE NOT EXISTS (SELECT 1 FROM normalised_posts np WHERE np.source_post_id = sp.id);"
INFO "Pending normalisation: $pending"
if ([int]$pending -gt 0) { WARN "$pending posts not yet normalised" }

$nulls     = q "SELECT COUNT(*) FROM normalised_posts WHERE source_post_id IS NULL;"
INFO "NULL source_post_ids : $nulls"
if ([int]$nulls -gt 0) { WARN "$nulls normalised_posts with NULL source_post_id" }

$logs = q "SELECT platform, status, records_fetched, checked_at FROM connector_health_logs ORDER BY checked_at DESC LIMIT 10;"
INFO "Recent connector health:"
$logs -split "`n" | ForEach-Object { INFO "  $_" }

try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    OK "Backend /health: $($health.StatusCode)"
} catch {
    WARN "Backend /health unreachable: $($_.Exception.Message)"
}

$sched = docker inspect --format="{{.State.Running}}" ndip-scheduler-1 2>$null
if ($sched -eq "true") { OK "Scheduler container running" }
else                    { FAIL "Scheduler container not running: $sched" }

$lang = q "SELECT character_maximum_length FROM information_schema.columns WHERE table_name='social_posts' AND column_name='language';"
INFO "social_posts.language type: VARCHAR($lang)"
if ([int]$lang -lt 50) { WARN "Language column may still be narrow: $lang" }
else                    { OK  "Language column is VARCHAR($lang) -- OK" }

INFO "------------------------------------"
if ($FAIL -gt 0) {
    Write-Host "[FAIL] Health check FAILED ($FAIL hard failures, $WARN warnings)" -ForegroundColor Red
    exit 1
} elseif ($WARN -gt 0) {
    Write-Host "[WARN] Health check passed with $WARN warning(s)" -ForegroundColor Yellow
    exit 2
} else {
    Write-Host "[OK]   All checks passed" -ForegroundColor Green
    exit 0
}
