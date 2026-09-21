# SolutionBridge Local Deployment Script
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  SolutionBridge — Starting Local Production Deployment   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$env:DATABASE_URL = "sqlite:///./solutionbridge_dev.db"

Write-Host "`n[1/3] Checking Database Status..." -ForegroundColor Yellow
python -m alembic upgrade head
python scripts/seed_database.py

Write-Host "`n[2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
$apiProcess = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -PassThru

Write-Host "[3/3] Starting Streamlit PSE Portal on http://127.0.0.1:8501 ..." -ForegroundColor Yellow
$dashProcess = Start-Process -FilePath "python" -ArgumentList "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "8501" -PassThru

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  SolutionBridge Services Are LIVE!                       " -ForegroundColor Green
Write-Host "  • FastAPI Swagger Docs:  http://127.0.0.1:8000/docs     " -ForegroundColor Green
Write-Host "  • Streamlit PSE Portal:  http://127.0.0.1:8501          " -ForegroundColor Green
Write-Host "  • Live Web Demo:         https://noor-r.github.io/SolutionBridge/ " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate services."

try {
    while ($true) {
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $dashProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Services stopped cleanly." -ForegroundColor Green
}
