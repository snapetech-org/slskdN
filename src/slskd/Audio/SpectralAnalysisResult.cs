// <copyright file="SpectralAnalysisResult.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio
{
    using System;
    using System.Globalization;

    /// <summary>
    ///     What a spectral measurement says about where a lossless file's audio came from.
    /// </summary>
    public enum SpectralVerdict
    {
        /// <summary>Too little usable audio, or the decode failed.</summary>
        Inconclusive,

        /// <summary>No lossy lowpass shelf; content reaches the expected bandwidth.</summary>
        Genuine,

        /// <summary>A shelf in the range shared by 320 kbps MP3, Opus, and some mastering filters.</summary>
        Suspect,

        /// <summary>A lossy encoder's lowpass shelf survives in the lossless file.</summary>
        Lossy,

        /// <summary>A hi-res file whose content stops where a 44.1/48 kHz source would.</summary>
        Upsampled,
    }

    /// <summary>
    ///     The result of measuring a file's spectral lowpass shelf. See <see cref="SpectralClassifier"/>.
    /// </summary>
    public sealed class SpectralAnalysisResult
    {
        public SpectralVerdict Verdict { get; init; }

        public int SampleRateHz { get; init; }

        public int FramesAnalyzed { get; init; }

        /// <summary>Gets where a qualifying lossy-style shelf starts; null when there is none.</summary>
        public double? CutoffHz { get; init; }

        /// <summary>Gets the level just below the shelf minus the level just above it, in dB.</summary>
        public double? ShelfDropDb { get; init; }

        /// <summary>Gets the 90th-percentile level above the shelf relative to just below it, in dB (negative).</summary>
        public double? AboveShelfDb { get; init; }

        /// <summary>Gets the likely lossy source, such as "MP3 ~128 kbps", for Lossy and Suspect verdicts.</summary>
        public string EstimatedSource { get; init; } = string.Empty;

        public string Detail { get; init; } = string.Empty;

        /// <summary>
        ///     Gets a one-line description for transcode reasons and library issues.
        /// </summary>
        public string Describe()
        {
            var source = string.IsNullOrEmpty(EstimatedSource) ? string.Empty : $" (~{EstimatedSource})";
            return Verdict switch
            {
                SpectralVerdict.Lossy => $"spectral: lossy shelf at {Khz(CutoffHz)} kHz{source}",
                SpectralVerdict.Suspect => $"spectral (suspect): shelf at {Khz(CutoffHz)} kHz{source}; could also be a mastering lowpass",
                SpectralVerdict.Upsampled => $"spectral: content stops at {Khz(CutoffHz)} kHz in a {Khz(SampleRateHz)} kHz file{source}",
                SpectralVerdict.Genuine => "spectral: no lossy shelf",
                _ => $"spectral: inconclusive ({Detail})",
            };
        }

        /// <summary>
        ///     Records the measurement on <paramref name="variant"/>. Only a Lossy verdict marks the variant as a
        ///     suspected transcode; Suspect and Upsampled results are recorded in the reason only.
        /// </summary>
        /// <remarks>
        ///     <see cref="AudioVariant.EffectiveBandwidthHz"/> holds the shelf cutoff (or Nyquist when there is no
        ///     shelf) and <see cref="AudioVariant.HfEnergyRatio"/> the linear power ratio above the shelf, set only
        ///     when a shelf was found. <see cref="TranscodeDetector"/> re-derives the verdict from those two fields.
        /// </remarks>
        public void ApplyTo(AudioVariant variant)
        {
            if (Verdict == SpectralVerdict.Inconclusive)
            {
                return;
            }

            variant.EffectiveBandwidthHz = CutoffHz ?? SampleRateHz / 2.0;
            variant.HfEnergyRatio = AboveShelfDb is double above ? Math.Pow(10, above / 10) : null;

            if (Verdict == SpectralVerdict.Genuine)
            {
                return;
            }

            if (Verdict == SpectralVerdict.Lossy && !variant.TranscodeSuspect)
            {
                variant.TranscodeSuspect = true;
                variant.TranscodeReason = Describe();
                variant.QualityScore = Math.Min(0.6, variant.QualityScore * 0.5);   // same penalty as FlacAnalyzer
                return;
            }

            variant.TranscodeReason = string.IsNullOrEmpty(variant.TranscodeReason)
                ? Describe()
                : $"{variant.TranscodeReason}; {Describe()}";
        }

        private static string Khz(double? hz) => ((hz ?? 0) / 1000.0).ToString("0.0", CultureInfo.InvariantCulture);
    }
}
