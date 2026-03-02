# Naver AI Evolution - Windows Setup Script
param(
    [switch]$SkipPython,
    [switch]$SkipAdb
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\ai-projects\naver-ai-evolution"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Naver AI Evolution - Windows Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python Check
if (-not $SkipPython) {
    Write-Host "[1/5] Python Check..." -ForegroundColor Yellow
    
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "  OK: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Warning: Python not found" -ForegroundColor Yellow
    }
    
    # Create venv
    $venvPath = Join-Path $ProjectRoot "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Host "  Creating virtual environment..."
        python -m venv $venvPath
    }
    Write-Host "  OK: Virtual environment ready" -ForegroundColor Green
}

# 2. ADB Check
if (-not $SkipAdb) {
    Write-Host "[2/5] ADB Check..." -ForegroundColor Yellow
    
    $adbPaths = @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "C:\Android\sdk\platform-tools\adb.exe"
    )
    
    $adbFound = $false
    foreach ($adbPath in $adbPaths) {
        if (Test-Path $adbPath) {
            Write-Host "  OK: ADB found at $adbPath" -ForegroundColor Green
            $adbFound = $true
            break
        }
    }
    
    if (-not $adbFound) {
        try {
            $adbTest = adb version 2>&1
            Write-Host "  OK: ADB in PATH" -ForegroundColor Green
        } catch {
            Write-Host "  Warning: ADB not found" -ForegroundColor Yellow
        }
    }
}

# 3. WSL2 Check
Write-Host "[3/5] WSL2 Check..." -ForegroundColor Yellow
try {
    $wslList = wsl --list --verbose 2>&1
    Write-Host "  OK: WSL2 available" -ForegroundColor Green
} catch {
    Write-Host "  Warning: WSL2 not available" -ForegroundColor Yellow
}

# 4. Shared Directory
Write-Host "[4/5] Shared Directory Setup..." -ForegroundColor Yellow
$sharedDir = "C:\ai-projects\shared"
$dirs = @(
    "$sharedDir\message_queues\windows_inbox",
    "$sharedDir\message_queues\windows_outbox",
    "$sharedDir\message_queues\wsl_inbox",
    "$sharedDir\message_queues\wsl_outbox"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "  OK: Shared directories created" -ForegroundColor Green

# 5. Environment Variables
Write-Host "[5/5] Environment Variables Check..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "  OK: .env file exists" -ForegroundColor Green
} else {
    Write-Host "  Warning: .env file not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
