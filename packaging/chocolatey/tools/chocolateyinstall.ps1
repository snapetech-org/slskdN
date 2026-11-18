$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url        = "https://github.com/snapetech/slskdn/releases/download/v2026111723-slskdn.354/slskdn-main-win-x64.zip"
$checksum   = "72c282fb74f3fe3e0353abfbcf666357f1d83a10149ac24d39734ec999297ff0"

Install-ChocolateyZipPackage -PackageName 'slskdn' -Url $url -UnzipLocation $toolsDir -Checksum $checksum -ChecksumType 'sha256'

$vpnAgent = Join-Path $toolsDir "vpn-agent\slskdN-vpn-agent.exe"
if (Test-Path $vpnAgent) {
    Install-BinFile -Name "slskdN-vpn-agent" -Path $vpnAgent
}
