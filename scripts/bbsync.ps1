# bbsync.ps1 — scripts/bbsync.sh icin PowerShell sarmalayicisi.
# Git for Windows ile gelen bash.exe uzerinden calistirir.
#
#   .\scripts\bbsync.ps1 setup IODT-123
#   .\scripts\bbsync.ps1 init
#   .\scripts\bbsync.ps1 status
#   .\scripts\bbsync.ps1 push

param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $Args)

$ErrorActionPreference = 'Stop'

function Find-Bash {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        # ...\Git\cmd\git.exe -> ...\Git\bin\bash.exe
        $candidate = Join-Path (Split-Path (Split-Path $git.Source)) 'bin\bash.exe'
        if (Test-Path $candidate) { return $candidate }
    }
    $onPath = Get-Command bash -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    throw "bash.exe bulunamadi. Git for Windows kurulu mu?"
}

$bash   = Find-Bash
$script = Join-Path $PSScriptRoot 'bbsync.sh'

& $bash $script @Args
exit $LASTEXITCODE
