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
            Assert.Equal("Private Message from peer{room}",
                NotificationTitleFormatter.PrivateMessage("en", "peer{room}"));
            Assert.Equal("Room Mention by peer{room} in Music/{username}",
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
        public void ArabicPresentationIsolatesValuesWithoutReprocessingTheirBraces()
        {
            var result = NotificationTitleFormatter.Interpolate("Title {username} in {room}",
                new Dictionary<string, string> { ["username"] = "peer{room}", ["room"] = "room/{username}" }, true);
            Assert.Equal("Title \u2068peer{room}\u2069 in \u2068room/{username}\u2069", result);
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
