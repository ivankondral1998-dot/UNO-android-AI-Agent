param(
    [string]$Data = 'D:\UNO\corpus_prepared_v4',
    [string]$Parent = 'D:\UNO\B2_512\latest.uno',
    [string]$Out = ('D:\UNO\r54_probe_' + (Get-Date -Format 'yyyyMMdd_HHmmss')),
    [switch]$Resume
)
$ErrorActionPreference = 'Stop'
$Python = 'D:\UNO\env\Scripts\python.exe'
$Trainer = Join-Path $PSScriptRoot 'trainer.py'

foreach ($Path in @($Data, $Parent, $Out, $Python, $Trainer)) {
    if ([IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path)) -ne 'D:\') {
        throw "Use drive D: for UNO project files ($Path)"
    }
}
foreach ($Path in @($Data, $Parent, $Python, $Trainer)) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Required path missing: $Path" }
}
$Cache = 'D:\UNO\r54_probe_cache'
New-Item -ItemType Directory -Force -Path $Cache | Out-Null
foreach ($Name in @('TEMP', 'TMP', 'TORCH_HOME', 'PYTHONPYCACHEPREFIX', 'CUDA_CACHE_PATH', 'XDG_CACHE_HOME')) {
    [Environment]::SetEnvironmentVariable($Name, $Cache, 'Process')
}
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CUBLAS_WORKSPACE_CONFIG = ':4096:8'
# Clear inherited device hiding so telemetry and CUDA refer to the same single GPU.
Remove-Item Env:CUDA_VISIBLE_DEVICES -ErrorAction SilentlyContinue
$Arguments = @($Trainer, 'probe', '--out', $Out, '--parent', $Parent, '--data', $Data,
               '--device', 'cuda', '--steps', '3', '--seconds', '150')
if ($Resume) { $Arguments += '--resume' }
& $Python @Arguments
exit $LASTEXITCODE
