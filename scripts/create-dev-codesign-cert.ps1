param(
    [string]$Subject = "CN=Eleven GUI Dev",
    [string]$Password = "ElevenGUI-Dev-Only",
    [string]$OutputDir = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $OutputDir = Join-Path $repoRoot ".certs"
}

$storePath = "Cert:\CurrentUser\My"
$trustedPeopleStorePath = "Cert:\CurrentUser\TrustedPeople"
$trustedPublisherStorePath = "Cert:\CurrentUser\TrustedPublisher"
$rootStorePath = "Cert:\CurrentUser\Root"

$existing = Get-ChildItem $storePath | Where-Object { $_.Subject -eq $Subject } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $existing) {
    $existing = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $Subject `
        -CertStoreLocation $storePath `
        -KeyExportPolicy Exportable `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -HashAlgorithm SHA256 `
        -NotAfter (Get-Date).AddYears(3)
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$safePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$pfxPath = Join-Path $OutputDir "ElevenGUI-DevCodeSign.pfx"
$cerPath = Join-Path $OutputDir "ElevenGUI-DevCodeSign.cer"

Export-PfxCertificate -Cert $existing -FilePath $pfxPath -Password $safePassword | Out-Null
Export-Certificate -Cert $existing -FilePath $cerPath | Out-Null
Import-Certificate -FilePath $cerPath -CertStoreLocation $trustedPeopleStorePath | Out-Null
Import-Certificate -FilePath $cerPath -CertStoreLocation $trustedPublisherStorePath | Out-Null
Import-Certificate -FilePath $cerPath -CertStoreLocation $rootStorePath | Out-Null

if (-not $Quiet) {
    Write-Host "Subject: $($existing.Subject)"
    Write-Host "Thumbprint: $($existing.Thumbprint)"
    Write-Host "PFX: $pfxPath"
    Write-Host "CER: $cerPath"
}
Write-Output $existing.Thumbprint
