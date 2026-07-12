@echo off
echo Patching main.py to register V7 routes...
docker exec agora-backend-1 python -c "f=open('/app/app/main.py','r');c=f.read();f.close();c=c.replace('from app.api.routes import (','from app.api.routes import copilot as copilot_router, onboarding as onboarding_router
from app.api.routes import (') if 'copilot_router' not in c else c;c=c.replace('app.include_router(content_generation.router)','app.include_router(content_generation.router)
app.include_router(copilot_router.router)
app.include_router(onboarding_router.router)') if 'copilot_router.router' not in c else c;open('/app/app/main.py','w').write(c);print('main.py patched')"
echo main.py patch done
