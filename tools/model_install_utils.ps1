$ErrorActionPreference = "Stop"

$script:ModelInstallUtilsRoot = $PSScriptRoot

function Install-HuggingFaceModel {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][long]$ExpectedBytes,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256
    )

    $part = "$Destination.part"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null

    if (Test-Path -LiteralPath $Destination) {
        Write-Host "Already installed: $Destination"
        return
    }

    $needsDownload = $true
    if (Test-Path -LiteralPath $part) {
        $initialLength = (Get-Item -LiteralPath $part).Length
        Start-Sleep -Seconds 2
        $currentLength = (Get-Item -LiteralPath $part).Length
        if ($currentLength -ne $initialLength) {
            throw "Another download is still writing $part. Wait for it to finish, then run this installer again."
        }
        if ($currentLength -eq $ExpectedBytes) {
            $needsDownload = $false
            Write-Host "Partial file already has the expected size: $Name"
        }
    }

    if ($needsDownload) {
        $cacheBust = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $separator = if ($Url.Contains("?")) { "&" } else { "?" }
        $downloadUrl = "${Url}${separator}download=true&cachebust=$cacheBust"
        Write-Host "Downloading $Name ..."
        & curl.exe -L --fail --retry 10 --retry-all-errors --retry-delay 5 --continue-at - --noproxy "*" -H "Cache-Control: no-cache" --output $part $downloadUrl
        if ($LASTEXITCODE -ne 0) {
            throw "Download failed: $Name"
        }
    }

    $candidate = if (Test-Path -LiteralPath $Destination) { $Destination } else { $part }
    $actualBytes = (Get-Item -LiteralPath $candidate).Length
    if ($actualBytes -ne $ExpectedBytes) {
        throw "File size mismatch for $Name. Expected $ExpectedBytes bytes, got $actualBytes"
    }

    Write-Host "Verifying SHA256: $Name ..."
    $hashTool = Join-Path $script:ModelInstallUtilsRoot "hash_file.py"
    if (-not (Test-Path -LiteralPath $hashTool -PathType Leaf)) {
        throw "SHA256 tool not found: $hashTool"
    }
    $hashOutput = @(& python $hashTool $candidate)
    if ($LASTEXITCODE -ne 0) {
        throw "SHA256 verification tool failed: $Name"
    }
    $actualSha256 = $hashOutput[-1].Trim().ToLowerInvariant()
    if ($actualSha256 -ne $ExpectedSha256) {
        throw "SHA256 mismatch for $Name. Expected $ExpectedSha256, got $actualSha256"
    }

    if ($candidate -eq $part) {
        Move-Item -LiteralPath $part -Destination $Destination
    }
    Write-Host "Installed: $Destination"
}
