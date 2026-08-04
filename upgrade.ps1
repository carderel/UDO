# UDO upgrade wrapper. All logic lives in upgrade.py (cross-platform,
# stdlib-only); this script just execs it with whichever Python launcher
# is on PATH.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$UpgradePy = Join-Path $ScriptDir "upgrade.py"

$python3 = Get-Command python3 -ErrorAction SilentlyContinue
if ($python3) {
    & python3 $UpgradePy @args
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 $UpgradePy @args
    exit $LASTEXITCODE
}

Write-Host "Error: no python3 or py -3 launcher found on PATH." -ForegroundColor Red
Write-Host "Install Python 3 and re-run this script." -ForegroundColor Red
exit 1
