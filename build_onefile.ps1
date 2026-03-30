param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"
$SpecPath = Join-Path $ProjectRoot "GFAC Bulletin Studio.spec"
$AppName = "GFAC Bulletin Studio"
$IconPath = Join-Path $ProjectRoot "assets\\app.ico"

Write-Host "Cleaning previous build folders..."
if (Test-Path $DistDir) {
    Remove-Item $DistDir -Recurse -Force
}
if (Test-Path $BuildDir) {
    Remove-Item $BuildDir -Recurse -Force
}
if (Test-Path $SpecPath) {
    Remove-Item $SpecPath -Force
}

Write-Host "Building one-file $AppName..."
& $PythonExe -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed for $PythonExe. Run: $PythonExe -m pip install pyinstaller"
}

$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", $AppName,
    "--collect-data", "customtkinter",
    "--hidden-import", "comtypes.client",
    "--add-data", "$ProjectRoot\assets;assets",
    "--add-data", "$ProjectRoot\templates;templates",
    "--add-data", "$ProjectRoot\thumbnails;thumbnails"
)

if (Test-Path $IconPath) {
    $PyInstallerArgs += @("--icon", $IconPath)
}

$PyInstallerArgs += "$ProjectRoot\main.py"

& $PythonExe @PyInstallerArgs

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller one-file build failed."
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Open: $DistDir\$AppName.exe"
