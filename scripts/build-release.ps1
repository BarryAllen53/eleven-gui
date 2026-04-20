param(
    [string]$Version = "1.0.2"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $root "build"
$distDir = Join-Path $root "dist"
$artifactDir = Join-Path $distDir "release"
$nuitkaRoot = Join-Path $root ".nuitka"
$localAppDataDir = Join-Path $nuitkaRoot "localappdata"
$appDataDir = Join-Path $nuitkaRoot "appdata"
$homeDir = Join-Path $nuitkaRoot "home"
$tempDir = Join-Path $nuitkaRoot "temp"
$cacheDir = Join-Path $nuitkaRoot "cache"
$downloadsDir = Join-Path $nuitkaRoot "downloads"
$pipCacheDir = Join-Path $nuitkaRoot "pip-cache"

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path $localAppDataDir | Out-Null
New-Item -ItemType Directory -Force -Path $appDataDir | Out-Null
New-Item -ItemType Directory -Force -Path $homeDir | Out-Null
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $downloadsDir | Out-Null
New-Item -ItemType Directory -Force -Path $pipCacheDir | Out-Null

$env:LOCALAPPDATA = $localAppDataDir
$env:APPDATA = $appDataDir
$env:USERPROFILE = $homeDir
$env:HOME = $homeDir
$env:TEMP = $tempDir
$env:TMP = $tempDir
$env:PIP_CACHE_DIR = $pipCacheDir
$env:NUITKA_CACHE_DIR_BYTECODE = Join-Path $cacheDir "bytecode"
$env:NUITKA_CACHE_DIR_DLL_DEPENDENCIES = Join-Path $cacheDir "dll-dependencies"
$env:NUITKA_CACHE_DIR_CCACHE = Join-Path $cacheDir "ccache"
$env:NUITKA_CACHE_DIR_DOWNLOADS = $downloadsDir

python -m pip install -r (Join-Path $root "requirements.txt")

python -m nuitka `
  --onefile `
  --mingw64 `
  --assume-yes-for-downloads `
  --clean-cache=all `
  --enable-plugin=pyside6 `
  --windows-console-mode=disable `
  --company-name="BarryAllen53" `
  --product-name="Eleven GUI" `
  --file-description="Accessible ElevenLabs desktop client" `
  --file-version="$Version.0" `
  --product-version="$Version.0" `
  --output-dir="$buildDir" `
  --output-filename="ElevenGUI.exe" `
  --onefile-tempdir-spec="{CACHE_DIR}/ElevenGUI/{VERSION}" `
  --include-data-dir="$root\\eleven_gui\\assets=eleven_gui/assets" `
  "$root\\main.py"

$exePath = Join-Path $buildDir "main.onefile.exe"
if (-not (Test-Path $exePath)) {
    $exePath = Join-Path $buildDir "ElevenGUI.exe"
}

if (-not (Test-Path $exePath)) {
    throw "Nuitka build did not produce an executable."
}

$portableDir = Join-Path $artifactDir "ElevenGUI-$Version-win64"
New-Item -ItemType Directory -Force -Path $portableDir | Out-Null
Copy-Item $exePath (Join-Path $portableDir "ElevenGUI.exe") -Force
Copy-Item (Join-Path $root ".env.example") (Join-Path $portableDir ".env.example") -Force
Copy-Item (Join-Path $root "README.md") (Join-Path $portableDir "README.md") -Force
Copy-Item (Join-Path $root "LICENSE") (Join-Path $portableDir "LICENSE") -Force
Set-Content -Path (Join-Path $portableDir ".portable") -Value "portable" -Encoding ascii

$zipPath = Join-Path $artifactDir "ElevenGUI-$Version-win64.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path (Join-Path $portableDir "*") -DestinationPath $zipPath

Write-Host "Executable:" (Join-Path $portableDir "ElevenGUI.exe")
Write-Host "Archive:" $zipPath
