@echo off
docker exec agora-backend-1 python -c "open('/tmp/fx.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/fx.b64','a').write('CmNvbnRlbnQgPSBvcGVuKCcvYXBwL2FwcC9tYWluLnB5JykucmVhZCgpCmNvbnRlbnQgPSBjb250ZW50LnJlcGxhY2UoJ2Zyb20gYXBwLnJvdXRlcnMubGVhcm5pbmdfcm91dGVyIGltcG9ydCByb3V0ZXIgYXMgbGVhcm5pbmdfcm91dGVy')"
docker exec agora-backend-1 python -c "open('/tmp/fx.b64','a').write('JywgJ2Zyb20gYXBwLmFwaS5yb3V0ZXMubGVhcm5pbmdfcm91dGVyIGltcG9ydCByb3V0ZXIgYXMgbGVhcm5pbmdfcm91dGVyJykKb3BlbignL2FwcC9hcHAvbWFpbi5weScsICd3Jykud3JpdGUoY29udGVudCkKcHJpbnQoJ21haW4ucHkg')"
docker exec agora-backend-1 python -c "open('/tmp/fx.b64','a').write('Zml4ZWQnKQo=')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/fx.b64').read()).decode())"
docker restart agora-backend-1
timeout /t 8 /nobreak > nul
docker exec agora-backend-1 python -c "import sys;sys.path.insert(0,chr(47)+chr(97)+chr(112)+chr(112));from app.api.routes.learning_router import router;print(chr(79)+chr(75),len(router.routes),chr(114)+chr(111)+chr(117)+chr(116)+chr(101)+chr(115))"
pause