// <copyright file="Mp3Analyzer.cs" company="slskdN Team">
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
    ///     MP3-specific analysis: tag-stripped stream hash, encoder hints, and coarse quality heuristics.
    /// </summary>
    public class Mp3Analyzer
    {
        private const string AnalyzerVersion = "audioqa-2";

        /// <summary>
        ///     Analyze an MP3 file and derive codec-specific fingerprints plus quality heuristics.
        /// </summary>
        /// <param name="filePath">Absolute path to the MP3 file.</param>
        /// <param name="variant">Baseline variant metadata (bitrate, etc.).</param>
        /// <returns>MP3 analysis result.</returns>
        public Mp3AnalysisResult Analyze(string filePath, AudioVariant variant)
        {
            if (string.IsNullOrWhiteSpace(filePath))
            {
                throw new ArgumentException("File path cannot be null or empty.", nameof(filePath));
            }

            var result = new Mp3AnalysisResult
            {
                AnalyzerVersion = AnalyzerVersion,
            };

            result.Mp3StreamHash = ComputeStreamHash(filePath);
            PopulateEncoderInfo(filePath, result);

            // Base quality from bitrate / preset
            var bitrate = variant?.BitrateKbps ?? 0;
            result.QualityScore = bitrate switch
            {
                >= 320 => 0.80,
                >= 260 => 0.76,
                >= 220 => 0.72,
                >= 190 => 0.70,
                >= 160 => 0.60,
                >= 128 => 0.50,
                _ => 0.35,
            };

            // Basic transcode suspicion: high bitrate but unknown/low-energy hint
            if (bitrate >= 256 && string.Equals(result.Mp3Encoder, "Unknown", StringComparison.OrdinalIgnoreCase))
            {
                result.TranscodeSuspect = true;
                result.TranscodeReason = "High bitrate with unknown encoder";
                result.QualityScore = Math.Min(result.QualityScore, 0.5);
            }

            return result;
        }

        private static string ComputeStreamHash(string filePath)
        {
            try
            {
                using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                var fileLength = fs.Length;

                var start = ReadId3v2Size(fs);
                var end = fileLength - ReadId3v1Size(fs);

                start = Math.Clamp(start, 0, (int)fileLength);
                end = Math.Clamp(end, start, fileLength);

                using var sha = SHA256.Create();
                fs.Position = start;
                var buffer = new byte[8192];
                long remaining = end - start;
                while (remaining > 0)
                {
                    var toRead = (int)Math.Min(buffer.Length, remaining);
                    var read = fs.Read(buffer, 0, toRead);
                    if (read <= 0)
                    {
                        break;
                    }

                    sha.TransformBlock(buffer, 0, read, null, 0);
                    remaining -= read;
                }

                sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
                return BitConverter.ToString(sha.Hash!).Replace("-", string.Empty).ToLowerInvariant();
            }
            catch
            {
                return string.Empty;
            }
        }

        private static int ReadId3v2Size(FileStream fs)
        {
            try
            {
                var header = new byte[10];
                fs.Position = 0;
                if (fs.Read(header, 0, 10) != 10)
                {
                    return 0;
                }

                if (header[0] != 'I' || header[1] != 'D' || header[2] != '3')
                {
                    return 0;
                }

                // Size is 4 syncsafe bytes at 6-9
                int size = (header[6] & 0x7F) << 21 |
                           (header[7] & 0x7F) << 14 |
                           (header[8] & 0x7F) << 7 |
                           (header[9] & 0x7F);

                // Total size includes the 10-byte header
                return size + 10;
            }
            catch
            {
                return 0;
            }
        }

        private static int ReadId3v1Size(FileStream fs)
        {
            try
            {
                if (fs.Length < 128)
                {
                    return 0;
                }

                var buffer = new byte[3];
                fs.Position = fs.Length - 128;
                if (fs.Read(buffer, 0, 3) != 3)
                {
                    return 0;
                }

                return buffer[0] == 'T' && buffer[1] == 'A' && buffer[2] == 'G' ? 128 : 0;
            }
            catch
            {
                return 0;
            }
        }

        private static void PopulateEncoderInfo(string filePath, Mp3AnalysisResult result)
        {
            try
            {
                using var tagFile = TagLib.File.Create(filePath);
                var firstCodec = tagFile?.Properties?.Codecs?.FirstOrDefault();
                var description = firstCodec?.Description;

                if (!string.IsNullOrWhiteSpace(description))
                {
                    result.Mp3Encoder = description.Contains("LAME", StringComparison.OrdinalIgnoreCase) ? "LAME" :
                                        description.Contains("Xing", StringComparison.OrdinalIgnoreCase) ? "Xing" :
                                        description.Contains("Fraunhofer", StringComparison.OrdinalIgnoreCase) ? "FhG" :
                                        "Unknown";
                }

                // Preset hints: TagLib reports some VBR/CBR info in Description
                if (!string.IsNullOrWhiteSpace(description))
                {
                    if (description.Contains("V0", StringComparison.OrdinalIgnoreCase))
                    {
                        result.Mp3EncoderPreset = "V0";
                    }
                    else if (description.Contains("V2", StringComparison.OrdinalIgnoreCase))
                    {
                        result.Mp3EncoderPreset = "V2";
                    }
                    else if (description.Contains("CBR") || description.Contains("CBR", StringComparison.OrdinalIgnoreCase))
                    {
                        result.Mp3EncoderPreset = "CBR";
                    }
                }
            }
            catch
            {
                // leave encoder info unknown
            }

            result.Mp3Encoder ??= "Unknown";
        }
    }

    /// <summary>
    ///     Result of MP3 analysis.
    /// </summary>
    public class Mp3AnalysisResult
    {
        public string Mp3StreamHash { get; set; } = string.Empty;
        public string Mp3Encoder { get; set; } = string.Empty;
        public string Mp3EncoderPreset { get; set; } = string.Empty;
        public int? Mp3FramesAnalyzed { get; set; }
        public double? EffectiveBandwidthHz { get; set; }
        public double? NominalLowpassHz { get; set; }
        public double? SpectralFlatnessScore { get; set; }
        public double? HfEnergyRatio { get; set; }
        public double QualityScore { get; set; }
        public bool TranscodeSuspect { get; set; }
        public string TranscodeReason { get; set; } = string.Empty;
        public string AnalyzerVersion { get; set; } = string.Empty;
    }
}
