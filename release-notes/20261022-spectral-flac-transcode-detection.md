---
category: added
audience: users, operators
area: audio-quality
action: none
breaking: false
---
Opt-in spectral analysis now flags sharp high-frequency cutoffs in local FLAC files, helping users spot clear lossy sources or high-resolution upsampling while leaving borderline mastering filters review-only. It reuses the configured `integrations.chromaprint.ffmpeg_path`, does not require Chromaprint, and analyzes existing HashDb rows only when their files are analyzed again.
