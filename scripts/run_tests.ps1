param(
    [switch]$WithPostgres
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
    throw "Create the virtual environment first: python -m venv .venv"
}

if ($WithPostgres) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is required for -WithPostgres. Start/install Docker Desktop, then run this command again."
    }
    docker compose up -d postgres
    $ready = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        docker compose exec -T postgres pg_isready -U krishi -d krishi_awaaz | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        throw "PostgreSQL did not become ready within 40 seconds."
    }
    $env:DATABASE_URL = "postgresql+psycopg://krishi:krishi@localhost:5432/krishi_awaaz"
    $env:RUN_POSTGRES_TESTS = "1"
}

.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pytest -q
