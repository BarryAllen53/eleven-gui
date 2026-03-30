param(
    [string]$Version = "1.0.1",
    [switch]$SkipPortableBuild
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $root "dist\release"
$portableDir = Join-Path $releaseDir "ElevenGUI-$Version-win64"
$portableExe = Join-Path $portableDir "ElevenGUI.exe"
$installerScript = Join-Path $root "installer\ElevenGUI.iss"

if (-not $SkipPortableBuild -or -not (Test-Path $portableExe)) {
    & (Join-Path $PSScriptRoot "build-release.ps1") -Version $Version
    if ($LASTEXITCODE -ne 0) {
        throw "Portable build failed."
    }
}

if (-not (Test-Path $portableExe)) {
    throw "Portable executable was not found at '$portableExe'."
}

& (Join-Path $PSScriptRoot "sign-artifact.ps1") -Files @($portableExe)

$portableZip = Join-Path $releaseDir "ElevenGUI-$Version-win64.zip"
if (Test-Path $portableZip) {
    Remove-Item $portableZip -Force
}
Compress-Archive -Path (Join-Path $portableDir "*") -DestinationPath $portableZip

$isccPath = & (Join-Path $PSScriptRoot "install-inno-setup.ps1")
if (-not (Test-Path $isccPath)) {
    throw "ISCC.exe was not found."
}

& $isccPath "/DMyAppVersion=$Version" "/DReleaseDir=$releaseDir" $installerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed."
}

$installerPath = Join-Path $releaseDir "ElevenGUI-$Version-setup.exe"
if (-not (Test-Path $installerPath)) {
    throw "Installer output was not found at '$installerPath'."
}

& (Join-Path $PSScriptRoot "sign-artifact.ps1") -Files @($installerPath)

Write-Host "Installer:" $installerPath
