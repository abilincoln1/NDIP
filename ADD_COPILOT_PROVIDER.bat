@echo off
echo Adding CopilotProvider to layout.tsx...

docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('aW1wb3J0IHR5cGUgeyBNZXRhZGF0YSB9IGZyb20gIm5leHQiOwppbXBvcnQgIi4vZ2xvYmFscy5jc3MiOwppbXBvcnQgIi4vZ2xvYmFscy1vdmVycmlkZS5jc3MiOwppbXBvcnQgU2lkZWJhciBmcm9tICJAL2NvbXBvbmVudHMvbGF5b3V0L1NpZGViYXIiOwppbXBv')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('cnQgQUlDb3BpbG90LCB7IENvcGlsb3RQcm92aWRlciB9IGZyb20gIkAvY29tcG9uZW50cy91aS9BSUNvcGlsb3QiOwoKZXhwb3J0IGNvbnN0IG1ldGFkYXRhOiBNZXRhZGF0YSA9IHsKICB0aXRsZTogIk5ESVAgfCBOYXRpb25hbCAmIERpYXNwb3JhIEludGVsbGln')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('ZW5jZSBQbGF0Zm9ybSIsCiAgZGVzY3JpcHRpb246ICJOYXRpb25hbCAmIERpYXNwb3JhIEludGVsbGlnZW5jZSBQbGF0Zm9ybSDigJQgVW5kZXJzdGFuZGluZyBOaWdlcmlhLiBVbmRlcnN0YW5kaW5nIHRoZSBEaWFzcG9yYS4gSW5mb3JtaW5nIExlYWRlcnNoaXAu')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('IiwKICBpY29uczogeyBpY29uOiAiL2ljb24uc3ZnIiB9LAp9OwoKZXhwb3J0IGRlZmF1bHQgZnVuY3Rpb24gUm9vdExheW91dCh7IGNoaWxkcmVuIH06IHsgY2hpbGRyZW46IFJlYWN0LlJlYWN0Tm9kZSB9KSB7CiAgcmV0dXJuICgKICAgIDxodG1sIGxhbmc9ImVu')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('Ij4KICAgICAgPGJvZHkgY2xhc3NOYW1lPSJmbGV4IGgtc2NyZWVuIG92ZXJmbG93LWhpZGRlbiI+CiAgICAgICAgPENvcGlsb3RQcm92aWRlcj4KICAgICAgICAgIDxTaWRlYmFyIC8+CiAgICAgICAgICA8bWFpbiBjbGFzc05hbWU9ImZsZXgtMSBvdmVyZmxvdy15')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('LWF1dG8gYmctc2xhdGUtOTUwIHAtNiBsZzpwLTgiPgogICAgICAgICAgICB7Y2hpbGRyZW59CiAgICAgICAgICA8L21haW4+CiAgICAgICAgICA8QUlDb3BpbG90IC8+CiAgICAgICAgPC9Db3BpbG90UHJvdmlkZXI+CiAgICAgIDwvYm9keT4KICAgIDwvaHRtbD4K')"
docker exec agora-backend-1 python -c "open('/tmp/layout_cp.b64','a').write('ICApOwp9Cg==')"
docker exec agora-backend-1 python -c "import base64;open('/tmp/layout_cp.tsx','wb').write(base64.b64decode(open('/tmp/layout_cp.b64').read()));print('Ready')"
docker cp agora-backend-1:/tmp/layout_cp.tsx frontend\src\app\layout.tsx
echo Updated Windows source
echo Verifying CopilotProvider export in AICopilot...
docker exec agora-frontend-1 node -e "const c=require('fs').readFileSync('/app/src/components/ui/AICopilot.tsx','utf8');console.log('CopilotProvider exported:',c.includes('export function CopilotProvider'))"

echo Rebuilding frontend with CopilotProvider in layout...
docker compose up --build frontend -d

echo Done. Now test the Copilot on Leadership Pack.
pause