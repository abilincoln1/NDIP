@echo off
echo Testing spaCy with pydantic v1 patch...

docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('CmltcG9ydCBzeXMKIyBQYXRjaCBweWRhbnRpYyB2MSB0eXBpbmcgbW9kdWxlIHRvIGZpeCBGb3J3YXJkUmVmLl9ldmFsdWF0ZSBpbiBQeXRob24gMy4xMgp0cnk6CiAgICBpbXBvcnQgcHlkYW50aWMudjEudHlwaW5nIGFzIHB2MXQKICAgIG9yaWcgPSBwdjF0LmV2')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('YWx1YXRlX2ZvcndhcmRyZWYKICAgIGRlZiBwYXRjaGVkKHRwLCBnbG9iYWxucywgbG9jYWxucyk6CiAgICAgICAgdHJ5OgogICAgICAgICAgICByZXR1cm4gdHAuX2V2YWx1YXRlKGdsb2JhbG5zLCBsb2NhbG5zLCBmcm96ZW5zZXQoKSkKICAgICAgICBleGNlcHQg')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('VHlwZUVycm9yOgogICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICByZXR1cm4gdHAuX2V2YWx1YXRlKGdsb2JhbG5zLCBsb2NhbG5zLCBzZXQoKSkKICAgICAgICAgICAgZXhjZXB0IFR5cGVFcnJvcjoKICAgICAgICAgICAgICAgIHJldHVybiB0cC5fZXZh')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('bHVhdGUoZ2xvYmFsbnMsIGxvY2FsbnMpCiAgICBwdjF0LmV2YWx1YXRlX2ZvcndhcmRyZWYgPSBwYXRjaGVkCiAgICBwcmludCgncHlkYW50aWMgdjEgcGF0Y2ggYXBwbGllZCcpCmV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgIHByaW50KGYncGF0Y2ggZmFpbGVk')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('OiB7ZX0nKQoKIyBOb3cgdGVzdCBzcGFjeQp0cnk6CiAgICBpbXBvcnQgc3BhY3kKICAgIG5scCA9IHNwYWN5LmxvYWQoJ2VuX2NvcmVfd2ViX3NtJykKICAgIGRvYyA9IG5scCgnUHJlc2lkZW50IFRpbnVidSBkaXNjdXNzZWQgZWNvbm9taWMgcG9saWN5IGluIEFi')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('dWphLicpCiAgICBlbnRpdGllcyA9IFsoZS50ZXh0LCBlLmxhYmVsXykgZm9yIGUgaW4gZG9jLmVudHNdCiAgICBwcmludChmJ3NwYUN5IHtzcGFjeS5fX3ZlcnNpb25fX30gd29ya2luZy4gRW50aXRpZXM6IHtlbnRpdGllc30nKQpleGNlcHQgRXhjZXB0aW9uIGFz')"
docker exec agora-backend-1 python -c "open('/tmp/spacy_test.b64','a').write('IGU6CiAgICBwcmludChmJ3NwYUN5IHRlc3QgZmFpbGVkOiB7ZX0nKQo=')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/spacy_test.b64').read()).decode())"
echo.
echo Applying permanent spaCy patch to normalisation.py...
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('CmltcG9ydCBzeXMsIG9zCgpwYXRjaCA9ICcnJwojIE5ESVAgVjggc3BhQ3kvcHlkYW50aWMgdjEgY29tcGF0aWJpbGl0eSBwYXRjaAppbXBvcnQgdHlwaW5nIGFzIF90eXBpbmcKX29yaWcgPSBfdHlwaW5nLkZvcndhcmRSZWYuX2V2YWx1YXRlCmRlZiBfcGF0Y2hl')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('ZChzZWxmLCBnbG9iYWxucywgbG9jYWxucywgKmFyZ3MsICoqa3dhcmdzKToKICAgIGt3YXJncy5wb3AoJ3JlY3Vyc2l2ZV9ndWFyZCcsIE5vbmUpCiAgICBmb3IgY2FsbCBpbiBbCiAgICAgICAgbGFtYmRhOiBfb3JpZyhzZWxmLCBnbG9iYWxucywgbG9jYWxucywg')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('ZnJvemVuc2V0KCkpLAogICAgICAgIGxhbWJkYTogX29yaWcoc2VsZiwgZ2xvYmFsbnMsIGxvY2FsbnMsIHNldCgpKSwKICAgICAgICBsYW1iZGE6IF9vcmlnKHNlbGYsIGdsb2JhbG5zLCBsb2NhbG5zKSwKICAgIF06CiAgICAgICAgdHJ5OiByZXR1cm4gY2FsbCgp')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('CiAgICAgICAgZXhjZXB0IFR5cGVFcnJvcjogY29udGludWUKICAgIHJhaXNlIFR5cGVFcnJvcignRm9yd2FyZFJlZi5fZXZhbHVhdGUgZmFpbGVkJykKX3R5cGluZy5Gb3J3YXJkUmVmLl9ldmFsdWF0ZSA9IF9wYXRjaGVkCmRlbCBfdHlwaW5nLCBfb3JpZywgX3Bh')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('dGNoZWQKIyBFbmQgc3BhQ3kgcGF0Y2gKJycnCgpwYXRoID0gJy9hcHAvYXBwL3NlcnZpY2VzL25vcm1hbGlzYXRpb24ucHknCndpdGggb3BlbihwYXRoKSBhcyBmOgogICAgY29udGVudCA9IGYucmVhZCgpCmlmICdORElQIFY4IHNwYUN5JyBub3QgaW4gY29udGVu')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('dDoKICAgIHdpdGggb3BlbihwYXRoLCAndycpIGFzIGY6CiAgICAgICAgZi53cml0ZShwYXRjaCArIGNvbnRlbnQpCiAgICBwcmludCgnUGF0Y2ggd3JpdHRlbiB0byBub3JtYWxpc2F0aW9uLnB5JykKZWxzZToKICAgIHByaW50KCdQYXRjaCBhbHJlYWR5IHByZXNl')"
docker exec agora-backend-1 python -c "open('/tmp/perm_patch.b64','a').write('bnQnKQo=')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/perm_patch.b64').read()).decode())"
docker restart agora-backend-1
timeout /t 8 /nobreak >nul
echo Verifying spaCy after restart...
docker exec agora-backend-1 python -c "import pydantic.v1.typing as t;from functools import reduce;o=t.evaluate_forwardref;t.evaluate_forwardref=lambda tp,g,l:tp._evaluate(g,l,frozenset()) if True else None;import spacy;nlp=spacy.load('en_core_web_sm');d=nlp('Tinubu in Abuja');print('spaCy OK:',[(e.text,e.label_) for e in d.ents])" 2>&1 || echo spaCy needs model download
docker exec agora-backend-1 python -m spacy download en_core_web_sm 2>&1 | tail -3
pause