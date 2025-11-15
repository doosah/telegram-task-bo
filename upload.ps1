# Simple upload to GitHub
Write-Host "========================================" -ForegroundColor Green
Write-Host "  UPLOAD TO GITHUB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Initialize Git if needed
if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git..." -ForegroundColor Yellow
    git init
}

# Add files
Write-Host "Adding files..." -ForegroundColor Yellow
git add .

# Commit
Write-Host "Saving changes..." -ForegroundColor Yellow
git commit -m "Telegram bot for tasks" 2>&1 | Out-Null

Write-Host ""
Write-Host "Enter your GitHub username:" -ForegroundColor Cyan
$username = Read-Host

Write-Host ""
Write-Host "Enter repository name:" -ForegroundColor Cyan
$repoName = Read-Host

Write-Host ""
Write-Host "Connecting to GitHub..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin "https://github.com/$username/$repoName.git"

Write-Host ""
Write-Host "Uploading files..." -ForegroundColor Yellow
Write-Host "NOTE: Enter your login and Personal Access Token!" -ForegroundColor Red
Write-Host ""

git branch -M main
git push -u origin main

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DONE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Enter to exit..."
Read-Host

