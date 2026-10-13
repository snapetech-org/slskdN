// <copyright file="PrometheusService.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="PrometheusService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Telemetry;

using System;
using System.Globalization;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

public class PrometheusService
{
    private static Regex PrometheusLineSplittingRegex { get; } = new Regex(@"([a-zA-Z_:][a-zA-Z0-9_:]*)(?:{(.*)})?\s+([^\s]+)", RegexOptions.Compiled);
    private static Regex PrometheusLabelSplittingRegex { get; } = new Regex("([a-zA-Z_][a-zA-Z0-9_]*)\\s*=\\s*\"([^\"]*)\"", RegexOptions.Compiled);

    /// <summary>
    ///     These metrics repeat many times with disambiguating labels, and this conflicts with the current approach
    ///     for building metrics in object format; dictionary entries (keyed by the names seen in this list) conflict,
    ///     and values are merged and potentially collide. This could be fixed by pulling disambiguating labels up into
    ///     the names, but these labels are things like HTTP route names, exception types, and server addresses. All of
    ///     which has very little value to an application that wants to display metrics to an end user (which is why this exists).
    ///
    ///     The easy solution is to just ignore these classes of metrics, and that's what I'm going to do.
    ///
    ///     This can be revisited if someone feels very strongly.
    /// </summary>
    private static Regex[] ExcludedMetrics { get; } = new[]
    {
        new Regex("^microsoft_aspnetcore_hosting_http_server_request_duration.*", RegexOptions.Compiled),
        new Regex("^system_net_http_http_client_request_time_in_queue.*", RegexOptions.Compiled),
        new Regex("^system_net_http_http_client_request_duration.*", RegexOptions.Compiled),
        new Regex("^microsoft_aspnetcore_server_kestrel_kestrel_connection_duration.*", RegexOptions.Compiled),
    };

    /// <summary>
    ///     Get the current list of Prometheus metrics in Prometheus exposition format (text based).
    /// </summary>
    /// <returns></returns>
    public virtual async Task<string> GetMetricsAsString()
    {
        using var stream = new MemoryStream();
        using var reader = new StreamReader(stream);

        await Prometheus.Metrics.DefaultRegistry.CollectAndExportAsTextAsync(stream);
        stream.Position = 0;

        return await reader.ReadToEndAsync();
    }

    /// <summary>
    ///     Gets Prometheus exposition text filtered by metric-family name.
    /// </summary>
    public virtual async Task<string> GetMetricsAsString(IEnumerable<Regex>? include, IEnumerable<Regex>? exclude)
    {
        var prometheusText = await GetMetricsAsString();
        if (include == null && exclude == null)
        {
            return prometheusText;
        }

        return PrometheusMetricFilter.FilterText(
            prometheusText,
            include?.ToArray(),
            exclude?.ToArray());
    }

    /// <summary>
    ///     Get the current list of Prometheus metrics in object format.
    /// </summary>
    /// <param name="include">An optional list of filters. If omitted, all metrics are included.</param>
    /// <returns></returns>
    public virtual async Task<Dictionary<string, PrometheusMetric>> GetMetricsAsObject(IEnumerable<Regex>? include = null)
    {
        return await GetMetricsAsObject(include, null);
    }

