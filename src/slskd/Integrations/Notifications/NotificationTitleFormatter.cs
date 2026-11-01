namespace slskd.Integrations.Notifications
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Text;
    using System.Text.Json;
    using System.Text.RegularExpressions;

    /// <summary>
    /// Formats only app-authored titles, using the same catalogs as the Web UI.
    /// User-provided message bodies and notification prefixes are not translated.
    /// </summary>
    internal static class NotificationTitleFormatter
    {
        internal const string PrivateMessageSource = "Private Message from {username}";
        internal const string RoomMentionSource = "Room Mention by {username} in {room}";

        private static readonly HashSet<string> SupportedLanguages = new(StringComparer.Ordinal)
        {
            "es", "zh-Hans", "hi", "de", "ja", "fr", "pt-BR", "ar", "ko", "zh-Hant", "vi", "id",
        };

        private static readonly ConcurrentDictionary<string, Dictionary<string, string>> Catalogs = new();

        internal static string PrivateMessage(string language, string username) => Format(
            language,
            PrivateMessageSource,
            new Dictionary<string, string> { ["username"] = username });

        internal static string RoomMention(string language, string username, string room) => Format(
            language,
            RoomMentionSource,
            new Dictionary<string, string> { ["username"] = username, ["room"] = room });

        internal static string TranslateSource(string language, string source)
        {
            if (!SupportedLanguages.Contains(language ?? string.Empty))
            {
                return source;
            }

            var catalog = Catalogs.GetOrAdd(language, locale =>
            {
                using var stream = typeof(NotificationTitleFormatter).Assembly.GetManifestResourceStream(
                    $"slskd.NotificationLocales.{locale}.json");
                return stream is null
                    ? new Dictionary<string, string>()
                    : JsonSerializer.Deserialize<Dictionary<string, string>>(stream) ?? new Dictionary<string, string>();
            });

            return catalog.TryGetValue(source, out var translation) && !string.IsNullOrWhiteSpace(translation)
                ? translation
                : source;
        }

        internal static string Format(string language, string source, IReadOnlyDictionary<string, string> values) =>
            Interpolate(TranslateSource(language, source), values);

        // Replace placeholders in the original template only; never rescan inserted user data.
        internal static string Interpolate(string template, IReadOnlyDictionary<string, string> values) =>
            Regex.Replace(template, @"\{([a-zA-Z][a-zA-Z0-9_]*)\}", match =>
            {
                if (!values.TryGetValue(match.Groups[1].Value, out var value))
                {
                    return match.Value;
                }

                var safeValue = RemoveBidiFormattingControls(value);
                return safeValue.Length == 0 ? string.Empty : $"\u2068{safeValue}\u2069";
            });

        private static string RemoveBidiFormattingControls(string value)
        {
            var sanitized = new StringBuilder(value.Length);
            foreach (var character in value)
            {
                if (character == '\u061C' || character == '\u200E' || character == '\u200F' ||
                    character >= '\u202A' && character <= '\u202E' ||
                    character >= '\u2066' && character <= '\u206F')
                {
                    continue;
                }

                sanitized.Append(character);
            }

            return sanitized.ToString();
        }

        // ntfy accepts RFC 2047 UTF-8 headers; encode non-ASCII titles for .NET HTTP transport.
        internal static string EncodeNtfyTitle(string title)
        {
            foreach (var character in title)
            {
                if (character > 127)
                {
                    return $"=?UTF-8?B?{Convert.ToBase64String(Encoding.UTF8.GetBytes(title))}?=";
                }
            }

            return title;
        }
    }
}
