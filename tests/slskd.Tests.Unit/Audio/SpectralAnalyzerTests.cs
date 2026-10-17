// <copyright file="SpectralAnalyzerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Audio
{
    using System;
    using System.ComponentModel.DataAnnotations;
    using System.IO;
    using System.Linq;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.Extensions.Logging.Abstractions;
    using slskd.Audio;
    using slskd.Tests.Unit;
    using Xunit;
    using SpectralAnalysisOptions = slskd.Options.AudioOptions.SpectralAnalysisOptions;

    // Uses tests/slskd.Tests.FakeFfmpeg, which synthesizes PCM when its input file starts with its synth header,
    // so the decode pipeline runs the same way on every platform without a real ffmpeg.
    public class SpectralAnalyzerTests : IDisposable
    {
        private const string SynthHeader = "SLSKDN-FAKE-FFMPEG-SYNTH";
        private readonly string directory = Path.Combine(Path.GetTempPath(), $"spectral-{Guid.NewGuid():N}");

        public SpectralAnalyzerTests()
        {
            Directory.CreateDirectory(directory);
        }

        public void Dispose()
        {
            Directory.Delete(directory, recursive: true);
        }

        [Fact]
        public async Task AnalyzeAsync_FindsTheShelfOfALossySource()
        {
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true, MaxFrames = 30 });
            var input = WriteSynthInput("sample_rate=44100 seconds=6 top_hz=16600");

            var result = await analyzer.AnalyzeAsync(input, 44100, durationSeconds: 6);

            Assert.NotNull(result);
            Assert.Equal(SpectralVerdict.Lossy, result!.Verdict);
            Assert.InRange(result.CutoffHz!.Value, 16300, 17000);
            Assert.Equal("MP3 128 kbps", result.EstimatedSource);
            Assert.Equal(30, result.FramesAnalyzed);
        }

        [Fact]
        public async Task AnalyzeAsync_NaturalRolloffIsGenuine()
        {
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true, MaxFrames = 30 });
            var input = WriteSynthInput("sample_rate=44100 seconds=6 rolloff=true");

            var result = await analyzer.AnalyzeAsync(input, 44100, durationSeconds: 6);

            Assert.Equal(SpectralVerdict.Genuine, result!.Verdict);
        }

        [Fact]
        public async Task AnalyzeAsync_StopsDecodingOnceTheFrameBudgetIsSpent()
        {
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true, MaxFrames = 25 });
            var input = WriteSynthInput("sample_rate=44100 seconds=600 top_hz=16600");   // ~3,200 frames available

            var result = await analyzer.AnalyzeAsync(input, 44100, durationSeconds: 60).WaitAsync(TimeSpan.FromSeconds(30));

            Assert.Equal(25, result!.FramesAnalyzed);
            Assert.Equal(SpectralVerdict.Lossy, result.Verdict);
        }

        [Fact]
        public async Task AnalyzeAsync_SilenceIsInconclusive()
        {
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true, MaxFrames = 30 });
            var input = WriteSynthInput("sample_rate=44100 seconds=0 silent_seconds=4");

            var result = await analyzer.AnalyzeAsync(input, 44100, durationSeconds: 4);

            Assert.Equal(SpectralVerdict.Inconclusive, result!.Verdict);
            Assert.Equal(0, result.FramesAnalyzed);
        }

        [Fact]
        public async Task AnalyzeAsync_DecodeFailureIsInconclusive()
        {
            // Without the synth header the fake floods stderr and exits 1.
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true });
            var input = Path.Combine(directory, "not-audio.flac");
            await File.WriteAllTextAsync(input, "not audio");

            var result = await analyzer.AnalyzeAsync(input, 44100, durationSeconds: 200).WaitAsync(TimeSpan.FromSeconds(30));

            Assert.Equal(SpectralVerdict.Inconclusive, result!.Verdict);
            Assert.Equal("ffmpeg could not decode the file", result.Detail);
        }

        [Fact]
        public async Task AnalyzeAsync_CancellationStopsTheDecode()
        {
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true, MaxFrames = 10000 });
            var input = WriteSynthInput("sample_rate=44100 seconds=3600 top_hz=16600");
            using var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(300));

            await Assert.ThrowsAnyAsync<OperationCanceledException>(
                () => analyzer.AnalyzeAsync(input, 44100, durationSeconds: 60, cancellation.Token).WaitAsync(TimeSpan.FromSeconds(30)));
        }

        [Fact]
        public async Task AnalyzeAsync_WhenDisabled_ReturnsNullWithoutDecoding()
        {
            using var analyzer = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = false });

            var result = await analyzer.AnalyzeAsync(Path.Combine(directory, "missing.flac"), 44100, durationSeconds: 60);

            Assert.Null(result);
            Assert.False(analyzer.IsEnabled);
            Assert.False(analyzer.AnalyzeCompletedDownloads);
        }

        [Fact]
        public async Task AnalyzeAsync_WhenFfmpegIsMissing_ReturnsNull()
        {
            using var analyzer = CreateAnalyzer(
                new SpectralAnalysisOptions { Enabled = true },
                ffmpegPath: Path.Combine(directory, "no-such-ffmpeg"));

            var result = await analyzer.AnalyzeAsync(WriteSynthInput("seconds=6"), 44100, durationSeconds: 6);

            Assert.Null(result);
        }

        [Fact]
        public void AnalyzeCompletedDownloads_RequiresTheMasterSwitch()
        {
            using var off = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = false, AnalyzeCompletedDownloads = true });
            using var on = CreateAnalyzer(new SpectralAnalysisOptions { Enabled = true, AnalyzeCompletedDownloads = true });

            Assert.False(off.AnalyzeCompletedDownloads);
            Assert.True(on.AnalyzeCompletedDownloads);
        }

        [Fact]
        public void CreateProcessStartInfo_SkipsTheIntroOnlyWhenAsked()
        {
            var withSkip = SpectralAnalyzer.CreateProcessStartInfo("ffmpeg", "a.flac", startSeconds: 30).ArgumentList.ToList();
            var withoutSkip = SpectralAnalyzer.CreateProcessStartInfo("ffmpeg", "a.flac", startSeconds: 0).ArgumentList.ToList();

            Assert.Equal("30", withSkip[withSkip.IndexOf("-ss") + 1]);
            Assert.True(withSkip.IndexOf("-ss") < withSkip.IndexOf("-i"));
            Assert.DoesNotContain("-ss", withoutSkip);
            Assert.Equal(new[] { "-f", "f32le", "pipe:1" }, withoutSkip.TakeLast(3));
        }

        [Fact]
        public async Task AccumulatePowerAsync_SkipsSilentFramesAndReportsTheEnd()
        {
            var frameBytes = SpectralClassifier.FftSize * sizeof(float);
            var pcm = new byte[frameBytes * 3];
            for (var i = 0; i < SpectralClassifier.FftSize; i++)
            {
                // Frame 2 is a full-scale tone; frames 1 and 3 are silent.
                BitConverter.TryWriteBytes(pcm.AsSpan(frameBytes + (i * sizeof(float))), (float)Math.Sin(i * 0.3));
            }

            var power = new double[(SpectralClassifier.FftSize / 2) + 1];
            var (frames, reachedEnd) = await SpectralAnalyzer.AccumulatePowerAsync(new MemoryStream(pcm), power, maxFrames: 10, CancellationToken.None);

            Assert.Equal(1, frames);
            Assert.True(reachedEnd);
            Assert.True(power.Max() > 0);
        }

        [Fact]
        public async Task AccumulatePowerAsync_StopsAtTheBudgetBeforeTheEnd()
        {
            var frameBytes = SpectralClassifier.FftSize * sizeof(float);
            var pcm = new byte[frameBytes * 5];
            for (var i = 0; i < pcm.Length / sizeof(float); i++)
            {
                BitConverter.TryWriteBytes(pcm.AsSpan(i * sizeof(float)), (float)Math.Sin(i * 0.3));
            }

            var power = new double[(SpectralClassifier.FftSize / 2) + 1];
            var (frames, reachedEnd) = await SpectralAnalyzer.AccumulatePowerAsync(new MemoryStream(pcm), power, maxFrames: 2, CancellationToken.None);

            Assert.Equal(2, frames);
            Assert.False(reachedEnd);
        }

        [Theory]
        [InlineData(10, 1, false)]
        [InlineData(600, 0, false)]
        [InlineData(600, 9, false)]
        [InlineData(600, 1, true)]
        public void Options_ValidateFrameBudgetAndConcurrency(int maxFrames, int maxConcurrent, bool valid)
        {
            var options = new SpectralAnalysisOptions { MaxFrames = maxFrames, MaxConcurrentAnalyses = maxConcurrent };

            var errors = options.Validate(new ValidationContext(options)).ToList();

            Assert.Equal(valid, errors.Count == 0);
        }

        private static string FakeFfmpegPath()
        {
            var executableName = OperatingSystem.IsWindows() ? "slskd.Tests.FakeFfmpeg.exe" : "slskd.Tests.FakeFfmpeg";
            return Path.Combine(AppContext.BaseDirectory, "fake-ffmpeg", executableName);
        }

        private static SpectralAnalyzer CreateAnalyzer(SpectralAnalysisOptions spectral, string? ffmpegPath = null)
        {
            var options = new slskd.Options
            {
                Audio = new slskd.Options.AudioOptions { SpectralAnalysis = spectral },
                Integration = new slskd.Options.IntegrationOptions
                {
                    Chromaprint = new slskd.Options.IntegrationOptions.ChromaprintOptions
                    {
                        FfmpegPath = ffmpegPath ?? FakeFfmpegPath(),
                    },
                },
            };
            return new SpectralAnalyzer(new TestOptionsMonitor<slskd.Options>(options), NullLogger<SpectralAnalyzer>.Instance);
        }

        private string WriteSynthInput(string settings)
        {
            var path = Path.Combine(directory, $"{Guid.NewGuid():N}.flac");
            File.WriteAllText(path, $"{SynthHeader} {settings}\n");
            return path;
        }
    }
}
