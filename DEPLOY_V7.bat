@echo off
echo ================================================
echo  NDIP V7 - Full Deployment
echo ================================================
echo.
echo Step 1: Deploying backend files...
call deploy_copilot.py.bat
call deploy_onboarding.py.bat
call deploy_v7_migration.py.bat
echo.
echo Step 2: Patching main.py...
call patch_main.bat
echo.
echo Step 3: Running database migration...
docker exec agora-backend-1 python scripts/v7_migration.py
echo.
echo Step 4: Restarting backend...
docker restart agora-backend-1
echo.
echo Step 5: Deploying frontend components...
call deploy_AICopilot.tsx.bat
call deploy_HelpOverlay.tsx.bat
call deploy_GuidedTour.tsx.bat
echo.
echo Step 6: Verifying backend endpoints...
docker exec agora-backend-1 python -c "import time; time.sleep(3); import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
echo.
echo ================================================
echo  V7 Deployment Complete
echo ================================================
echo.
echo Next: Open http://localhost:3000 and test the Copilot button (bottom right)
echo       Press H on any dashboard to toggle the Help overlay
pause
