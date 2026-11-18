param(
    [Parameter(Mandatory)]
    [string]$PackageVersion
)

$ErrorActionPreference = 'Stop'

choco install slskdn --version "$PackageVersion" --source "$PWD" --yes --no-progress
if ($LASTEXITCODE -ne 0) {
    throw "Chocolatey install test failed with exit code $LASTEXITCODE"
}

$installedTools = Join-Path $env:ChocolateyInstall 'lib/slskdn/tools'
$daemon = Get-ChildItem -LiteralPath $installedTools -Filter slskd.exe -Recurse
if (-not $daemon) {
    throw "Chocolatey did not extract slskd.exe"
}

choco uninstall slskdn --yes --no-progress
if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $installedTools)) {
    throw "Chocolatey uninstall test did not remove the package"
}

Write-Host "Chocolatey install and uninstall checks passed for slskdn $PackageVersion"
