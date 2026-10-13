# Flathub submission checklist

Before submitting to Flathub, update `io.github.slskd.slskdn.yml` as follows.

## 1. .NET 10.0 runtime — ✅ done

- `dotnet` module uses `https://dotnetcli.azureedge.net/dotnet/Runtime/10.0.6/dotnet-runtime-10.0.6-linux-x64.tar.gz` with sha256. No `curl | tar`; Flatpak extracts the archive and build-commands copy into `/app/dotnet/`.
- To bump: get tarball URL from <https://dotnet.microsoft.com/download/dotnet/10.0>, then `curl -sL <url> | sha256sum`.

## 2. slskdn application — ✅ done

- `slskdn` module uses `https://github.com/snapetech/slskdn/releases/download/2026101222-slskdn.350/slskdn-main-linux-glibc-x64.zip` with sha256.
- Stable releases publish the Linux glibc x64 asset as `slskdn-main-linux-glibc-x64.zip`.
- Build-commands copy `slskd*`, `*.dll`, and `wwwroot/` into `/app/lib/slskdn/`. Wrapper runs `/app/dotnet/dotnet /app/lib/slskdn/slskd.dll`.

## 3. Icon — ✅ done

- Manifest uses `slskdn.svg` installed as `share/icons/hicolor/scalable/apps/io.github.slskd.slskdn.svg` (Icon=io.github.slskd.slskdn in desktop).

## 4. Build and test

```bash
flatpak-builder --force-clean build-dir io.github.slskd.slskdn.yml
flatpak-builder --run build-dir io.github.slskd.slskdn.yml sh -c "echo OK"
flatpak build-bundle build-dir slskdn.flatpak io.github.slskd.slskdn
flatpak install --user slskdn.flatpak
flatpak run io.github.slskd.slskdn
```

## 5. Flathub

- See <https://docs.flathub.org/docs/for-app-authors/submission/>.
- App ID `io.github.slskd.slskdn` must match the Flathub application; ensure the `app-id` in the manifest is what Flathub expects.
