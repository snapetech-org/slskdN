// <copyright file="SpectralAnalyzer.cs" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio;

using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Serilog;

/// <summary>
/// Measures sharp high-frequency cutoffs in lossless audio. A cutoff is evidence, not proof,
/// so borderline mastering filters are reported as suspect instead of being marked as lossy.
/// </summary>
internal sealed class SpectralAnalyzer
{
    private const int WindowSize = 8192;
    private const double BandWidthHz = 100;
    private const double MinimumSearchHz = 10000;
    private const int WindowRadiusHz = 500;
    private const double SilenceRmsThreshold = 0.001;
    private const double MinimumWallDropDb = 20;
    private const int MaximumFrameBudget = 6000;
    private static readonly double[] HannWindow = CreateHannWindow();

    private readonly ILogger log = Log.ForContext<SpectralAnalyzer>();
    private bool missingFfmpegWarningLogged;

    /// <summary>
    /// Decodes a bounded portion of a local audio file and measures its average spectrum.
    /// </summary>
    /// <param name="filePath">Path to the local audio file.</param>
    /// <param name="ffmpegPath">Configured ffmpeg executable or path.</param>
    /// <param name="sampleRateHz">Native sample rate from the file metadata.</param>
    /// <param name="durationMs">Duration used to skip long introductions.</param>
    /// <param name="frameBudget">Maximum number of FFT windows to inspect.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The measured bandwidth and its evidence classification.</returns>
    internal async Task<SpectralAnalysisResult> AnalyzeFileAsync(
        string filePath,
        string? ffmpegPath,
        int sampleRateHz,
        int durationMs,
        int frameBudget,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(filePath))
        {
            throw new ArgumentException("Audio file path is required.", nameof(filePath));
        }

        if (sampleRateHz < 22000)
        {
            return SpectralAnalysisResult.Inconclusive("Sample rate is too low for high-frequency cutoff analysis.");
        }

        if (frameBudget is < 1 or > MaximumFrameBudget)
        {
            throw new ArgumentOutOfRangeException(nameof(frameBudget), $"Frame budget must be between 1 and {MaximumFrameBudget}.");
        }

        var resolvedFfmpegPath = AudioSketchService.ResolveExecutablePath(ffmpegPath);
        if (resolvedFfmpegPath is null)
        {
            if (!missingFfmpegWarningLogged)
            {
                missingFfmpegWarningLogged = true;
                log.Warning("[AudioSpectral] ffmpeg is not configured or missing; spectral transcode analysis will be skipped");
            }

            return SpectralAnalysisResult.Inconclusive("Configured ffmpeg executable is unavailable.");
        }

        if (!File.Exists(filePath))
        {
            return SpectralAnalysisResult.Inconclusive("Audio file is unavailable.");
        }

        var powerSums = new double[(WindowSize / 2) + 1];
        var pcmWindow = new byte[WindowSize * sizeof(float)];
        var real = new double[WindowSize];
        var imaginary = new double[WindowSize];
        var scannedFrames = 0;
        var analyzedFrames = 0;

