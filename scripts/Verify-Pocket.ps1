# Pocket portable offline integrity verification (no network or admin rights).
# Run only if your organization's script policy permits PowerShell scripts.
param([switch]$SkipRuntimeTest)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifest = Join-Path $root 'bundle-manifest.sha256'
$exe = Join-Path $root 'PocketDesk.exe'
$internal = Join-Path $root '_internal'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    Write-Error 'Missing bundle-manifest.sha256: extract a fresh ZIP'; exit 2
}
$bad = 0
$seen = 0
foreach ($line in Get-Content -LiteralPath $manifest -Encoding UTF8) {
    if ($line -notmatch '^([0-9a-f]{64})  (.+)$') {
        Write-Warning "Invalid manifest entry: $line"; $bad++; continue
    }
    $expected = $Matches[1]
    $name = $Matches[2]
    $path = Join-Path $root ($name.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Write-Warning "MISSING: $name"; $bad++; continue
    }
    try {
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { Write-Warning "CHANGED: $name"; $bad++ }
    } catch {
        Write-Warning "UNREADABLE: $name"; $bad++
    }
    $seen++
}
foreach ($name in @('PIL\_imaging*.pyd', '_ctypes*.pyd', '_tkinter*.pyd', 'unicodedata*.pyd')) {
    if (-not @(Get-ChildItem -Path (Join-Path $internal $name) -ErrorAction SilentlyContinue).Count) {
        Write-Warning "MISSING DLL: $name"; $bad++
    }
}
Write-Host "Checked $seen files; errors: $bad"
if ($bad -gt 0) {
    Write-Host 'Re-extract the complete ZIP to a NEW local folder; contact IT if files are blocked.'
    exit 2
}
Write-Host 'PASS: bundled files match SHA256 manifest'
if ($SkipRuntimeTest) { exit 0 }
$log = Join-Path $env:TEMP ("Pocket-deps-{0}.log" -f $PID)
try {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $exe
    $info.WorkingDirectory = $root
    $info.Arguments = '--self-test-deps --deps-log="' + $log + '"'
    $info.UseShellExecute = $false
    $process = [System.Diagnostics.Process]::Start($info)
    if (-not $process.WaitForExit(45000)) {
        $process.Kill(); $process.WaitForExit()
        Write-Warning 'Runtime check timed out'; exit 3
    }
    if ($process.ExitCode -ne 0) {
        Write-Warning "Runtime check failed: $($process.ExitCode)"
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log }
        else { Write-Host 'No traceback: EXE bootloader or security policy may have blocked execution.' }
        exit 3
    }
    if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force }
    Write-Host 'PASS: _ctypes, unicodedata, _tkinter, Pillow and ImageTk work'
    exit 0
} catch {
    Write-Warning "Could not start test: $_"
    Write-Host 'Ask IT to inspect Windows Defender / AppLocker / WDAC / EDR logs.'
    exit 3
}