    /// <summary>
    ///     Gets the current Prometheus metrics in object format after applying metric-name filters.
    /// </summary>
    public virtual async Task<Dictionary<string, PrometheusMetric>> GetMetricsAsObject(
        IEnumerable<Regex>? include,
        IEnumerable<Regex>? exclude)
    {
        var includePatterns = include?.ToArray();
        var excludePatterns = exclude?.ToArray();
        var prometheusText = await GetMetricsAsString(includePatterns, excludePatterns);

        var metrics = new Dictionary<string, PrometheusMetric>();

        if (string.IsNullOrWhiteSpace(prometheusText))
        {
            return metrics;
        }

        var lines = prometheusText.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        var helpLineIndexes = lines
            .Select((line, index) => new { line, index })
            .Where(x => x.line.StartsWith("# HELP", StringComparison.OrdinalIgnoreCase))
            .Select(x => x.index).ToArray();

        var offsets = helpLineIndexes.Select((startIndex, i) =>
        {
            var endIndex = i < helpLineIndexes.Length - 1
                ? helpLineIndexes[i + 1] - 1
                : lines.Length - 1;
            return (startIndex, endIndex);
        });

        foreach (var (startIndex, endIndex) in offsets)
        {
            // "# HELP " is 7 characters; a malformed/short HELP line would otherwise
            // throw ArgumentOutOfRangeException and fail the whole metrics response.
            var helpLine = lines[startIndex];
            if (helpLine.Length <= 7)
            {
                continue;
            }

            var header = helpLine.Substring(7).Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
            if (header.Length < 2)
            {
                continue;
            }

            var name = header[0];
            var help = header[1];

            if (includePatterns is not null && !includePatterns.Any(regex => regex.IsMatch(name)))
            {
                continue;
            }

            if (excludePatterns is not null && excludePatterns.Any(regex => regex.IsMatch(name)))
            {
                continue;
            }

            // see the note above about excluded metrics and why this is necessary
            if (ExcludedMetrics.Any(regex => regex.IsMatch(name)))
            {
                continue;
            }

            if (startIndex + 1 >= lines.Length)
            {
                continue;
            }

            // The line after a HELP line is only a TYPE line in well-formed output. A
            // custom collector could emit a HELP without a following TYPE, leaving a short
            // sample line here; Substring(7) on it would throw and fail the response.
            var typeLine = lines[startIndex + 1];
            if (!typeLine.StartsWith("# TYPE ", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var typeParts = typeLine.Substring(7).Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
            if (typeParts.Length < 2)
            {
                continue;
            }

            var type = typeParts[1];
            var metric = new PrometheusMetric() { Name = name, Help = help, Type = type };

            for (int i = startIndex + 2; i <= endIndex; i++)
            {
                var match = PrometheusLineSplittingRegex.Match(lines[i]);

                if (match.Success)
                {
                    var groups = match.Groups;
                    var sampleName = groups[1].Value;
                    var sampleLabels = groups[2].Value;
                    if (!double.TryParse(groups[3].Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var sampleValue))
                    {
                        continue;
                    }

                    var labels = ParseLabels(sampleLabels);

                    if (type.Equals("counter") || type.Equals("gauge"))
                    {
                        metric.Samples ??= [];
                        metric.Samples.Add(new PrometheusMetricSample() { Labels = labels, Value = sampleValue });
                    }
                    else if (type.Equals("histogram"))
                    {
                        if (sampleName.EndsWith("sum"))
                        {
                            metric.Sum = sampleValue;
                        }
                        else if (sampleName.EndsWith("count"))
                        {
                            metric.Count = sampleValue;
                        }
                        else
                        {
                            var le = labels.FirstOrDefault(label => label.Key == "le");

                            metric.Buckets ??= [];
                            metric.Buckets.Add(le.Value ?? string.Empty, new PrometheusMetricSample() { Labels = labels, Value = sampleValue });
                        }
                    }
                    else if (type.Equals("summary"))
                    {
                        if (sampleName.EndsWith("sum"))
                        {
                            metric.Sum = sampleValue;
                        }
                        else if (sampleName.EndsWith("count"))
                        {
                            metric.Count = sampleValue;
                        }
                        else
                        {
                            var quantile = labels.FirstOrDefault(label => label.Key == "quantile");

                            metric.Quantiles ??= [];
                            metric.Quantiles.Add(quantile.Value ?? string.Empty, sampleValue);
                        }
                    }
                }
            }

            metrics[name] = metric;
        }

        return metrics;
    }

    private static Dictionary<string, string> ParseLabels(string labelString)
    {
        if (string.IsNullOrEmpty(labelString))
        {
            return [];
        }

        var matches = PrometheusLabelSplittingRegex.Matches(labelString);

        if (matches.Count == 0)
        {
            return [];
        }

        Dictionary<string, string> labels = [];

        foreach (Match match in matches)
        {
            var key = match.Groups[1].Value;
            var value = match.Groups[2].Value;
            labels[key] = value;
        }

        return labels;
    }
}
