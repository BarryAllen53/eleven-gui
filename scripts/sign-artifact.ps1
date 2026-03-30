param(
    [Parameter(Mandatory = $true)]
    [string[]]$Files,
    [switch]$Required
)

$ErrorActionPreference = "Stop"

function Resolve-SignToolPath {
    if ($env:SIGNTOOL_PATH -and (Test-Path $env:SIGNTOOL_PATH)) {
        return $env:SIGNTOOL_PATH
    }

    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $sdkRoots = @(
        "C:\Program Files (x86)\Windows Kits\10\bin",
        "C:\Program Files\Windows Kits\10\bin"
    )

    foreach ($sdkRoot in $sdkRoots) {
        if (-not (Test-Path $sdkRoot)) {
            continue
        }
        $candidate = Get-ChildItem -Path $sdkRoot -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    return $null
}

function Resolve-CodeSigningCertificate {
    $storePath = "Cert:\CurrentUser\My"

    if ($env:CODESIGN_CERT_THUMBPRINT) {
        $thumbprint = ($env:CODESIGN_CERT_THUMBPRINT -replace "\s", "").ToUpperInvariant()
        $cert = Get-ChildItem $storePath | Where-Object { $_.Thumbprint -eq $thumbprint } | Select-Object -First 1
        if ($cert) {
            return $cert
        }
    }

    if ($env:CODESIGN_CERT_SUBJECT) {
        $subject = $env:CODESIGN_CERT_SUBJECT.Trim()
        $cert = Get-ChildItem $storePath | Where-Object { $_.Subject -like "*$subject*" } |
            Sort-Object NotAfter -Descending |
            Select-Object -First 1
        if ($cert) {
            return $cert
        }
    }

    if ($env:CODESIGN_CERT_PATH) {
        if (-not (Test-Path $env:CODESIGN_CERT_PATH)) {
            throw "Signing certificate was not found at '$($env:CODESIGN_CERT_PATH)'."
        }

        if (-not $env:CODESIGN_CERT_PASSWORD) {
            throw "CODESIGN_CERT_PASSWORD must be set when CODESIGN_CERT_PATH is used."
        }

        $securePassword = ConvertTo-SecureString $env:CODESIGN_CERT_PASSWORD -AsPlainText -Force
        $imported = Import-PfxCertificate -FilePath $env:CODESIGN_CERT_PATH -CertStoreLocation $storePath -Password $securePassword -Exportable
        return $imported
    }

    if ($env:CODESIGN_USE_DEV_CERT -eq "1") {
        $created = & (Join-Path $PSScriptRoot "create-dev-codesign-cert.ps1") -Quiet
        $thumbprint = ($created | Select-Object -Last 1).Trim()
        $cert = Get-ChildItem $storePath | Where-Object { $_.Thumbprint -eq $thumbprint } | Select-Object -First 1
        if ($cert) {
            return $cert
        }
    }

    return $null
}

$timestampUrl = if ($env:CODESIGN_TIMESTAMP_URL) { $env:CODESIGN_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }
$cert = Resolve-CodeSigningCertificate

if (-not $cert) {
    $message = "Code signing skipped. Provide a certificate through CODESIGN_CERT_PATH plus CODESIGN_CERT_PASSWORD, or use CODESIGN_CERT_THUMBPRINT / CODESIGN_CERT_SUBJECT, or set CODESIGN_USE_DEV_CERT=1."
    if ($Required) {
        throw $message
    }
    Write-Host $message
    exit 0
}

$signTool = Resolve-SignToolPath
$useSignTool = $signTool -and $env:CODESIGN_CERT_PATH -and $env:CODESIGN_CERT_PASSWORD

foreach ($file in $Files) {
    if (-not (Test-Path $file)) {
        $message = "Signing target '$file' was not found."
        if ($Required) {
            throw $message
        }
        Write-Host $message
        continue
    }

    if ($useSignTool) {
        & $signTool sign /fd SHA256 /td SHA256 /tr $timestampUrl /f $env:CODESIGN_CERT_PATH /p $env:CODESIGN_CERT_PASSWORD $file
        if ($LASTEXITCODE -ne 0) {
            throw "signtool failed for '$file' with exit code $LASTEXITCODE."
        }
        Write-Host "Signed $file with signtool"
        continue
    }

    $result = Set-AuthenticodeSignature -FilePath $file -Certificate $cert -TimestampServer $timestampUrl -HashAlgorithm SHA256
    if ($result.Status -notin @("Valid", "NotTrusted")) {
        throw "Authenticode signing failed for '$file' with status '$($result.Status)'."
    }
    Write-Host "Signed $file with Authenticode ($($result.Status))"
}
