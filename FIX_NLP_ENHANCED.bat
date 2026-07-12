@echo off
echo Adding pydantic patch to nlp_enhanced.py...

docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','a').write('CmltcG9ydCBzeXMsIG9zCgpwYXRoID0gJy9hcHAvYXBwL2FuYWx5dGljcy9ubHBfZW5oYW5jZWQucHknCndpdGggb3BlbihwYXRoKSBhcyBmOgogICAgY29udGVudCA9IGYucmVhZCgpCgpwYXRjaF9jb2RlID0gJycnIyBORElQIHNwYUN5L3B5ZGFudGljIHYxIGNv')"
docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','a').write('bXBhdGliaWxpdHkgcGF0Y2gKaW1wb3J0IHR5cGluZyBhcyBfdApfb3JpZ19ldmFsID0gX3QuRm9yd2FyZFJlZi5fZXZhbHVhdGUKZGVmIF9wYXRjaGVkX2V2YWwoc2VsZiwgZ2xvYmFsbnMsIGxvY2FsbnMsICphcmdzLCAqKmt3YXJncyk6CiAgICBmb3IgX2NhbGwg')"
docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','a').write('aW4gWwogICAgICAgIGxhbWJkYTogX29yaWdfZXZhbChzZWxmLCBnbG9iYWxucywgbG9jYWxucywgcmVjdXJzaXZlX2d1YXJkPWZyb3plbnNldCgpKSwKICAgICAgICBsYW1iZGE6IF9vcmlnX2V2YWwoc2VsZiwgZ2xvYmFsbnMsIGxvY2FsbnMsIGZyb3plbnNldCgp')"
docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','a').write('KSwKICAgICAgICBsYW1iZGE6IF9vcmlnX2V2YWwoc2VsZiwgZ2xvYmFsbnMsIGxvY2FsbnMpLAogICAgXToKICAgICAgICB0cnk6IHJldHVybiBfY2FsbCgpCiAgICAgICAgZXhjZXB0IFR5cGVFcnJvcjogY29udGludWUKX3QuRm9yd2FyZFJlZi5fZXZhbHVhdGUg')"
docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','a').write('PSBfcGF0Y2hlZF9ldmFsCmRlbCBfdCwgX29yaWdfZXZhbCwgX3BhdGNoZWRfZXZhbAojIEVuZCBwYXRjaAoKJycnCgppZiAnTkRJUCBzcGFDeS9weWRhbnRpYyB2MSBjb21wYXRpYmlsaXR5IHBhdGNoJyBub3QgaW4gY29udGVudDoKICAgIHdpdGggb3BlbihwYXRo')"
docker exec agora-backend-1 python -c "open('/tmp/nlp_patch.b64','a').write('LCAndycpIGFzIGY6CiAgICAgICAgZi53cml0ZShwYXRjaF9jb2RlICsgY29udGVudCkKICAgIHByaW50KCdQYXRjaCBhZGRlZCB0byBubHBfZW5oYW5jZWQucHknKQplbHNlOgogICAgcHJpbnQoJ0FscmVhZHkgcGF0Y2hlZCcpCg==')"
docker exec agora-backend-1 python -c "import base64;exec(base64.b64decode(open('/tmp/nlp_patch.b64').read()).decode())"

echo Verifying spaCy loads correctly during ingest...
docker exec agora-backend-1 python -c "import sys;sys.path.insert(0,'/app');from app.analytics import nlp_enhanced;nlp=nlp_enhanced._load_spacy();print('NLP OK:',nlp)"

echo Done.
pause