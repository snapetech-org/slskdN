// <copyright file="SpectralClassifier.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio
{
    using System;
    using System.Collections.Generic;
    using System.Globalization;

    /// <summary>
    ///     Finds the lowpass shelf a lossy encoder (MP3, AAC, Opus, Vorbis) leaves in the spectrum. Converting the
    ///     decoded audio to FLAC cannot restore what the encoder removed, so a lossless file made from a lossy one
    ///     shows a sharp wall (a 25-55 dB drop within a few hundred Hz) with nothing above it, while genuine CD
    ///     audio rolls off gradually or has a mastering/anti-alias filter at 20.9 kHz or higher.
    /// </summary>
    /// <remarks>
    ///     Pure functions over an averaged power spectrum, so they can be tested without ffmpeg.
    ///     <see cref="SpectralAnalyzer"/> does the decoding.
    /// </remarks>
    public static class SpectralClassifier
    {
        public const int FftSize = 8192;

        /// <summary>Gets the minimum number of non-silent frames for a usable average.</summary>
        public const int MinFrames = 20;

        private const double TargetBandHz = 100.0;
        private const double MinShelfDropDb = 20.0;
        private const double MaxAboveShelfDb = -15.0;
        private const double SearchStartHz = 10000.0;
        private const double SearchWindowHz = 500.0;

        // Measured on real files: LAME walls sit at 16.6 (128k), 18.6-18.7 (192k/V2), 19.3-19.4 (256k/V0) and
        // 20.0 kHz (320k). Late-80s digital masters (PCM-1630 era) wall at 20.4-20.6 kHz and modern masters at
        // 20.9 kHz or higher, so everything from 19.8 kHz up is never called Lossy.
        private const double GenuineFromHz = 20900.0;
        private const double SuspectFromHz = 19800.0;
        private const double HiResUpsampledFromHz = 19500.0;
        private const double HiResNyquistHz = 30000.0;

        /// <summary>
        ///     Averages per-bin power over <paramref name="frames"/> frames into roughly 100 Hz bands, in dB.
        /// </summary>
        public static (double[] BandDb, double BandHz) BuildBands(double[] power, int frames, int sampleRateHz)
        {
            var binHz = (double)sampleRateHz / FftSize;
            var binsPerBand = Math.Max(1, (int)Math.Round(TargetBandHz / binHz));
            var bandCount = (FftSize / 2) / binsPerBand;
            var bands = new double[bandCount];
            for (var b = 0; b < bandCount; b++)
            {
                double sum = 0;
                for (var k = b * binsPerBand; k < (b + 1) * binsPerBand; k++)
                {
                    sum += power[k];
                }

                bands[b] = 10 * Math.Log10((sum / binsPerBand / frames) + 1e-20);
            }

            return (bands, binHz * binsPerBand);
        }

        /// <summary>
        ///     Classifies an averaged band spectrum built by <see cref="BuildBands"/>.
        /// </summary>
        public static SpectralAnalysisResult Classify(double[] bandDb, double bandHz, int sampleRateHz, int framesAnalyzed)
        {
            var nyquist = sampleRateHz / 2.0;
            var shelf = FindShelf(bandDb, bandHz, nyquist);

            if (shelf is null)
            {
                return new SpectralAnalysisResult
                {
                    Verdict = SpectralVerdict.Genuine,
                    SampleRateHz = sampleRateHz,
                    FramesAnalyzed = framesAnalyzed,
                    Detail = $"no lossy shelf; content reaches {Khz(nyquist)} kHz",
                };
            }

            var (cutoffHz, dropDb, aboveDb) = shelf.Value;
            var verdict = VerdictForShelf(cutoffHz, nyquist);
            return new SpectralAnalysisResult
            {
                Verdict = verdict,
                SampleRateHz = sampleRateHz,
                FramesAnalyzed = framesAnalyzed,
                CutoffHz = cutoffHz,
                ShelfDropDb = dropDb,
                AboveShelfDb = aboveDb,
                EstimatedSource = EstimateSource(verdict, cutoffHz),
                Detail = $"shelf at {Khz(cutoffHz)} kHz, {dropDb.ToString("0", CultureInfo.InvariantCulture)} dB drop",
            };
        }

        /// <summary>
        ///     Gets the verdict for a qualifying shelf at <paramref name="cutoffHz"/>. Shared with
        ///     <see cref="TranscodeDetector"/> so a stored measurement always re-derives the same verdict.
        /// </summary>
        public static SpectralVerdict VerdictForShelf(double cutoffHz, double nyquistHz)
        {
            if (nyquistHz > HiResNyquistHz)
            {
                // A hi-res container: a wall around 19.5-24 kHz means a 44.1/48 kHz source; lower means lossy.
                return cutoffHz >= HiResUpsampledFromHz ? SpectralVerdict.Upsampled : SpectralVerdict.Lossy;
            }

            if (cutoffHz >= GenuineFromHz)
            {
                return SpectralVerdict.Genuine;
            }

            return cutoffHz >= SuspectFromHz ? SpectralVerdict.Suspect : SpectralVerdict.Lossy;
        }

        /// <summary>
        ///     Estimates the lossy source from a shelf position. LAME's default lowpass per bitrate is the strongest
        ///     tell; AAC, Opus, and Vorbis encoders land in similar places.
        /// </summary>
        public static string EstimateLossySource(double cutoffHz) => cutoffHz switch
        {
            < 11500 => "lossy 64 kbps or lower",
            < 15000 => "lossy 96 kbps",
            < 17000 => "MP3 128 kbps",
            < 18300 => "MP3 160 kbps",
            < 18950 => "MP3 192 kbps / V2",
            < 19700 => "MP3 256 kbps / V0",
            _ => "MP3 320 kbps or Opus",
        };

        // In-place iterative radix-2 Cooley-Tukey FFT. re.Length must be a power of two.
        internal static void Fft(double[] re, double[] im)
        {
            var n = re.Length;
            for (int i = 1, j = 0; i < n; i++)
            {
                var bit = n >> 1;
                for (; (j & bit) != 0; bit >>= 1)
                {
                    j ^= bit;
                }

                j ^= bit;
                if (i < j)
                {
                    (re[i], re[j]) = (re[j], re[i]);
                    (im[i], im[j]) = (im[j], im[i]);
                }
            }

            for (var len = 2; len <= n; len <<= 1)
            {
                var angle = -2 * Math.PI / len;
                double wr = Math.Cos(angle), wi = Math.Sin(angle);
                for (var i = 0; i < n; i += len)
                {
                    double cr = 1, ci = 0;
                    for (var k = 0; k < len / 2; k++)
                    {
                        int a = i + k, b = a + (len / 2);
                        var xr = (re[b] * cr) - (im[b] * ci);
                        var xi = (re[b] * ci) + (im[b] * cr);
                        re[b] = re[a] - xr;
                        im[b] = im[a] - xi;
                        re[a] += xr;
                        im[a] += xi;
                        var t = (cr * wr) - (ci * wi);
                        ci = (cr * wi) + (ci * wr);
                        cr = t;
                    }
                }
            }
        }

        internal static double[] HannWindow(int size)
        {
            var window = new double[size];
            for (var i = 0; i < size; i++)
            {
                window[i] = 0.5 - (0.5 * Math.Cos(2 * Math.PI * i / (size - 1)));
            }

            return window;
        }

        private static string EstimateSource(SpectralVerdict verdict, double cutoffHz) => verdict switch
        {
            SpectralVerdict.Lossy or SpectralVerdict.Suspect => EstimateLossySource(cutoffHz),
            SpectralVerdict.Upsampled => cutoffHz >= 23000 ? "48 kHz master" : "44.1 kHz (CD) master",
            _ => string.Empty,
        };

        // The steepest drop between the 500 Hz just below a candidate and the 500 Hz just above it, searched from
        // 10 kHz to just short of Nyquist (every resampler rolls off the last few bands). Returns null unless the
        // drop is deep enough and nothing substantial remains above it.
        private static (double CutoffHz, double DropDb, double AboveDb)? FindShelf(double[] band, double bandHz, double nyquist)
        {
            var lo = Index(SearchStartHz, bandHz);
            var top = Math.Min(band.Length, Index(nyquist * 0.985, bandHz));
            var w = Math.Max(2, Index(SearchWindowHz, bandHz));
            const int gap = 1;
            var best = -1;
            double bestDrop = 0;
            for (var c = lo + w; c + gap + w <= top; c++)
            {
                var drop = Mean(band, c - w, c) - Mean(band, c + gap, c + gap + w);
                if (drop > bestDrop)
                {
                    bestDrop = drop;
                    best = c;
                }
            }

            if (best < 0 || bestDrop < MinShelfDropDb)
            {
                return null;
            }

            // Refine to the band where the fall starts: the last band still within 6 dB of the level below.
            var below = Mean(band, best - w, best);
            var edge = best;
            while (edge + 1 < top && band[edge + 1] > below - 6)
            {
                edge++;
            }

            while (edge > lo && band[edge] < below - 6)
            {
                edge--;
            }

            var aboveStart = Math.Min(top - 1, edge + 1 + Math.Max(1, Index(300, bandHz)));
            var aboveDb = aboveStart < top ? Percentile(band, aboveStart, top, 0.9) - below : 0;
            if (aboveDb > MaxAboveShelfDb)
            {
                return null;
            }

            return ((edge + 1) * bandHz, bestDrop, aboveDb);
        }

        private static int Index(double hz, double bandHz) => (int)(hz / bandHz);

        private static double Mean(double[] values, int from, int to)
        {
            double sum = 0;
            var count = 0;
            for (var i = Math.Max(0, from); i < Math.Min(values.Length, to); i++)
            {
                sum += values[i];
                count++;
            }

            return count > 0 ? sum / count : double.NaN;
        }

        private static double Percentile(double[] values, int from, int to, double quantile)
        {
            var list = new List<double>();
            for (var i = Math.Max(0, from); i < Math.Min(values.Length, to); i++)
            {
                list.Add(values[i]);
            }

            if (list.Count == 0)
            {
                return double.NaN;
            }

            list.Sort();
            return list[(int)Math.Min(list.Count - 1, Math.Floor(quantile * list.Count))];
        }

        private static string Khz(double hz) => (hz / 1000.0).ToString("0.0", CultureInfo.InvariantCulture);
    }
}
