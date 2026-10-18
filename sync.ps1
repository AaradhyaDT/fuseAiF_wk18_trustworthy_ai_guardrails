<#
.SYNOPSIS
    Automates Git pull, auto-commit generation, pre-commit hygiene checks, and push for fuseAiF_wk18_trustworthy_ai_guardrails.

.DESCRIPTION
    1. Runs linter (ruff) and tests (pytest).
    2. Pulls with --autostash so local work is preserved.
    3. Auto-generates conventional commit message if none provided.
    4. Stages, commits, and pushes to origin main.

.EXAMPLE
    .\sync.ps1
    .\sync.ps1 -m "feat(guardrails): add input pii detector"
    .\sync.ps1 -PullOnly
#>

param (
    [Alias("m")]
    [string]$Message,

    [switch]$PullOnly,

    [switch]$SkipTests,

    [switch]$WhatIf
)

$ErrorActionPreference = "Continue"

Write-Host "[Git Sync] Repository: fuseAiF_wk18_trustworthy_ai_guardrails" -ForegroundColor Cyan

# 1. Verification Gate
if (-not $SkipTests -and -not $PullOnly) {
    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        Write-Host "[Verify] Running ruff lint check..." -ForegroundColor Yellow
        ruff check .
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Ruff check failed! Aborting sync." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }

    if (Get-Command pytest -ErrorAction SilentlyContinue) {
        if (Test-Path "tests") {
            Write-Host "[Verify] Running pytest suite..." -ForegroundColor Yellow
            pytest tests/ -q
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] Pytest suite failed! Aborting sync." -ForegroundColor Red
                exit $LASTEXITCODE
            }
        }
    }
}

# 2. Pull latest
Write-Host "[Git Sync] Pulling latest changes from origin main..." -ForegroundColor Cyan
git pull --autostash origin main

if ($PullOnly) {
    Write-Host "[Git Sync] Pull complete (PullOnly mode)." -ForegroundColor Green
    exit 0
}

# 3. Check diff
$statusLines = git status --porcelain
if (-not $statusLines) {
    Write-Host "[Git Sync] Working tree clean. Nothing to commit." -ForegroundColor Green
    exit 0
}

# 4. Determine commit message
if (-not $Message) {
    $added = @($statusLines | Where-Object { $_ -match 'A|\?\?' }).Count
    $modified = @($statusLines | Where-Object { $_ -match '^\s*M' }).Count
    $deleted = @($statusLines | Where-Object { $_ -match 'D' }).Count

    if ($added -gt 0 -and $modified -eq 0) {
        $Message = "feat(guardrails): add initial components and evaluation suite"
    } elseif ($modified -gt 0) {
        $Message = "refactor(guardrails): update pipeline and tests"
    } else {
        $Message = "chore: update repository files"
    }
}

if ($WhatIf) {
    Write-Host "[WhatIf] Staged changes detected. Commit message would be: $Message" -ForegroundColor Magenta
    git status
    exit 0
}

# 5. Stage, commit & push
Write-Host "[Git Sync] Staging changes..." -ForegroundColor Cyan
git add .

Write-Host "[Git Sync] Committing with: '$Message'" -ForegroundColor Cyan
git commit -m "$Message"

Write-Host "[Git Sync] Pushing to origin main..." -ForegroundColor Cyan
git push origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "[Git Sync] Push rejected. Retrying with pull --rebase..." -ForegroundColor Yellow
    git pull --rebase origin main
    git push origin main
}

Write-Host "[Git Sync] Synchronization complete!" -ForegroundColor Green
