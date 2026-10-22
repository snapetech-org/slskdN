// <copyright file="AacAnalyzer.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Audio.Analyzers
{
    using System;
    using System.IO;
    using System.Security.Cryptography;
    using System.Text;
    using TagLib;
    using System.Linq;

    /// <summary>
    ///     AAC-specific analysis: stream hash, profile flags, and coarse quality heuristics.
    /// </summary>
    public class AacAnalyzer
    {
        private const string AnalyzerVersion = "audioqa-2";

        /// <summary>
        ///     Analyze an AAC file and derive codec-specific fingerprints plus quality heuristics.
        /// </summary>
        /// <param name="filePath">Absolute path to the AAC/MP4 file.</param>
        /// <param name="variant">Baseline variant metadata (bitrate, etc.).</param>
        /// <returns>AAC analysis result.</returns>
        public AacAnalysisResult Analyze(string filePath, AudioVariant variant)
        {
            if (string.IsNullOrWhiteSpace(filePath))
            {
                throw new ArgumentException("File path cannot be null or empty.", nameof(filePath));
            }

            var result = new AacAnalysisResult
            {
                AnalyzerVersion = AnalyzerVersion,
            };

            result.AacStreamHash = ComputeStreamHash(filePath);
            PopulateFromTags(filePath, result);

            var bitrate = variant?.BitrateKbps ?? 0;
            result.AacNominalBitrateKbps ??= bitrate > 0 ? bitrate : null;

            // Base quality by profile + bitrate
            var profile = result.AacProfile ?? "LC";
            if (string.Equals(profile, "HE", StringComparison.OrdinalIgnoreCase) || string.Equals(profile, "HEv2", StringComparison.OrdinalIgnoreCase))
            {
                if (bitrate >= 96) result.QualityScore = 0.65;
                else if (bitrate >= 64) result.QualityScore = 0.55;
                else result.QualityScore = 0.45;
            }
            else
            {
                if (bitrate >= 256) result.QualityScore = 0.80;
                else if (bitrate >= 192) result.QualityScore = 0.75;
                else if (bitrate >= 128) result.QualityScore = 0.70;
                else if (bitrate >= 96) result.QualityScore = 0.60;
                else result.QualityScore = 0.45;
            }

            // Simple transcode suspicion
            if (bitrate >= 256 && string.Equals(result.AacProfile, "Unknown", StringComparison.OrdinalIgnoreCase))
            {
                result.TranscodeSuspect = true;
                result.TranscodeReason = "High bitrate AAC with unknown profile";
                result.QualityScore = Math.Min(result.QualityScore, 0.55);
            }

            result.QualityScore = Math.Clamp(result.QualityScore, 0.0, 0.85);
            return result;
        }

        private static string ComputeStreamHash(string filePath)
        {
            var ext = Path.GetExtension(filePath)?.ToLowerInvariant();

            try
            {
                if (ext == ".aac")
                {
                    return HashFile(filePath);
                }

                if (ext == ".m4a" || ext == ".mp4" || ext == ".aacp")
                {
                    var hash = HashMdatAtom(filePath);
                    if (hash != null)
                    {
                        return hash;
                    }
                }

                // Fallback: hash first 1MB
                using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                using var sha = SHA256.Create();
                var buffer = new byte[1024 * 1024];
                var read = fs.Read(buffer, 0, buffer.Length);
                sha.TransformBlock(buffer, 0, read, null, 0);
                sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
                return BitConverter.ToString(sha.Hash!).Replace("-", string.Empty).ToLowerInvariant();
            }
            catch
            {
                return string.Empty;
            }
        }

        private static string HashFile(string filePath)
        {
            using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var sha = SHA256.Create();
            var buffer = new byte[8192];
            int read;
            while ((read = fs.Read(buffer, 0, buffer.Length)) > 0)
            {
                sha.TransformBlock(buffer, 0, read, null, 0);
            }

            sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
            return BitConverter.ToString(sha.Hash!).Replace("-", string.Empty).ToLowerInvariant();
        }

        private static string HashMdatAtom(string filePath)
        {
            try
            {
                using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                using var sha = SHA256.Create();
                var buffer = new byte[8];

                while (fs.Position + 8 <= fs.Length)
                {
                    if (fs.Read(buffer, 0, 8) != 8)
                    {
                        break;
                    }

                    var size = ReadUInt32BigEndian(buffer, 0);
                    var type = Encoding.ASCII.GetString(buffer, 4, 4);

                    if (size < 8)
                    {
                        break;
                    }

                    var payloadSize = (long)size - 8;
                    if (type == "mdat")
                    {
                        var remaining = payloadSize;
                        var chunk = new byte[8192];
                        while (remaining > 0)
                        {
                            var toRead = (int)Math.Min(chunk.Length, remaining);
                            var read = fs.Read(chunk, 0, toRead);
                            if (read <= 0)
                            {
                                break;
                            }

                            sha.TransformBlock(chunk, 0, read, null, 0);
                            remaining -= read;
                        }

                        sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
                        return BitConverter.ToString(sha.Hash!).Replace("-", string.Empty).ToLowerInvariant();
                    }

                    // skip this atom
                    fs.Seek(payloadSize, SeekOrigin.Current);
                }
            }
            catch
            {
                // fall through
            }

            return string.Empty;
        }

        private static void PopulateFromTags(string filePath, AacAnalysisResult result)
        {
            try
            {
                using var tagFile = TagLib.File.Create(filePath);
                var props = tagFile?.Properties;
                result.AacNominalBitrateKbps ??= props?.AudioBitrate;

                var description = props?.Codecs != null && props.Codecs.Any()
                    ? props.Codecs.First().Description
                    : string.Empty;

                if (!string.IsNullOrWhiteSpace(description))
                {
                    if (description.Contains("HEv2", StringComparison.OrdinalIgnoreCase))
                    {
                        result.AacProfile = "HEv2";
                        result.AacPsPresent = true;
                        result.AacSbrPresent = true;
                    }
                    else if (description.Contains("HE-AAC", StringComparison.OrdinalIgnoreCase) ||
                             description.Contains("SBR", StringComparison.OrdinalIgnoreCase))
                    {
                        result.AacProfile = "HE";
                        result.AacSbrPresent = true;
                    }
                    else if (description.Contains("LC", StringComparison.OrdinalIgnoreCase))
                    {
                        result.AacProfile = "LC";
                    }
                    else
                    {
                        result.AacProfile = "Unknown";
                    }
                }
                else
                {
                    result.AacProfile = "Unknown";
                }
            }
            catch
            {
                result.AacProfile ??= "Unknown";
            }
        }

        private static uint ReadUInt32BigEndian(byte[] buffer, int offset)
        {
            return ((uint)buffer[offset] << 24) |
                   ((uint)buffer[offset + 1] << 16) |
                   ((uint)buffer[offset + 2] << 8) |
                   buffer[offset + 3];
        }
    }

    /// <summary>
    ///     Result of AAC analysis.
    /// </summary>
    public class AacAnalysisResult
    {
        public string AacStreamHash { get; set; } = string.Empty;
        public string AacProfile { get; set; } = string.Empty;
        public bool? AacSbrPresent { get; set; }
        public bool? AacPsPresent { get; set; }
        public int? AacNominalBitrateKbps { get; set; }
        public double? EffectiveBandwidthHz { get; set; }
        public double? HfEnergyRatio { get; set; }
        public double QualityScore { get; set; }
        public bool TranscodeSuspect { get; set; }
        public string TranscodeReason { get; set; } = string.Empty;
        public string AnalyzerVersion { get; set; } = string.Empty;
    }
}
