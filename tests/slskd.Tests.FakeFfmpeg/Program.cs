// <copyright file="Program.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

// A test-owned stand-in for ffmpeg.
//
// By default it floods stderr and exits 1, which exercises callers' stream draining and failure handling.
//
// If the "-i" input file starts with SynthHeader, it instead writes synthetic mono 32-bit float PCM to stdout, as
// "ffmpeg ... -f f32le pipe:1" would. The rest of the header line is space-separated key=value settings:
//   sample_rate=44100   samples per second
//   seconds=5           length of the audio
//   top_hz=16600        highest component frequency (a lossy-style shelf); omit for content up to 97% of Nyquist
//   rolloff=true        components fade gradually toward the top, like genuine CD audio
//   silent_seconds=0    leading digital silence
const string SynthHeader = "SLSKDN-FAKE-FFMPEG-SYNTH";

var inputIndex = Array.IndexOf(args, "-i");
var inputPath = inputIndex >= 0 && inputIndex + 1 < args.Length ? args[inputIndex + 1] : null;
var firstLine = inputPath is not null && File.Exists(inputPath) ? File.ReadLines(inputPath).FirstOrDefault() : null;

if (firstLine is null || !firstLine.StartsWith(SynthHeader, StringComparison.Ordinal))
{
    Console.Error.WriteLine(new string('x', 65_536));
    return 1;
}

var settings = firstLine[SynthHeader.Length..]
    .Split(' ', StringSplitOptions.RemoveEmptyEntries)
    .Select(pair => pair.Split('=', 2))
    .Where(parts => parts.Length == 2)
    .ToDictionary(parts => parts[0], parts => parts[1]);

double Setting(string key, double fallback) =>
    settings.TryGetValue(key, out var value) ? double.Parse(value, System.Globalization.CultureInfo.InvariantCulture) : fallback;

var sampleRate = (int)Setting("sample_rate", 44100);
var seconds = Setting("seconds", 5);
var topHz = Setting("top_hz", sampleRate / 2.0 * 0.97);
var rolloff = settings.TryGetValue("rolloff", out var rolloffValue) && rolloffValue == "true";
var silentSamples = (int)(Setting("silent_seconds", 0) * sampleRate);

// A sum of sine components every 100 Hz with fixed pseudo-random phases. Each component advances by rotating a
// unit phasor, which is fast and exact enough for a few seconds of audio.
var random = new Random(1234);
var frequencies = new List<double>();
for (var f = 100.0; f <= topHz; f += 100)
{
    frequencies.Add(f);
}

var count = frequencies.Count;
var amplitude = new double[count];
var re = new double[count];
var im = new double[count];
var stepRe = new double[count];
var stepIm = new double[count];
for (var i = 0; i < count; i++)
{
    var f = frequencies[i];
    amplitude[i] = (rolloff ? Math.Pow(10, -(f / topHz) * 30 / 20) : 1.0) * 0.5 / Math.Sqrt(count);
    var phase = random.NextDouble() * 2 * Math.PI;
    re[i] = Math.Cos(phase);
    im[i] = Math.Sin(phase);
    stepRe[i] = Math.Cos(2 * Math.PI * f / sampleRate);
    stepIm[i] = Math.Sin(2 * Math.PI * f / sampleRate);
}

var totalSamples = silentSamples + (int)(seconds * sampleRate);
var buffer = new byte[4096 * sizeof(float)];
using var stdout = Console.OpenStandardOutput();
try
{
    for (var start = 0; start < totalSamples; start += 4096)
    {
        var n = Math.Min(4096, totalSamples - start);
        for (var s = 0; s < n; s++)
        {
            double sample = 0;
            if (start + s >= silentSamples)
            {
                for (var i = 0; i < count; i++)
                {
                    sample += amplitude[i] * im[i];
                    var nextRe = (re[i] * stepRe[i]) - (im[i] * stepIm[i]);
                    im[i] = (re[i] * stepIm[i]) + (im[i] * stepRe[i]);
                    re[i] = nextRe;
                }
            }

            BitConverter.TryWriteBytes(buffer.AsSpan(s * sizeof(float)), (float)sample);
        }

        stdout.Write(buffer, 0, n * sizeof(float));
    }
}
catch (IOException)
{
    // The reader stopped early (for example, its frame budget was spent) and closed the pipe.
}

return 0;
