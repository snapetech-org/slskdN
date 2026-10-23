FROM docker.io/snapetech/slskdn:2026100421-slskdn.338

# The parent image's root entrypoint handles Cloudron volume ownership, then execs the app as slskdn.
ENV SLSKD_APP_DIR=/app/data \
    SLSKD_DOWNLOADS_DIR=/app/data/downloads \
    SLSKD_SHARED_DIR=/app/data/music

# nosemgrep: dockerfile.security.missing-user.missing-user -- the inherited entrypoint performs volume ownership setup, then drops to slskdn before executing this command.
CMD ["/bin/sh", "-ec", "mkdir -p \"$SLSKD_DOWNLOADS_DIR\" \"$SLSKD_SHARED_DIR\"; exec ./slskd"]
