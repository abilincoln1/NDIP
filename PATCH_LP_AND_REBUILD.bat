@echo off
echo Patching LP page in Windows source and rebuilding...

docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('CmNvbnN0IGZzID0gcmVxdWlyZSgnZnMnKTsKY29uc3QgcGF0aCA9IHByb2Nlc3MuYXJndlsxXTsKbGV0IGMgPSBmcy5yZWFkRmlsZVN5bmMocGF0aCwgJ3V0ZjgnKTsKCmlmIChjLmluY2x1ZGVzKCd1c2VDb3BpbG90RGF0YScpKSB7CiAgY29uc29sZS5sb2coJ2Fs')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('cmVhZHkgcGF0Y2hlZCcpOwogIHByb2Nlc3MuZXhpdCgwKTsKfQoKLy8gQWRkIGltcG9ydApjID0gYy5yZXBsYWNlKAogICdpbXBvcnQgYXBpIGZyb20gIkAvbGliL2FwaSI7JywKICAnaW1wb3J0IGFwaSBmcm9tICJAL2xpYi9hcGkiO1xuaW1wb3J0IHsgdXNlQ29w')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('aWxvdERhdGEgfSBmcm9tICJAL2NvbXBvbmVudHMvdWkvQUlDb3BpbG90IjsnCik7CgovLyBBZGQgaG9vayBpbnNpZGUgY29tcG9uZW50CmMgPSBjLnJlcGxhY2UoCiAgJ2NvbnN0IFthY3Rpb25zLCBzZXRBY3Rpb25zXSA9IHVzZVN0YXRlPGFueT4obnVsbCk7JywK')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('ICAnY29uc3QgW2FjdGlvbnMsIHNldEFjdGlvbnNdID0gdXNlU3RhdGU8YW55PihudWxsKTtcbiAgY29uc3QgeyBzZXRQYWdlRGF0YSB9ID0gdXNlQ29waWxvdERhdGEoKTsnCik7CgovLyBBZGQgc2V0UGFnZURhdGEgY2FsbCBhZnRlciBkYXRhIGxvYWRzCmMgPSBj')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('LnJlcGxhY2UoCiAgJy50aGVuKHIgPT4gc2V0RGF0YShyLmRhdGEpKScsCiAgYC50aGVuKHIgPT4geyBzZXREYXRhKHIuZGF0YSk7IGlmIChyLmRhdGEpIHsgc2V0UGFnZURhdGEoeyBuYXJyYXRpdmVzOiByLmRhdGEubmFycmF0aXZlX2Fzc2Vzc21lbnRzIHx8IFtd')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('LCBlbmdhZ2VtZW50X2luZGV4OiByLmRhdGEuZW5nYWdlbWVudF9pbmRleCwgc2VudGltZW50X3Njb3JlOiByLmRhdGEuc2VudGltZW50X3Njb3JlLCBjb25maWRlbmNlOiByLmRhdGEuY29uZmlkZW5jZV9sYWJlbCwgd2F0Y2hsaXN0X2NyaXRpY2FsX2NvdW50OiAo')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('ci5kYXRhLnJpc2tzIHx8IFtdKS5maWx0ZXIoKHg6IGFueSkgPT4geC5sZXZlbCA9PT0gJ0NyaXRpY2FsJykubGVuZ3RoLCB3YXRjaGxpc3RfaGlnaF9jb3VudDogKHIuZGF0YS5yaXNrcyB8fCBbXSkuZmlsdGVyKCh4OiBhbnkpID0+IHgubGV2ZWwgPT09ICdXYXJu')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('aW5nJykubGVuZ3RoLCByaXNrczogci5kYXRhLnJpc2tzIHx8IFtdLCB0b3Bfb3Bwb3J0dW5pdGllczogci5kYXRhLm9wcG9ydHVuaXRpZXMgfHwgW10sIHNpZ25pZmljYW50X2NoYW5nZXM6IHIuZGF0YS5zaWduaWZpY2FudF9jaGFuZ2VzIHx8IFtdIH0pOyB9IH0p')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.b64','a').write('YAopOwoKZnMud3JpdGVGaWxlU3luYyhwYXRoLCBjKTsKY29uc29sZS5sb2coJ3BhdGNoZWQ6ICcgKyBwYXRoKTsK')"
docker exec agora-backend-1 python -c "import base64;open('/tmp/lp_patch.js','wb').write(base64.b64decode(open('/tmp/lp_patch.b64').read()))"
echo Copying LP page to backend for patching...
docker cp frontend\src\app\leadership-pack\page.tsx agora-backend-1:/tmp/lp_orig.tsx
docker exec agora-backend-1 node /tmp/lp_patch.js /tmp/lp_orig.tsx
docker cp agora-backend-1:/tmp/lp_orig.tsx frontend\src\app\leadership-pack\page.tsx
echo LP page patched in Windows source

echo Verifying patch...
docker exec agora-backend-1 python -c "c=open('/tmp/lp_orig.tsx').read();print('useCopilotData:', 'useCopilotData' in c, '| setPageData:', 'setPageData' in c)"

echo Rebuilding frontend image with patched LP page...
docker compose up --build frontend -d

echo Done. Open http://localhost:3000/leadership-pack
echo Ask the Copilot: What changed since yesterday?
pause