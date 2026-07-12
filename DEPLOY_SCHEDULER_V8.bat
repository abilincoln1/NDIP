@echo off
echo Deploying V8 scheduler (adds snapshot after ingest)...

docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('IyEvYmluL3NoCiMgTkRJUCBWOCDigJQgU2NoZWR1bGVyIGVudHJ5cG9pbnQKIyBSdW5zIGRhaWx5IGluZ2VzdCBhdCAwNjowMCBVVEMgdGhlbiBzbmFwc2hvdCArIG1hdGVyaWFsaXNhdGlvbiBpbW1lZGlhdGVseSBhZnRlcgojIFJ1bnMgc25hcHNob3QgYWdhaW4g')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('YXQgMjM6NTkgVVRDIHRvIGNhcHR1cmUgZW5kLW9mLWRheSBzdGF0ZQoKZWNobyAiTkRJUCBWOCBTY2hlZHVsZXIgc3RhcnRpbmcuLi4iCgpydW5fZGFpbHlfY3ljbGUoKSB7CiAgICBlY2hvICJbJChkYXRlIC11ICcrJVktJW0tJWQgJUg6JU0gVVRDJyldIFN0YXJ0')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('aW5nIGRhaWx5IGluZ2VzdCBjeWNsZS4uLiIKICAgIGNkIC9hcHAKICAgIHB5dGhvbiBzY3JpcHRzL2RhaWx5X2luZ2VzdC5weQogICAgZWNobyAiWyQoZGF0ZSAtdSAnKyVZLSVtLSVkICVIOiVNIFVUQycpXSBJbmdlc3QgY29tcGxldGUuIFJ1bm5pbmcgbWF0ZXJp')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('YWxpc2F0aW9uLi4uIgogICAgcHl0aG9uIHNjcmlwdHMvbWF0ZXJpYWxpc2VfdjgucHkKICAgIGVjaG8gIlskKGRhdGUgLXUgJyslWS0lbS0lZCAlSDolTSBVVEMnKV0gTWF0ZXJpYWxpc2F0aW9uIGNvbXBsZXRlLiBUYWtpbmcgc25hcHNob3QuLi4iCiAgICBweXRo')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('b24gc2NyaXB0cy9kYWlseV9zbmFwc2hvdC5weQogICAgZWNobyAiWyQoZGF0ZSAtdSAnKyVZLSVtLSVkICVIOiVNIFVUQycpXSBEYWlseSBjeWNsZSBjb21wbGV0ZS4iCn0KCnJ1bl9lb2Rfc25hcHNob3QoKSB7CiAgICBlY2hvICJbJChkYXRlIC11ICcrJVktJW0t')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('JWQgJUg6JU0gVVRDJyldIFJ1bm5pbmcgZW5kLW9mLWRheSBzbmFwc2hvdC4uLiIKICAgIGNkIC9hcHAKICAgIHB5dGhvbiBzY3JpcHRzL2RhaWx5X3NuYXBzaG90LnB5CiAgICBlY2hvICJbJChkYXRlIC11ICcrJVktJW0tJWQgJUg6JU0gVVRDJyldIEVuZC1vZi1k')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('YXkgc25hcHNob3QgY29tcGxldGUuIgp9Cgp3aGlsZSB0cnVlOyBkbwogICAgSE9VUj0kKGRhdGUgLXUgJyslSCcpCiAgICBNSU49JChkYXRlIC11ICcrJU0nKQoKICAgICMgMDY6MDAgVVRDIOKAlCBmdWxsIGRhaWx5IGN5Y2xlCiAgICBpZiBbICIkSE9VUiIgPSAi')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('MDYiIF0gJiYgWyAiJE1JTiIgPSAiMDAiIF07IHRoZW4KICAgICAgICBydW5fZGFpbHlfY3ljbGUKICAgICAgICBzbGVlcCA2MQogICAgIyAyMzo1OSBVVEMg4oCUIGVuZCBvZiBkYXkgc25hcHNob3QKICAgIGVsaWYgWyAiJEhPVVIiID0gIjIzIiBdICYmIFsgIiRN')"
docker exec agora-backend-1 python -c "open('/tmp/sched_b64.txt','a').write('SU4iID0gIjU5IiBdOyB0aGVuCiAgICAgICAgcnVuX2VvZF9zbmFwc2hvdAogICAgICAgIHNsZWVwIDYxCiAgICBlbHNlCiAgICAgICAgc2xlZXAgMzAKICAgIGZpCmRvbmUK')"
docker exec agora-backend-1 python -c "import base64;open('/tmp/scheduler_v8.sh','wb').write(base64.b64decode(open('/tmp/sched_b64.txt').read()));print('Ready')"
docker cp agora-backend-1:/tmp/scheduler_v8.sh scheduler_v8.sh
echo Copied to Windows folder
docker cp scheduler_v8.sh agora-scheduler-1:/app/scheduler_v8.sh
docker exec agora-scheduler-1 chmod +x /app/scheduler_v8.sh
echo Deployed to scheduler container
echo Current scheduler process:
docker exec agora-scheduler-1 ps aux

echo.
echo Scheduler V8 deployed.
echo The new script adds materialise_v8.py and daily_snapshot.py after each ingest.
echo To activate: update docker-compose.yml scheduler command to: sh /app/scheduler_v8.sh
echo Then run: docker compose up -d scheduler
pause