class Slskdn < Formula
  desc "Unofficial slskd fork with batteries-included Soulseek features"
  homepage "https://github.com/snapetech/slskdn"
  license "AGPL-3.0-or-later"
  version "2026111302-slskdn.353"
  on_macos do
    on_arm do
      url "https://github.com/snapetech/slskdn/releases/download/2026111302-slskdn.353/slskdn-main-osx-arm64.zip"
      sha256 "f253570121e595490a99396dbed0892eed3cecc52b1fcb87f738473e1eb1682a"
    end
    on_intel do
      url "https://github.com/snapetech/slskdn/releases/download/2026111302-slskdn.353/slskdn-main-osx-x64.zip"
      sha256 "0fac321bedfb3d501dd4968a4c89be20f96257c4e14ab57f92604a76e46650eb"
    end
  end
  on_linux do
    url "https://github.com/snapetech/slskdn/releases/download/2026111302-slskdn.353/slskdn-main-linux-glibc-x64.zip"
    sha256 "2e348f2ebbaacaebb182807ef583734f8c748f8ef6f297e77638126b241ec511"
  end
  def install
    libexec.install Dir["*"]
    (bin/"slskd").write_exec_script libexec/"slskd"
    (bin/"slskdn").write_exec_script libexec/"slskd"
    if (libexec/"vpn-agent/slskdN-vpn-agent").exist?
      (bin/"slskdN-vpn-agent").write_exec_script libexec/"vpn-agent/slskdN-vpn-agent"
    end
  end
end
