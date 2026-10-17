// <copyright file="SpectralAnalysisResultTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Audio
{
    using System.Linq;
    using slskd.Audio;
    using Xunit;

    public class SpectralAnalysisResultTests
    {
        [Fact]
        public void ApplyTo_Lossy_MarksTheVariantAsASuspectedTranscode()
        {
            var variant = Flac(qualityScore: 1.0);

            Lossy(16600).ApplyTo(variant);

            Assert.True(variant.TranscodeSuspect);
            Assert.Equal("spectral: lossy shelf at 16.6 kHz (~MP3 128 kbps)", variant.TranscodeReason);
            Assert.Equal(0.5, variant.QualityScore);
            Assert.Equal(16600, variant.EffectiveBandwidthHz);
            Assert.NotNull(variant.HfEnergyRatio);
        }

        [Fact]
        public void ApplyTo_LossyOnAnAlreadySuspectVariant_AppendsWithoutPenalizingTwice()
        {
            var variant = Flac(qualityScore: 0.4);
            variant.TranscodeSuspect = true;
            variant.TranscodeReason = "FLAC bitrate too low";

            Lossy(16600).ApplyTo(variant);

            Assert.True(variant.TranscodeSuspect);
            Assert.Equal(0.4, variant.QualityScore);
            Assert.StartsWith("FLAC bitrate too low; spectral: lossy shelf", variant.TranscodeReason);
        }

        [Fact]
        public void ApplyTo_Suspect_RecordsTheReasonWithoutFlagging()
        {
            var variant = Flac(qualityScore: 1.0);
            var suspect = new SpectralAnalysisResult
            {
                Verdict = SpectralVerdict.Suspect,
                SampleRateHz = 44100,
                CutoffHz = 20500,
                AboveShelfDb = -40,
                EstimatedSource = "MP3 320 kbps or Opus",
            };

            suspect.ApplyTo(variant);

            Assert.False(variant.TranscodeSuspect);
            Assert.Equal(1.0, variant.QualityScore);
            Assert.Contains("spectral (suspect)", variant.TranscodeReason);
        }

        [Fact]
        public void ApplyTo_Genuine_RecordsFullBandwidthAndNoShelf()
        {
            var variant = Flac(qualityScore: 1.0);

            new SpectralAnalysisResult { Verdict = SpectralVerdict.Genuine, SampleRateHz = 44100 }.ApplyTo(variant);

            Assert.False(variant.TranscodeSuspect);
            Assert.Equal(22050, variant.EffectiveBandwidthHz);
            Assert.Null(variant.HfEnergyRatio);
            Assert.Empty(variant.TranscodeReason);
        }

        [Fact]
        public void ApplyTo_Inconclusive_LeavesTheVariantUnchanged()
        {
            var variant = Flac(qualityScore: 1.0);

            new SpectralAnalysisResult { Verdict = SpectralVerdict.Inconclusive, Detail = "too little audio" }.ApplyTo(variant);

            Assert.Null(variant.EffectiveBandwidthHz);
            Assert.Null(variant.HfEnergyRatio);
            Assert.False(variant.TranscodeSuspect);
        }

        [Theory]
        [InlineData(16600, true)]
        [InlineData(19700, true)]
        [InlineData(20000, false)]   // Suspect: not flagged
        [InlineData(20500, false)]   // Suspect: not flagged
        [InlineData(21000, false)]   // mastering filter
        public void TranscodeDetector_RederivesTheSameVerdictFromStoredFields(double wallHz, bool expectSuspect)
        {
            var bands = Enumerable.Range(0, 220).Select(b => b * 100.0 < wallHz ? -20.0 : -75.0).ToArray();
            var measured = SpectralClassifier.Classify(bands, 100, 44100, 600);
            var analyzed = Flac(qualityScore: 1.0);
            measured.ApplyTo(analyzed);

            // A row read back from HashDb carries only the stored measurement, not the flag.
            var stored = Flac(qualityScore: 1.0);
            stored.EffectiveBandwidthHz = analyzed.EffectiveBandwidthHz;
            stored.HfEnergyRatio = analyzed.HfEnergyRatio;

            var (isSuspect, reason) = new TranscodeDetector().DetectTranscode(stored);

            Assert.Equal(expectSuspect, isSuspect);
            Assert.Equal(analyzed.TranscodeSuspect, isSuspect);
            if (expectSuspect)
            {
                Assert.Equal(measured.Describe(), reason);
            }
        }

        [Fact]
        public void TranscodeDetector_UnanalyzedLosslessFile_IsNotFlaggedBySpectralRule()
        {
            var (isSuspect, _) = new TranscodeDetector().DetectTranscode(Flac(qualityScore: 1.0));

            Assert.False(isSuspect);
        }

        [Fact]
        public void TranscodeDetector_GenuineMeasurement_IsNotFlagged()
        {
            var variant = Flac(qualityScore: 1.0);
            variant.EffectiveBandwidthHz = 22050;   // no shelf: HfEnergyRatio stays null

            var (isSuspect, _) = new TranscodeDetector().DetectTranscode(variant);

            Assert.False(isSuspect);
        }

        private static SpectralAnalysisResult Lossy(double cutoffHz) => new()
        {
            Verdict = SpectralVerdict.Lossy,
            SampleRateHz = 44100,
            CutoffHz = cutoffHz,
            ShelfDropDb = 45,
            AboveShelfDb = -50,
            EstimatedSource = SpectralClassifier.EstimateLossySource(cutoffHz),
        };

        // A healthy 16-bit/44.1 kHz FLAC whose bitrate passes the bitrate rule.
        private static AudioVariant Flac(double qualityScore) => new()
        {
            Codec = "FLAC",
            SampleRateHz = 44100,
            BitDepth = 16,
            Channels = 2,
            BitrateKbps = 900,
            QualityScore = qualityScore,
        };
    }
}
