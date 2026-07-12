@echo off
echo Deploying inspect_schema.py...
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','w').write('')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('IiIiUnVuIHRoaXMgdG8gc2VlIHRoZSBhY3R1YWwgY29sdW1uIG5hbWVzIGluIGtleSB0YWJsZXMuIiIiCmltcG9ydCBzeXMKc3lzLnBhdGguaW5zZXJ0KDAsICcvYXBwJykKZnJvbSBzcWxhbGNoZW15IGltcG9ydCB0ZXh0CmZyb20gYXBwLmRiLmRhdGFiYXNlIGlt')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('cG9ydCBTZXNzaW9uTG9jYWwKCmRiID0gU2Vzc2lvbkxvY2FsKCkKdGFibGVzID0gWyduYXJyYXRpdmVfdHJlbmRzJywgJ2FuYWx5dGljc19zbmFwc2hvdHMnLCAnc29jaWFsX3Bvc3RzJywKICAgICAgICAgICdub3JtYWxpc2VkX3Bvc3RzJywgJ29wcG9ydHVuaXR5')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('X2FsaWdubWVudF9zY29yZXMnLAogICAgICAgICAgJ3N0YWtlaG9sZGVyX2luZmx1ZW5jZV9wcm9maWxlcycsICdvcHBvcnR1bml0eV9hc3Nlc3NtZW50cyddCgpmb3IgdGFibGUgaW4gdGFibGVzOgogICAgdHJ5OgogICAgICAgIHJlc3VsdCA9IGRiLmV4ZWN1dGUo')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('dGV4dChmIiIiCiAgICAgICAgICAgIFNFTEVDVCBjb2x1bW5fbmFtZSwgZGF0YV90eXBlCiAgICAgICAgICAgIEZST00gaW5mb3JtYXRpb25fc2NoZW1hLmNvbHVtbnMKICAgICAgICAgICAgV0hFUkUgdGFibGVfbmFtZSA9ICd7dGFibGV9JwogICAgICAgICAgICBP')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('UkRFUiBCWSBvcmRpbmFsX3Bvc2l0aW9uCiAgICAgICAgIiIiKSkuZmV0Y2hhbGwoKQogICAgICAgIGlmIHJlc3VsdDoKICAgICAgICAgICAgcHJpbnQoZiJcbnt0YWJsZX06IikKICAgICAgICAgICAgZm9yIGNvbCwgZHR5cGUgaW4gcmVzdWx0OgogICAgICAgICAg')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('ICAgICAgcHJpbnQoZiIgIHtjb2x9ICh7ZHR5cGV9KSIpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcHJpbnQoZiJcbnt0YWJsZX06IE5PVCBGT1VORCIpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcHJpbnQoZiJcbnt0YWJsZX06IEVSUk9S')"
docker exec agora-backend-1 python -c "open('/tmp/inspect_b64.txt','a').write('IC0ge2V9IikKZGIuY2xvc2UoKQo=')"
docker exec agora-backend-1 python -c "import base64;open('/app/scripts/inspect_schema.py','wb').write(base64.b64decode(open('/tmp/inspect_b64.txt').read()));print('Written: /app/scripts/inspect_schema.py')"
echo Done