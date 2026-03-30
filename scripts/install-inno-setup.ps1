param(
    [string]$Version = "6.7.1"
)

$ErrorActionPreference = "Stop"

function Get-IsccPath {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $repoRoot = Split-Path -Parent $PSScriptRoot
    $localPath = Join-Path $repoRoot ".tools\InnoSetup\ISCC.exe"
    if (Test-Path $localPath) {
        return $localPath
    }

    return $null
}

$existing = Get-IsccPath
if ($existing) {
    Write-Output $existing
    exit 0
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $repoRoot ".tools"
$installDir = Join-Path $toolsRoot "InnoSetup"
$downloadDir = Join-Path $toolsRoot "downloads"
$installerPath = Join-Path $downloadDir "innosetup-$Version.exe"
$releaseTag = "is-" + ($Version -replace "\.", "_")
$downloadUrl = "https://github.com/jrsoftware/issrc/releases/download/$releaseTag/innosetup-$Version.exe"

New-Item -ItemType Directory -Force -Path $installDir | Out-Null
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null

Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath

$arguments = @(
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART",
    "/SP-",
    "/CURRENTUSER",
    "/DIR=`"$installDir`""
)

$process = Start-Process -FilePath $installerPath -ArgumentList $arguments -PassThru -Wait
if ($process.ExitCode -ne 0) {
    throw "Inno Setup installer exited with code $($process.ExitCode)."
}

$isccPath = Get-ChildItem -Path $installDir -Filter ISCC.exe -Recurse -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName -First 1
if (-not $isccPath -or -not (Test-Path $isccPath)) {
    throw "ISCC.exe was not found after installation."
}

Write-Output $isccPath
