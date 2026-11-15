param([ValidateSet('Check','Train','Resume','Evaluate')][string]$Mode = 'Check')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Create .venv and install the CUDA torch wheel as README_RTX.md describes.' }
$env:CUBLAS_WORKSPACE_CONFIG = ':4096:8'
$env:PYTHONOPTIMIZE = '0'
foreach ($line in Get-Content SHA256SUMS) {
    $parts = $line -split '  ', 2
    if ($parts.Length -ne 2) { throw 'Malformed SHA256SUMS' }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $parts[1]).Hash.ToLowerInvariant()
    if ($actual -ne $parts[0]) { throw "Bundle checksum mismatch: $($parts[1])" }
}
function Invoke-CheckedPython([string[]]$Arguments) {
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python stopped (exit $LASTEXITCODE). Preserve logs and checkpoint." }
}
New-Item -ItemType Directory -Force -Path logs | Out-Null
$log = Join-Path 'logs' ($Mode + '-' + [DateTime]::UtcNow.Ticks + '.txt')
Start-Transcript -Path $log | Out-Null
try {
$receipt = 'cuda-check.json'
if ($Mode -eq 'Check') {
    if (Test-Path $receipt) { throw 'CUDA check receipt already exists. Preserve it; choose a fresh extracted copy to repeat.' }
    & nvidia-smi
    if ($LASTEXITCODE -ne 0) { throw 'NVIDIA driver/monitor unavailable.' }
    Invoke-CheckedPython -Arguments @('rtx_check.py', '--output', $receipt)
} elseif ($Mode -eq 'Train' -or $Mode -eq 'Resume') {
    if (!(Test-Path $receipt)) { throw 'Run .\RTX.ps1 Check first. No CUDA check receipt.' }
    $arguments = @('torch_backend.py','train','.','rtx_run','--device','cuda','--precision','float32','--steps','1000','--batch','4','--seed','150015','--max-seconds','1800','--max-temp','78','--max-mib','6500','--cuda-receipt',$receipt)
    if ($Mode -eq 'Resume') { $arguments += '--resume' }
    Invoke-CheckedPython -Arguments $arguments
} else {
    Invoke-CheckedPython -Arguments @('torch_backend.py','evaluate','.','rtx_run')
}

} finally { Stop-Transcript | Out-Null }
