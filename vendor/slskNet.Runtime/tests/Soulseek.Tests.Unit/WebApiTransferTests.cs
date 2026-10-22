// <copyright file="WebApiTransferTests.cs" company="slskdN Team">
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

namespace Soulseek.Tests.Unit
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Reflection;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.Extensions.Configuration;
    using Moq;
    using WebAPI.Controllers;
    using WebAPI.DTO;
    using WebAPI.Trackers;
    using Xunit;

    public class WebApiTransferTests
    {
        [Fact(DisplayName = "Transfer tracker ignores stale transfer removal")]
        public void Transfer_Tracker_Ignores_Stale_Transfer_Removal()
        {
            var tracker = new TransferTracker();

            var ex = Record.Exception(() => tracker.TryRemove(TransferDirection.Download, "missing", "missing-id"));

            Assert.Null(ex);
        }

        [Fact(DisplayName = "Transfer tracker disposes cancellation token source when removing transfer")]
        public void Transfer_Tracker_Disposes_Cancellation_Token_Source_When_Removing_Transfer()
        {
            var tracker = new TransferTracker();
            var cancellationTokenSource = new CancellationTokenSource();
            var transfer = new Soulseek.Transfer(TransferDirection.Download, "user", "file.mp3", 1, TransferStates.Queued, 1, 0);

            tracker.AddOrUpdate(transfer, cancellationTokenSource);
            tracker.TryRemove(TransferDirection.Download, "user", WebAPI.DTO.Transfer.FromSoulseekTransfer(transfer).Id);

            Assert.Throws<ObjectDisposedException>(() => _ = cancellationTokenSource.Token);
        }

        [Fact(DisplayName = "Transfer tracker disposes cancellation token sources when removing user")]
        public void Transfer_Tracker_Disposes_Cancellation_Token_Sources_When_Removing_User()
        {
            var tracker = new TransferTracker();
            var cancellationTokenSource = new CancellationTokenSource();
            var transfer = new Soulseek.Transfer(TransferDirection.Download, "user", "file.mp3", 1, TransferStates.Queued, 1, 0);

            tracker.AddOrUpdate(transfer, cancellationTokenSource);
            tracker.TryRemove(TransferDirection.Download, "user");

            Assert.Throws<ObjectDisposedException>(() => _ = cancellationTokenSource.Token);
        }

        [Fact(DisplayName = "Transfer tracker disposes replaced cancellation token source")]
        public void Transfer_Tracker_Disposes_Replaced_Cancellation_Token_Source()
        {
            var tracker = new TransferTracker();
            var oldCancellationTokenSource = new CancellationTokenSource();
            var newCancellationTokenSource = new CancellationTokenSource();
            var transfer = new Soulseek.Transfer(TransferDirection.Download, "user", "file.mp3", 1, TransferStates.Queued, 1, 0);

            tracker.AddOrUpdate(transfer, oldCancellationTokenSource);
            tracker.AddOrUpdate(transfer, newCancellationTokenSource);

            Assert.Throws<ObjectDisposedException>(() => _ = oldCancellationTokenSource.Token);
            Assert.True(tracker.TryGet(TransferDirection.Download, "user", WebAPI.DTO.Transfer.FromSoulseekTransfer(transfer).Id, out var record));
            Assert.Same(newCancellationTokenSource, record.CancellationTokenSource);

            newCancellationTokenSource.Dispose();
        }

        [Fact(DisplayName = "Transfer enqueue rejects null request")]
        public async Task Transfer_Enqueue_Rejects_Null_Request()
        {
            var controller = new TransfersController(CreateConfiguration(Path.GetTempPath()), Mock.Of<ISoulseekClient>(), new TransferTracker());

            var response = await controller.Enqueue("user", null);

            Assert.IsType<BadRequestObjectResult>(response);
        }

        [Fact(DisplayName = "Transfer enqueue rejects negative size")]
        public async Task Transfer_Enqueue_Rejects_Negative_Size()
        {
            var controller = new TransfersController(CreateConfiguration(Path.GetTempPath()), Mock.Of<ISoulseekClient>(), new TransferTracker());

            var response = await controller.Enqueue("user", new QueueDownloadRequest { Filename = "file.mp3", Size = -1 });

            Assert.IsType<BadRequestObjectResult>(response);
        }

        [Fact(DisplayName = "Transfer endpoints reject blank route values")]
        public async Task Transfer_Endpoints_Reject_Blank_Route_Values()
        {
            var controller = new TransfersController(CreateConfiguration(Path.GetTempPath()), Mock.Of<ISoulseekClient>(), new TransferTracker());

            Assert.IsType<BadRequestObjectResult>(controller.CancelDownload(" ", "id"));
            Assert.IsType<BadRequestObjectResult>(controller.CancelDownload("user", " "));
            Assert.IsType<BadRequestObjectResult>(controller.CancelUpload(" ", "id"));
            Assert.IsType<BadRequestObjectResult>(controller.CancelUpload("user", " "));
            Assert.IsType<BadRequestObjectResult>(await controller.Enqueue(" ", new QueueDownloadRequest { Filename = "file.mp3", Size = 1 }));
            Assert.IsType<BadRequestObjectResult>(controller.GetDownloads(" "));
            Assert.IsType<BadRequestObjectResult>(await controller.GetPlaceInQueue(" ", "id"));
            Assert.IsType<BadRequestObjectResult>(await controller.GetPlaceInQueue("user", " "));
            Assert.IsType<BadRequestObjectResult>(controller.GetUploads(" "));
            Assert.IsType<BadRequestObjectResult>(controller.GetUploads(" ", "id"));
            Assert.IsType<BadRequestObjectResult>(controller.GetUploads("user", " "));
        }

        [Fact(DisplayName = "Transfer upload lookup returns not found for missing id")]
        public void Transfer_Upload_Lookup_Returns_Not_Found_For_Missing_Id()
        {
            var controller = new TransfersController(CreateConfiguration(Path.GetTempPath()), Mock.Of<ISoulseekClient>(), new TransferTracker());

            var response = controller.GetUploads("user", "missing");

            Assert.IsType<NotFoundResult>(response);
        }

        [Fact(DisplayName = "Transfer enqueue defers output file creation until stream factory is invoked")]
        public async Task Transfer_Enqueue_Defers_Output_File_Creation_Until_Stream_Factory_Is_Invoked()
        {
            var root = CreateTempDirectory();

            try
            {
                Func<Task<Stream>> capturedStreamFactory = null;
                var client = new Mock<ISoulseekClient>();
                var downloadCompletion = new TaskCompletionSource<Soulseek.Transfer>(TaskCreationOptions.RunContinuationsAsynchronously);
                var remoteFilename = "album/track.mp3";

                client.Setup(m => m.DownloadAsync(
                        "user",
                        remoteFilename,
                        It.IsAny<Func<Task<Stream>>>(),
                        1,
                        0,
                        null,
                        It.IsAny<TransferOptions>(),
                        It.IsAny<CancellationToken>()))
                    .Callback<string, string, Func<Task<Stream>>, long?, long, int?, TransferOptions, CancellationToken>((callbackUsername, callbackFilename, streamFactory, size, startOffset, token, options, cancellationToken) =>
                    {
                        capturedStreamFactory = streamFactory;
                        var transfer = new Soulseek.Transfer(TransferDirection.Download, "user", remoteFilename, 1, TransferStates.Queued, 1, 0);
                        options.StateChanged((TransferStates.None, transfer));
                    })
                    .Returns(downloadCompletion.Task);

                var controller = new TransfersController(CreateConfiguration(root), client.Object, new TransferTracker());

                var response = await controller.Enqueue("user", new QueueDownloadRequest { Filename = remoteFilename, Size = 1 });
                var localFilename = Path.Combine(root, "album", "track.mp3");

                var status = Assert.IsType<StatusCodeResult>(response);
                Assert.Equal(201, status.StatusCode);
                Assert.NotNull(capturedStreamFactory);
                Assert.False(File.Exists(localFilename));

                var stream = await capturedStreamFactory();
                await stream.DisposeAsync();

                Assert.True(File.Exists(localFilename));
            }
            finally
            {
                Directory.Delete(root, recursive: true);
            }
        }

        [Fact(DisplayName = "Transfer enqueue disposes untracked cancellation token source when download faults")]
        public async Task Transfer_Enqueue_Disposes_Untracked_Cancellation_Token_Source_When_Download_Faults()
        {
            CancellationToken capturedCancellationToken = default;
            var client = new Mock<ISoulseekClient>();

            client.Setup(m => m.DownloadAsync(
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<Func<Task<Stream>>>(),
                    It.IsAny<long>(),
                    It.IsAny<long>(),
                    It.IsAny<int?>(),
                    It.IsAny<TransferOptions>(),
                    It.IsAny<CancellationToken>()))
                .Callback<string, string, Func<Task<Stream>>, long, long, int?, TransferOptions, CancellationToken>((username, filename, streamFactory, size, startOffset, token, options, cancellationToken) =>
                {
                    capturedCancellationToken = cancellationToken;
                })
                .Returns(Task.FromException<Soulseek.Transfer>(new InvalidOperationException("boom")));

            var controller = new TransfersController(CreateConfiguration(Path.GetTempPath()), client.Object, new TransferTracker());

            var response = await controller.Enqueue("user", new QueueDownloadRequest { Filename = "file.mp3", Size = 1 });

            var status = Assert.IsType<ObjectResult>(response);
            Assert.Equal(500, status.StatusCode);
            Assert.Throws<ObjectDisposedException>(() => _ = GetCancellationTokenSource(capturedCancellationToken).Token);
        }

        private static IConfiguration CreateConfiguration(string outputDirectory)
        {
            return new ConfigurationBuilder()
                .AddInMemoryCollection(new Dictionary<string, string> { ["OUTPUT_DIR"] = outputDirectory })
                .Build();
        }

        private static string CreateTempDirectory()
        {
            var path = Path.Combine(Path.GetTempPath(), "slsknet-runtime-tests", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(path);
            return path;
        }

        private static CancellationTokenSource GetCancellationTokenSource(CancellationToken token)
        {
            var source = typeof(CancellationToken).GetField("_source", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(token) as CancellationTokenSource;
            return source ?? throw new InvalidOperationException("Unable to inspect cancellation token source");
        }
    }
}
