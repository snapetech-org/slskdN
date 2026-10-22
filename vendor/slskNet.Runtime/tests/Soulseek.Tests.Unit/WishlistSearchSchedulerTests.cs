// <copyright file="WishlistSearchSchedulerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
// </copyright>

namespace Soulseek.Tests.Unit
{
    using System;
    using System.Collections.Generic;
    using System.Threading;
    using System.Threading.Tasks;
    using Moq;
    using Xunit;

    public class WishlistSearchSchedulerTests
    {
        [Fact(DisplayName = "Wishlist scheduler searches each configured term using wishlist scope")]
        public async Task Wishlist_Scheduler_Searches_Each_Configured_Term_Using_Wishlist_Scope()
        {
            var client = new Mock<ISoulseekClient>();
            var callCount = 0;
            client.SetupGet(m => m.ServerInfo).Returns(new ServerInfo(wishlistInterval: 1));
            client.Setup(m => m.SearchAsync(
                    It.IsAny<SearchQuery>(),
                    It.IsAny<SearchScope>(),
                    It.IsAny<int?>(),
                    It.IsAny<SearchOptions>(),
                    It.IsAny<CancellationToken>()))
                .Callback(() => callCount++)
                .Returns(Task.FromResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), (IReadOnlyCollection<SearchResponse>)new List<SearchResponse>())));

            var finished = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            using (var cts = new CancellationTokenSource())
            using (var scheduler = new WishlistSearchScheduler(
                client.Object,
                new[] { "alpha", "beta" },
                new WishlistSearchSchedulerOptions(System.TimeSpan.FromMilliseconds(250), System.TimeSpan.FromMilliseconds(1))))
            {
                scheduler.SearchCompleted += (_, __) =>
                {
                    if (callCount >= 2)
                    {
                        finished.TrySetResult(true);
                        cts.Cancel();
                    }
                };

                scheduler.Start(cts.Token);
                await finished.Task;
            }

            client.Verify(
                m => m.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.Is<SearchScope>(s => s.Type == SearchScopeType.Wishlist),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()),
                Times.Exactly(2));
        }

        [Fact(DisplayName = "Wishlist scheduler can stop and restart")]
        public async Task Wishlist_Scheduler_Can_Stop_And_Restart()
        {
            var client = new Mock<ISoulseekClient>();
            var callCount = 0;
            client.SetupGet(m => m.ServerInfo).Returns(new ServerInfo(wishlistInterval: 1));
            client.Setup(m => m.SearchAsync(
                    It.IsAny<SearchQuery>(),
                    It.IsAny<SearchScope>(),
                    It.IsAny<int?>(),
                    It.IsAny<SearchOptions>(),
                    It.IsAny<CancellationToken>()))
                .Callback(() => callCount++)
                .Returns(Task.FromResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), (IReadOnlyCollection<SearchResponse>)new List<SearchResponse>())));

            using (var scheduler = new WishlistSearchScheduler(
                client.Object,
                new[] { "alpha" },
                new WishlistSearchSchedulerOptions(System.TimeSpan.FromSeconds(30), System.TimeSpan.FromMilliseconds(1))))
            {
                scheduler.Start();
                await WaitForCallCountAsync(() => callCount, 1);
                scheduler.Stop();

                await WaitForStoppedAsync(scheduler);

                scheduler.Start();
                await WaitForCallCountAsync(() => callCount, 2);
                scheduler.Stop();
            }

            client.Verify(
                m => m.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.Is<SearchScope>(s => s.Type == SearchScopeType.Wishlist),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()),
                Times.Exactly(2));
        }

        [Fact(DisplayName = "Wishlist scheduler restarts after stop while previous loop is draining")]
        public async Task Wishlist_Scheduler_Restarts_After_Stop_While_Previous_Loop_Is_Draining()
        {
            var client = new Mock<ISoulseekClient>();
            var callCount = 0;
            var firstSearchStarted = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            var releaseFirstSearch = new TaskCompletionSource<(Search Search, IReadOnlyCollection<SearchResponse> Responses)>(TaskCreationOptions.RunContinuationsAsynchronously);
            var secondSearchStarted = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

            client.SetupGet(m => m.ServerInfo).Returns(new ServerInfo(wishlistInterval: 1));
            client.Setup(m => m.SearchAsync(
                    It.IsAny<SearchQuery>(),
                    It.IsAny<SearchScope>(),
                    It.IsAny<int?>(),
                    It.IsAny<SearchOptions>(),
                    It.IsAny<CancellationToken>()))
                .Returns(() =>
                {
                    var current = Interlocked.Increment(ref callCount);

                    if (current == 1)
                    {
                        firstSearchStarted.SetResult(true);
                        return releaseFirstSearch.Task;
                    }

                    secondSearchStarted.TrySetResult(true);
                    return Task.FromResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), (IReadOnlyCollection<SearchResponse>)new List<SearchResponse>()));
                });

            using (var scheduler = new WishlistSearchScheduler(
                client.Object,
                new[] { "alpha" },
                new WishlistSearchSchedulerOptions(System.TimeSpan.FromSeconds(30), System.TimeSpan.FromMilliseconds(1))))
            {
                scheduler.Start();
                await firstSearchStarted.Task;

                scheduler.Stop();
                scheduler.Start();

                releaseFirstSearch.SetResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), new List<SearchResponse>()));

                var completed = await Task.WhenAny(secondSearchStarted.Task, Task.Delay(System.TimeSpan.FromSeconds(3)));
                Assert.Equal(secondSearchStarted.Task, completed);

                scheduler.Stop();
            }

            Assert.True(callCount >= 2);
        }

        [Fact(DisplayName = "Wishlist scheduler can stop and dispose after canceled restart drains")]
        public async Task Wishlist_Scheduler_Can_Stop_And_Dispose_After_Canceled_Restart_Drains()
        {
            var client = new Mock<ISoulseekClient>();
            var firstSearchStarted = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            var releaseFirstSearch = new TaskCompletionSource<(Search Search, IReadOnlyCollection<SearchResponse> Responses)>(TaskCreationOptions.RunContinuationsAsynchronously);

            client.SetupGet(m => m.ServerInfo).Returns(new ServerInfo(wishlistInterval: 1));
            client.Setup(m => m.SearchAsync(
                    It.IsAny<SearchQuery>(),
                    It.IsAny<SearchScope>(),
                    It.IsAny<int?>(),
                    It.IsAny<SearchOptions>(),
                    It.IsAny<CancellationToken>()))
                .Returns(() =>
                {
                    firstSearchStarted.TrySetResult(true);
                    return releaseFirstSearch.Task;
                });

            var scheduler = new WishlistSearchScheduler(
                client.Object,
                new[] { "alpha" },
                new WishlistSearchSchedulerOptions(System.TimeSpan.FromSeconds(30), System.TimeSpan.FromMilliseconds(1)));

            scheduler.Start();
            await firstSearchStarted.Task;

            scheduler.Stop();
            scheduler.Start();
            scheduler.Stop();

            releaseFirstSearch.SetResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), new List<SearchResponse>()));
            await WaitForStoppedAsync(scheduler);

            var stopException = Record.Exception(() => scheduler.Stop());
            var disposeException = Record.Exception(() => scheduler.Dispose());

            Assert.Null(stopException);
            Assert.Null(disposeException);
        }

        [Fact(DisplayName = "Wishlist scheduler rejects start after dispose")]
        public void Wishlist_Scheduler_Rejects_Start_After_Dispose()
        {
            var client = new Mock<ISoulseekClient>();
            client.SetupGet(m => m.ServerInfo).Returns(new ServerInfo(wishlistInterval: 1));
            var scheduler = new WishlistSearchScheduler(client.Object, new[] { "alpha" });

            scheduler.Dispose();

            Assert.Throws<ObjectDisposedException>(() => scheduler.Start());
        }

        [Fact(DisplayName = "Wishlist scheduler does not report event handler failures as search failures")]
        public async Task Wishlist_Scheduler_Does_Not_Report_Event_Handler_Failures_As_Search_Failures()
        {
            var client = new Mock<ISoulseekClient>();
            var expectedException = new InvalidOperationException("handler failed");
            var eventCount = 0;

            client.Setup(m => m.SearchAsync(
                    It.IsAny<SearchQuery>(),
                    It.IsAny<SearchScope>(),
                    It.IsAny<int?>(),
                    It.IsAny<SearchOptions>(),
                    It.IsAny<CancellationToken>()))
                .Returns(Task.FromResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), (IReadOnlyCollection<SearchResponse>)new List<SearchResponse>())));

            using (var scheduler = new WishlistSearchScheduler(client.Object, new[] { "alpha" }))
            {
                scheduler.SearchCompleted += (_, args) =>
                {
                    Interlocked.Increment(ref eventCount);
                    Assert.Null(args.Exception);
                    throw expectedException;
                };

                var exception = await Assert.ThrowsAsync<InvalidOperationException>(() =>
                    scheduler.InvokeMethod<Task>("RunSearchAsync", "alpha", CancellationToken.None));

                Assert.Same(expectedException, exception);
                Assert.Equal(1, eventCount);
            }
        }

        [Fact(DisplayName = "Wishlist scheduler uses minimum interval when ServerInfo is null")]
        public async Task Wishlist_Scheduler_Uses_Minimum_Interval_When_ServerInfo_Is_Null()
        {
            var client = new Mock<ISoulseekClient>();
            var callCount = 0;
            client.SetupGet(m => m.ServerInfo).Returns((ServerInfo)null);
            client.Setup(m => m.SearchAsync(
                    It.IsAny<SearchQuery>(),
                    It.IsAny<SearchScope>(),
                    It.IsAny<int?>(),
                    It.IsAny<SearchOptions>(),
                    It.IsAny<CancellationToken>()))
                .Callback(() => callCount++)
                .Returns(Task.FromResult((new Search(SearchQuery.FromText("x"), SearchScope.Wishlist, 1, SearchStates.Completed, 0, 0, 0), (IReadOnlyCollection<SearchResponse>)new List<SearchResponse>())));

            using (var scheduler = new WishlistSearchScheduler(
                client.Object,
                new[] { "alpha" },
                new WishlistSearchSchedulerOptions(minimumInterval: System.TimeSpan.FromMilliseconds(1))))
            {
                scheduler.Start();
                await WaitForCallCountAsync(() => callCount, 2);
                scheduler.Stop();

                Assert.True(callCount >= 2);
            }
        }

        [Fact(DisplayName = "Wishlist scheduler caps oversized server intervals")]
        public void Wishlist_Scheduler_Caps_Oversized_Server_Intervals()
        {
            var client = new Mock<ISoulseekClient>();
            client.SetupGet(m => m.ServerInfo).Returns(new ServerInfo(wishlistInterval: int.MaxValue));

            using (var scheduler = new WishlistSearchScheduler(
                client.Object,
                new[] { "alpha" },
                new WishlistSearchSchedulerOptions(minimumInterval: System.TimeSpan.FromMilliseconds(1))))
            {
                var interval = scheduler.InvokeMethod<System.TimeSpan>("GetInterval");

                Assert.Equal(System.TimeSpan.FromMilliseconds(int.MaxValue), interval);
            }
        }

        [Theory(DisplayName = "Wishlist scheduler options reject non-positive intervals")]
        [InlineData(0, 1)]
        [InlineData(-1, 1)]
        [InlineData(1, 0)]
        [InlineData(1, -1)]
        public void Wishlist_Scheduler_Options_Reject_Non_Positive_Intervals(int overrideMilliseconds, int minimumMilliseconds)
        {
            TimeSpan? intervalOverride = overrideMilliseconds == 1 ? System.TimeSpan.FromMilliseconds(1) : System.TimeSpan.FromMilliseconds(overrideMilliseconds);
            TimeSpan? minimumInterval = minimumMilliseconds == 1 ? System.TimeSpan.FromMilliseconds(1) : System.TimeSpan.FromMilliseconds(minimumMilliseconds);

            Assert.Throws<ArgumentOutOfRangeException>(() => new WishlistSearchSchedulerOptions(intervalOverride, minimumInterval));
        }

        private static async Task WaitForCallCountAsync(System.Func<int> getCallCount, int expected)
        {
            using (var timeout = new CancellationTokenSource(System.TimeSpan.FromSeconds(3)))
            {
                while (getCallCount() < expected)
                {
                    timeout.Token.ThrowIfCancellationRequested();
                    await Task.Delay(10, timeout.Token).ConfigureAwait(false);
                }
            }
        }

        private static async Task WaitForStoppedAsync(WishlistSearchScheduler scheduler)
        {
            using (var timeout = new CancellationTokenSource(System.TimeSpan.FromSeconds(3)))
            {
                while (scheduler.IsRunning)
                {
                    timeout.Token.ThrowIfCancellationRequested();
                    await Task.Delay(10, timeout.Token).ConfigureAwait(false);
                }
            }
        }
    }
}
