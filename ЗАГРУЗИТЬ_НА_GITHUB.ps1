# СКРИПТ ДЛЯ АВТОМАТИЧЕСКОЙ ЗАГРУЗКИ НА GITHUB
# Просто запустите этот файл двойным кликом!

Write-Host "========================================" -ForegroundColor Green
Write-Host "  ЗАГРУЗКА БОТА НА GITHUB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Переходим в папку с ботом
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Текущая папка: $scriptPath" -ForegroundColor Yellow
Write-Host ""

# Проверяем, инициализирован ли Git
if (-not (Test-Path ".git")) {
    Write-Host "Инициализируем Git..." -ForegroundColor Yellow
    git init
}

# Добавляем все файлы
Write-Host "Добавляем файлы..." -ForegroundColor Yellow
git add .

# Сохраняем изменения
Write-Host "Сохраняем изменения..." -ForegroundColor Yellow
git commit -m "Загрузка Telegram бота для задач"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Теперь нужно подключить к вашему репозиторию на GitHub." -ForegroundColor Cyan
Write-Host ""
Write-Host "Введите имя вашего репозитория на GitHub (например: telegram-task-bot):" -ForegroundColor Yellow
$repoName = Read-Host

Write-Host ""
Write-Host "Введите ваше имя пользователя GitHub:" -ForegroundColor Yellow
$username = Read-Host

Write-Host ""
Write-Host "Подключаем к GitHub..." -ForegroundColor Yellow

# Удаляем старый remote, если есть
git remote remove origin 2>$null

# Добавляем новый remote
git remote add origin "https://github.com/$username/$repoName.git"

Write-Host ""
Write-Host "Загружаем файлы на GitHub..." -ForegroundColor Yellow
Write-Host "Вам нужно будет ввести логин и пароль (Personal Access Token)" -ForegroundColor Cyan
Write-Host ""

git branch -M main
git push -u origin main

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ВСЁ ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Файлы загружены на GitHub!" -ForegroundColor Green
Write-Host "Теперь переходите к настройке Railway (см. файл RAILWAY_ПРОСТО.md)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

