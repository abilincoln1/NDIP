@echo off
echo Full fix: pydantic + LP pagedata + rebuild...

echo Patching pydantic v1 typing.py...
docker exec agora-backend-1 python -c "f=open('/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py');c=f.read();f.close();old='return cast(Any, type_)._evaluate(globalns, localns, set())';new='try:\n        return cast(Any, type_)._evaluate(globalns, localns, frozenset())\n    except TypeError:\n        return cast(Any, type_)._evaluate(globalns, localns, set())';c=c.replace(old,new) if 'frozenset' not in c else c;open('/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py','w').write(c);print('patched' if 'frozenset' in c else 'pattern not found')"

echo Verifying spaCy...
docker exec agora-backend-1 python -c "import spacy;nlp=spacy.load('en_core_web_sm');print('spaCy OK')" 2>nul || echo spaCy needs restart - will verify after

echo Applying LP pagedata wiring to Windows source...
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('CmNvbnN0IGZzID0gcmVxdWlyZSgnZnMnKTsKY29uc3QgcGF0aCA9ICcvYXBwL3NyYy9hcHAvbGVhZGVyc2hpcC1wYWNrL3BhZ2UudHN4JzsKbGV0IGMgPSBmcy5yZWFkRmlsZVN5bmMocGF0aCwgJ3V0ZjgnKTsKCi8vIEFkZCB1c2VDb3BpbG90RGF0YSBpbXBvcnQK')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('aWYgKCFjLmluY2x1ZGVzKCd1c2VDb3BpbG90RGF0YScpKSB7CiAgYyA9IGMucmVwbGFjZSgnaW1wb3J0IGFwaSBmcm9tICJAL2xpYi9hcGkiOycsICdpbXBvcnQgYXBpIGZyb20gIkAvbGliL2FwaSI7XG5pbXBvcnQgeyB1c2VDb3BpbG90RGF0YSB9IGZyb20gIkAv')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('Y29tcG9uZW50cy91aS9BSUNvcGlsb3QiOycpOwp9CgovLyBBZGQgaG9vawppZiAoIWMuaW5jbHVkZXMoJ3NldFBhZ2VEYXRhJykpIHsKICBjID0gYy5yZXBsYWNlKCdjb25zdCBbYWN0aW9ucywgc2V0QWN0aW9uc10gPSB1c2VTdGF0ZTxhbnk+KG51bGwpOycsICdj')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('b25zdCBbYWN0aW9ucywgc2V0QWN0aW9uc10gPSB1c2VTdGF0ZTxhbnk+KG51bGwpO1xuICBjb25zdCB7IHNldFBhZ2VEYXRhIH0gPSB1c2VDb3BpbG90RGF0YSgpOycpOwp9CgovLyBBZGQgc2V0UGFnZURhdGEgY2FsbCB3aXRoIGNvcnJlY3QgdHlwZXMKaWYgKCFj')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('LmluY2x1ZGVzKCdzZXRQYWdlRGF0YSgnKSkgewogIGMgPSBjLnJlcGxhY2UoCiAgICAnLnRoZW4ociA9PiBzZXREYXRhKHIuZGF0YSkpJywKICAgIGAudGhlbihyID0+IHsgc2V0RGF0YShyLmRhdGEpOyBpZiAoci5kYXRhKSB7IHNldFBhZ2VEYXRhKHsgbmFycmF0')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('aXZlczogci5kYXRhLm5hcnJhdGl2ZV9hc3Nlc3NtZW50cyB8fCBbXSwgZW5nYWdlbWVudF9pbmRleDogci5kYXRhLmVuZ2FnZW1lbnRfaW5kZXgsIHNlbnRpbWVudF9zY29yZTogci5kYXRhLnNlbnRpbWVudF9zY29yZSwgY29uZmlkZW5jZTogci5kYXRhLmNvbmZp')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('ZGVuY2VfbGFiZWwsIHdhdGNobGlzdF9jcml0aWNhbF9jb3VudDogKHIuZGF0YS5yaXNrcyB8fCBbXSkuZmlsdGVyKCh4OiBhbnkpID0+IHgubGV2ZWwgPT09ICdDcml0aWNhbCcpLmxlbmd0aCwgd2F0Y2hsaXN0X2hpZ2hfY291bnQ6IChyLmRhdGEucmlza3MgfHwg')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('W10pLmZpbHRlcigoeDogYW55KSA9PiB4LmxldmVsID09PSAnV2FybmluZycpLmxlbmd0aCwgcmlza3M6IHIuZGF0YS5yaXNrcyB8fCBbXSwgdG9wX29wcG9ydHVuaXRpZXM6IHIuZGF0YS5vcHBvcnR1bml0aWVzIHx8IFtdLCBzaWduaWZpY2FudF9jaGFuZ2VzOiBy')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('LmRhdGEuc2lnbmlmaWNhbnRfY2hhbmdlcyB8fCBbXSB9KTsgfSB9KWAKICApOwp9CgovLyBGaXggYW55IGV4aXN0aW5nIGluY29ycmVjdCBmaWx0ZXIgdHlwZXMKYyA9IGMucmVwbGFjZSgvXC5maWx0ZXJcKFwoeFwpID0+IHhcLmxldmVsL2csICcuZmlsdGVyKCh4')"
docker exec agora-backend-1 python -c "open('/tmp/tsfix_node.b64','a').write('OiBhbnkpID0+IHgubGV2ZWwnKTsKCmZzLndyaXRlRmlsZVN5bmMocGF0aCwgYyk7CmNvbnNvbGUubG9nKCdMUCBwYWdlIHBhdGNoZWQnKTsK')"
docker exec agora-backend-1 python -c "import base64;open('/tmp/tsfix.js','wb').write(base64.b64decode(open('/tmp/tsfix_node.b64').read()));print('script ready')"
docker cp agora-backend-1:/tmp/tsfix.js tsfix.js
docker cp frontend\src\app\leadership-pack\page.tsx agora-backend-1:/tmp/lp_page.tsx
docker exec agora-backend-1 python -c "import subprocess;open('/tmp/tsfix2.js','w').write(open('/tmp/tsfix.js').read().replace('/app/src/app/leadership-pack/page.tsx','/tmp/lp_page.tsx'))"
docker exec agora-backend-1 node /tmp/tsfix2.js
docker cp agora-backend-1:/tmp/lp_page.tsx frontend\src\app\leadership-pack\page.tsx
echo LP page updated in Windows source

echo Rebuilding frontend image...
docker compose up --build frontend -d

echo Done!
echo Open http://localhost:3000/leadership-pack and test the Copilot
pause