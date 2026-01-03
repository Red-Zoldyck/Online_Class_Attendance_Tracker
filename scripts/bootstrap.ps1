param(
    [string]$Python = "python",
    [string]$DbEngine = "django.db.backends.mysql",
    [string]$DbName = "attendance_tracker",
    [string]$DbUser = "root",
    [string]$DbPassword = "@dmin123",
    [string]$DbHost = "localhost",
    [string]$DbPort = "3306",
    [switch]$ImportStudents,
    [string]$DumpPath = "./Dump20260102.sql"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $here

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )
    Write-Host "==> $Message" -ForegroundColor Cyan
    & $Action
}

function Ensure-Venv {
    param(
        [string]$PythonExe
    )
    $venvPython = Join-Path $here "venv/Scripts/python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating virtual environment with $PythonExe" -ForegroundColor Yellow
        & $PythonExe -m venv venv
    }
    return $venvPython
}

$venvPy = Invoke-Step "Ensure virtualenv" { Ensure-Venv -PythonExe $Python }

Invoke-Step "Upgrade pip" { & $venvPy -m pip install --upgrade pip }
Invoke-Step "Install requirements" { & $venvPy -m pip install -r requirements.txt }

# Set database env vars for downstream Django commands
$env:DB_ENGINE = $DbEngine
$env:DB_NAME = $DbName
$env:DB_USER = $DbUser
$env:DB_PASSWORD = $DbPassword
$env:DB_HOST = $DbHost
$env:DB_PORT = $DbPort

Invoke-Step "Apply migrations" { & $venvPy manage.py migrate }
Invoke-Step "Seed groups/permissions" { & $venvPy scripts/setup_groups.py }

if ($ImportStudents) {
    if (-not (Test-Path $DumpPath)) {
        throw "Dump file not found: $DumpPath"
    }
    Invoke-Step "Import students from dump" { & $venvPy scripts/import_students_from_dump.py }
}

Write-Host "Bootstrap complete. You can now run: `venv\\Scripts\\python.exe manage.py runserver`" -ForegroundColor Green
