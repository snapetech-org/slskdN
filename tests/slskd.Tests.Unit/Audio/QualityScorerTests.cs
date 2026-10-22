// <copyright file="QualityScorerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Audio
{
    using slskd.Audio;
    using Xunit;

    public class QualityScorerTests
    {
        [Fact]
        public void QualityScorer_FLAC_16bit_44100_Should_Score_High()
        {
            var variant = new AudioVariant
            {
                Codec = "FLAC",
                BitDepth = 16,
                SampleRateHz = 44100,
                BitrateKbps = 900,
                DynamicRangeDR = 11.2,
                HasClipping = false,
                Channels = 2,
            };

            var scorer = new QualityScorer();
            var score = scorer.ComputeQualityScore(variant);

            Assert.InRange(score, 0.95, 1.0);
        }

        [Fact]
        public void TranscodeDetector_LowBitrateFLAC_Should_DetectTranscode()
        {
            var variant = new AudioVariant
            {
                Codec = "FLAC",
                BitDepth = 16,
                SampleRateHz = 44100,
                BitrateKbps = 200,  // Impossibly low for lossless
                DynamicRangeDR = 6.1,
                Channels = 2,
            };

            var detector = new TranscodeDetector();
            var (isSuspect, reason) = detector.DetectTranscode(variant);

            Assert.True(isSuspect);
            Assert.Contains("bitrate", reason, System.StringComparison.OrdinalIgnoreCase);
        }

        [Fact]
        public void TranscodeDetector_UsesMeasuredBandwidthInsteadOfBitrateEstimate()
        {
            var detector = new TranscodeDetector();
            var measured = new AudioVariant
            {
                Codec = "MP3",
                SampleRateHz = 44100,
                BitrateKbps = 320,
                EffectiveBandwidthHz = 16600,
            };
            var unmeasured = new AudioVariant
            {
                Codec = "MP3",
                SampleRateHz = 44100,
                BitrateKbps = 128,
            };

            var (measuredIsSuspect, measuredReason) = detector.DetectTranscode(measured);
            var (unmeasuredIsSuspect, _) = detector.DetectTranscode(unmeasured);

            Assert.True(measuredIsSuspect);
            Assert.Contains("spectral bandwidth", measuredReason, System.StringComparison.OrdinalIgnoreCase);
            Assert.False(unmeasuredIsSuspect);
        }
    }
}
