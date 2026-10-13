Name:           slskdn
Version:        2026101222.slskdn.350
Release:        1%{?dist}
Summary:        slskdN, an unofficial batteries-included fork of slskd

License:        AGPL-3.0-or-later
URL:            https://github.com/snapetech/slskdn
# Pre-built zip from GitHub releases (asset slskdn-main-linux-glibc-x64.zip). CI overwrites Version and Source0.
Source0:        https://github.com/snapetech/slskdn/releases/download/2026101222-slskdn.350/slskdn-main-linux-glibc-x64.zip
Source1:        slskd.service
Source2:        slskd.yml
Source3:        slskd.conf
Source4:        slskd.tmpfiles

BuildArch:      x86_64
BuildRequires:  systemd-rpm-macros
BuildRequires:  unzip
BuildRequires:  patchelf
# Required for user creation in %pre
Requires(pre):  shadow-utils
Requires:       systemd
Requires:       libicu
# Disable debuginfo - this is a pre-built .NET binary
%global debug_package %{nil}
%define __strip /bin/true
%global slskd_appdir /usr/lib/slskd
Conflicts:      slskd

%description
slskdN is an unofficial batteries-included fork of slskd with decentralized pods,
content validation, swarm downloads, DHT mesh networking, auto-replace, wishlist,
security hardening.

Stable Features:
- Auto-replace stuck downloads - Automatically finds and switches to working sources
- Wishlist/background search - Never miss rare content with automated searches
- Smart source ranking - Intelligent scoring based on speed, queue, and history
- Tabbed browsing - Browse multiple users simultaneously with persistent state
- User notes & ratings - Color-coded ratings and persistent notes for users
- Push notifications - Ntfy and Pushover support for messages and mentions
- Multi-select folder downloads - Download multiple folders with checkbox selection
- Advanced search filters - Visual filter editor with bitrate, duration, file size
- PWA/mobile support - Install as standalone app on iOS/Android
- Delete files on disk - Remove downloads and delete files in one action
- Block users from results - Hide specific users from search results
- Save search filters - Persistent filter preferences across sessions
- Chat room improvements - Right-click context menu for browse/chat/notes
- Multiple download destinations - Configure multiple folders with routing
- Download history badges - Visual indicators for successful download history
- Clear all searches - One-click cleanup of search history
- Configurable search page size - 25 to 500 results per page
- Multi-source swarm downloads - Download from multiple peers simultaneously
- DHT mesh networking - Decentralized peer discovery and mesh overlay
- CSRF protection - Full CSRF token validation for web UI
- Security hardening - NetworkGuard, fingerprint detection, security profiles

Advanced Features:
- Decentralized pod communities - Private micro-communities over mesh overlay with DHT discovery
- Content validation - Byzantine consensus & proof-of-storage with cryptographic commitments
- MusicBrainz integration - Metadata enrichment, library health scanning, AcoustID fingerprinting
- Service fabric - Generic mesh service layer for decentralized applications

Modern web UI for the Soulseek network. Unofficial fork and drop-in replacement
for slskd.

%prep
%setup -q -c

%install
# Install application
install -dm755 %{buildroot}%{slskd_appdir}
cp -r * %{buildroot}%{slskd_appdir}/
chmod +x %{buildroot}%{slskd_appdir}/slskd
# Match the Nix package fix: current Fedora-family systems ship liblttng-ust.so.1,
# while the published .NET bundle still references liblttng-ust.so.0 here.
tracept_provider=$(find %{buildroot}%{slskd_appdir} -name libcoreclrtraceptprovider.so -print -quit); \
if [ -n "${tracept_provider}" ]; then \
  patchelf --replace-needed liblttng-ust.so.0 liblttng-ust.so.1 "${tracept_provider}"; \
else \
  echo "libcoreclrtraceptprovider.so not present in staged RPM payload; skipping SONAME patch"; \
fi

# Create symlink
install -dm755 %{buildroot}%{_bindir}
ln -sf %{slskd_appdir}/slskd %{buildroot}%{_bindir}/slskd