        var startInfo = new ProcessStartInfo
        {
            FileName = resolvedFfmpegPath,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        startInfo.ArgumentList.Add("-hide_banner");
        startInfo.ArgumentList.Add("-nostdin");
        startInfo.ArgumentList.Add("-loglevel");
        startInfo.ArgumentList.Add("error");
        if (durationMs > 45000)
        {
            startInfo.ArgumentList.Add("-ss");
            startInfo.ArgumentList.Add("30");
        }

        startInfo.ArgumentList.Add("-i");
        startInfo.ArgumentList.Add(filePath);
        startInfo.ArgumentList.Add("-map");
        startInfo.ArgumentList.Add("0:a:0");
        startInfo.ArgumentList.Add("-vn");
        startInfo.ArgumentList.Add("-ac");
        startInfo.ArgumentList.Add("1");
        startInfo.ArgumentList.Add("-ar");
        startInfo.ArgumentList.Add(sampleRateHz.ToString(CultureInfo.InvariantCulture));
        startInfo.ArgumentList.Add("-f");
        startInfo.ArgumentList.Add("f32le");
        startInfo.ArgumentList.Add("-acodec");
        startInfo.ArgumentList.Add("pcm_f32le");
        startInfo.ArgumentList.Add("pipe:1");

        using var process = new Process { StartInfo = startInfo };
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        var expectedSeconds = (frameBudget * WindowSize / (double)sampleRateHz) * 3 + 30;
        timeout.CancelAfter(TimeSpan.FromSeconds(Math.Clamp(expectedSeconds, 30, 1200)));

        try
        {
            if (!process.Start())
            {
                return SpectralAnalysisResult.Inconclusive("ffmpeg could not be started.");
            }

            var standardErrorTask = process.StandardError.ReadToEndAsync(CancellationToken.None);
            var output = process.StandardOutput.BaseStream;
            while (scannedFrames < frameBudget && await ReadWindowAsync(output, pcmWindow, timeout.Token).ConfigureAwait(false))
            {
                scannedFrames++;
                if (AccumulateFrame(pcmWindow, real, imaginary, powerSums))
                {
                    analyzedFrames++;
                }
            }

            var reachedFrameBudget = scannedFrames >= frameBudget;
            if (reachedFrameBudget)
            {
                TryTerminate(process);
            }

            await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
            await standardErrorTask.ConfigureAwait(false);
            if (process.ExitCode != 0 && !reachedFrameBudget)
            {
                log.Warning("[AudioSpectral] ffmpeg exited with code {ExitCode}; spectral analysis was skipped", process.ExitCode);
                return SpectralAnalysisResult.Inconclusive("ffmpeg could not decode the audio file.");
            }

            if (analyzedFrames == 0)
            {
                return SpectralAnalysisResult.Inconclusive("No non-silent FFT windows were available.");
            }

            var bands = BuildBandLevels(powerSums, analyzedFrames, sampleRateHz);
            return Classify(bands, BandWidthHz, sampleRateHz, analyzedFrames);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            await StopProcessAsync(process).ConfigureAwait(false);
            throw;
        }
        catch (OperationCanceledException)
        {
            await StopProcessAsync(process).ConfigureAwait(false);
            log.Warning("[AudioSpectral] ffmpeg exceeded the bounded spectral-analysis time budget");
            return SpectralAnalysisResult.Inconclusive("Spectral analysis timed out.");
        }
        catch (Exception exception)
        {
            await StopProcessAsync(process).ConfigureAwait(false);
            log.Warning(exception, "[AudioSpectral] Failed to analyze local audio; the file will remain unclassified");
            return SpectralAnalysisResult.Inconclusive("Spectral analysis failed.");
        }
    }

