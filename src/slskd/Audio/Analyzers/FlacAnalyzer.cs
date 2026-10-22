// <copyright file="FlacAnalyzer.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio.Analyzers
{
    using System;
    using System.IO;
    using System.Security.Cryptography;
    using slskd.Audio;
    using slskd.Transfers.MultiSource;

    /// <summary>
    ///     FLAC-specific analysis: STREAMINFO parsing, fingerprints, and simple quality heuristics.
    /// </summary>
    public class FlacAnalyzer
    {
        private const string AnalyzerVersion = "audioqa-2";

        /// <summary>
        ///     Analyze a FLAC file and derive codec-specific fingerprints plus quality heuristics.
        /// </summary>
        /// <param name="filePath">Absolute path to the FLAC file.</param>
        /// <param name="variant">Baseline variant metadata (bitrate, etc.).</param>
        /// <returns>FLAC analysis result.</returns>
        public FlacAnalysisResult Analyze(string filePath, AudioVariant variant)
        {
            if (string.IsNullOrWhiteSpace(filePath))
            {
                throw new ArgumentException("File path cannot be null or empty.", nameof(filePath));
            }

            var result = new FlacAnalysisResult
            {
                AnalyzerVersion = AnalyzerVersion,
            };

            var header = ReadHeader(filePath, FlacStreamInfoParser.MinimumBytesNeeded);
            if (header == null || !FlacStreamInfoParser.TryParse(header, out var streamInfo))
            {
                result.TranscodeReason = "FLAC STREAMINFO unavailable";
                return result;
            }

            result.FlacStreamInfoHash42 = ComputeStreamInfoHash(header);
            result.FlacPcmMd5 = streamInfo.AudioMd5Hex;
            result.FlacMinBlockSize = streamInfo.MinBlockSize;
            result.FlacMaxBlockSize = streamInfo.MaxBlockSize;
            result.FlacMinFrameSize = streamInfo.MinFrameSize;
            result.FlacMaxFrameSize = streamInfo.MaxFrameSize;
            result.FlacTotalSamples = streamInfo.TotalSamples;
            result.SampleRateHz = streamInfo.SampleRate;
            result.BitDepth = streamInfo.BitsPerSample;
            result.Channels = streamInfo.Channels;

            // Baseline quality: high for well-formed FLAC
            var baseQuality = (streamInfo.SampleRate >= 88200 && streamInfo.BitsPerSample >= 24) ? 1.0 : 0.95;

            if (streamInfo.SampleRate < 44100)
            {
                baseQuality -= 0.1; // downsampled or unusual rate
            }

            baseQuality = Math.Clamp(baseQuality, 0.0, 1.0);

            // STREAMINFO bitrate heuristic; spectral analysis can add stronger evidence later.
            var expectedMinKbps = EstimateMinFlacBitrate(streamInfo.SampleRate, streamInfo.BitsPerSample, streamInfo.Channels);
            var actualKbps = variant?.BitrateKbps ?? 0;

            if (actualKbps > 0 && actualKbps < expectedMinKbps * 0.6)
            {
                result.TranscodeSuspect = true;
                result.TranscodeReason = $"Bitrate {actualKbps}kbps too low for {streamInfo.SampleRate}Hz/{streamInfo.BitsPerSample}bit FLAC";
            }
            else if (streamInfo.SampleRate <= 44100 && streamInfo.BitsPerSample <= 16 && actualKbps > 0 && actualKbps < expectedMinKbps * 0.7)
            {
                result.TranscodeSuspect = true;
                result.TranscodeReason = "Low-res FLAC likely sourced from lossy";
            }

            result.QualityScore = result.TranscodeSuspect ? Math.Min(0.6, baseQuality * 0.5) : baseQuality;
            return result;
        }

        private static byte[] ReadHeader(string filePath, int length)
        {
            try
            {
                var buffer = new byte[length];
                using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                var read = fs.Read(buffer, 0, length);
                return read == length ? buffer : Array.Empty<byte>();
            }
            catch (IOException)
            {
                return Array.Empty<byte>();
            }
            catch (UnauthorizedAccessException)
            {
                return Array.Empty<byte>();
            }
        }

        private static string ComputeStreamInfoHash(byte[] header)
        {
            // Hash the first 42 bytes (fLaC + metadata header + STREAMINFO body)
            using var sha = SHA256.Create();
            var hash = sha.ComputeHash(header, 0, FlacStreamInfoParser.MinimumBytesNeeded);
            return BitConverter.ToString(hash).Replace("-", string.Empty).ToLowerInvariant();
        }

        private static int EstimateMinFlacBitrate(int sampleRate, int bitsPerSample, int channels)
        {
            // ~50% of raw PCM bitrate (rough heuristic)
            var raw = (sampleRate * bitsPerSample * channels) / 1000;
            return (int)(raw * 0.5);
        }
    }

    /// <summary>
    ///     Result of FLAC analysis.
    /// </summary>
    public class FlacAnalysisResult
    {
        public string FlacStreamInfoHash42 { get; set; } = string.Empty;
        public string FlacPcmMd5 { get; set; } = string.Empty;
        public int? FlacMinBlockSize { get; set; }
        public int? FlacMaxBlockSize { get; set; }
        public int? FlacMinFrameSize { get; set; }
        public int? FlacMaxFrameSize { get; set; }
        public long? FlacTotalSamples { get; set; }
        public int? SampleRateHz { get; set; }
        public int? BitDepth { get; set; }
        public int? Channels { get; set; }
        public double QualityScore { get; set; }
        public bool TranscodeSuspect { get; set; }
        public string TranscodeReason { get; set; } = string.Empty;
        public string AnalyzerVersion { get; set; } = string.Empty;
    }
}
