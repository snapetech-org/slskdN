# Keep Playwright's browsers and Linux libraries matched to the repo's pinned
# @playwright/test version. The E2E harness also launches ASP.NET net10.0 nodes.
FROM mcr.microsoft.com/dotnet/aspnet@sha256:222759b391a1aaf241166672c8f99b2d4ada452e7b5319f3c6e8f265a37b5ad4 AS aspnet-runtime
FROM mcr.microsoft.com/playwright@sha256:eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27

COPY --from=aspnet-runtime /usr/share/dotnet /usr/share/dotnet
ENV PATH="/usr/share/dotnet:${PATH}"

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
    at-spi2-core \
    dbus-x11 \
    espeak-ng \
    ffmpeg \
    iproute2 \
    orca \
    pulseaudio-utils \
    speech-dispatcher \
    speech-dispatcher-espeak-ng \
    x11-xkb-utils \
    && rm -rf /var/lib/apt/lists/*

USER pwuser

CMD ["sleep", "infinity"]
