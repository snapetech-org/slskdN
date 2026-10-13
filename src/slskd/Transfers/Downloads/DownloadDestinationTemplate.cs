// <copyright file="DownloadDestinationTemplate.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Transfers.Downloads;

using System;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using slskd.Common.Security;
using slskd.Transfers;

/// <summary>
///     Expands configured completed-download path templates into safe relative directories.
/// </summary>
internal static class DownloadDestinationTemplate
{
    private const int MaximumTemplateLength = 1024;
    private const int MaximumSegmentUtf8Bytes = 200;
    private static readonly Regex TokenPattern = new(@"\$\{(?<name>[A-Za-z_]+)\}", RegexOptions.Compiled | RegexOptions.CultureInvariant);
    private static readonly char[] Separators = ['/', '\\'];

    /// <summary>
    ///     Validates the static part of a configured relative path template.
    /// </summary>
    /// <param name="template">The configured template.</param>
    public static void Validate(string template)
    {
        ArgumentNullException.ThrowIfNull(template);

        if (template.Length > MaximumTemplateLength)
        {
            throw new ArgumentException($"The template cannot exceed {MaximumTemplateLength} characters", nameof(template));
        }

        if (template.Contains('\0') || template.StartsWith("/", StringComparison.Ordinal) ||
            template.StartsWith("\\", StringComparison.Ordinal) ||
            (template.Length >= 2 && char.IsAsciiLetter(template[0]) && template[1] == ':'))
        {
            throw new ArgumentException("The template must be a relative path", nameof(template));
        }

        var literalPath = TokenPattern.Replace(template, "token");
        if (literalPath.Contains("${", StringComparison.Ordinal))
        {
            throw new ArgumentException("Tokens must use the form ${TOKEN_NAME}", nameof(template));
        }

        if (PathGuard.ContainsTraversal(literalPath))
        {
            throw new ArgumentException("The template cannot contain a raw or encoded traversal component", nameof(template));
        }

        foreach (Match match in TokenPattern.Matches(template))
        {
            if (!IsSupportedToken(match.Groups["name"].Value))
            {
                throw new ArgumentException($"Unsupported token '{match.Value}'", nameof(template));
            }
        }
    }

    /// <summary>
    ///     Renders a validated template using metadata retained with a download request.
    /// </summary>
    /// <param name="template">The relative template to render.</param>
    /// <param name="transfer">The completed transfer.</param>
    /// <param name="request">The owning download request, if present.</param>
    /// <returns>A relative path, or an empty string for the download root.</returns>
    public static string Render(string template, Transfer transfer, DownloadRequest? request)
    {
        ArgumentNullException.ThrowIfNull(transfer);
        Validate(template);

        if (string.IsNullOrWhiteSpace(template))
        {
            return string.Empty;
        }

        var sourcePath = GetSourcePath(transfer.Filename);
        var sourceDirectory = sourcePath.Split('/', StringSplitOptions.RemoveEmptyEntries).LastOrDefault() ?? "_singles";
        var batchId = transfer.BatchId ?? request?.BatchId;
        var tokens = new System.Collections.Generic.Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["SOURCE_USERNAME"] = transfer.Username,
            ["SOURCE_PATH"] = sourcePath,
            ["SOURCE_DIRECTORY"] = sourceDirectory,
            ["BATCH_ID"] = batchId?.ToString("D") ?? "unknown_batch_id",
            ["BATCH_EXTERNAL_ID"] = NonEmpty(request?.BatchExternalId, "unknown_batch_external_id"),
            ["SEARCH_ID"] = request?.SearchId?.ToString("D") ?? "unknown_search_id",
            ["SEARCH_TEXT"] = NonEmpty(request?.SearchText, "unknown_search_text"),
        };

        var expanded = TokenPattern.Replace(template, match =>
        {
            var name = match.Groups["name"].Value;
            if (!tokens.TryGetValue(name, out var value))
            {
                throw new ArgumentException($"Unsupported token '{match.Value}'", nameof(template));
            }

            return name.Equals("SOURCE_PATH", StringComparison.OrdinalIgnoreCase)
                ? value
                : SanitizeSegment(value);
        });

