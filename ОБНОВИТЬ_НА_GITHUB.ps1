# БЫСТРОЕ ОБНОВЛЕНИЕ НА GITHUB (если репозиторий уже подключен)
# Просто запустите этот файл двойным кликом!

Write-Host "========================================" -ForegroundColor Green
Write-Host "  ОБНОВЛЕНИЕ БОТА НА GITHUB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Переходим в папку с ботом
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Текущая папка: $scriptPath" -ForegroundColor Yellow
Write-Host ""

# Проверяем, инициализирован ли Git
if (-not (Test-Path ".git")) {
    Write-Host "❌ ОШИБКА: Git не инициализирован!" -ForegroundColor Red
    Write-Host "Используйте файл ЗАГРУЗИТЬ_НА_GITHUB.ps1 для первой загрузки" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Нажмите любую клавишу для выхода..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# Проверяем, подключен ли remote
$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host "❌ ОШИБКА: Репозиторий не подключен к GitHub!" -ForegroundColor Red
    Write-Host "Используйте файл ЗАГРУЗИТЬ_НА_GITHUB.ps1 для подключения" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Нажмите любую клавишу для выхода..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host "Репозиторий: $remote" -ForegroundColor Cyan
Write-Host ""

# Добавляем все файлы
Write-Host "Добавляем изменения..." -ForegroundColor Yellow
git add .

# Проверяем, есть ли изменения
$status = git status --porcelain
if (-not $status) {
    Write-Host "✅ Нет изменений для загрузки" -ForegroundColor Green
    Write-Host ""
    Write-Host "Нажмите любую клавишу для выхода..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# Сохраняем изменения
Write-Host "Сохраняем изменения..." -ForegroundColor Yellow
$commitMessage = "Обновление бота: исправления и улучшения"
git commit -m $commitMessage

Write-Host ""
Write-Host "Загружаем на GitHub..." -ForegroundColor Yellow
Write-Host ""

# Загружаем на GitHub
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✅ ГОТОВО!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Изменения загружены на GitHub!" -ForegroundColor Green
    Write-Host "Railway автоматически обновит бота в течение 1-2 минут" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Проверьте статус деплоя в Railway:" -ForegroundColor Yellow
    Write-Host "https://railway.app" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ❌ ОШИБКА ПРИ ЗАГРУЗКЕ" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Проверьте подключение к GitHub и попробуйте снова" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

