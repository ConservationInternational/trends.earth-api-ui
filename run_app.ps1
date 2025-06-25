# PowerShell script to run the Trends.Earth API Dashboard
Write-Host "Starting Trends.Earth API Dashboard..." -ForegroundColor Green
Write-Host "Using conda environment with all dependencies installed..." -ForegroundColor Yellow

Set-Location "c:\Users\azvoleff\Code\LandDegradation\trends.earth-api-ui"

Write-Host "Running diagnostic first..." -ForegroundColor Cyan
& C:\Users\azvoleff\Miniforge3\Scripts\conda.exe run -p "c:\Users\azvoleff\Code\LandDegradation\trends.earth-api-ui\.conda" --no-capture-output python diagnose.py

Write-Host "`nIf diagnostic passed, starting the app..." -ForegroundColor Cyan
& C:\Users\azvoleff\Miniforge3\Scripts\conda.exe run -p "c:\Users\azvoleff\Code\LandDegradation\trends.earth-api-ui\.conda" --no-capture-output python -m trendsearth_ui.app

Read-Host "Press Enter to continue..."
