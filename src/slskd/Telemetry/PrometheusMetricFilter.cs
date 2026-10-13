// <copyright file="PrometheusMetricFilter.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Telemetry;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

/// <summary>
///     Validates caller-supplied metric-name filters and applies them to exposition data.
/// </summary>
public static class PrometheusMetricFilter
{
    public const int MaximumPatternCount = 8;
    public const int MaximumPatternLength = 128;
    public static TimeSpan PatternTimeout { get; } = TimeSpan.FromMilliseconds(100);

    public static List<Regex>? Compile(string?[]? patterns, string parameterName)
    {
        if (patterns == null || patterns.Length == 0)
        {
            return null;
        }

        if (patterns.Length > MaximumPatternCount)
        {
            throw new MetricsFilterValidationException(
                $"The '{parameterName}' parameter accepts at most {MaximumPatternCount} patterns.");
        }

        var compiledPatterns = new List<Regex>(patterns.Length);
        for (var index = 0; index < patterns.Length; index++)
        {
            var pattern = patterns[index];
            if (string.IsNullOrWhiteSpace(pattern))
            {
                throw new MetricsFilterValidationException(
                    $"The '{parameterName}' parameter cannot contain an empty pattern.");
            }

            if (pattern.Length > MaximumPatternLength)
            {
                throw new MetricsFilterValidationException(
                    $"Each '{parameterName}' pattern must be {MaximumPatternLength} characters or fewer.");
            }

            try
            {
                compiledPatterns.Add(new Regex(
                    pattern,
                    RegexOptions.CultureInvariant,
                    PatternTimeout));
            }
            catch (ArgumentException)
            {
                throw new MetricsFilterValidationException(
                    $"The '{parameterName}' pattern at position {index + 1} is not a valid regular expression.");
            }
        }

        return compiledPatterns;
    }

    public static bool Matches(
        string metricName,
        IReadOnlyList<Regex>? include,
        IReadOnlyList<Regex>? exclude)
    {
        var included = include == null || include.Count == 0 || include.Any(regex => regex.IsMatch(metricName));
        return included && (exclude == null || !exclude.Any(regex => regex.IsMatch(metricName)));
    }

    public static string FilterText(
        string exposition,
        IReadOnlyList<Regex>? include,
        IReadOnlyList<Regex>? exclude)
    {
        if (include == null && exclude == null)
        {
            return exposition;
        }

        var output = new List<string>();
        var pendingComments = new List<string>();
        var familyLines = new List<string>();
        string? familyName = null;

        void FlushFamily()
        {
            if (familyName != null && Matches(familyName, include, exclude))
            {
                output.AddRange(pendingComments);
                output.AddRange(familyLines);
            }

            pendingComments.Clear();
            familyLines.Clear();
            familyName = null;
        }

        var lines = exposition.Split('\n');
        foreach (var line in lines)
        {
            if (TryGetFamilyHeader(line, out var headerName))
            {
                if (familyName != null && !string.Equals(familyName, headerName, StringComparison.Ordinal))
                {
                    FlushFamily();
                }

                if (familyName == null)
                {
                    familyName = headerName;
                    familyLines.AddRange(pendingComments);
                    pendingComments.Clear();
                }

                familyLines.Add(line);
                continue;
            }

            if (line == "# EOF")
            {
                FlushFamily();
                output.AddRange(pendingComments);
                pendingComments.Clear();
                output.Add(line);
                continue;
            }

            if (familyName != null)
            {
                familyLines.Add(line);
                continue;
            }

            if (TryGetSampleName(line, out var sampleName))
            {
                if (Matches(sampleName, include, exclude))
                {
                    output.AddRange(pendingComments);
                    output.Add(line);
                }

                pendingComments.Clear();
            }
            else
            {
                pendingComments.Add(line);
            }
        }

        FlushFamily();
        output.AddRange(pendingComments);
        return string.Join("\n", output);
    }

    private static bool TryGetFamilyHeader(string line, out string familyName)
    {
        const string helpPrefix = "# HELP ";
        const string typePrefix = "# TYPE ";
        var prefixLength = line.StartsWith(helpPrefix, StringComparison.Ordinal)
            ? helpPrefix.Length
            : line.StartsWith(typePrefix, StringComparison.Ordinal)
                ? typePrefix.Length
                : 0;

        if (prefixLength == 0)
        {
            familyName = string.Empty;
            return false;
        }

        var headerEnd = line.IndexOf(' ', prefixLength);
        if (headerEnd <= prefixLength)
        {
            familyName = string.Empty;
            return false;
        }

        familyName = line[prefixLength..headerEnd];
        return true;
    }

    private static bool TryGetSampleName(string line, out string sampleName)
    {
        var nameEnd = line.IndexOfAny([' ', '\t']);
        if (nameEnd <= 0)
        {
            sampleName = string.Empty;
            return false;
        }

        var labelStart = line.IndexOf('{');
        sampleName = labelStart > 0 && labelStart < nameEnd
            ? line[..labelStart]
            : line[..nameEnd];
        return true;
    }
}

public sealed class MetricsFilterValidationException : Exception
{
    public MetricsFilterValidationException(string message)
        : base(message)
    {
    }
}
