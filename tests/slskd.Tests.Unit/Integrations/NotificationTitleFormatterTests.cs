namespace slskd.Tests.Unit.Integrations
{
    using System;
    using System.Collections.Generic;
    using System.Text;
    using slskd.Integrations.Notifications;
    using Xunit;

    public class NotificationTitleFormatterTests
    {
        [Fact]
        public void TitleFallbackPreservesOpaqueTokensInsideUserData()
        {
            Assert.Equal("Private Message from \u2068peer{room}\u2069",
                NotificationTitleFormatter.PrivateMessage("en", "peer{room}"));
            Assert.Equal("Room Mention by \u2068peer{room}\u2069 in \u2068Music/{username}\u2069",
                NotificationTitleFormatter.RoomMention("unsupported", "peer{room}", "Music/{username}"));
        }

        [Fact]
        public void EmbeddedUiCatalogIsSelectedWithoutDuplicatingTranslations()
        {
            Assert.Equal("Descripción general", NotificationTitleFormatter.TranslateSource("es", "Overview"));
            Assert.Equal("not present", NotificationTitleFormatter.TranslateSource("es", "not present"));
            Assert.Equal("Overview", NotificationTitleFormatter.TranslateSource("unsupported", "Overview"));
        }

        [Fact]
        public void PresentationIsolatesValuesInEveryLocaleWithoutReprocessingTheirBraces()
        {
            var result = NotificationTitleFormatter.Interpolate("Title {username} in {room}",
                new Dictionary<string, string> { ["username"] = "peer{room}", ["room"] = "room/{username}" });
            Assert.Equal("Title \u2068peer{room}\u2069 in \u2068room/{username}\u2069", result);
        }

        [Fact]
        public void LeftToRightTitlesIsolateRightToLeftValues()
        {
            Assert.Equal("Private Message from \u2068שלום 2025\u2069",
                NotificationTitleFormatter.PrivateMessage("en", "שלום 2025"));
            Assert.Equal("Room Mention by \u2068غرفة 42\u2069 in \u2068Music\u2069",
                NotificationTitleFormatter.RoomMention("en", "غرفة 42", "Music"));
        }

        [Fact]
        public void TitleStripsInjectedBidiControlsBeforeIsolatingValues()
        {
            Assert.Equal("Room Mention by \u2068peername\u2069 in \u2068Musicroom\u2069",
                NotificationTitleFormatter.RoomMention(
                    "en",
                    "peer\u061C\u200E\u200F\u202A\u202B\u202C\u202D\u202E\u2066\u2067\u2068\u2069\u206A\u206B\u206C\u206D\u206E\u206Fname",
                    "Music\u2068room\u202C"));
        }

        [Fact]
        public void NtfyHeaderEncodingPreservesNonAsciiTitleContent()
        {
            const string title = "prefix: peer / العربية / {room}";
            var encoded = NotificationTitleFormatter.EncodeNtfyTitle(title);
            Assert.StartsWith("=?UTF-8?B?", encoded);
            Assert.Equal(title, Encoding.UTF8.GetString(Convert.FromBase64String(encoded[10..^2])));
            Assert.Equal("plain title", NotificationTitleFormatter.EncodeNtfyTitle("plain title"));
        }
    }
}
