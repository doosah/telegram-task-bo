# Простая загрузка на GitHub
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ЗАГРУЗКА НА GITHUB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Инициализируем Git если нужно
if (-not (Test-Path ".git")) {
    Write-Host "Инициализируем Git..." -ForegroundColor Yellow
    git init
}

# Добавляем файлы
Write-Host "Добавляем файлы..." -ForegroundColor Yellow
git add .

# Коммитим
Write-Host "Сохраняем изменения..." -ForegroundColor Yellow
git commit -m "Telegram bot for tasks" 2>&1 | Out-Null

Write-Host ""
Write-Host "Введите имя пользователя GitHub:" -ForegroundColor Cyan
$username = Read-Host

Write-Host ""
Write-Host "Введите имя репозитория:" -ForegroundColor Cyan
$repoName = Read-Host

Write-Host ""
Write-Host "Подключаем к GitHub..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin "https://github.com/$username/$repoName.git"

Write-Host ""
Write-Host "Загружаем файлы..." -ForegroundColor Yellow
Write-Host "ВНИМАНИЕ: Введите логин и Personal Access Token!" -ForegroundColor Red
Write-Host ""

git branch -M main
git push -u origin main

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Нажмите Enter для выхода..."
Read-Host

