// <copyright file="TransferOptionsTests.cs" company="JP Dillingham">
//     Copyright (c) JP Dillingham. All rights reserved.
//     Copyright (c) slskdN Team.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

namespace Soulseek.Tests.Unit.Options
{
    using System;
    using System.Threading;
    using System.Threading.Tasks;
    using AutoFixture.Xunit2;
    using Xunit;

    public class TransferOptionsTests
    {
        [Trait("Category", "Instantiation")]
        [Theory(DisplayName = "Instantiates with given data"), AutoData]
        public void Instantiates_Given_Data(
            bool seekInput,
            bool seekOutput,
            bool disposeInput,
            bool disposeOutput,
            Func<Transfer, int, CancellationToken, Task<int>> governor,
            Action<(TransferStates PreviousState, Transfer Transfer)> stateChanged,
            int maximumLingerTime,
            Action<(long PreviousBytesTransferred, Transfer Transfer)> progressUpdated,
            Func<Transfer, CancellationToken, Task> acquireSlot,
            Action<Transfer, int, int, int> reporter,
            Action<Transfer> slotReleased,
            Func<Transfer, long, long> sizeMismatchResolver,
            int progressUpdateInterval,
            long progressUpdateMinimumBytes)
        {
            maximumLingerTime = Math.Abs(maximumLingerTime % 10000);
            progressUpdateInterval = Math.Abs(progressUpdateInterval % 10000);
            progressUpdateMinimumBytes = Math.Abs(progressUpdateMinimumBytes % 10000);

            var o = new TransferOptions(
                governor,
                stateChanged,
                progressUpdated,
                acquireSlot,
                slotReleased,
                reporter,
                sizeMismatchResolver,
                maximumLingerTime,
                seekInput,
                seekOutput,
                disposeInput,
                disposeOutput,
                progressUpdateInterval,
                progressUpdateMinimumBytes);

            Assert.Equal(seekInput, o.SeekInputStreamAutomatically);
            Assert.Equal(seekOutput, o.SeekOutputStreamAutomatically);
            Assert.Equal(disposeInput, o.DisposeInputStreamOnCompletion);
            Assert.Equal(disposeOutput, o.DisposeOutputStreamOnCompletion);
            Assert.Equal(governor, o.Governor);
            Assert.Equal(stateChanged, o.StateChanged);
            Assert.Equal(progressUpdated, o.ProgressUpdated);
            Assert.Equal(maximumLingerTime, o.MaximumLingerTime);
            Assert.Equal(progressUpdateInterval, o.ProgressUpdateInterval);
            Assert.Equal(progressUpdateMinimumBytes, o.ProgressUpdateMinimumBytes);
            Assert.Equal(acquireSlot, o.SlotAwaiter);
            Assert.Equal(slotReleased, o.SlotReleased);
            Assert.Equal(reporter, o.Reporter);
            Assert.Equal(sizeMismatchResolver, o.SizeMismatchResolver);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Throws given negative maximum linger time")]
        public void Throws_Given_Negative_Maximum_Linger_Time()
        {
            var ex = Record.Exception(() => new TransferOptions(maximumLingerTime: -1));

            Assert.NotNull(ex);
            Assert.IsType<ArgumentOutOfRangeException>(ex);
            Assert.Equal("maximumLingerTime", ((ArgumentOutOfRangeException)ex).ParamName);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Instantiates with defaults")]
        public async Task Instantiates_With_Defaults()
        {
            var o = new TransferOptions();

            Assert.True(o.SeekOutputStreamAutomatically);
            Assert.True(o.DisposeInputStreamOnCompletion);
            Assert.True(o.DisposeOutputStreamOnCompletion);

            var ex = await Record.ExceptionAsync(() => o.Governor(null, 1, CancellationToken.None));
            Assert.Null(ex);

            var ex2 = await Record.ExceptionAsync(() => o.SlotAwaiter(null, CancellationToken.None));
            Assert.Null(ex2);

            Assert.Null(o.StateChanged);
            Assert.Null(o.ProgressUpdated);
            Assert.Null(o.SlotReleased);
            Assert.Equal(0, o.ProgressUpdateInterval);
            Assert.Equal(0, o.ProgressUpdateMinimumBytes);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Throws given negative progress update interval")]
        public void Throws_Given_Negative_Progress_Update_Interval()
        {
            var ex = Record.Exception(() => new TransferOptions(progressUpdateInterval: -1));

            Assert.NotNull(ex);
            Assert.IsType<ArgumentOutOfRangeException>(ex);
            Assert.Equal("progressUpdateInterval", ((ArgumentOutOfRangeException)ex).ParamName);
        }

        [Trait("Category", "Instantiation")]
        [Fact(DisplayName = "Throws given negative progress update minimum bytes")]
        public void Throws_Given_Negative_Progress_Update_Minimum_Bytes()
        {
            var ex = Record.Exception(() => new TransferOptions(progressUpdateMinimumBytes: -1));

            Assert.NotNull(ex);
            Assert.IsType<ArgumentOutOfRangeException>(ex);
            Assert.Equal("progressUpdateMinimumBytes", ((ArgumentOutOfRangeException)ex).ParamName);
        }

        [Trait("Category", "WithAdditionalStateChanged")]
        [Theory(DisplayName = "WithAdditionalStateChanged returns copy other than StateChanged"), AutoData]
        public void WithAdditionalStateChanged_Returns_Copy_Other_Than_StateChanged(
            bool seekInput,
            bool disposeInput,
            bool disposeOutput,
            Func<Transfer, long, long> sizeMismatchResolver,
            Func<Transfer, int, CancellationToken, Task<int>> governor,
            Action<(TransferStates PreviousState, Transfer Transfer)> stateChanged,
            int maximumLingerTime,
            Action<(long PreviousBytesTransferred, Transfer Transfer)> progressUpdated,
            Func<Transfer, CancellationToken, Task> acquireSlot,
            Action<Transfer> slotReleased,
            int progressUpdateInterval,
            long progressUpdateMinimumBytes)
        {
            maximumLingerTime = Math.Abs(maximumLingerTime % 10000);
            progressUpdateInterval = Math.Abs(progressUpdateInterval % 10000);
            progressUpdateMinimumBytes = Math.Abs(progressUpdateMinimumBytes % 10000);

            var n = new TransferOptions(
                governor: governor,
                stateChanged: stateChanged,
                progressUpdated: progressUpdated,
                slotAwaiter: acquireSlot,
                slotReleased: slotReleased,
                maximumLingerTime: maximumLingerTime,
                progressUpdateInterval: progressUpdateInterval,
                progressUpdateMinimumBytes: progressUpdateMinimumBytes,
                seekInputStreamAutomatically: seekInput,
                disposeInputStreamOnCompletion: disposeInput,
                disposeOutputStreamOnCompletion: disposeOutput,
                sizeMismatchResolver: sizeMismatchResolver);

            var o = n.WithAdditionalStateChanged(null);

            Assert.Equal(seekInput, o.SeekInputStreamAutomatically);
            Assert.Equal(disposeInput, o.DisposeInputStreamOnCompletion);
            Assert.Equal(disposeOutput, o.DisposeOutputStreamOnCompletion);
            Assert.Equal(governor, o.Governor);
            Assert.Equal(progressUpdated, o.ProgressUpdated);
            Assert.Equal(maximumLingerTime, o.MaximumLingerTime);
            Assert.Equal(progressUpdateInterval, o.ProgressUpdateInterval);
            Assert.Equal(progressUpdateMinimumBytes, o.ProgressUpdateMinimumBytes);
            Assert.Equal(acquireSlot, o.SlotAwaiter);
            Assert.Equal(slotReleased, o.SlotReleased);
            Assert.Equal(sizeMismatchResolver, o.SizeMismatchResolver);

            Assert.NotEqual(stateChanged, o.StateChanged);
        }

        [Trait("Category", "WithAdditionalStateChanged")]
        [Fact(DisplayName = "WithAdditionalStateChanged returns copy that executes both StateChanged")]
        public void WithAdditionalStateChanged_Returns_Copy_That_Executes_Both_StateChanged()
        {
            var one = false;
            var two = false;

            var n = new TransferOptions(stateChanged: (_) => { one = true; });

            var o = n.WithAdditionalStateChanged((_) => { two = true; });

            o.StateChanged(default);

            Assert.True(one);
            Assert.True(two);
        }

        [Trait("Category", "WithAdditionalStateChanged")]
        [Fact(DisplayName = "WithAdditionalStateChanged returns copy that does not throw if both StateChanged are null")]
        public void WithAdditionalStateChanged_Returns_Copy_That_Does_Not_Throw_If_Both_StateChanged_Are_Null()
        {
            var n = new TransferOptions(stateChanged: null);

            var o = n.WithAdditionalStateChanged(null);

            var ex = Record.Exception(() => o.StateChanged(default));

            Assert.Null(ex);
        }

        [Trait("Category", "WithDisposalOptions")]
        [Theory(DisplayName = "WithDisposalOptions returns unchanged copy if both options are null"), AutoData]
        public void WithAdditionalStateChanged_Returns_Unchanged_Copy_If_Both_Options_Are_Null(
            bool seekInput,
            bool disposeInput,
            bool disposeOutput,
            Func<Transfer, long, long> sizeMismatchResolver,
            Func<Transfer, int, CancellationToken, Task<int>> governor,
            Action<(TransferStates PreviousState, Transfer Transfer)> stateChanged,
            int maximumLingerTime,
            Action<(long PreviousBytesTransferred, Transfer Transfer)> progressUpdated,
            Func<Transfer, CancellationToken, Task> acquireSlot,
            Action<Transfer> slotReleased,
            int progressUpdateInterval,
            long progressUpdateMinimumBytes)
        {
            maximumLingerTime = Math.Abs(maximumLingerTime % 10000);
            progressUpdateInterval = Math.Abs(progressUpdateInterval % 10000);
            progressUpdateMinimumBytes = Math.Abs(progressUpdateMinimumBytes % 10000);

            var n = new TransferOptions(
                governor: governor,
                stateChanged: stateChanged,
                progressUpdated: progressUpdated,
                slotAwaiter: acquireSlot,
                slotReleased: slotReleased,
                maximumLingerTime: maximumLingerTime,
                progressUpdateInterval: progressUpdateInterval,
                progressUpdateMinimumBytes: progressUpdateMinimumBytes,
                seekInputStreamAutomatically: seekInput,
                disposeInputStreamOnCompletion: disposeInput,
                disposeOutputStreamOnCompletion: disposeOutput,
                sizeMismatchResolver: sizeMismatchResolver);

            var o = n.WithDisposalOptions();

            Assert.Equal(governor, o.Governor);
            Assert.Equal(stateChanged, o.StateChanged);
            Assert.Equal(progressUpdated, o.ProgressUpdated);
            Assert.Equal(acquireSlot, o.SlotAwaiter);
            Assert.Equal(slotReleased, o.SlotReleased);
            Assert.Equal(maximumLingerTime, o.MaximumLingerTime);
            Assert.Equal(progressUpdateInterval, o.ProgressUpdateInterval);
            Assert.Equal(progressUpdateMinimumBytes, o.ProgressUpdateMinimumBytes);
            Assert.Equal(seekInput, o.SeekInputStreamAutomatically);
            Assert.Equal(disposeInput, o.DisposeInputStreamOnCompletion);
            Assert.Equal(disposeOutput, o.DisposeOutputStreamOnCompletion);
            Assert.Equal(sizeMismatchResolver, o.SizeMismatchResolver);
        }

        [Trait("Category", "WithDisposalOptions")]
        [Theory(DisplayName = "WithDisposalOptions returns changed copy if both options are specified"), AutoData]
        public void WithAdditionalStateChanged_Returns_Changed_Copy_If_Both_Options_Are_Specified(
            bool seekInput,
            bool disposeInput,
            bool disposeOutput,
            Func<Transfer, long, long> sizeMismatchResolver,
            Func<Transfer, int, CancellationToken, Task<int>> governor,
            Action<(TransferStates PreviousState, Transfer Transfer)> stateChanged,
            int maximumLingerTime,
            Action<(long PreviousBytesTransferred, Transfer Transfer)> progressUpdated,
            Func<Transfer, CancellationToken, Task> acquireSlot,
            Action<Transfer> slotReleased,
            int progressUpdateInterval,
            long progressUpdateMinimumBytes)
        {
            maximumLingerTime = Math.Abs(maximumLingerTime % 10000);
            progressUpdateInterval = Math.Abs(progressUpdateInterval % 10000);
            progressUpdateMinimumBytes = Math.Abs(progressUpdateMinimumBytes % 10000);

            var n = new TransferOptions(
                governor: governor,
                stateChanged: stateChanged,
                progressUpdated: progressUpdated,
                slotAwaiter: acquireSlot,
                slotReleased: slotReleased,
                maximumLingerTime: maximumLingerTime,
                progressUpdateInterval: progressUpdateInterval,
                progressUpdateMinimumBytes: progressUpdateMinimumBytes,
                seekInputStreamAutomatically: seekInput,
                disposeInputStreamOnCompletion: !disposeInput,
                disposeOutputStreamOnCompletion: !disposeOutput,
                sizeMismatchResolver: sizeMismatchResolver);

            var o = n.WithDisposalOptions(
                disposeInputStreamOnCompletion: disposeInput,
                disposeOutputStreamOnCompletion: disposeOutput);

            Assert.Equal(governor, o.Governor);
            Assert.Equal(stateChanged, o.StateChanged);
            Assert.Equal(progressUpdated, o.ProgressUpdated);
            Assert.Equal(acquireSlot, o.SlotAwaiter);
            Assert.Equal(slotReleased, o.SlotReleased);
            Assert.Equal(maximumLingerTime, o.MaximumLingerTime);
            Assert.Equal(progressUpdateInterval, o.ProgressUpdateInterval);
            Assert.Equal(progressUpdateMinimumBytes, o.ProgressUpdateMinimumBytes);
            Assert.Equal(seekInput, o.SeekInputStreamAutomatically);
            Assert.Equal(disposeInput, o.DisposeInputStreamOnCompletion);
            Assert.Equal(disposeOutput, o.DisposeOutputStreamOnCompletion);
            Assert.Equal(sizeMismatchResolver, o.SizeMismatchResolver);
        }
    }
}
