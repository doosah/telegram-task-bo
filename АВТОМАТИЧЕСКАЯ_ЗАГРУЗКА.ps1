# АВТОМАТИЧЕСКАЯ ЗАГРУЗКА НА GITHUB
# Просто запустите этот файл!

Write-Host "========================================" -ForegroundColor Green
Write-Host "  АВТОМАТИЧЕСКАЯ ЗАГРУЗКА НА GITHUB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Переходим в папку скрипта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Папка: $scriptPath" -ForegroundColor Yellow
Write-Host ""

# Проверяем Git
if (-not (Test-Path ".git")) {
    Write-Host "Инициализируем Git..." -ForegroundColor Yellow
    git init
}

# Добавляем файлы
Write-Host "Добавляем файлы..." -ForegroundColor Yellow
git add .

# Коммитим
Write-Host "Сохраняем изменения..." -ForegroundColor Yellow
git commit -m "Telegram бот для задач" -q

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ПОДКЛЮЧЕНИЕ К GITHUB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Спрашиваем имя пользователя GitHub
Write-Host "Введите ваше имя пользователя GitHub:" -ForegroundColor Cyan
Write-Host "(например: doosah)" -ForegroundColor Gray
$username = Read-Host

Write-Host ""
Write-Host "Введите имя вашего репозитория на GitHub:" -ForegroundColor Cyan
Write-Host "(например: telegram-task-bot)" -ForegroundColor Gray
$repoName = Read-Host

Write-Host ""
Write-Host "Подключаем к GitHub..." -ForegroundColor Yellow

# Удаляем старый remote
git remote remove origin 2>$null

# Добавляем новый remote
$repoUrl = "https://github.com/$username/$repoName.git"
git remote add origin $repoUrl

Write-Host ""
Write-Host "Загружаем файлы на GitHub..." -ForegroundColor Yellow
Write-Host "ВНИМАНИЕ: Вас попросят ввести логин и пароль!" -ForegroundColor Red
Write-Host "Пароль = Personal Access Token (не обычный пароль!)" -ForegroundColor Red
Write-Host ""

# Переименовываем ветку в main
git branch -M main

# Загружаем
Write-Host "Начинаем загрузку..." -ForegroundColor Yellow
git push -u origin main

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Файлы загружены на GitHub!" -ForegroundColor Green
Write-Host ""
Write-Host "Теперь настройте Railway:" -ForegroundColor Cyan
Write-Host "1. Откройте https://railway.app" -ForegroundColor White
Write-Host "2. New Project → Deploy from GitHub repo" -ForegroundColor White
Write-Host "3. Выберите ваш репозиторий: $repoName" -ForegroundColor White
Write-Host "4. Добавьте переменные (см. RAILWAY_ПРОСТО.md)" -ForegroundColor White
Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

