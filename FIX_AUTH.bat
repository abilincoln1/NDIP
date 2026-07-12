@echo off
docker exec agora-backend-1 python -c "open('/tmp/fix2.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/fix2.b64','a').write('CmNvbnRlbnQgPSBvcGVuKCcvYXBwL2FwcC9hcGkvcm91dGVzL2xlYXJuaW5nX3JvdXRlci5weScpLnJlYWQoKQpjb250ZW50ID0gY29udGVudC5yZXBsYWNlKCdmcm9tIGFwcC5hdXRoLmF1dGggaW1wb3J0IGdldF9jdXJyZW50X3VzZXIn')"
docker exec agora-backend-1 python -c "open('/tmp/fix2.b64','a').write('LCAnZnJvbSBhcHAuY29yZS5zZWN1cml0eSBpbXBvcnQgZ2V0X2N1cnJlbnRfdXNlcicpCm9wZW4oJy9hcHAvYXBwL2FwaS9yb3V0ZXMvbGVhcm5pbmdfcm91dGVyLnB5JywgJ3cnKS53cml0ZShjb250ZW50KQpwcmludCgnbGVhcm5pbmdf')"
docker exec agora-backend-1 python -c "open('/tmp/fix2.b64','a').write('cm91dGVyLnB5IGltcG9ydCBmaXhlZCcpCg==')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/fix2.b64').read()).decode())"
docker restart agora-backend-1
timeout /t 8 /nobreak > nul
docker exec agora-backend-1 python -c "import sys;sys.path.insert(0,"/app");from app.api.routes.learning_router import router;print("Learning router OK:",len(router.routes),"routes")"
pause