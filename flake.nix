{
  description = "slskdN, an unofficial slskd fork with batteries-included Soulseek features";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        version = "2026101222-slskdn.350";
        
        # Helper function to build slskdn from a given version and sources
        mkSlskdn = { pname, version, sources }:
          if builtins.hasAttr system sources then
            let
              srcConfig = sources.${system};
            in
            pkgs.stdenv.mkDerivation {
              inherit pname version;

              src = pkgs.fetchurl {
                inherit (srcConfig) url sha256;
              };

              nativeBuildInputs = [ pkgs.unzip pkgs.makeWrapper pkgs.autoPatchelfHook pkgs.patchelf ];
              dontStrip = true;
              buildInputs = [
                pkgs.curl
                pkgs.icu
                pkgs.krb5
                pkgs.lttng-ust.out
                pkgs.libunwind
                pkgs.openssl
                pkgs.stdenv.cc.cc
                pkgs.util-linux
                pkgs.zlib
              ];

              unpackPhase = "unzip $src";

              installPhase = ''
                mkdir -p $out/libexec/${pname} $out/bin
                cp -r * $out/libexec/${pname}/
                chmod +x $out/libexec/${pname}/slskd

                # .NET's trace provider still references the old SONAME on current nixpkgs.
                patchelf \
                  --replace-needed liblttng-ust.so.0 liblttng-ust.so.1 \
                  $out/libexec/${pname}/libcoreclrtraceptprovider.so
                
                makeWrapper $out/libexec/${pname}/slskd $out/bin/slskd \
                  --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [
                    pkgs.curl
                    pkgs.icu
                    pkgs.krb5
                    pkgs.lttng-ust.out
                    pkgs.libunwind
                    pkgs.openssl
                    pkgs.stdenv.cc.cc
                    pkgs.util-linux
                    pkgs.zlib
                  ]}
                ln -s slskd $out/bin/${pname}
              '';

              meta = with pkgs.lib; {
                description = "Unofficial slskd fork with batteries-included Soulseek features";
                homepage = "https://github.com/snapetech/slskdn";
                license = licenses.agpl3Plus;
                platforms = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
              };
            }
          else
            throw "Unsupported system: ${system}";
        
        stableSources = {
          "x86_64-linux" = {
            url = "https://github.com/snapetech/slskdn/releases/download/2026101222-slskdn.350/slskdn-main-linux-glibc-x64.zip";
            sha256 = "sha256-3NLvFqMHfY3xLCJgzsOZ947jBspxOzYVjmnBVNyFFUE="; # x86_64-linux (glibc)
          };
          "aarch64-linux" = {
            url = "https://github.com/snapetech/slskdn/releases/download/${version}/slskdn-main-linux-glibc-arm64.zip";
            sha256 = "sha256-th6nCbu0vgEqmLMQffXypBrnoktUgRUzlplD0MOvINk="; # aarch64-linux (glibc)
          };
          "x86_64-darwin" = {
            url = "https://github.com/snapetech/slskdn/releases/download/${version}/slskdn-main-osx-x64.zip";
            sha256 = "sha256-I8TB8vOHCVFiq20ySJYzLqJOkNejpdQFA8bAMwcFNTQ="; # x86_64-darwin
          };
          "aarch64-darwin" = {
            url = "https://github.com/snapetech/slskdn/releases/download/${version}/slskdn-main-osx-arm64.zip";
            sha256 = "sha256-j9tFXbiwEzERe7nyMTuy3al+x9WPsIroEjRgJg0Yws4="; # aarch64-darwin
          };
        };
      in
      {
        packages = {
          default = mkSlskdn {
            pname = "slskdn";
            version = version;
            sources = stableSources;
          };
        };
      }
    );
}
