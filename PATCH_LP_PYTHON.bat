@echo off
echo Patching LP page using Python (no node needed)...

docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('CnBhdGggPSAnL3RtcC9scF9vcmlnLnRzeCcKd2l0aCBvcGVuKHBhdGgpIGFzIGY6CiAgICBjID0gZi5yZWFkKCkKCmlmICd1c2VDb3BpbG90RGF0YScgaW4gYzoKICAgIHByaW50KCdhbHJlYWR5IHBhdGNoZWQnKQogICAgZXhpdCgwKQoKIyBBZGQgaW1wb3J0CmMg')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('PSBjLnJlcGxhY2UoCiAgICAnaW1wb3J0IGFwaSBmcm9tICJAL2xpYi9hcGkiOycsCiAgICAnaW1wb3J0IGFwaSBmcm9tICJAL2xpYi9hcGkiO1xuaW1wb3J0IHsgdXNlQ29waWxvdERhdGEgfSBmcm9tICJAL2NvbXBvbmVudHMvdWkvQUlDb3BpbG90IjsnCikKCiMg')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('QWRkIGhvb2sKYyA9IGMucmVwbGFjZSgKICAgICdjb25zdCBbYWN0aW9ucywgc2V0QWN0aW9uc10gPSB1c2VTdGF0ZTxhbnk+KG51bGwpOycsCiAgICAnY29uc3QgW2FjdGlvbnMsIHNldEFjdGlvbnNdID0gdXNlU3RhdGU8YW55PihudWxsKTtcbiAgY29uc3QgeyBz')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('ZXRQYWdlRGF0YSB9ID0gdXNlQ29waWxvdERhdGEoKTsnCikKCiMgQWRkIHNldFBhZ2VEYXRhIGFmdGVyIGRhdGEgbG9hZHMgLSB1c2Ugc3RyaW5nIGNvbmNhdCB0byBhdm9pZCBxdW90ZSBpc3N1ZXMKZmlsdGVyX2NyaXRpY2FsID0gIi5maWx0ZXIoKHg6IGFueSkg')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('PT4geC5sZXZlbCA9PT0gJ0NyaXRpY2FsJykubGVuZ3RoIgpmaWx0ZXJfd2FybmluZyA9ICIuZmlsdGVyKCh4OiBhbnkpID0+IHgubGV2ZWwgPT09ICdXYXJuaW5nJykubGVuZ3RoIgpzZXRwYWdlID0gKAogICAgIi50aGVuKHIgPT4geyBzZXREYXRhKHIuZGF0YSk7')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('IGlmIChyLmRhdGEpIHsgc2V0UGFnZURhdGEoeyIKICAgICIgbmFycmF0aXZlczogci5kYXRhLm5hcnJhdGl2ZV9hc3Nlc3NtZW50cyB8fCBbXSwiCiAgICAiIGVuZ2FnZW1lbnRfaW5kZXg6IHIuZGF0YS5lbmdhZ2VtZW50X2luZGV4LCIKICAgICIgc2VudGltZW50')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('X3Njb3JlOiByLmRhdGEuc2VudGltZW50X3Njb3JlLCIKICAgICIgY29uZmlkZW5jZTogci5kYXRhLmNvbmZpZGVuY2VfbGFiZWwsIgogICAgIiB3YXRjaGxpc3RfY3JpdGljYWxfY291bnQ6IChyLmRhdGEucmlza3MgfHwgW10pIiArIGZpbHRlcl9jcml0aWNhbCAr')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('ICIsIgogICAgIiB3YXRjaGxpc3RfaGlnaF9jb3VudDogKHIuZGF0YS5yaXNrcyB8fCBbXSkiICsgZmlsdGVyX3dhcm5pbmcgKyAiLCIKICAgICIgcmlza3M6IHIuZGF0YS5yaXNrcyB8fCBbXSwiCiAgICAiIHRvcF9vcHBvcnR1bml0aWVzOiByLmRhdGEub3Bwb3J0')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('dW5pdGllcyB8fCBbXSwiCiAgICAiIHNpZ25pZmljYW50X2NoYW5nZXM6IHIuZGF0YS5zaWduaWZpY2FudF9jaGFuZ2VzIHx8IFtdIgogICAgIiB9KTsgfSB9KSIKKQoKYyA9IGMucmVwbGFjZSgnLnRoZW4ociA9PiBzZXREYXRhKHIuZGF0YSkpJywgc2V0cGFnZSkK')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('CndpdGggb3BlbihwYXRoLCAndycpIGFzIGY6CiAgICBmLndyaXRlKGMpCgpwcmludCgncGF0Y2hlZCBPSycpCnByaW50KCd1c2VDb3BpbG90RGF0YSBpbiBmaWxlOicsICd1c2VDb3BpbG90RGF0YScgaW4gYykKcHJpbnQoJ3NldFBhZ2VEYXRhIGluIGZpbGU6Jywg')"
docker exec agora-backend-1 python -c "open('/tmp/lp_patch.py.b64','a').write('J3NldFBhZ2VEYXRhJyBpbiBjKQo=')"
docker exec agora-backend-1 python -c "import base64;open('/tmp/lp_patch.py','wb').write(base64.b64decode(open('/tmp/lp_patch.py.b64').read()));print('script ready')"
docker cp frontend\src\app\leadership-pack\page.tsx agora-backend-1:/tmp/lp_orig.tsx
docker exec agora-backend-1 python /tmp/lp_patch.py
docker cp agora-backend-1:/tmp/lp_orig.tsx frontend\src\app\leadership-pack\page.tsx
echo LP page updated in Windows source

echo Verifying...
docker exec agora-backend-1 python -c "c=open('/tmp/lp_orig.tsx').read();print('useCopilotData:', 'useCopilotData' in c, '| setPageData:', 'setPageData' in c)"

echo Forcing fresh build...
docker compose build --no-cache frontend
docker compose up -d frontend

echo Done. Open http://localhost:3000/leadership-pack
pause