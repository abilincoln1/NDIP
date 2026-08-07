content = open('/app/scheduler_v8.sh').read()
marker = 'echo "NDIP V8 Scheduler starting..."'
insert = '\npython /app/scheduler_v2.py &'
if 'scheduler_v2.py' in content:
    print('Already patched')
else:
    content = content.replace(marker, marker + insert)
    open('/app/scheduler_v8.sh', 'w').write(content)
    print('Patched OK')
print(open('/app/scheduler_v8.sh').read())
