// <copyright file="SpectralClassifierTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Audio
{
    using System;
    using System.Linq;
    using slskd.Audio;
    using Xunit;

    public class SpectralClassifierTests
    {
        private const double BandHz = 100;

        [Theory]
        [InlineData(16600, "MP3 128 kbps")]
        [InlineData(18700, "MP3 192 kbps / V2")]
        [InlineData(19300, "MP3 256 kbps / V0")]
        [InlineData(14000, "lossy 96 kbps")]
        public void Classify_BrickWallShelf_IsLossyWithSourceEstimate(double wallHz, string expectedSource)
        {
            var result = SpectralClassifier.Classify(Wall(44100, wallHz, levelBelow: -20, levelAbove: -75), BandHz, 44100, 600);

            Assert.Equal(SpectralVerdict.Lossy, result.Verdict);
            Assert.InRange(result.CutoffHz!.Value, wallHz - 200, wallHz + 200);
            Assert.True(result.ShelfDropDb >= 20);
            Assert.True(result.AboveShelfDb <= -15);
            Assert.Equal(expectedSource, result.EstimatedSource);
        }

        [Fact]
        public void Classify_NaturalRolloffToNyquist_IsGenuine()
        {
            // Falls 30 dB between 0 Hz and 22 kHz with no step anywhere.
            var bands = Enumerable.Range(0, 220).Select(b => -20 - (30.0 * b / 220)).ToArray();

            var result = SpectralClassifier.Classify(bands, BandHz, 44100, 600);

            Assert.Equal(SpectralVerdict.Genuine, result.Verdict);
            Assert.Null(result.CutoffHz);
        }

        [Fact]
        public void Classify_ModernMasteringFilter_IsGenuine()
        {
            var result = SpectralClassifier.Classify(Wall(44100, 21000, -20, -75), BandHz, 44100, 600);

            Assert.Equal(SpectralVerdict.Genuine, result.Verdict);
        }

        [Theory]
        [InlineData(20500)]   // early-digital mastering filter or older 320 kbps MP3
        [InlineData(20000)]   // 320 kbps MP3 or a mastering lowpass
        public void Classify_ShelfInTheAmbiguousBand_IsSuspect(double wallHz)
        {
            var result = SpectralClassifier.Classify(Wall(44100, wallHz, -20, -75), BandHz, 44100, 600);

            Assert.Equal(SpectralVerdict.Suspect, result.Verdict);
        }

        [Fact]
        public void Classify_DropWithContentStillAbove_IsNotAShelf()
        {
            // A 25 dB step, but the "above" region is only 10 dB down: real content, not an encoder lowpass.
            var bands = Wall(44100, 16600, -20, -45);
            for (var b = 170; b < bands.Length; b++)
            {
                bands[b] = -30;
            }

            var result = SpectralClassifier.Classify(bands, BandHz, 44100, 600);

            Assert.Equal(SpectralVerdict.Genuine, result.Verdict);
        }

        [Fact]
        public void Classify_HiResFileWallingAtCdNyquist_IsUpsampled()
        {
            var result = SpectralClassifier.Classify(Wall(96000, 22000, -20, -80), BandHz, 96000, 600);

            Assert.Equal(SpectralVerdict.Upsampled, result.Verdict);
            Assert.Equal("44.1 kHz (CD) master", result.EstimatedSource);
        }

        [Fact]
        public void Classify_HiResFileWithLossyShelf_IsLossy()
        {
            var result = SpectralClassifier.Classify(Wall(96000, 16600, -20, -80), BandHz, 96000, 600);

            Assert.Equal(SpectralVerdict.Lossy, result.Verdict);
        }

        [Theory]
        [InlineData(19799, 22050, SpectralVerdict.Lossy)]
        [InlineData(19800, 22050, SpectralVerdict.Suspect)]
        [InlineData(20899, 22050, SpectralVerdict.Suspect)]
        [InlineData(20900, 22050, SpectralVerdict.Genuine)]
        [InlineData(19499, 48000, SpectralVerdict.Lossy)]
        [InlineData(19500, 48000, SpectralVerdict.Upsampled)]
        public void VerdictForShelf_UsesTheDocumentedBoundaries(double cutoffHz, double nyquistHz, SpectralVerdict expected)
        {
            Assert.Equal(expected, SpectralClassifier.VerdictForShelf(cutoffHz, nyquistHz));
        }

        [Fact]
        public void BuildBands_AveragesBinsIntoRoughly100HzBands()
        {
            var power = new double[(SpectralClassifier.FftSize / 2) + 1];
            Array.Fill(power, 1.0);

            var (bandDb, bandHz) = SpectralClassifier.BuildBands(power, frames: 1, sampleRateHz: 44100);

            Assert.InRange(bandHz, 95, 105);
            Assert.All(bandDb, level => Assert.InRange(level, -0.001, 0.001));   // 10*log10(1)
        }

        [Fact]
        public void Fft_PutsAPureToneInItsBin()
        {
            const int n = 1024;
            const int bin = 37;
            var re = Enumerable.Range(0, n).Select(i => Math.Sin(2 * Math.PI * bin * i / n)).ToArray();
            var im = new double[n];

            SpectralClassifier.Fft(re, im);

            var magnitudes = Enumerable.Range(0, n / 2).Select(k => (re[k] * re[k]) + (im[k] * im[k])).ToArray();
            Assert.Equal(bin, Array.IndexOf(magnitudes, magnitudes.Max()));
            Assert.InRange(Math.Sqrt(magnitudes[bin]), (n / 2.0) - 1e-6, (n / 2.0) + 1e-6);
        }

        // Band levels for a file at sampleRateHz: flat at levelBelow up to wallHz, then levelAbove.
        private static double[] Wall(int sampleRateHz, double wallHz, double levelBelow, double levelAbove)
        {
            var count = (int)(sampleRateHz / 2.0 / BandHz);
            return Enumerable.Range(0, count).Select(b => b * BandHz < wallHz ? levelBelow : levelAbove).ToArray();
        }
    }
}
