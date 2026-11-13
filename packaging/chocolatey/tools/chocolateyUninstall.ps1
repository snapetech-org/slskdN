$ErrorActionPreference = 'Stop'

Uninstall-BinFile -Name "slskdN-vpn-agent"
Uninstall-ChocolateyZipPackage -PackageName "slskdn" -ZipFileName "slskdn-main-win-x64.zip"
