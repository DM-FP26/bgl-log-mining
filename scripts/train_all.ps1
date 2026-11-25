# Train the LSTM, then the GRU on the GPU. Run from the repo root in PowerShell:
#   .\scripts\train_all.ps1            (first time)
#   .\scripts\train_all.ps1 -Resume    (continue after a crash)
#   .\scripts\train_all.ps1 -BatchSize 256   (if you get "CUDA out of memory")
param(
    [switch]$Resume,
    [int]$BatchSize = 0
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

if (Test-Path ".\.venv\Scripts\Activate.ps1") { . .\.venv\Scripts\Activate.ps1 }

python scripts/check_gpu.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "GPU check failed. Do NOT continue. See docs/GPU-HANDOFF-FRIEND.md and send Nafi a screenshot." -ForegroundColor Red
    exit 1
}

foreach ($model in @("lstm", "gru")) {
    $argsList = @("scripts/train.py", "--config", "configs/train.yaml", "--model", $model,
                  "--device", "cuda", "--out", "handoff/results/$model")
    if ($Resume) { $argsList += "--resume" }
    if ($BatchSize -gt 0) { $argsList += @("--batch-size", "$BatchSize") }
    Write-Host "=== Training $model ===" -ForegroundColor Cyan
    python @argsList
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Training $model failed. Run again with -Resume, or send Nafi a screenshot." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "DONE. Now send the results back:" -ForegroundColor Green
Write-Host "  git add handoff/results"
Write-Host "  git status        (only files under handoff/results should be listed)"
Write-Host "  git commit -m 'GPU training results: lstm + gru'"
Write-Host "  git push -u origin gpu-run"
