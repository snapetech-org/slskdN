// <copyright file="OpusAnalyzer.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio.Analyzers
{
    using System;
    using System.IO;
    using System.Linq;
    using System.Security.Cryptography;
    using TagLib;

    /// <summary>
    ///     Opus-specific analysis: stream hash, basic metadata, and coarse heuristics.
    /// </summary>
    public class OpusAnalyzer
    {
        private const string AnalyzerVersion = "audioqa-2";

        /// <summary>
        ///     Analyze an Opus file and derive codec-specific fingerprints plus quality heuristics.
        /// </summary>
        /// <param name="filePath">Absolute path to the Opus file.</param>
        /// <param name="variant">Baseline variant metadata (bitrate, etc.).</param>
        /// <returns>Opus analysis result.</returns>
        public OpusAnalysisResult Analyze(string filePath, AudioVariant variant)
        {
            if (string.IsNullOrWhiteSpace(filePath))
            {
                throw new ArgumentException("File path cannot be null or empty.", nameof(filePath));
            }

            var result = new OpusAnalysisResult
            {
                AnalyzerVersion = AnalyzerVersion,
            };

            result.OpusStreamHash = ComputeStreamHash(filePath);
            PopulateFromTags(filePath, result);

            var bitrate = variant?.BitrateKbps ?? 0;
            result.OpusNominalBitrateKbps ??= bitrate > 0 ? bitrate : null;

            // Base quality by nominal bitrate
            result.QualityScore = bitrate switch
            {
                >= 160 => 0.80,
                >= 128 => 0.75,
                >= 96 => 0.70,
                >= 64 => 0.60,
                _ => 0.45,
            };

            // Bandwidth mode adjustments
            if (string.Equals(result.OpusBandwidthMode, "Fullband", StringComparison.OrdinalIgnoreCase))
            {
                result.QualityScore = Math.Min(0.85, result.QualityScore + 0.05);
            }
            else if (!string.IsNullOrWhiteSpace(result.OpusBandwidthMode) &&
                     (result.OpusBandwidthMode.Equals("Narrowband", StringComparison.OrdinalIgnoreCase) ||
                      result.OpusBandwidthMode.Equals("Wideband", StringComparison.OrdinalIgnoreCase)))
            {
                result.QualityScore = Math.Max(0.4, result.QualityScore - 0.1);
            }

            result.QualityScore = Math.Clamp(result.QualityScore, 0.0, 0.85);
            return result;
        }

        private static string ComputeStreamHash(string filePath)
        {
            try
            {
                using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                var buffer = new byte[16384]; // read initial pages; hash ID header + first data pages

                var read = fs.Read(buffer, 0, buffer.Length);
                if (read <= 0)
                {
                    return string.Empty;
                }

                using var sha = SHA256.Create();
                sha.TransformBlock(buffer, 0, read, null, 0);
                sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
                return BitConverter.ToString(sha.Hash!).Replace("-", string.Empty).ToLowerInvariant();
            }
            catch
            {
                return string.Empty;
            }
        }

        private static void PopulateFromTags(string filePath, OpusAnalysisResult result)
        {
            try
            {
                using var tagFile = TagLib.File.Create(filePath);
                var props = tagFile?.Properties;

                // TagLib exposes Opus properties via container
                result.OpusNominalBitrateKbps ??= props?.AudioBitrate;

                var description = props?.Codecs?.FirstOrDefault()?.Description ?? string.Empty;
                if (description.Contains("audio", StringComparison.OrdinalIgnoreCase))
                {
                    result.OpusApplication = "Audio";
                }
                else if (description.Contains("voip", StringComparison.OrdinalIgnoreCase))
                {
                    result.OpusApplication = "VoIP";
                }
                else if (description.Contains("lowdelay", StringComparison.OrdinalIgnoreCase))
                {
                    result.OpusApplication = "LowDelay";
                }

                if (description.Contains("fullband", StringComparison.OrdinalIgnoreCase))
                {
                    result.OpusBandwidthMode = "Fullband";
                }
                else if (description.Contains("wideband", StringComparison.OrdinalIgnoreCase))
                {
                    result.OpusBandwidthMode = "Wideband";
                }
                else if (description.Contains("narrowband", StringComparison.OrdinalIgnoreCase))
                {
                    result.OpusBandwidthMode = "Narrowband";
                }
            }
            catch
            {
                // leave fields unknown
            }
        }
    }

    /// <summary>
    ///     Result of Opus analysis.
    /// </summary>
    public class OpusAnalysisResult
    {
        public string OpusStreamHash { get; set; } = string.Empty;
        public int? OpusNominalBitrateKbps { get; set; }
        public string OpusApplication { get; set; } = string.Empty;
        public string OpusBandwidthMode { get; set; } = string.Empty;
        public double? EffectiveBandwidthHz { get; set; }
        public double? HfEnergyRatio { get; set; }
        public double QualityScore { get; set; }
        public bool TranscodeSuspect { get; set; }
        public string TranscodeReason { get; set; } = string.Empty;
        public string AnalyzerVersion { get; set; } = string.Empty;
    }
}
