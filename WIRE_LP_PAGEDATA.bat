@echo off
echo Wiring Leadership Pack pageData into Copilot (EB-012)...

docker exec agora-frontend-1 node -e "require('fs').writeFileSync('/tmp/patch_lp.b64','')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','CmNvbnN0IGZzID0gcmVxdWlyZSgnZnMnKTsKbGV0IGMgPSBmcy5yZWFkRmlsZVN5bmMoJy9hcHAvc3JjL2FwcC9sZWFkZXJzaGlwLXBhY2svcGFnZS50c3gnLCAndXRmOCcpOwoKLy8gMS4gQWRkIHVzZUNvcGlsb3REYXRhIGltcG9ydCBhZnRlciB0aGUgZXhpc3Rp')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','bmcgYXBpIGltcG9ydAppZiAoIWMuaW5jbHVkZXMoJ3VzZUNvcGlsb3REYXRhJykpIHsKICBjID0gYy5yZXBsYWNlKAogICAgJ2ltcG9ydCBhcGkgZnJvbSAiQC9saWIvYXBpIjsnLAogICAgJ2ltcG9ydCBhcGkgZnJvbSAiQC9saWIvYXBpIjtcbmltcG9ydCB7IHVz')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','ZUNvcGlsb3REYXRhIH0gZnJvbSAiQC9jb21wb25lbnRzL3VpL0FJQ29waWxvdCI7JwogICk7Cn0KCi8vIDIuIEFkZCB1c2VDb3BpbG90RGF0YSBob29rIGFmdGVyIHVzZVN0YXRlIGRlY2xhcmF0aW9ucwppZiAoIWMuaW5jbHVkZXMoJ3NldFBhZ2VEYXRhJykpIHsK')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','ICBjID0gYy5yZXBsYWNlKAogICAgJ2NvbnN0IFthY3Rpb25zLCBzZXRBY3Rpb25zXSA9IHVzZVN0YXRlPGFueT4obnVsbCk7JywKICAgICdjb25zdCBbYWN0aW9ucywgc2V0QWN0aW9uc10gPSB1c2VTdGF0ZTxhbnk+KG51bGwpO1xuICBjb25zdCB7IHNldFBhZ2VE')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','YXRhIH0gPSB1c2VDb3BpbG90RGF0YSgpOycKICApOwp9CgovLyAzLiBBZGQgc2V0UGFnZURhdGEgY2FsbCBhZnRlciBkYXRhIGlzIHNldAppZiAoIWMuaW5jbHVkZXMoJ3NldFBhZ2VEYXRhKCcpKSB7CiAgYyA9IGMucmVwbGFjZSgKICAgICcudGhlbihyID0+IHNl')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','dERhdGEoci5kYXRhKSknLAogICAgYC50aGVuKHIgPT4geyBzZXREYXRhKHIuZGF0YSk7IGlmIChyLmRhdGEpIHsgc2V0UGFnZURhdGEoeyBuYXJyYXRpdmVzOiByLmRhdGEubmFycmF0aXZlX2Fzc2Vzc21lbnRzIHx8IFtdLCBlbmdhZ2VtZW50X2luZGV4OiByLmRh')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','dGEuZW5nYWdlbWVudF9pbmRleCwgc2VudGltZW50X3Njb3JlOiByLmRhdGEuc2VudGltZW50X3Njb3JlLCBjb25maWRlbmNlOiByLmRhdGEuY29uZmlkZW5jZV9sYWJlbCwgd2F0Y2hsaXN0X2NyaXRpY2FsX2NvdW50OiAoci5kYXRhLnJpc2tzIHx8IFtdKS5maWx0')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','ZXIoKHgpID0+IHgubGV2ZWwgPT09ICdDcml0aWNhbCcpLmxlbmd0aCwgd2F0Y2hsaXN0X2hpZ2hfY291bnQ6IChyLmRhdGEucmlza3MgfHwgW10pLmZpbHRlcigoeCkgPT4geC5sZXZlbCA9PT0gJ1dhcm5pbmcnKS5sZW5ndGgsIHJpc2tzOiByLmRhdGEucmlza3Mg')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','fHwgW10sIHRvcF9vcHBvcnR1bml0aWVzOiByLmRhdGEub3Bwb3J0dW5pdGllcyB8fCBbXSwgc2lnbmlmaWNhbnRfY2hhbmdlczogci5kYXRhLnNpZ25pZmljYW50X2NoYW5nZXMgfHwgW10gfSk7IH0gfSlgCiAgKTsKfQoKZnMud3JpdGVGaWxlU3luYygnL2FwcC9z')"
docker exec agora-frontend-1 node -e "require('fs').appendFileSync('/tmp/patch_lp.b64','cmMvYXBwL2xlYWRlcnNoaXAtcGFjay9wYWdlLnRzeCcsIGMpOwpjb25zb2xlLmxvZygncGF0Y2hlZCcpOwo=')"
docker exec agora-frontend-1 node -e "const s=Buffer.from(require('fs').readFileSync('/tmp/patch_lp.b64','utf8'),'base64').toString();require('fs').writeFileSync('/tmp/patch_lp.js',s);console.log('script ready')"
docker exec agora-frontend-1 node /tmp/patch_lp.js

echo Building frontend...
docker exec agora-frontend-1 npm run build
docker restart agora-frontend-1

echo Done. Open Leadership Pack and ask Copilot: What changed since yesterday?
pause