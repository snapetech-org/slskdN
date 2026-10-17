// <copyright file="TranscodeDetector.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio
{
    using System;

    /// <summary>
    /// Heuristics for lossy-to-lossless transcode detection.
    /// </summary>
    public class TranscodeDetector
    {
        public (bool IsSuspect, string Reason) DetectTranscode(AudioVariant variant)
        {
            if (variant == null)
            {
                throw new ArgumentNullException(nameof(variant));
            }

            // Rule 1: FLAC with impossibly low bitrate
            if (variant.Codec == "FLAC")
            {
                var minExpected = EstimateMinFLACBitrate(variant);
                if (variant.BitrateKbps < minExpected)
                {
                    return (true, $"FLAC bitrate {variant.BitrateKbps}kbps too low for {variant.SampleRateHz}Hz/{variant.BitDepth}bit (expected ≥{minExpected}kbps)");
                }
            }

            // Rule 2: Lossless with poor dynamic range
            if (IsLosslessCodec(variant.Codec) && variant.DynamicRangeDR.HasValue)
            {
                if (variant.DynamicRangeDR < 5)
                {
                    return (true, $"Lossless file with DR={variant.DynamicRangeDR:F1} suggests lossy source");
                }
            }

            // Rule 3: Upsampled audio (48kHz or 96kHz from 44.1kHz source)
            if (variant.SampleRateHz == 48000 || variant.SampleRateHz == 96000)
            {
                // Check encoder signature for clues
                if (variant.EncoderSignature != null &&
                    variant.EncoderSignature.Contains("LAME", StringComparison.OrdinalIgnoreCase))
                {
                    // MP3 encoder in FLAC.
                    return (true, "Lossy encoder signature in lossless file");
                }
            }

            // Rule 4a: Measured spectral shelf (lossless files analyzed by SpectralAnalyzer). A shelf was found only
            // when HfEnergyRatio is set; the verdict is re-derived exactly as SpectralClassifier reached it.
            if (IsLosslessCodec(variant.Codec))
            {
                if (variant.EffectiveBandwidthHz is double cutoffHz &&
                    variant.HfEnergyRatio.HasValue &&
                    variant.SampleRateHz > 0 &&
                    SpectralClassifier.VerdictForShelf(cutoffHz, variant.SampleRateHz / 2.0) == SpectralVerdict.Lossy)
                {
                    var measured = new SpectralAnalysisResult
                    {
                        Verdict = SpectralVerdict.Lossy,
                        CutoffHz = cutoffHz,
                        EstimatedSource = SpectralClassifier.EstimateLossySource(cutoffHz),
                    };
                    return (true, measured.Describe());
                }

                return (false, string.Empty);
            }

            // Rule 4b: Spectral bandwidth approximation for lossy codecs (estimated from bitrate, not measured)
            if (variant.BitrateKbps > 0)
            {
                var effectiveBandwidth = EstimateSpectralBandwidth(variant);
                var expectedBandwidth = variant.SampleRateHz / 2.0;

                if (effectiveBandwidth < expectedBandwidth * 0.6)
                {
                    return (true, $"Spectral bandwidth {effectiveBandwidth / 1000:F1}kHz suggests {EstimateOriginalLossyBitrate(effectiveBandwidth)}kbps lossy source");
                }
            }

            return (false, string.Empty);
        }

        private double EstimateSpectralBandwidth(AudioVariant variant)
        {
            // Placeholder: estimate from bitrate for lossy codecs
            return variant.Codec switch
            {
                "MP3" => variant.BitrateKbps switch
                {
                    >= 320 => 20000,
                    >= 192 => 18000,
                    >= 128 => 16000,
                    _ => 14000,
                },
                _ => variant.SampleRateHz / 2.0,  // Nyquist frequency
            };
        }

        private int EstimateOriginalLossyBitrate(double bandwidth)
        {
            if (bandwidth >= 19000) return 320;
            if (bandwidth >= 17000) return 192;
            if (bandwidth >= 15000) return 160;
            return 128;
        }

        private int EstimateMinFLACBitrate(AudioVariant variant)
        {
            // Rough lower-bound for lossless bitrate (50% of raw PCM)
            var raw = (variant.SampleRateHz * (variant.BitDepth ?? 16) * variant.Channels) / 1000;
            return (int)(raw * 0.5);
        }

        internal static bool IsLosslessCodec(string codec)
        {
            return codec switch
            {
                "FLAC" => true,
                "ALAC" => true,
                "WAV" => true,
                "AIFF" => true,
                _ => false,
            };
        }
    }
}