    internal static SpectralAnalysisResult Classify(
        IReadOnlyList<double> bandLevelsDb,
        double bandWidthHz,
        int sampleRateHz,
        int framesAnalyzed = 0)
    {
        if (bandLevelsDb is null || bandLevelsDb.Count == 0 || bandWidthHz <= 0 || sampleRateHz < 22000)
        {
            return SpectralAnalysisResult.Inconclusive("Insufficient spectral data.");
        }

        var finiteLevels = new List<double>(bandLevelsDb.Count);
        for (var index = 0; index < bandLevelsDb.Count; index++)
        {
            if (double.IsFinite(bandLevelsDb[index]))
            {
                finiteLevels.Add(bandLevelsDb[index]);
            }
        }

        if (finiteLevels.Count == 0 || finiteLevels.Max() <= -120)
        {
            return SpectralAnalysisResult.Inconclusive("Spectrum is silent or below the usable noise floor.");
        }

        var nyquistHz = sampleRateHz / 2.0;
        var windowBands = Math.Max(1, (int)Math.Ceiling(WindowRadiusHz / bandWidthHz));
        var firstBand = Math.Max(windowBands, (int)Math.Ceiling(MinimumSearchHz / bandWidthHz));
        var lastBand = Math.Min(
            bandLevelsDb.Count - windowBands,
            (int)Math.Floor(((nyquistHz * 0.985) - WindowRadiusHz) / bandWidthHz));

        var bestIndex = -1;
        var bestDropDb = double.NegativeInfinity;
        var bestBelowDb = double.NaN;
        for (var index = firstBand; index <= lastBand; index++)
        {
            var belowDb = AverageFinite(bandLevelsDb, index - windowBands, index);
            var aboveDb = AverageFinite(bandLevelsDb, index, index + windowBands);
            var dropDb = belowDb - aboveDb;
            if (dropDb > bestDropDb)
            {
                bestIndex = index;
                bestDropDb = dropDb;
                bestBelowDb = belowDb;
            }
        }

        if (bestIndex < 0 || bestDropDb < MinimumWallDropDb)
        {
            return new SpectralAnalysisResult(SpectralVerdict.Genuine, null, null, null, null, framesAnalyzed, "No sharp high-frequency cutoff was found.");
        }

        var abovePercentileDb = PercentileFinite(bandLevelsDb, bestIndex + windowBands, bandLevelsDb.Count, 0.90);
        if (!double.IsFinite(abovePercentileDb) || bestBelowDb - abovePercentileDb < 15)
        {
            return new SpectralAnalysisResult(SpectralVerdict.Genuine, null, null, null, bestDropDb, framesAnalyzed, "The high-frequency spectrum does not support a low-pass verdict.");
        }

        var refinementThreshold = bestBelowDb - Math.Max(3, bestDropDb * 0.2);
        var refinedIndex = bestIndex;
        while (refinedIndex > bestIndex - windowBands && bandLevelsDb[refinedIndex - 1] <= refinementThreshold)
        {
            refinedIndex--;
        }

        var cutoffHz = refinedIndex * bandWidthHz;
        var averageAboveDb = AverageFinite(bandLevelsDb, bestIndex + windowBands, bandLevelsDb.Count);
        var hfEnergyRatio = Math.Pow(10, (averageAboveDb - bestBelowDb) / 10);
        var nominalLowpassHz = EstimateNominalLowpass(cutoffHz, nyquistHz);

        var verdict = ClassifyCutoff(cutoffHz, bestDropDb, nyquistHz);
        var reason = BuildReason(verdict, cutoffHz, nominalLowpassHz);
        return new SpectralAnalysisResult(verdict, cutoffHz, nominalLowpassHz, hfEnergyRatio, bestDropDb, framesAnalyzed, reason);
    }

    private static SpectralVerdict ClassifyCutoff(double cutoffHz, double dropDb, double nyquistHz)
    {
        if (nyquistHz > 30000)
        {
            if (cutoffHz is >= 19500 and <= 24000)
            {
                return SpectralVerdict.Upsampled;
            }

            return cutoffHz < 19500 ? SpectralVerdict.Lossy : SpectralVerdict.Genuine;
        }

        if (cutoffHz >= 20900)
        {
            return SpectralVerdict.Genuine;
        }

        if (cutoffHz >= 20250 || (cutoffHz >= 19800 && dropDb < 30))
        {
            return SpectralVerdict.Suspect;
        }

        return SpectralVerdict.Lossy;
    }

    private static double? EstimateNominalLowpass(double cutoffHz, double nyquistHz)
    {
        if (nyquistHz > 30000 && cutoffHz is >= 19500 and <= 24000)
        {
            return cutoffHz;
        }

        if (cutoffHz < 17200)
        {
            return 16600;
        }

        if (cutoffHz < 19000)
        {
            return 18650;
        }

        if (cutoffHz < 19800)
        {
            return 19350;
        }

        if (cutoffHz <= 20250)
        {
            return 20000;
        }

        return null;
    }

