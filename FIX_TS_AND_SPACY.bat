@echo off
echo Applying TS fix and spaCy patch...

echo Fixing TypeScript error in Leadership Pack...
docker exec agora-frontend-1 node -e "require('fs').writeFileSync('/tmp/tsfix.b64','')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/tsfix.b64','CmNvbnN0IGZzID0gcmVxdWlyZSgnZnMnKTsKbGV0IGMgPSBmcy5yZWFkRmlsZVN5bmMoJy9hcHAvc3JjL2FwcC9sZWFkZXJzaGlwLXBhY2svcGFnZS50c3gnLCAndXRmOCcpOwpjID0gYy5yZXBsYWNlKAogICIuZmlsdGVyKCh4KSA9PiB4LmxldmVsID09PSAnQ3Jp')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/tsfix.b64','dGljYWwnKS5sZW5ndGgsIHdhdGNobGlzdF9oaWdoX2NvdW50OiAoci5kYXRhLnJpc2tzIHx8IFtdKS5maWx0ZXIoKHgpID0+IHgubGV2ZWwgPT09ICdXYXJuaW5nJykiLAogICIuZmlsdGVyKCh4OiBhbnkpID0+IHgubGV2ZWwgPT09ICdDcml0aWNhbCcpLmxlbmd0')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/tsfix.b64','aCwgd2F0Y2hsaXN0X2hpZ2hfY291bnQ6IChyLmRhdGEucmlza3MgfHwgW10pLmZpbHRlcigoeDogYW55KSA9PiB4LmxldmVsID09PSAnV2FybmluZycpIgopOwpmcy53cml0ZUZpbGVTeW5jKCcvYXBwL3NyYy9hcHAvbGVhZGVyc2hpcC1wYWNrL3BhZ2UudHN4Jywg')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/tsfix.b64','Yyk7CmNvbnNvbGUubG9nKCdUUyBmaXggYXBwbGllZCcpOwo=')"
docker exec agora-frontend-1 node -e "const s=Buffer.from(require('fs').readFileSync('/tmp/tsfix.b64','utf8'),'base64').toString();require('fs').writeFileSync('/tmp/tsfix.js',s)"
docker exec agora-frontend-1 node /tmp/tsfix.js

echo Running spacy_fix...
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','a').write('CmltcG9ydCBzeXMKCnBhdGggPSAnL3Vzci9sb2NhbC9saWIvcHl0aG9uMy4xMi9zaXRlLXBhY2thZ2VzL3B5ZGFudGljL3YxL3R5cGluZy5weScKd2l0aCBvcGVuKHBhdGgpIGFzIGY6CiAgICBjb250ZW50ID0gZi5yZWFkKCkKCm9sZCA9ICdyZXR1cm4gY2FzdChB')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','a').write('bnksIHR5cGVfKS5fZXZhbHVhdGUoZ2xvYmFsbnMsIGxvY2FsbnMsIHNldCgpKScKbmV3ID0gJycndHJ5OgogICAgICAgIHJldHVybiBjYXN0KEFueSwgdHlwZV8pLl9ldmFsdWF0ZShnbG9iYWxucywgbG9jYWxucywgZnJvemVuc2V0KCkpCiAgICBleGNlcHQgVHlw')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','a').write('ZUVycm9yOgogICAgICAgIHRyeToKICAgICAgICAgICAgcmV0dXJuIGNhc3QoQW55LCB0eXBlXykuX2V2YWx1YXRlKGdsb2JhbG5zLCBsb2NhbG5zLCBzZXQoKSkKICAgICAgICBleGNlcHQgVHlwZUVycm9yOgogICAgICAgICAgICByZXR1cm4gY2FzdChBbnksIHR5')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','a').write('cGVfKS5fZXZhbHVhdGUoZ2xvYmFsbnMsIGxvY2FsbnMpJycnCgppZiBvbGQgaW4gY29udGVudDoKICAgIGNvbnRlbnQgPSBjb250ZW50LnJlcGxhY2Uob2xkLCBuZXcpCiAgICB3aXRoIG9wZW4ocGF0aCwgJ3cnKSBhcyBmOgogICAgICAgIGYud3JpdGUoY29udGVu')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','a').write('dCkKICAgIHByaW50KCdweWRhbnRpYyB2MSB0eXBpbmcucHkgcGF0Y2hlZCBzdWNjZXNzZnVsbHknKQplbGlmICdmcm96ZW5zZXQoKScgaW4gY29udGVudDoKICAgIHByaW50KCdhbHJlYWR5IHBhdGNoZWQnKQplbHNlOgogICAgcHJpbnQoJ3BhdHRlcm4gbm90IGZv')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_fix.b64','a').write('dW5kIC0gY2hlY2tpbmcgZmlsZS4uLicpCiAgICBmb3IgaSwgbGluZSBpbiBlbnVtZXJhdGUoY29udGVudC5zcGxpdChjaHIoMTApKVs1MTA6NTMwXSwgNTEwKToKICAgICAgICBwcmludChmJ3tpfToge2xpbmV9JykK')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/spacy_fix.b64').read()).decode())"

echo Verifying spaCy...
docker exec agora-backend-1 python -c "import spacy;nlp=spacy.load('en_core_web_sm');d=nlp('Tinubu in Abuja');print('spaCy OK:',[(e.text,e.label_) for e in d.ents])"

echo Rebuilding frontend...
docker exec agora-frontend-1 npm run build
docker restart agora-frontend-1

echo All done.
pause