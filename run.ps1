# Запуск dev-сервера (настройки читаются из .env автоматически)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.env")) {
    Write-Host "Файл .env не найден. Скопируйте .env.example в .env и заполните настройки." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "Виртуальное окружение venv не найдено. Создайте: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

$env:PYTHONDONTWRITEBYTECODE = "1"
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

& ".\venv\Scripts\python.exe" manage.py runserver --noreload