    private static string BuildReason(SpectralVerdict verdict, double cutoffHz, double? nominalLowpassHz)
    {
        var cutoff = (cutoffHz / 1000).ToString("F1", CultureInfo.InvariantCulture);
        var bitrate = nominalLowpassHz switch
        {
            <= 17000 => " (~MP3 128 kbps)",
            <= 19000 => " (~MP3 192 kbps)",
            <= 19800 => " (~MP3 256 kbps)",
            <= 20250 => " (~MP3 320 kbps)",
            _ => string.Empty,
        };

        return verdict switch
        {
            SpectralVerdict.Lossy => $"Lossy spectral shelf at {cutoff} kHz{bitrate}.",
            SpectralVerdict.Suspect => $"Suspect spectral low-pass at {cutoff} kHz; review the source before treating it as lossy.",
            SpectralVerdict.Upsampled => $"High-resolution audio has a {cutoff} kHz cutoff consistent with upsampling from 44.1/48 kHz audio.",
            SpectralVerdict.Genuine => $"Spectral cutoff at {cutoff} kHz is consistent with high-frequency source content.",
            _ => "Spectral analysis was inconclusive.",
        };
    }

    private static double[] BuildBandLevels(double[] powerSums, int framesAnalyzed, int sampleRateHz)
    {
        var nyquistHz = sampleRateHz / 2.0;
        var bandCount = (int)Math.Floor(nyquistHz / BandWidthHz) + 1;
        var bandPower = new double[bandCount];
        var bandBins = new int[bandCount];

        for (var bin = 1; bin < powerSums.Length; bin++)
        {
            var frequencyHz = bin * sampleRateHz / (double)WindowSize;
            var band = (int)(frequencyHz / BandWidthHz);
            if (band >= bandCount)
            {
                continue;
            }

            bandPower[band] += powerSums[bin];
            bandBins[band]++;
        }

        var levelsDb = new double[bandCount];
        for (var band = 0; band < bandCount; band++)
        {
            var averagePower = bandBins[band] == 0
                ? 0
                : bandPower[band] / (bandBins[band] * (double)framesAnalyzed);
            levelsDb[band] = 10 * Math.Log10(Math.Max(averagePower, 1e-30));
        }

        return levelsDb;
    }

    private static bool AccumulateFrame(byte[] pcmWindow, double[] real, double[] imaginary, double[] powerSums)
    {
        var rmsPower = 0.0;
        for (var sampleIndex = 0; sampleIndex < WindowSize; sampleIndex++)
        {
            var sample = ReadSample(pcmWindow, sampleIndex);
            rmsPower += sample * sample;
        }

        if (Math.Sqrt(rmsPower / WindowSize) < SilenceRmsThreshold)
        {
            return false;
        }

        for (var sampleIndex = 0; sampleIndex < WindowSize; sampleIndex++)
        {
            real[sampleIndex] = ReadSample(pcmWindow, sampleIndex) * HannWindow[sampleIndex];
            imaginary[sampleIndex] = 0;
        }

        Transform(real, imaginary);
        for (var bin = 1; bin < powerSums.Length; bin++)
        {
            powerSums[bin] += (real[bin] * real[bin]) + (imaginary[bin] * imaginary[bin]);
        }

        return true;
    }

    private static float ReadSample(byte[] pcmWindow, int sampleIndex)
    {
        var bytes = pcmWindow.AsSpan(sampleIndex * sizeof(float), sizeof(float));
        return BitConverter.Int32BitsToSingle(BinaryPrimitives.ReadInt32LittleEndian(bytes));
    }

