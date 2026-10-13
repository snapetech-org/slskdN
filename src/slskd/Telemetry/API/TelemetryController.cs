// <copyright file="TelemetryController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Telemetry;

using slskd.Core.Security;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

/// <summary>
///     Telemetry.
/// </summary>
[Route("api/v{version:apiVersion}/[controller]")]
[ApiVersion("0")]
[ApiController]
[Produces("application/json")]
[ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
public class TelemetryController : ControllerBase
{
    /// <summary>
    ///     Initializes a new instance of the <see cref="TelemetryController"/> class.
    /// </summary>
    /// <param name="telemetryService"></param>
    public TelemetryController(TelemetryService telemetryService)
    {
        Telemetry = telemetryService;
    }

    private TelemetryService Telemetry { get; }

    /// <summary>
    ///     KPIs for the app, based on the Prometheus dashboard
    ///     * process_Working_set_bytes = total memory used
    ///     * dotnet_total_memory_bytes = sum of all managed memory
    ///     * process_cpu_seconds_total = total cpu time spent (not a great measure)
    ///     * system_runtime_cpu_usage = % of cpu consumed
    ///     * system_net_sockets_* = TCP activity
    ///     KPIs for the _system_, not the app
    ///     * node_memory_* = info about _system_ memory
    ///     * node_filesystem_avail_bytes = how much space is left on the system
    ///     * node_network = info about network adapters on the system
    ///     Other
    ///     * process_start_time_seconds = unix timestamp of start time.
    /// </summary>
    private List<Regex> KpiRegexes { get; } = new List<Regex>
    {
        new Regex("slskd_.*", RegexOptions.Compiled),
        new Regex("node_(?!cpu)", RegexOptions.Compiled),
        new Regex("process_.*", RegexOptions.Compiled),
        new Regex("dotnet_total_memory_bytes", RegexOptions.Compiled),
        new Regex("system_runtime_[cpu_usage|working_set|alloc_total]", RegexOptions.Compiled),
        new Regex("system_net_sockets.*", RegexOptions.Compiled),
        new Regex("microsoft_aspnetcore_server_kestrel_[current|total]_connections", RegexOptions.Compiled),
    };

    /// <summary>
    ///     Gets application metrics.
    /// </summary>
    /// <returns></returns>
    [HttpGet("metrics")]
    [Authorize(Policy = AuthPolicy.Any)]
    [Produces("text/plain", "application/json")]
    [ProducesResponseType(typeof(string), 400)]
    public async Task<IActionResult> Get([FromQuery] string[]? include, [FromQuery] string[]? exclude)
    {
        List<Regex>? includeFilters;
        List<Regex>? excludeFilters;
        try
        {
            includeFilters = PrometheusMetricFilter.Compile(include, "include");
            excludeFilters = PrometheusMetricFilter.Compile(exclude, "exclude");
        }
        catch (MetricsFilterValidationException exception)
        {
            return BadRequest(exception.Message);
        }

        var acceptsJson = Request.GetTypedHeaders().Accept?.Any(header =>
            string.Equals(header.MediaType.Value, "application/json", StringComparison.OrdinalIgnoreCase)) == true;

        try
        {
            if (acceptsJson)
            {
                Dictionary<string, PrometheusMetric> dict = includeFilters == null && excludeFilters == null
                    ? await Telemetry.Prometheus.GetMetricsAsObject()
                    : await Telemetry.Prometheus.GetMetricsAsObject(includeFilters, excludeFilters);
                return Ok(dict);
            }

            var response = await Telemetry.Prometheus.GetMetricsAsString(includeFilters, excludeFilters);
            return Content(response, "text/plain");
        }
        catch (RegexMatchTimeoutException)
        {
            return BadRequest("A metrics filter exceeded its evaluation time limit. Simplify the pattern and try again.");
        }
    }

    /// <summary>
    ///     Gets gets key performance indicators for the application.
    /// </summary>
    /// <returns></returns>
    [HttpGet("metrics/kpi")]
    [Authorize(Policy = AuthPolicy.Any)]
    public async Task<IActionResult> GetKpis()
    {
        Dictionary<string, PrometheusMetric> dict = await Telemetry.Prometheus.GetMetricsAsObject(include: KpiRegexes);
        return Ok(dict);
    }
}
