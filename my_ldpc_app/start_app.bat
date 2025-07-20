@echo off
echo Starting LDPC Designer Application...
echo.

echo [1/3] Starting Backend Server...
start "LDPC Backend" cmd /k "cd /d %~dp0backend && python main.py"

echo [2/3] Waiting for backend to start...
timeout /t 3 /nobreak >nul

echo [3/3] Starting Flutter Web Application...
cd /d %~dp0
flutter run -d chrome

echo.
echo Application should now be running!
echo Backend: http://127.0.0.1:5000
echo Frontend: http://localhost:port (check Flutter output)
echo.
pause
