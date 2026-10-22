// <copyright file="CallbackInfrastructureTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Core;

using System;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Serilog.Events;
using Xunit;

public class CallbackInfrastructureTests
{
    [Fact]
    public void TimedCounter_WhenElapsedInterleavesWithCountUp_PreservesTotalCount()
    {
        long captured = -1;
        using var counter = new TimedCounter(TimeSpan.FromMinutes(1), value => captured = value);

        counter.CountUp(2);
        counter.CountUp(3);

        var elapsedMethod = typeof(TimedCounter).GetMethod(
            "Elapsed",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("TimedCounter.Elapsed method was not found.");

        elapsedMethod.Invoke(counter, [null, null!]);

        Assert.Equal(5, captured);
        Assert.Equal(0, counter.Count);
    }

    [Fact]
    public void RateLimiter_WhenStagedActionThrows_IsolatesFailureAndAllowsLaterTicks()
    {
        using var rateLimiter = new RateLimiter(interval: 1000);
        var attempts = 0;
        var successfulTicks = 0;

        rateLimiter.Invoke(() => { });
        rateLimiter.Invoke(() =>
        {
            attempts++;
            throw new InvalidOperationException("boom");
        });

        var elapsedMethod = typeof(RateLimiter).GetMethod(
            "Timer_Elapsed",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("RateLimiter.Timer_Elapsed method was not found.");

        elapsedMethod.Invoke(rateLimiter, [null, EventArgs.Empty]);

        rateLimiter.Invoke(() => successfulTicks++);
        elapsedMethod.Invoke(rateLimiter, [null, EventArgs.Empty]);

        Assert.Equal(1, attempts);
        Assert.Equal(1, successfulTicks);
    }

    [Fact]
    public void RateLimiter_ConcurrencyLimit_IncludesImmediateAndStagedCallbacks()
    {
        using var rateLimiter = new RateLimiter(interval: 60_000, concurrencyLimit: 1);
        using var firstStarted = new ManualResetEventSlim();
        using var releaseFirst = new ManualResetEventSlim();
        using var secondStarted = new ManualResetEventSlim();
        var activeCallbacks = 0;
        var maximumConcurrentCallbacks = 0;

        void EnterCallback()
        {
            var active = Interlocked.Increment(ref activeCallbacks);
            int previousMaximum;
            while (active > (previousMaximum = Volatile.Read(ref maximumConcurrentCallbacks)) &&
                Interlocked.CompareExchange(ref maximumConcurrentCallbacks, active, previousMaximum) != previousMaximum)
            {
            }
        }

        var elapsedMethod = typeof(RateLimiter).GetMethod(
            "Timer_Elapsed",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("RateLimiter.Timer_Elapsed method was not found.");

        // The callback intentionally blocks. Use a dedicated thread so thread
        // pool starvation in the parallel test suite cannot make the gate
        // assertion time out before the callback starts.
        var firstTask = Task.Factory.StartNew(
            () => rateLimiter.Invoke(() =>
            {
                EnterCallback();
                firstStarted.Set();
                try
                {
                    releaseFirst.Wait();
                }
                finally
                {
                    Interlocked.Decrement(ref activeCallbacks);
                }
            }),
            CancellationToken.None,
            TaskCreationOptions.LongRunning,
            TaskScheduler.Default);

        try
        {
            Assert.True(firstStarted.Wait(TimeSpan.FromSeconds(10)));
            rateLimiter.Invoke(() =>
            {
                EnterCallback();
                try
                {
                    secondStarted.Set();
                }
                finally
                {
                    Interlocked.Decrement(ref activeCallbacks);
                }
            });

            elapsedMethod.Invoke(rateLimiter, [null, EventArgs.Empty]);

            Assert.False(secondStarted.IsSet);
        }
        finally
        {
            releaseFirst.Set();
        }

        Assert.True(firstTask.Wait(TimeSpan.FromSeconds(10)));
        elapsedMethod.Invoke(rateLimiter, [null, EventArgs.Empty]);

        Assert.True(secondStarted.Wait(TimeSpan.FromSeconds(5)));
        Assert.Equal(1, maximumConcurrentCallbacks);
    }

    [Fact]
    public void RateLimiter_Dispose_ReleasesConcurrencyState()
    {
        var rateLimiter = new RateLimiter(interval: 1000, concurrencyLimit: 1);

        var activeExecutionsField = typeof(RateLimiter).GetField(
            "_activeExecutions",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("RateLimiter active execution field was not found.");

        rateLimiter.Dispose();

        Assert.Equal(0, activeExecutionsField.GetValue(rateLimiter));
    }

    [Fact]
    public void RateLimiter_Dispose_WhenFlushActionThrows_StillDisposesOwnedResources()
    {
        var rateLimiter = new RateLimiter(interval: 1000, concurrencyLimit: 1, flushOnDispose: true);

        var activeExecutionsField = typeof(RateLimiter).GetField(
            "_activeExecutions",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("RateLimiter active execution field was not found.");

        rateLimiter.Invoke(() => { });
        rateLimiter.Invoke(() => throw new InvalidOperationException("boom"));

        var exception = Assert.Throws<InvalidOperationException>(() => rateLimiter.Dispose());

        Assert.Equal("boom", exception.Message);
        Assert.Equal(0, activeExecutionsField.GetValue(rateLimiter));
    }

    [Fact]
    public void TimedCounter_WhenElapsedCallbackThrows_StillResetsAndAllowsLaterTicks()
    {
        var attempts = 0;
        using var counter = new TimedCounter(TimeSpan.FromMinutes(1), _ =>
        {
            attempts++;
            if (attempts == 1)
            {
                throw new InvalidOperationException("boom");
            }
        });

        var elapsedMethod = typeof(TimedCounter).GetMethod(
            "Elapsed",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("TimedCounter.Elapsed method was not found.");

        counter.CountUp(2);
        elapsedMethod.Invoke(counter, [null, null!]);

        Assert.Equal(0, counter.Count);

        counter.CountUp(3);
        elapsedMethod.Invoke(counter, [null, null!]);

        Assert.Equal(2, attempts);
        Assert.Equal(0, counter.Count);
    }

    [Fact]
    public void ExponentialMovingAverage_WhenOnUpdateThrows_StillUpdatesValueAndAllowsLaterUpdates()
    {
        var attempts = 0;
        var average = new ExponentialMovingAverage(0.5, _ =>
        {
            attempts++;
            if (attempts == 1)
            {
                throw new InvalidOperationException("boom");
            }
        });

        average.Update(10);

        Assert.True(average.Initialized);
        Assert.Equal(10, average.Value);

        average.Update(20);

        Assert.Equal(2, attempts);
        Assert.Equal(15, average.Value);
    }

    [Fact]
    public void DelegatingSink_WhenObserverThrows_SwallowsFailureAndAllowsLaterEmit()
    {
        var attempts = 0;
        var sink = new DelegatingSink(_ =>
        {
            attempts++;
            if (attempts == 1)
            {
                throw new InvalidOperationException("boom");
            }
        });

        var logEvent = new LogEvent(
            DateTimeOffset.UtcNow,
            LogEventLevel.Information,
            exception: null,
            MessageTemplate.Empty,
            []);

        sink.Emit(logEvent);
        sink.Emit(logEvent);

        Assert.Equal(2, attempts);
    }
}