    private static void Transform(double[] real, double[] imaginary)
    {
        var j = 0;
        for (var i = 1; i < WindowSize; i++)
        {
            var bit = WindowSize >> 1;
            while ((j & bit) != 0)
            {
                j ^= bit;
                bit >>= 1;
            }

            j ^= bit;
            if (i < j)
            {
                (real[i], real[j]) = (real[j], real[i]);
                (imaginary[i], imaginary[j]) = (imaginary[j], imaginary[i]);
            }
        }

        for (var length = 2; length <= WindowSize; length <<= 1)
        {
            var angle = -2 * Math.PI / length;
            var stepReal = Math.Cos(angle);
            var stepImaginary = Math.Sin(angle);
            var halfLength = length >> 1;

            for (var start = 0; start < WindowSize; start += length)
            {
                var twiddleReal = 1.0;
                var twiddleImaginary = 0.0;
                for (var offset = 0; offset < halfLength; offset++)
                {
                    var evenIndex = start + offset;
                    var oddIndex = evenIndex + halfLength;
                    var oddReal = (real[oddIndex] * twiddleReal) - (imaginary[oddIndex] * twiddleImaginary);
                    var oddImaginary = (real[oddIndex] * twiddleImaginary) + (imaginary[oddIndex] * twiddleReal);
                    var evenReal = real[evenIndex];
                    var evenImaginary = imaginary[evenIndex];

                    real[evenIndex] = evenReal + oddReal;
                    imaginary[evenIndex] = evenImaginary + oddImaginary;
                    real[oddIndex] = evenReal - oddReal;
                    imaginary[oddIndex] = evenImaginary - oddImaginary;

                    var nextTwiddleReal = (twiddleReal * stepReal) - (twiddleImaginary * stepImaginary);
                    twiddleImaginary = (twiddleReal * stepImaginary) + (twiddleImaginary * stepReal);
                    twiddleReal = nextTwiddleReal;
                }
            }
        }
    }

    private static double[] CreateHannWindow()
    {
        var window = new double[WindowSize];
        for (var index = 0; index < window.Length; index++)
        {
            window[index] = 0.5 - (0.5 * Math.Cos((2 * Math.PI * index) / (WindowSize - 1)));
        }

        return window;
    }

    private static async Task<bool> ReadWindowAsync(Stream stream, byte[] buffer, CancellationToken cancellationToken)
    {
        var read = 0;
        while (read < buffer.Length)
        {
            var count = await stream.ReadAsync(buffer.AsMemory(read), cancellationToken).ConfigureAwait(false);
            if (count == 0)
            {
                return false;
            }

            read += count;
        }

        return true;
    }

    private static double AverageFinite(IReadOnlyList<double> values, int start, int end)
    {
        var total = 0.0;
        var count = 0;
        for (var index = Math.Max(0, start); index < Math.Min(values.Count, end); index++)
        {
            if (double.IsFinite(values[index]))
            {
                total += values[index];
                count++;
            }
        }

        return count == 0 ? double.NaN : total / count;
    }

    private static double PercentileFinite(IReadOnlyList<double> values, int start, int end, double percentile)
    {
        var finite = new List<double>();
        for (var index = Math.Max(0, start); index < Math.Min(values.Count, end); index++)
        {
            if (double.IsFinite(values[index]))
            {
                finite.Add(values[index]);
            }
        }

        if (finite.Count == 0)
        {
            return double.NaN;
        }

        finite.Sort();
        var percentileIndex = (int)Math.Floor((finite.Count - 1) * percentile);
        return finite[percentileIndex];
    }

    private static void TryTerminate(Process process)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch (InvalidOperationException)
        {
            // The process exited while the bounded PCM window was being consumed.
        }
        catch (Win32Exception)
        {
            // A concurrent process exit is already sufficient to release its output streams.
        }
    }

    private static async Task StopProcessAsync(Process process)
    {
        TryTerminate(process);
        try
        {
            await process.WaitForExitAsync(CancellationToken.None).ConfigureAwait(false);
        }
        catch (InvalidOperationException)
        {
            // The process was not started.
        }
    }
}

internal enum SpectralVerdict
{
    Inconclusive,
    Genuine,
    Suspect,
    Lossy,
    Upsampled,
}

internal sealed record SpectralAnalysisResult(
    SpectralVerdict Verdict,
    double? EffectiveBandwidthHz,
    double? NominalLowpassHz,
    double? HfEnergyRatio,
    double? WallDropDb,
    int FramesAnalyzed,
    string Reason)
{
    public static SpectralAnalysisResult Inconclusive(string reason)
    {
        return new SpectralAnalysisResult(SpectralVerdict.Inconclusive, null, null, null, null, 0, reason);
    }
}
