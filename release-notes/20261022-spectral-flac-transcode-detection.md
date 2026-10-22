# Opt-in FLAC spectral transcode detection

slskdN can now measure sharp high-frequency cutoffs in local FLAC files and flag
clear evidence of a lossy source or high-resolution upsampling. Borderline
mastering filters remain review-only. The feature is opt-in and reuses the
configured `integrations.chromaprint.ffmpeg_path` executable; Chromaprint itself
does not need to be enabled. The frame budget bounds how much audio ffmpeg
decodes per file. Existing HashDb rows are not decoded by analyzer migration and
receive spectral measurements when the local file is analyzed again.
