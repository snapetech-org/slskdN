class Slskdn < Formula
  desc "Unofficial slskd fork with batteries-included Soulseek features"
  homepage "https://github.com/snapetech/slskdn"
  license "AGPL-3.0-or-later"
  version "2026111723-slskdn.354"

  on_macos do
    on_arm do
      url "https://github.com/snapetech/slskdn/releases/download/v2026111723-slskdn.354/slskdn-main-osx-arm64.zip"
      sha256 "363afc1f527240fea8ad20e002644a0ab6522dd4e2757426639fc4cf39f2a995"
    end
    on_intel do
      url "https://github.com/snapetech/slskdn/releases/download/v2026111723-slskdn.354/slskdn-main-osx-x64.zip"
      sha256 "2358410269c17245353b784cab5c34d07e74350b46cb5456e4e4c0e05d5f7461"
    end
  end

  on_linux do
    url "https://github.com/snapetech/slskdn/releases/download/v2026111723-slskdn.354/slskdn-main-linux-glibc-x64.zip"
    sha256 "78ebfb83318ac57e939a067e94e2b3f3fec7778a0e05dd9cf38da89b6e3913c8"
  end

  def install
    libexec.install Dir["*"]
    (bin/"slskd").write_exec_script libexec/"slskd"
    (bin/"slskdn").write_exec_script libexec/"slskd"
    if (libexec/"vpn-agent/slskdN-vpn-agent").exist?
      (bin/"slskdN-vpn-agent").write_exec_script libexec/"vpn-agent/slskdN-vpn-agent"
    end
  end

  test do
    assert_match "slskd", shell_output("#{bin}/slskd --help", 1)
    if (bin/"slskdN-vpn-agent").exist?
      assert_match "slskdN-vpn-agent", shell_output("#{bin}/slskdN-vpn-agent --help")
    end
  end
end
