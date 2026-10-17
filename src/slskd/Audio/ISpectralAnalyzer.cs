// <copyright file="ISpectralAnalyzer.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio
{
    using System.Threading;
    using System.Threading.Tasks;

    /// <summary>
    ///     Measures the lowpass shelf a lossy source leaves in a local lossless file (audio.spectral_analysis).
    /// </summary>
    public interface ISpectralAnalyzer
    {
        /// <summary>
        ///     Gets a value indicating whether spectral analysis is enabled in configuration.
        /// </summary>
        bool IsEnabled { get; }

        /// <summary>
        ///     Gets a value indicating whether completed lossless downloads should be analyzed.
        /// </summary>
        bool AnalyzeCompletedDownloads { get; }

        /// <summary>
        ///     Decodes <paramref name="filePath"/> with ffmpeg at its native sample rate and classifies its spectrum.
        /// </summary>
        /// <param name="filePath">A local audio file.</param>
        /// <param name="sampleRateHz">The file's native sample rate.</param>
        /// <param name="durationSeconds">The file's duration; longer tracks skip their first 30 seconds.</param>
        /// <param name="cancellationToken">Stops the decode.</param>
        /// <returns>
        ///     The result, or null when analysis is disabled or ffmpeg is unavailable. A failed decode returns an
        ///     <see cref="SpectralVerdict.Inconclusive"/> result.
        /// </returns>
        Task<SpectralAnalysisResult?> AnalyzeAsync(
            string filePath,
            int sampleRateHz,
            double durationSeconds,
            CancellationToken cancellationToken = default);
    }
}
