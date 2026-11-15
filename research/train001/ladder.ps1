# Run from repo root; JDK21 + Kotlin2.2.21 on PATH. CPU Double only.
$ErrorActionPreference = 'Stop'
$build = Join-Path ([System.IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $build | Out-Null
try {
    $sources = @(Get-ChildItem android/core/src/main/kotlin/org/unovyra/uno/core/*.kt | ForEach-Object FullName)
    $sources += (Resolve-Path research/f-gradients/ReverseF.kt).Path
    $sources += (Resolve-Path research/f-gradients/LearnedMemory.kt).Path
    $sources += @(Get-ChildItem research/train001/*.kt | ForEach-Object FullName)
    $jar = Join-Path $build 'train.jar'
    & kotlinc @sources -include-runtime -d $jar
    if ($LASTEXITCODE -ne 0) { throw 'Kotlin compilation failed' }
    & java -Xmx1500m -cp $jar org.unovyra.uno.research.LadderRunKt @args
    if ($LASTEXITCODE -ne 0) { throw 'Trainer refused or failed; preserve checkpoint directory' }
} finally {
    Remove-Item -Recurse -Force $build
}
