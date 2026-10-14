// <copyright file="Program.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using BenchmarkDotNet.Running;
using slskd.Tests.Performance.HashDb;

BenchmarkSwitcher.FromAssembly(typeof(HashDbPerformanceBenchmarks).Assembly).Run(args);
