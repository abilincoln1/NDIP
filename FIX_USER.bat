@echo off
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','a').write('CmNvbnRlbnQgPSBvcGVuKCcvYXBwL2FwcC9hcGkvcm91dGVzL2xlYXJuaW5nX3JvdXRlci5weScpLnJlYWQoKQoKIyBGaXggYWxsIG9jY3VycmVuY2VzIG9mIGN1cnJlbnRfdXNlci5pZCB0byBoYW5kbGUgZGljdCBvciBvYmplY3QKY29u')"
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','a').write('dGVudCA9IGNvbnRlbnQucmVwbGFjZSgKICAgICd1c2VyX2lkID0gc3RyKGN1cnJlbnRfdXNlci5pZCknLAogICAgJ3VzZXJfaWQgPSBzdHIoY3VycmVudF91c2VyLmlkIGlmIGhhc2F0dHIoY3VycmVudF91c2VyLCAiaWQiKSBlbHNlIGN1')"
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','a').write('cnJlbnRfdXNlci5nZXQoImlkIikgb3IgY3VycmVudF91c2VyLmdldCgic3ViIiwgInVua25vd24iKSknCikKY29udGVudCA9IGNvbnRlbnQucmVwbGFjZSgKICAgICdkZWNpZGVkX2J5ICAgICAgICAgICAgICBVVUlEIE5PVCBOVUxMLCcs')"
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','a').write('CiAgICAnZGVjaWRlZF9ieSAgICAgICAgICAgICAgVVVJRCBOT1QgTlVMTCwnCikKCm9wZW4oJy9hcHAvYXBwL2FwaS9yb3V0ZXMvbGVhcm5pbmdfcm91dGVyLnB5JywgJ3cnKS53cml0ZShjb250ZW50KQpwcmludCgnRml4ZWQgY3VycmVu')"
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','a').write('dF91c2VyIHJlZmVyZW5jZXMnKQoKIyBWZXJpZnkKd2l0aCBvcGVuKCcvYXBwL2FwcC9hcGkvcm91dGVzL2xlYXJuaW5nX3JvdXRlci5weScpIGFzIGY6CiAgICBjID0gZi5yZWFkKCkKY291bnQgPSBjLmNvdW50KCdoYXNhdHRyKGN1cnJl')"
docker exec agora-backend-1 python -c "open('/tmp/fix3.b64','a').write('bnRfdXNlcicpCnByaW50KGYnRml4ZWQge2NvdW50fSBvY2N1cnJlbmNlcycpCg==')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/fix3.b64').read()).decode())"
docker restart agora-backend-1
timeout /t 6 /nobreak > nul
echo Backend restarted
pause