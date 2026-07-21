$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Building Posterfolio 1.0.0" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host ""

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "The project virtual environment was not found at .venv\Scripts\python.exe"
}

$Python = Resolve-Path ".\.venv\Scripts\python.exe"

Write-Host "[1/5] Installing/updating PyInstaller..." -ForegroundColor Yellow
& $Python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed." }

Write-Host "[2/5] Removing previous build output..." -ForegroundColor Yellow
Remove-Item ".\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\release" -Recurse -Force -ErrorAction SilentlyContinue
New-Item ".\release" -ItemType Directory -Force | Out-Null

Write-Host "[3/5] Building the standalone application..." -ForegroundColor Yellow
& $Python -m PyInstaller --noconfirm --clean ".\packaging\posterfolio.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$Exe = ".\dist\Posterfolio\Posterfolio.exe"
if (-not (Test-Path $Exe)) {
    throw "Build finished without producing $Exe"
}

Write-Host "[4/5] Locating Inno Setup..." -ForegroundColor Yellow
$InnoCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe"
)

$ISCC = $InnoCandidates |
    Where-Object { $_ -and (Test-Path $_) } |
    Select-Object -First 1

if (-not $ISCC) {
    Write-Host ""
    Write-Host "The standalone application was built successfully:" -ForegroundColor Green
    Write-Host "  $ProjectRoot\dist\Posterfolio\Posterfolio.exe"
    Write-Host ""
    Write-Host "Inno Setup was not found, so the installer was not created." -ForegroundColor Yellow
    Write-Host "Checked these locations:"
    $InnoCandidates | ForEach-Object { Write-Host "  $_" }
    exit 2
}

Write-Host "Found Inno Setup compiler:" -ForegroundColor Green
Write-Host "  $ISCC"

Write-Host "[5/5] Building the Windows installer..." -ForegroundColor Yellow
& $ISCC ".\packaging\Posterfolio.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

$Installer = ".\release\Posterfolio-1.0.0-Setup.exe"
if (-not (Test-Path $Installer)) {
    throw "Installer compilation completed without producing $Installer"
}

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host ""
Write-Host "Standalone application:"
Write-Host "  $ProjectRoot\dist\Posterfolio\Posterfolio.exe"
Write-Host ""
Write-Host "Installer:"
Write-Host "  $ProjectRoot\release\Posterfolio-1.0.0-Setup.exe"
Write-Host ""
Write-Host "Test the standalone application before installing:"
Write-Host '  .\dist\Posterfolio\Posterfolio.exe'
