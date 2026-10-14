param(
    [switch]$Evaluate,
    [switch]$Scenario,
    [string]$ScenarioName = "bad_deployment",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Invoke-CheckedCommand {
    param(
        [string]$Label,
        [string[]]$CommandArgs
    )

    Write-Host ""
    Write-Host "== $Label =="
    & $CommandArgs[0] $CommandArgs[1..($CommandArgs.Length - 1)]

    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($CommandArgs -join ' ')"
    }
}

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    throw "Python 3.11+ was not found. Install Python and reopen PowerShell."
}

if (-not $SkipInstall) {
    Invoke-CheckedCommand -Label "Installing project dependencies" -CommandArgs @($pythonCmd.Source, "-m", "pip", "install", "-r", "requirements.txt")
    Invoke-CheckedCommand -Label "Installing local package in editable mode" -CommandArgs @($pythonCmd.Source, "-m", "pip", "install", "-e", ".")
}

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCmd) {
    Write-Host "Ollama is not installed or not on PATH."
    Write-Host "Install it from: https://ollama.com/download/windows"
    Write-Host "Then run: ollama pull qwen3:4b"
    exit 1
}

$ollamaListOutput = & ollama list 2>$null
if (-not ($ollamaListOutput -match "qwen3:4b")) {
    Write-Host "Qwen3 4B model is not present locally. Pulling it now..."
    Invoke-CheckedCommand -Label "Pulling Ollama model qwen3:4b" -CommandArgs @($ollamaCmd.Source, "pull", "qwen3:4b")
}

Write-Host "Ensuring Ollama server is running..."
$ollamaServeRunning = $false
try {
    $null = & ollama list 2>$null
    if ($LASTEXITCODE -eq 0) { $ollamaServeRunning = $true }
} catch {}

if (-not $ollamaServeRunning) {
    Start-Process -FilePath $ollamaCmd.Source -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

Invoke-CheckedCommand -Label "Running pytest checks" -CommandArgs @($pythonCmd.Source, "-m", "pytest", "-q")

if ($Evaluate) {
    Invoke-CheckedCommand -Label "Running evaluation harness" -CommandArgs @($pythonCmd.Source, "-m", "incident_triage_agent.cli", "--evaluate")
} elseif ($Scenario) {
    Invoke-CheckedCommand -Label "Running single scenario: $ScenarioName" -CommandArgs @($pythonCmd.Source, "-m", "incident_triage_agent.cli", "--scenario", $ScenarioName)
} else {
    Write-Host ""
    Write-Host "No mode selected. Examples:"
    Write-Host "  .\run_poc.ps1 -Scenario -ScenarioName bad_deployment"
    Write-Host "  .\run_poc.ps1 -Evaluate"
}
