# run.ps1 — Single-group autoresearch loop (PowerShell version)
# Usage: .\run.ps1 -Group forex [-MaxSessions 10]
#
# Runs claude -p for one group, restarting after each session until MaxSessions reached
# or script is interrupted with Ctrl+C.

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("forex", "commod", "index", "v2")]
    [string]$Group,

    [int]$MaxSessions = 20  # safety limit

)

$ErrorActionPreference = "Stop"
$GroupDir = Join-Path $PSScriptRoot "autoresearch-$Group"

if (-not (Test-Path $GroupDir)) {
    Write-Host "ERROR: $GroupDir does not exist" -ForegroundColor Red
    exit 1
}

# Count existing sessions from knowledge_history
$HistoryDir = Join-Path $GroupDir "knowledge_history"
$ExistingSessions = 0
if (Test-Path $HistoryDir) {
    $ExistingSessions = (Get-ChildItem -Path $HistoryDir -Filter "session_*.md" -ErrorAction SilentlyContinue).Count
}
$StartSession = $ExistingSessions + 1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Autoresearch: $Group" -ForegroundColor Cyan
Write-Host " Directory: $GroupDir" -ForegroundColor Cyan
Write-Host " Starting from session $StartSession" -ForegroundColor Cyan
Write-Host " Max sessions: $MaxSessions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$LogFile = Join-Path $GroupDir "run_powershell.log"

$Session = $StartSession
$MaxSession = $StartSession + $MaxSessions - 1

while ($Session -le $MaxSession) {
    $Now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host ""
    Write-Host "=== Session $Session starting at $Now ===" -ForegroundColor Yellow
    Write-Host "Log: $LogFile" -ForegroundColor Gray

    $StartExp = ($Session - 1) * 50 + 1
    $Prompt = @"
讀 CLAUDE.md 和 program.md, 然後開始 autoresearch loop.
如果 knowledge.md 存在先讀它了解前幾個 session 的結論.
你是 session $Session. 從 exp $StartExp 開始編號.
不要停, 不要問人. 看到 PLATEAU_DETECTED 就執行 reset 流程 (更新 knowledge.md, 複製到 knowledge_history/session_${Session}.md, commit, 然後結束).
"@

    # Change to group directory and run claude
    Push-Location $GroupDir
    try {
        "=== Session $Session at $Now ===" | Out-File -FilePath $LogFile -Append -Encoding utf8
        # Run claude and capture output
        & claude --permission-mode auto -p $Prompt *>&1 | Tee-Object -FilePath $LogFile -Append
        $ExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "=== Session $Session ended (exit: $ExitCode) ===" -ForegroundColor Green

    # Check if knowledge file was created
    $KnowledgeFile = Join-Path $HistoryDir "session_${Session}.md"
    if (Test-Path $KnowledgeFile) {
        Write-Host "Knowledge: $KnowledgeFile created" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Knowledge file NOT created (session may have crashed)" -ForegroundColor Yellow
    }

    $Session++

    if ($Session -le $MaxSession) {
        Write-Host "=== Waiting 10s before next session... ===" -ForegroundColor Gray
        Start-Sleep -Seconds 10
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Done. Ran $($Session - $StartSession) sessions for $Group." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
