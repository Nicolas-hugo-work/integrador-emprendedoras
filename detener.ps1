$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\proyecto-integrador'
docker compose stop
Write-Host 'Servicios de Kawsay detenidos. Los datos de MariaDB se conservaron.' -ForegroundColor Yellow
