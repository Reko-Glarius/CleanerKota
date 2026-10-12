$ErrorActionPreference = 'Stop'
$previousCache = $env:PYINSTALLER_CONFIG_DIR
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'build\pyinstaller-cache'
Push-Location $PSScriptRoot
try {
    python -m PyInstaller --noconfirm --clean CleanerKota.spec
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el ejecutable.' }
    Write-Host "Ejecutable generado: $PSScriptRoot\dist\CleanerKota.exe"
} finally {
    $env:PYINSTALLER_CONFIG_DIR = $previousCache
    Pop-Location
}