# Install systemd service
install -Dm644 %{SOURCE1} %{buildroot}%{_unitdir}/slskd.service
if [ -x %{buildroot}%{slskd_appdir}/vpn-agent/slskdN-vpn-agent ]; then
  install -Dm755 %{buildroot}%{slskd_appdir}/vpn-agent/slskdN-vpn-agent %{buildroot}%{_bindir}/slskdN-vpn-agent
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-split.service %{buildroot}%{_unitdir}/slskdN-vpn-split.service
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-ingress.service %{buildroot}%{_unitdir}/slskdN-vpn-ingress.service
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-ingress-renew.service %{buildroot}%{_unitdir}/slskdN-vpn-ingress-renew.service
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-ingress-renew.timer %{buildroot}%{_unitdir}/slskdN-vpn-ingress-renew.timer
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-gluetun-compat.service %{buildroot}%{_unitdir}/slskdN-vpn-gluetun-compat.service
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-watchdog.service %{buildroot}%{_unitdir}/slskdN-vpn-watchdog.service
  install -Dm644 %{buildroot}%{slskd_appdir}/vpn-agent/systemd/slskdN-vpn-watchdog.timer %{buildroot}%{_unitdir}/slskdN-vpn-watchdog.timer
  for unit in %{buildroot}%{_unitdir}/slskdN-vpn-{split,ingress,gluetun-compat,watchdog}.service; do
    sed -i \
      -e 's#/usr/local/bin/slskdN-vpn-agent#/usr/bin/slskdN-vpn-agent#g' \
      -e 's#slskdN\.service#slskd.service#g' \
      -e '/^Environment=SLSKDN_CONFIG=/d' \
      -e '/^Environment=SLSKDN_SERVICE_USER=/d' \
      -e '/^Environment=SLSKDN_PROCESS_NAME=/d' \
      -e '/^Environment=SLSKDN_SERVICE_NAME=/d' \
      "$unit"
    sed -i '/^\[Service\]/a Environment=SLSKDN_CONFIG=/etc/slskd/slskd.yml\nEnvironment=SLSKDN_SERVICE_USER=slskd\nEnvironment=SLSKDN_PROCESS_NAME=slskd\nEnvironment=SLSKDN_SERVICE_NAME=slskd' "$unit"
  done
fi

# Install config
install -dm755 %{buildroot}%{_sysconfdir}/slskd
install -Dm644 %{SOURCE2} %{buildroot}%{_sysconfdir}/slskd/slskd.yml

# Install sysusers
install -Dm644 %{SOURCE3} %{buildroot}%{_sysusersdir}/slskd.conf

# Install tmpfiles
install -Dm644 %{SOURCE4} %{buildroot}%{_tmpfilesdir}/slskd.conf

# Create data directories
install -dm775 %{buildroot}%{_sharedstatedir}/slskd
install -dm775 %{buildroot}%{_sharedstatedir}/slskd/downloads
install -dm775 %{buildroot}%{_sharedstatedir}/slskd/incomplete
install -dm755 %{buildroot}%{_sharedstatedir}/slskdN-vpn

%pre
getent passwd slskd >/dev/null || useradd -r -s /sbin/nologin -d %{_sharedstatedir}/slskd -c "slskd service account" slskd

%post
%tmpfiles_create %{_tmpfilesdir}/slskd.conf
%systemd_post slskd.service
echo ""
echo "🔋 slskdn has been installed!"
echo ""
echo "1. Edit the configuration:"
echo "   sudo nano /etc/slskd/slskd.yml"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl enable --now slskd"
echo ""
echo "3. Access the web UI at:"
echo "   http://localhost:5030"
echo ""
echo "VPN helper:"
echo "   /usr/bin/slskdN-vpn-agent"
echo "   Configure WireGuard/static forwards before enabling slskdN-vpn-* units."
echo ""

%preun
%systemd_preun slskd.service

%postun
%systemd_postun_with_restart slskd.service

%files
%license %{slskd_appdir}/LICENSE
%{slskd_appdir}/
%{_bindir}/slskd
%{_bindir}/slskdN-vpn-agent
%{_unitdir}/slskd.service
%{_unitdir}/slskdN-vpn-split.service
%{_unitdir}/slskdN-vpn-ingress.service
%{_unitdir}/slskdN-vpn-ingress-renew.service
%{_unitdir}/slskdN-vpn-ingress-renew.timer
%{_unitdir}/slskdN-vpn-gluetun-compat.service
%{_unitdir}/slskdN-vpn-watchdog.service
%{_unitdir}/slskdN-vpn-watchdog.timer
%{_tmpfilesdir}/slskd.conf
%config(noreplace) %attr(0664,slskd,slskd) %{_sysconfdir}/slskd/slskd.yml
%dir %attr(0775,slskd,slskd) %{_sharedstatedir}/slskd
%dir %attr(0775,slskd,slskd) %{_sharedstatedir}/slskd/downloads
%dir %attr(0775,slskd,slskd) %{_sharedstatedir}/slskd/incomplete
%dir %attr(0755,root,root) %{_sharedstatedir}/slskdN-vpn
%{_sysusersdir}/slskd.conf

%changelog
* Sat Mar 23 2026 snapetech <slskdn@proton.me> - 0.24.5.slskdn.97-1
- Bump to 2026101222-slskdn.350 (slskdn-main-linux-glibc-x64.zip)

* Sat Dec 06 2025 snapetech <slskdn@proton.me> - 0.24.1.slskdn.7-1
- Fix race condition in SourceRankingService
- Update branding

* Fri Dec 05 2025 snapetech <slskdn@proton.me> - 0.24.1.slskdn.6-1
- Initial slskdn release
