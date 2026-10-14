# build static web content
# note: pin this to amd64 to speed it up, it is prohibitively slow under QEMU
FROM --platform=$BUILDPLATFORM node:20-alpine AS web

WORKDIR /slskd

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY tests/e2e/package.json tests/e2e/package.json
COPY patches patches/.

RUN apk add --no-cache bash \
  && npm install --global "$(node -p 'require("./package.json").packageManager')"

COPY bin bin/.
COPY src/web src/web/.

RUN DISABLE_ESLINT_PLUGIN=true bash ./bin/build --web-only --skip-tests --version 0.0.1.65534-local

# build, test, and publish application binaries
# note: this needs to be pinned to an amd64 image in order to publish armv7 binaries
# https://github.com/dotnet/dotnet-docker/issues/1537#issuecomment-615269150
FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0-noble AS publish
ARG TARGETPLATFORM
ARG VERSION=0.0.1.65534-local

WORKDIR /slskd

COPY LICENSE .
COPY bin bin/.
COPY config config/.
COPY tools/slskd.BuildTasks tools/slskd.BuildTasks/.
COPY src/slskd src/slskd/.
COPY src/slskdN.VpnAgent src/slskdN.VpnAgent/.
COPY tests tests/.
COPY vendor vendor/.
COPY docs/self-hosted-relay-tester-guide.md docs/self-hosted-relay-tester-guide.md

COPY --from=web /slskd/src/web/build /slskd/src/slskd/wwwroot/.

RUN bash ./bin/build --dotnet-only --skip-tests --version $VERSION

RUN bash ./bin/publish --no-prebuild --platform $TARGETPLATFORM --version $VERSION --output ../../dist/${TARGETPLATFORM}

# application
FROM mcr.microsoft.com/dotnet/runtime-deps:10.0-noble AS slskd
ARG LIBMSQUIC_VERSION=2.4.18

RUN apt-get update && apt-get install --no-install-recommends -y \
  ca-certificates \
  ffmpeg \
  gosu \
  jq \
  libchromaprint-tools \
  wget \
  tini \
  yt-dlp \
  && \
  arch="$(dpkg --print-architecture)" \
  && \
  case "$arch" in \
    amd64) deb_arch=amd64 ;; \
    arm64) deb_arch=arm64 ;; \
    armhf) deb_arch=armhf ;; \
    *) echo "Unsupported architecture for libmsquic: $arch" >&2; exit 1 ;; \
  esac \
  && \
  wget -q -O /tmp/libmsquic.deb "https://packages.microsoft.com/ubuntu/24.04/prod/pool/main/libm/libmsquic/libmsquic_${LIBMSQUIC_VERSION}_${deb_arch}.deb" \
  && \
  apt-get install --no-install-recommends -y /tmp/libmsquic.deb \
  && \
  find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} + \
  && \
  rm -rf \
  /tmp/* \
  /var/lib/apt/lists/* \
  /var/cache/apt/* \
  /var/tmp/*

RUN groupadd --system slskdn \
  && useradd --system --gid slskdn --home-dir /app --shell /usr/sbin/nologin slskdn \
  && mkdir -p /.net \
  && chmod 1777 /.net

ARG TARGETPLATFORM
ARG TAG=0.0.1
ARG VERSION=0.0.1.65534-local
ARG REVISION=0
ARG BUILD_DATE

HEALTHCHECK --interval=60s --timeout=3s --start-period=60m --retries=3 CMD wget -q -O - http://localhost:${SLSKD_HTTP_PORT}/health

ENV SHELL=/usr/bin/bash \
  DOTNET_EnableDiagnostics=0 \
  DOTNET_BUNDLE_EXTRACT_BASE_DIR=/.net \
  DOTNET_gcServer=0 \
  DOTNET_gcConcurrent=1 \
  DOTNET_GCHeapHardLimit=0x80000000 \
  DOTNET_GCConserveMemory=9 \
  SLSKD_UMASK=0022 \
  SLSKD_HTTP_ADDRESS=0.0.0.0 \
  SLSKD_HTTP_PORT=5030 \
  SLSKD_HTTPS_PORT=5031 \
  SLSKD_SLSK_LISTEN_PORT=50300 \
  SLSKD_APP_DIR=/app \
  SLSKD_DOCKER_TAG=$TAG \
  SLSKD_DOCKER_VERSION=$VERSION \
  SLSKD_DOCKER_REVISION=$REVISION \
  SLSKD_DOCKER_BUILD_DATE=$BUILD_DATE

LABEL org.opencontainers.image.title=slskdn \
  org.opencontainers.image.description="slskdN is an unofficial fork of slskd with batteries-included Soulseek features: SongID, Discovery Graph, multi-source downloads, DHT mesh networking, auto-replace, wishlist, and security hardening" \
  org.opencontainers.image.authors="slskdN Team" \
  org.opencontainers.image.vendor="slskdN Team" \
  org.opencontainers.image.licenses=AGPL-3.0 \
  org.opencontainers.image.url=https://github.com/snapetech-org/slskdN \
  org.opencontainers.image.source=https://github.com/snapetech-org/slskdN \
  org.opencontainers.image.documentation=https://github.com/snapetech-org/slskdN \
  org.opencontainers.image.ref.name="slskdN - unofficial fork of slskd" \
  org.opencontainers.image.version=$VERSION \
  org.opencontainers.image.revision=$REVISION \
  org.opencontainers.image.created=$BUILD_DATE

WORKDIR /slskd
COPY --from=publish /slskd/dist/${TARGETPLATFORM} .

COPY packaging/docker/slskdn-container-start /usr/local/bin/slskdn-container-start
COPY packaging/docker/install-optional-media-tools /usr/local/bin/install-optional-media-tools
RUN chmod +x /usr/local/bin/slskdn-container-start /usr/local/bin/install-optional-media-tools

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/slskdn-container-start"]
CMD ["./slskd"]
