class Slskdn < Formula
  desc "Unofficial slskd fork with batteries-included Soulseek features"
  homepage "https://github.com/snapetech/slskdn"
  license "AGPL-3.0-or-later"
  version "2026101222-slskdn.350"
  on_macos do
    on_arm do
      url "https://github.com/snapetech/slskdn/releases/download/2026101222-slskdn.350/slskdn-main-osx-arm64.zip"
      sha256 "6f81bdf20cf7c9ef67b94f73d0987e0a2af4346a4d336605ee8041159a2f38e6"
    end
    on_intel do
      url "https://github.com/snapetech/slskdn/releases/download/2026101222-slskdn.350/slskdn-main-osx-x64.zip"
      sha256 "73a92dc1871a982c951c99181dd3c53a2fb07e4908575218a258733bd7b3c308"
    end
  end
  on_linux do
    url "https://github.com/snapetech/slskdn/releases/download/2026101222-slskdn.350/slskdn-main-linux-glibc-x64.zip"
    sha256 "dcd2ef16a3077d8df12c2260cec399f78ee306ca713b36158e69c154dc851541"
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
