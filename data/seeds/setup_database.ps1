
# PPR Bitcoin Database Setup Script
Write-Host "================================" -ForegroundColor Cyan
Write-Host "PPR Bitcoin Database Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
$venvPath = "..\..\backend\venv"
if (-Not (Test-Path $venvPath)) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run backend/setup.bat first" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/3] Activating Python environment..." -ForegroundColor Green
& "$venvPath\Scripts\Activate.ps1"

Write-Host "[2/3] Checking Python and packages..." -ForegroundColor Green
python --version

Write-Host "[3/3] Running database setup..." -ForegroundColor Green
Write-Host ""

python setup_database.py

Write-Host ""
Read-Host "Press Enter to exit"