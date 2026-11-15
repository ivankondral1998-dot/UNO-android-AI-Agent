param(
    [ValidateSet('Check','Plan','Train','Resume','Suite','Evaluate')][string]$Mode='Check',
    [string]$Arm='',
    [int]$Seed=260015
)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Install Python3.12 + CUDA torch in .venv as README.md describes.' }
$env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
$env:PYTHONOPTIMIZE='0'
foreach ($line in Get-Content SHA256SUMS) {
    $parts=$line -split '  ',2
    if ($parts.Length -ne 2) { throw 'Malformed SHA256SUMS' }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $parts[1]).Hash.ToLowerInvariant() -ne $parts[0]) { throw "Bundle checksum mismatch: $($parts[1])" }
}
function Invoke-Checked([string[]]$Arguments) {
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Stopped with exit $LASTEXITCODE; preserve logs and checkpoints." }
}
New-Item -ItemType Directory -Force -Path logs | Out-Null
Start-Transcript -Path (Join-Path 'logs' ($Mode+'-'+[DateTime]::UtcNow.Ticks+'.txt')) | Out-Null
try {
    if ($Mode -eq 'Check') {
        & nvidia-smi
        if ($LASTEXITCODE -ne 0) { throw 'NVIDIA monitor unavailable.' }
        Invoke-Checked -Arguments @('train002/check.py','study','--receipt','cuda-check.json')
    } elseif ($Mode -eq 'Plan') {
        Invoke-Checked -Arguments @('train002/study.py','plan','study','--output','runs')
    } elseif ($Mode -eq 'Evaluate') {
        Invoke-Checked -Arguments @('train002/study.py','evaluate','study','--output','runs')
    } else {
        if (!(Test-Path 'cuda-check.json')) { throw 'Run Check first.' }
        if ($Mode -eq 'Suite') {
            Invoke-Checked -Arguments @('train002/study.py','suite','study','--output','runs','--receipt','cuda-check.json','--max-seconds','1800')
        } else {
            if ($Arm -eq '') { throw 'Specify -Arm; use Plan to see the predeclared arms.' }
            $command=if ($Mode -eq 'Resume') {'resume'} else {'train'}
            Invoke-Checked -Arguments @('train002/study.py',$command,'study','--output','runs','--arm',$Arm,'--seed',"$Seed",'--device','cuda','--receipt','cuda-check.json','--max-seconds','1800')
        }
    }
} finally { Stop-Transcript | Out-Null }
