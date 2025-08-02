# Diagnostic Agent CLI Wrapper Script for Windows
# Makes it easy to interact with the diagnostic agent

param(
    [string]$Question,
    [string]$Host = $env:DIAGNOSTIC_AGENT_HOST ?? "localhost",
    [int]$Port = $env:DIAGNOSTIC_AGENT_PORT ?? 5000,
    [string]$ActivationWord = $env:ACTIVATION_WORD,
    [switch]$Interactive,
    [switch]$Status,
    [switch]$Verbose,
    [switch]$Help
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliScript = Join-Path $scriptDir "cli_prompt.py"

# Check if Python script exists
if (!(Test-Path $cliScript)) {
    Write-Host "ERR: CLI script not found at $cliScript" -ForegroundColor Red
    exit 1
}

# Show usage if no arguments or help requested
if ($Help -or ($args.Count -eq 0 -and !$Interactive -and !$Status -and !$Question)) {
    Write-Host "Diagnostic Agent CLI" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\prompt.ps1 -Question `"Your question here`"          # Ask a single question"
    Write-Host "  .\prompt.ps1 -Interactive                              # Start interactive mode"
    Write-Host "  .\prompt.ps1 -Status                                   # Check agent status"
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -Question STRING      Question to ask the agent"
    Write-Host "  -Host STRING         Host where agent is running (default: $Host)"
    Write-Host "  -Port INT            Port where agent is listening (default: $Port)"
    Write-Host "  -ActivationWord STR  Activation word for protected endpoints"
    Write-Host "  -Interactive         Start interactive mode"
    Write-Host "  -Status              Check agent status"
    Write-Host "  -Verbose             Enable debug output"
    Write-Host "  -Help                Show this help"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\prompt.ps1 -Question `"What is the system status?`""
    Write-Host "  .\prompt.ps1 -Question `"Check network connectivity`""
    Write-Host "  .\prompt.ps1 -Question `"Scan for running processes`""
    Write-Host "  .\prompt.ps1 -Interactive"
    Write-Host "  .\prompt.ps1 -Host 192.168.1.100 -Question `"System health check`""
    Write-Host ""
    Write-Host "Environment Variables:" -ForegroundColor Gray
    Write-Host "  DIAGNOSTIC_AGENT_HOST  - Default host"
    Write-Host "  DIAGNOSTIC_AGENT_PORT  - Default port"
    Write-Host "  ACTIVATION_WORD        - Default activation word"
    Write-Host ""
    exit 0
}

# Build the Python command arguments
$pythonArgs = @(
    $cliScript,
    "--host", $Host,
    "--port", $Port
)

if ($ActivationWord) {
    $pythonArgs += @("--activation-word", $ActivationWord)
}

if ($Interactive) {
    $pythonArgs += "--interactive"
}

if ($Status) {
    $pythonArgs += "--status"
}

if ($Verbose) {
    $pythonArgs += "--verbose"
}

if ($Question) {
    $pythonArgs += $Question
}

# Execute the Python CLI script
try {
    & python $pythonArgs
} catch {
    Write-Host "ERR: Error executing CLI script: $_" -ForegroundColor Red
    exit 1
}
