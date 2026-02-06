@echo off
echo Starting AI Intelligence Platform...

:: Start Backend in a new window (Using -m to ensure imports work)
start "AI Backend" cmd /k "python -m src.api"

:: Start Frontend in a new window
cd ui
start "AI Frontend" cmd /k "npm run dev"

echo.
echo Application starting...
echo Backend: http://localhost:8001
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit this launcher (windows will stay open)...
pause
