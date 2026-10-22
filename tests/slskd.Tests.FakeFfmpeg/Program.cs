// <copyright file="Program.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
if (args.Contains("f32le", StringComparer.OrdinalIgnoreCase))
{
    const int sampleRate = 44100;
    const int windowSize = 8192;
    const int frameCount = 8;
    var tones = Enumerable.Range(1, 166).Select(index => index * 100).ToArray();
    var frame = new byte[windowSize * sizeof(float)];
    for (var sampleIndex = 0; sampleIndex < windowSize; sampleIndex++)
    {
        var sample = 0.0;
        foreach (var frequency in tones)
        {
            sample += Math.Sin(2 * Math.PI * frequency * sampleIndex / sampleRate);
        }

        var value = (float)(sample * (0.8 / tones.Length));
        BitConverter.TryWriteBytes(frame.AsSpan(sampleIndex * sizeof(float), sizeof(float)), value);
    }

    var standardOutput = Console.OpenStandardOutput();
    for (var index = 0; index < frameCount; index++)
    {
        standardOutput.Write(frame);
    }

    return 0;
}

Console.Error.WriteLine(new string('x', 65_536));
return 1;
