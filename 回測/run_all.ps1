# run_all.ps1 — Launch all 3 autoresearch groups in parallel
# Usage: .\run_all.ps1 [-MaxSessions 10]
#
# Uses PowerShell jobs to run 3 run.ps1 instances concurrently.
# Outputs are merged into separate log files per group.
# Press Ctrl+C to stop all.

param(
    [int]$MaxSessions = 10
)

$ErrorActionPreference = "Stop"
$Groups = @("forex", "commod", "index")
$Jobs = @{}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Autoresearch — parallel run (3 groups)" -ForegroundColor Cyan
Write-Host " MaxSessions per group: $MaxSessions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    # Launch each group as a background job
    foreach ($g in $Groups) {
        Write-Host "[run_all] Starting $g..." -ForegroundColor Green
        $Jobs[$g] = Start-Job -Name "autoresearch-$g" -ScriptBlock {
            param($Script, $Group, $Max)
            & $Script -Group $Group -MaxSessions $Max
        } -ArgumentList (Join-Path $PSScriptRoot "run.ps1"), $g, $MaxSessions

        Start-Sleep -Seconds 3
    }

    Write-Host ""
    Write-Host "[run_all] All 3 groups launched. Monitoring..." -ForegroundColor Cyan
    Write-Host "[run_all] Press Ctrl+C to stop all." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Check progress in real-time:" -ForegroundColor Gray
    Write-Host "  Get-Content autoresearch-forex\run_powershell.log -Wait -Tail 20" -ForegroundColor Gray
    Write-Host "  Get-Content autoresearch-commod\run_powershell.log -Wait -Tail 20" -ForegroundColor Gray
    Write-Host "  Get-Content autoresearch-index\run_powershell.log -Wait -Tail 20" -ForegroundColor Gray
    Write-Host ""

    # Wait for all jobs, printing status every 60 seconds
    while ($true) {
        Start-Sleep -Seconds 60
        $Now = Get-Date -Format "HH:mm:ss"
        Write-Host ""
        Write-Host "=== Status check at $Now ===" -ForegroundColor Yellow

        $AllDone = $true
        foreach ($g in $Groups) {
            $job = $Jobs[$g]
            $state = $job.State
            if ($state -eq "Running") {
                $AllDone = $false
            }

            # Count experiments from results.tsv
            $resultsFile = Join-Path $PSScriptRoot "autoresearch-$g\results.tsv"
            $nExp = 0
            if (Test-Path $resultsFile) {
                $nExp = (Get-Content $resultsFile).Count - 1
            }

            # Count git commits
            $gitDir = Join-Path $PSScriptRoot "autoresearch-$g"
            Push-Location $gitDir
            $nCommits = (git log --oneline 2>$null | Measure-Object).Count
            Pop-Location

            Write-Host "  $g : state=$state, experiments=$nExp, commits=$nCommits" -ForegroundColor White
        }

        if ($AllDone) {
            Write-Host ""
            Write-Host "[run_all] All jobs finished." -ForegroundColor Green
            break
        }
    }

    # Collect outputs
    Write-Host ""
    Write-Host "=== Final outputs ===" -ForegroundColor Cyan
    foreach ($g in $Groups) {
        Write-Host "--- $g ---" -ForegroundColor Yellow
        Receive-Job -Job $Jobs[$g] -Keep | Select-Object -Last 20
    }
} finally {
    Write-Host ""
    Write-Host "[run_all] Cleaning up jobs..." -ForegroundColor Yellow
    foreach ($g in $Groups) {
        if ($Jobs[$g]) {
            Stop-Job -Job $Jobs[$g] -ErrorAction SilentlyContinue
            Remove-Job -Job $Jobs[$g] -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "[run_all] Done." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " All done." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
