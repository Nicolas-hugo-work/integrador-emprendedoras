$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\proyecto-integrador'
docker compose up --build -d
Write-Host 'Kawsay está iniciando. Aplicación: http://localhost:3000' -ForegroundColor Green
Write-Host 'API: http://localhost:8000/docs' -ForegroundColor Cyan
Start-Process 'http://localhost:3000'
