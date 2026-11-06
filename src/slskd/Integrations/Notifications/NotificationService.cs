// <copyright file="NotificationService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Integrations.Notifications
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Net.Http;
    using System.Net.Http.Headers;
    using System.Text;
    using System.Threading.Tasks;
    using Microsoft.Extensions.Logging;
    using Microsoft.Extensions.Options;
    using slskd.Common.Security;
    using slskd.Integrations.Pushbullet;

    public class NotificationService : INotificationService
    {
        private static readonly TimeSpan RateLimitWindow = TimeSpan.FromSeconds(30);
        private readonly ConcurrentDictionary<string, DateTime> lastNotificationTimes = new();
        private readonly object _rateLimitLock = new();

        public NotificationService(
            IHttpClientFactory httpClientFactory,
            IOptionsMonitor<slskd.Options> optionsMonitor,
            ILogger<NotificationService> log,
            IPushbulletService pushbullet)
        {
            HttpClientFactory = httpClientFactory;
            OptionsMonitor = optionsMonitor;
            Log = log;
            Pushbullet = pushbullet;
        }

        private IHttpClientFactory HttpClientFactory { get; }
        private ILogger<NotificationService> Log { get; }
        private IOptionsMonitor<slskd.Options> OptionsMonitor { get; }
        private IPushbulletService Pushbullet { get; }

        public async Task SendAsync(string title, string body, string? cacheKey = null)
        {
            var options = OptionsMonitor.CurrentValue.Integration;

            if (options.Pushbullet.Enabled)
            {
                await Pushbullet.PushAsync(title, cacheKey ?? Guid.NewGuid().ToString(), body);
            }

            if (options.Ntfy.Enabled)
            {
                await SendNtfyAsync(options.Ntfy, title, body);
            }

            if (options.Pushover.Enabled)
            {
                await SendPushoverAsync(options.Pushover, title, body);
            }
        }

        public async Task SendPrivateMessageAsync(string username, string message)
        {
            // Rate limit per username
            var cacheKey = $"pm:{username}";
            if (!ShouldSendNotification(cacheKey))
            {
                return;
            }

            var options = OptionsMonitor.CurrentValue.Integration;
            var title = NotificationTitleFormatter.PrivateMessage(options.NotificationLanguage, username);

            if (options.Pushbullet.Enabled && options.Pushbullet.NotifyOnPrivateMessage)
            {
                await Pushbullet.PushAsync(title, username, message);
            }

            if (options.Ntfy.Enabled && options.Ntfy.NotifyOnPrivateMessage)
            {
                await SendNtfyAsync(options.Ntfy, title, message);
            }

            if (options.Pushover.Enabled && options.Pushover.NotifyOnPrivateMessage)
            {
                await SendPushoverAsync(options.Pushover, title, message);
            }
        }

        public async Task SendRoomMentionAsync(string room, string username, string message)
        {
            // Rate limit per room+username combination
            var cacheKey = $"room:{room}:{username}";
            if (!ShouldSendNotification(cacheKey))
            {
                return;
            }

            var options = OptionsMonitor.CurrentValue.Integration;
            var title = NotificationTitleFormatter.RoomMention(options.NotificationLanguage, username, room);

            if (options.Pushbullet.Enabled && options.Pushbullet.NotifyOnRoomMention)
            {
                await Pushbullet.PushAsync(title, room, message);
            }

            if (options.Ntfy.Enabled && options.Ntfy.NotifyOnRoomMention)
            {
                await SendNtfyAsync(options.Ntfy, title, message);
            }

            if (options.Pushover.Enabled && options.Pushover.NotifyOnRoomMention)
            {
                await SendPushoverAsync(options.Pushover, title, message);
            }
        }

        private async Task SendNtfyAsync(slskd.Options.IntegrationOptions.NtfyOptions options, string title, string body)
        {
            try
            {
                using var client = HttpClientFactory.CreateClient(OutboundUriGuard.NoRedirectHttpClientName);
                using var request = new HttpRequestMessage(HttpMethod.Post, options.Url);

                if (!string.IsNullOrWhiteSpace(options.AccessToken))
                {
                    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", options.AccessToken);
                }

                request.Headers.Add("Title", NotificationTitleFormatter.EncodeNtfyTitle($"{options.NotificationPrefix}: {title}"));
                request.Content = new StringContent(body, Encoding.UTF8, "text/plain");

                using var response = await client.SendAsync(request);
                response.EnsureSuccessStatusCode();
            }
            catch (Exception ex)
            {
                Log.LogError(ex, "Failed to send Ntfy notification");
            }
        }

        private async Task SendPushoverAsync(slskd.Options.IntegrationOptions.PushoverOptions options, string title, string body)
        {
            try
            {
                using var client = HttpClientFactory.CreateClient(OutboundUriGuard.NoRedirectHttpClientName);
                using var content = new FormUrlEncodedContent(new[]
                {
                    new KeyValuePair<string, string>("token", options.Token),
                    new KeyValuePair<string, string>("user", options.UserKey),
                    new KeyValuePair<string, string>("title", $"{options.NotificationPrefix}: {title}"),
                    new KeyValuePair<string, string>("message", body),
                });

                using var response = await client.PostAsync("https://api.pushover.net/1/messages.json", content);
                response.EnsureSuccessStatusCode();
            }
            catch (Exception ex)
            {
                Log.LogError(ex, "Failed to send Pushover notification");
            }
        }

        /// <summary>
        /// Checks if a notification should be rate limited based on the cache key.
        /// Returns true if the notification should be sent, false if rate limited.
        /// </summary>
        private bool ShouldSendNotification(string cacheKey)
        {
            var now = DateTime.UtcNow;

            lock (_rateLimitLock)
            {
                if (lastNotificationTimes.TryGetValue(cacheKey, out var lastTime))
                {
                    if (now - lastTime < RateLimitWindow)
                    {
                        Log.LogDebug("Rate limiting notification for key {CacheKey}", cacheKey);
                        return false;
                    }
                }

                lastNotificationTimes[cacheKey] = now;

                // Clean up old entries periodically (keep dict from growing unbounded)
                if (lastNotificationTimes.Count > 1000)
                {
                    var cutoff = now - RateLimitWindow;
                    foreach (var kvp in lastNotificationTimes)
                    {
                        if (kvp.Value < cutoff)
                        {
                            lastNotificationTimes.TryRemove(kvp.Key, out _);
                        }
                    }
                }

                return true;
            }
        }
    }
}
