@echo off
echo Starting Trends.Earth API Dashboard...
echo.
echo Using conda environment with all dependencies installed...
cd /d "c:\Users\azvoleff\Code\LandDegradation\trends.earth-api-ui"
C:\Users\azvoleff\Miniforge3\Scripts\conda.exe run -p "c:\Users\azvoleff\Code\LandDegradation\trends.earth-api-ui\.conda" --no-capture-output python -m trendsearth_ui.app
pause
