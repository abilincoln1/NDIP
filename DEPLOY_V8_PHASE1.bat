@echo off
echo ============================================================
echo  NDIP V8 Phase 1 — Full Deployment
echo  Security Hardening + Performance Fixes + Copilot Evolution
echo ============================================================
echo.

echo [1/8] Deploying backend files...
call deploy_be_v8_migration.py.bat
call deploy_be_copilot_v8.py.bat
call deploy_be_audit_middleware.py.bat
call deploy_be_rbac.py.bat
call deploy_be_daily_snapshot.py.bat
call deploy_be_materialise_v8.py.bat
call deploy_be_fix_spacy.py.bat
echo.

echo [2/8] Patching main.py (audit middleware + v8 copilot route)...
docker exec agora-backend-1 python -c "f=open('/app/app/main.py','r');c=f.read();f.close();already='AuditLogMiddleware' in c;print('main.py already patched' if already else 'needs patching');exit(0 if already else 1)"
if %ERRORLEVEL% NEQ 0 (
    docker exec agora-backend-1 python -c "f=open('/app/app/main.py','r');c=f.read();f.close();c=c.replace('from app.api.routes import copilot as copilot_router','from app.api.routes import copilot_v8 as copilot_router') if 'copilot_v8' not in c else c;c=c.replace('app = FastAPI(','from app.api.middleware.audit import AuditLogMiddleware\napp = FastAPI(') if 'AuditLogMiddleware' not in c else c;c=c.replace('app.add_middleware(CORSMiddleware','app.add_middleware(AuditLogMiddleware)\napp.add_middleware(CORSMiddleware') if 'AuditLogMiddleware' not in c or 'add_middleware(AuditLogMiddleware)' not in c else c;open('/app/app/main.py','w').write(c);print('main.py patched')"
    echo main.py patch applied
) else (
    echo main.py already up to date
)
echo.

echo [3/8] Patching database.py (connection pool)...
docker exec agora-backend-1 python -c "f=open('/app/app/db/database.py','r');c=f.read();f.close();already='pool_size=10' in c;print('pool config already present' if already else 'patching pool config');c=c.replace('create_engine(DATABASE_URL','create_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=300') if not already else c;open('/app/app/db/database.py','w').write(c);print('database.py updated')"
echo.

echo [4/8] Running V8 database migration...
docker exec agora-backend-1 python scripts/v8_migration.py
echo.

echo [5/8] Running spaCy compatibility fix...
docker exec agora-backend-1 python scripts/fix_spacy.py
echo.

echo [6/8] Restarting backend...
docker restart agora-backend-1
timeout /t 8 /nobreak >nul
echo.

echo [7/8] Running performance materialisation...
docker exec agora-backend-1 python scripts/materialise_v8.py
echo.

echo [8/8] Taking initial daily snapshot...
docker exec agora-backend-1 python scripts/daily_snapshot.py
echo.

echo [9/8] Deploying V8 frontend components...
call deploy_fe_AICopilot.tsx.bat
call deploy_fe_layout.tsx.bat
echo.

echo [10/8] Rebuilding frontend...
docker exec agora-frontend-1 npm run build
docker restart agora-frontend-1
echo.

echo [11/8] Verifying V8 deployment...
docker exec agora-backend-1 python -c "import urllib.request,json;d=json.loads(urllib.request.urlopen('http://localhost:8000/openapi.json').read());routes=[p for p in d['paths'] if any(x in p for x in ['copilot','onboarding','audit'])];print('V8 routes live:',len(routes));[print(' ',r) for r in sorted(routes)]"
echo.

echo ============================================================
echo  V8 Phase 1 Deployment Complete
echo ============================================================
echo.
echo What was deployed:
echo   EB-002  Async Anthropic API call (no more worker blocking)
echo   EB-003  UNIQUE constraint on opportunity_alignment_scores
echo   EB-004  RBAC tables (roles, permissions, user_roles)
echo   EB-005  Audit log table + middleware
echo   EB-006  spaCy compatibility fix
echo   EB-007  Role resolved from auth session (not hardcoded)
echo   EB-008  Opportunity assessments moved to ingest pipeline
echo   EB-009  Metrics summary pre-materialised
echo   EB-010  Situation room pre-materialised
echo   EB-011  Daily snapshot worker (enables today vs yesterday)
echo   EB-012  Copilot pageData context wiring
echo   EB-015  Conversation history in Copilot
echo   EB-017  DB connection pool configured
echo.
echo Next: Open http://localhost:3000 and test the Copilot.
echo       Ask "What changed since yesterday?" — it now has data.
echo.
pause