        if (expanded.Contains("${", StringComparison.Ordinal))
        {
            throw new ArgumentException("Tokens must use the form ${TOKEN_NAME}", nameof(template));
        }

        var segments = expanded
            .Split(Separators, StringSplitOptions.RemoveEmptyEntries)
            .Where(segment => segment != ".")
            .Select(segment =>
            {
                if (segment == "..")
                {
                    throw new ArgumentException("The rendered path cannot contain a '..' component", nameof(template));
                }

                return SanitizeSegment(segment);
            });

        var pathSegments = segments.ToArray();
        return pathSegments.Length == 0 ? string.Empty : System.IO.Path.Combine(pathSegments);
    }

    private static string GetSourcePath(string remoteFilename)
    {
        var normalized = Regex.Replace(remoteFilename.Trim(), @"^[a-zA-Z]:[\\/]*", string.Empty)
            .TrimStart('\\', '/')
            .TrimEnd('\\', '/');
        var sourceParts = normalized.Split(Separators, StringSplitOptions.RemoveEmptyEntries);
        if (sourceParts.Length == 0 || sourceParts.Any(part => part is "." or ".."))
        {
            throw new ArgumentException("Remote filename contains an unsafe path component", nameof(remoteFilename));
        }

        return string.Join('/', sourceParts
            .SkipLast(1)
            .Select(part => part.ToLocalRelativeFilename())
            .Select(SanitizeSegment));
    }

    private static string SanitizeSegment(string value)
    {
        var sanitized = new string(value
            .Select(character => char.IsControl(character) || character is '/' or '\\' or ':' or '*' or '?' or '"' or '<' or '>' or '|' or '%'
                ? '_'
                : character)
            .ToArray())
            .Trim()
            .TrimEnd('.', ' ');

        if (sanitized.Length == 0 || sanitized is "." or "..")
        {
            return "_";
        }

        if (IsWindowsReservedName(sanitized))
        {
            sanitized = $"_{sanitized}";
        }

        if (Encoding.UTF8.GetByteCount(sanitized) <= MaximumSegmentUtf8Bytes)
        {
            return sanitized;
        }

        var prefix = new StringBuilder();
        var prefixBytes = 0;
        foreach (var rune in sanitized.EnumerateRunes())
        {
            var text = rune.ToString();
            var textBytes = Encoding.UTF8.GetByteCount(text);
            if (prefixBytes + textBytes > MaximumSegmentUtf8Bytes - 13)
            {
                break;
            }

            prefix.Append(text);
            prefixBytes += textBytes;
        }

        var digest = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(sanitized)))[..12].ToLowerInvariant();
        return $"{prefix}~{digest}";
    }

    private static bool IsWindowsReservedName(string value)
    {
        var stem = value.Split('.', 2)[0];
        return stem.Equals("CON", StringComparison.OrdinalIgnoreCase) ||
            stem.Equals("PRN", StringComparison.OrdinalIgnoreCase) ||
            stem.Equals("AUX", StringComparison.OrdinalIgnoreCase) ||
            stem.Equals("NUL", StringComparison.OrdinalIgnoreCase) ||
            (stem.Length == 4 && (stem.StartsWith("COM", StringComparison.OrdinalIgnoreCase) || stem.StartsWith("LPT", StringComparison.OrdinalIgnoreCase)) &&
                stem[3] is >= '1' and <= '9');
    }

    private static bool IsSupportedToken(string token)
    {
        return token.Equals("SOURCE_USERNAME", StringComparison.OrdinalIgnoreCase) ||
            token.Equals("SOURCE_PATH", StringComparison.OrdinalIgnoreCase) ||
            token.Equals("SOURCE_DIRECTORY", StringComparison.OrdinalIgnoreCase) ||
            token.Equals("BATCH_ID", StringComparison.OrdinalIgnoreCase) ||
            token.Equals("BATCH_EXTERNAL_ID", StringComparison.OrdinalIgnoreCase) ||
            token.Equals("SEARCH_ID", StringComparison.OrdinalIgnoreCase) ||
            token.Equals("SEARCH_TEXT", StringComparison.OrdinalIgnoreCase);
    }

    private static string NonEmpty(string? value, string fallback)
        => string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
}
