// <copyright file="SpectralAnalyzer.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio
{
    using System;
    using System.Diagnostics;
    using System.Globalization;
    using System.IO;
    using System.Text;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.Extensions.Logging;
    using Microsoft.Extensions.Options;
    using slskd.Common.Security;

    /// <summary>
    ///     Decodes audio with ffmpeg to mono 32-bit float PCM at the file's own sample rate (no resampling, so hi-res
    ///     files keep their full band), averages a Hann-windowed FFT over up to MaxFrames non-silent frames, and
    ///     classifies the result with <see cref="SpectralClassifier"/>.
    /// </summary>
    public sealed class SpectralAnalyzer : ISpectralAnalyzer, IDisposable
    {
        private const int BytesPerFrame = SpectralClassifier.FftSize * sizeof(float);
        private const double SilentFrameRms = 0.001;   // about -60 dBFS
        private const double IntroSkipSeconds = 30;
        private const double IntroSkipMinDurationSeconds = 90;
        private const int MaxDiagnosticChars = 2048;

        private readonly IOptionsMonitor<slskd.Options> optionsMonitor;
        private readonly ILogger<SpectralAnalyzer> log;
        private readonly SemaphoreSlim decodeSlots;
        private int missingFfmpegWarningLogged;

        public SpectralAnalyzer(IOptionsMonitor<slskd.Options> optionsMonitor, ILogger<SpectralAnalyzer> log)
        {
            this.optionsMonitor = optionsMonitor;
            this.log = log;
            var slots = optionsMonitor.CurrentValue.Audio.SpectralAnalysis.MaxConcurrentAnalyses;
            decodeSlots = new SemaphoreSlim(slots, slots);
        }

        public bool IsEnabled => Settings.Enabled;

        public bool AnalyzeCompletedDownloads => Settings.Enabled && Settings.AnalyzeCompletedDownloads;

        private slskd.Options.AudioOptions.SpectralAnalysisOptions Settings => optionsMonitor.CurrentValue.Audio.SpectralAnalysis;

        public async Task<SpectralAnalysisResult?> AnalyzeAsync(
            string filePath,
            int sampleRateHz,
            double durationSeconds,
            CancellationToken cancellationToken = default)
        {
            if (!IsEnabled)
            {
                return null;
            }

            var configuredFfmpeg = optionsMonitor.CurrentValue.Integration.Chromaprint.FfmpegPath;
            var ffmpeg = AudioSketchService.ResolveExecutablePath(configuredFfmpeg);
            if (ffmpeg is null)
            {
                if (Interlocked.Exchange(ref missingFfmpegWarningLogged, 1) == 0)
                {
                    log.LogWarning(
                        "[Spectral] ffmpeg not configured or missing: {Path}; spectral analysis is skipped until ffmpeg is available",
                        configuredFfmpeg);
                }

                return null;
            }

            if (sampleRateHz <= 0)
            {
                return Inconclusive(sampleRateHz, 0, "unknown sample rate");
            }

            var startSeconds = durationSeconds > IntroSkipMinDurationSeconds ? IntroSkipSeconds : 0;

            await decodeSlots.WaitAsync(cancellationToken).ConfigureAwait(false);
            try
            {
                return await DecodeAndClassifyAsync(ffmpeg, filePath, sampleRateHz, startSeconds, Settings.MaxFrames, cancellationToken)
                    .ConfigureAwait(false);
            }
            finally
            {
                decodeSlots.Release();
            }
        }

        public void Dispose() => decodeSlots.Dispose();

        internal static ProcessStartInfo CreateProcessStartInfo(string ffmpeg, string filePath, double startSeconds)
        {
            var psi = new ProcessStartInfo
            {
                FileName = ffmpeg,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };

            psi.ArgumentList.Add("-hide_banner");
            psi.ArgumentList.Add("-nostdin");
            psi.ArgumentList.Add("-loglevel");
            psi.ArgumentList.Add("error");
            if (startSeconds > 0)
            {
                psi.ArgumentList.Add("-ss");
                psi.ArgumentList.Add(startSeconds.ToString(CultureInfo.InvariantCulture));
            }

            psi.ArgumentList.Add("-i");
            psi.ArgumentList.Add(filePath);
            psi.ArgumentList.Add("-map");
            psi.ArgumentList.Add("0:a:0");
            psi.ArgumentList.Add("-ac");
            psi.ArgumentList.Add("1");
            psi.ArgumentList.Add("-c:a");
            psi.ArgumentList.Add("pcm_f32le");
            psi.ArgumentList.Add("-f");
            psi.ArgumentList.Add("f32le");
            psi.ArgumentList.Add("pipe:1");
            return psi;
        }

        private async Task<SpectralAnalysisResult> DecodeAndClassifyAsync(
            string ffmpeg,
            string filePath,
            int sampleRateHz,
            double startSeconds,
            int maxFrames,
            CancellationToken cancellationToken)
        {
            using var process = new Process { StartInfo = CreateProcessStartInfo(ffmpeg, filePath, startSeconds) };
            var diagnostics = new StringBuilder();
            process.ErrorDataReceived += (_, args) =>
            {
                if (args.Data is null)
                {
                    return;
                }

                lock (diagnostics)
                {
                    if (diagnostics.Length < MaxDiagnosticChars)
                    {
                        diagnostics.AppendLine(args.Data);
                    }
                }
            };

            process.Start();
            process.BeginErrorReadLine();

            var power = new double[(SpectralClassifier.FftSize / 2) + 1];
            int frames;
            bool reachedEnd;
            try
            {
                (frames, reachedEnd) = await AccumulatePowerAsync(process.StandardOutput.BaseStream, power, maxFrames, cancellationToken)
                    .ConfigureAwait(false);

                if (!reachedEnd)
                {
                    // The frame budget is spent; ffmpeg would block writing the rest of the file.
                    StopProcess(process, filePath);
                }

                await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
            }
            catch
            {
                StopProcess(process, filePath);
                try
                {
                    await process.WaitForExitAsync(CancellationToken.None)
                        .WaitAsync(TimeSpan.FromSeconds(5), CancellationToken.None)
                        .ConfigureAwait(false);
                }
                catch (Exception cleanupException)
                {
                    log.LogWarning(cleanupException, "[Spectral] Failed to stop ffmpeg after analysis of {File} was interrupted",
                        LoggingSanitizer.SanitizeFilePath(filePath));
                }

                throw;
            }

            string diagnostic;
            lock (diagnostics)
            {
                diagnostic = diagnostics.ToString().Trim();
            }

            if (reachedEnd && process.ExitCode != 0 && frames < SpectralClassifier.MinFrames)
            {
                log.LogWarning("[Spectral] ffmpeg exited with code {Code} for {File}: {Diagnostic}",
                    process.ExitCode, LoggingSanitizer.SanitizeFilePath(filePath), diagnostic);
                return Inconclusive(sampleRateHz, frames, "ffmpeg could not decode the file");
            }

            if (frames < SpectralClassifier.MinFrames)
            {
                return Inconclusive(sampleRateHz, frames, "too little non-silent audio");
            }

            var (bandDb, bandHz) = SpectralClassifier.BuildBands(power, frames, sampleRateHz);
            var result = SpectralClassifier.Classify(bandDb, bandHz, sampleRateHz, frames);
            log.LogDebug("[Spectral] {Verdict} for {File}: {Detail}",
                result.Verdict, LoggingSanitizer.SanitizeFilePath(filePath), result.Detail);
            return result;
        }

        // Reads whole frames of float PCM and adds each non-silent frame's windowed power spectrum to power.
        // Returns the frames used and whether ffmpeg reached the end of the audio. Silent frames don't count toward
        // the budget, but at most four times the budget is read so a silent file can't decode forever.
        internal static async Task<(int Frames, bool ReachedEnd)> AccumulatePowerAsync(
            Stream pcm,
            double[] power,
            int maxFrames,
            CancellationToken cancellationToken)
        {
            var window = SpectralClassifier.HannWindow(SpectralClassifier.FftSize);
            var buffer = new byte[BytesPerFrame];
            var re = new double[SpectralClassifier.FftSize];
            var im = new double[SpectralClassifier.FftSize];
            var frames = 0;
            var framesRead = 0;
            var maxFramesRead = maxFrames * 4;

            while (frames < maxFrames && framesRead < maxFramesRead)
            {
                if (!await ReadFrameAsync(pcm, buffer, cancellationToken).ConfigureAwait(false))
                {
                    return (frames, true);
                }

                framesRead++;
                double sumSquares = 0;
                for (var i = 0; i < SpectralClassifier.FftSize; i++)
                {
                    double sample = BitConverter.ToSingle(buffer, i * sizeof(float));
                    sumSquares += sample * sample;
                    re[i] = sample * window[i];
                    im[i] = 0;
                }

                if (Math.Sqrt(sumSquares / SpectralClassifier.FftSize) < SilentFrameRms)
                {
                    continue;
                }

                SpectralClassifier.Fft(re, im);
                for (var k = 0; k < power.Length; k++)
                {
                    power[k] += (re[k] * re[k]) + (im[k] * im[k]);
                }

                frames++;
            }

            return (frames, false);
        }

        private static async Task<bool> ReadFrameAsync(Stream stream, byte[] buffer, CancellationToken cancellationToken)
        {
            var filled = 0;
            while (filled < buffer.Length)
            {
                var read = await stream.ReadAsync(buffer.AsMemory(filled), cancellationToken).ConfigureAwait(false);
                if (read <= 0)
                {
                    return false;
                }

                filled += read;
            }

            return true;
        }

        private static SpectralAnalysisResult Inconclusive(int sampleRateHz, int frames, string detail) => new()
        {
            Verdict = SpectralVerdict.Inconclusive,
            SampleRateHz = sampleRateHz,
            FramesAnalyzed = frames,
            Detail = detail,
        };

        private void StopProcess(Process process, string filePath)
        {
            try
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }
            }
            catch (Exception ex)
            {
                log.LogWarning(ex, "[Spectral] Failed to stop ffmpeg for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
            }
        }
    }
}
