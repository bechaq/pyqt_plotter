$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --name "PyQtPlotter" `
  --windowed `
  pyqt_plotter_main.py

Write-Host ""
Write-Host "Build complete."
Write-Host "Executable: $root\dist\PyQtPlotter\PyQtPlotter.exe"
