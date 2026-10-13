// <copyright file="FilesControllerSecurityTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Tests.Unit.Files
{
    using System;
    using System.Collections.Generic;
    using System.Text;
    using System.Threading.Tasks;
    using Microsoft.AspNetCore.Http;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.Extensions.Logging;
    using Microsoft.Extensions.Options;
    using Moq;
    using OneOf;
    using slskd;
    using slskd.Files;
    using slskd.Files.API;
    using Xunit;

    /// <summary>
    /// Security tests for FilesController, specifically targeting Base64-encoded path traversal.
    /// </summary>
    public class FilesControllerSecurityTests
    {
        private readonly Mock<FileService> mockFileService;
        private readonly Mock<IOptionsSnapshot<slskd.Options>> mockOptionsSnapshot;
        private readonly FilesController controller;

        public FilesControllerSecurityTests()
        {
            mockFileService = new Mock<FileService>(Mock.Of<IOptionsMonitor<slskd.Options>>());
            mockOptionsSnapshot = new Mock<IOptionsSnapshot<slskd.Options>>();

            var options = new slskd.Options
            {
                RemoteFileManagement = true,
                Directories = new slskd.Options.DirectoriesOptions
                {
                    Downloads = "/test/downloads",
                    Incomplete = "/test/incomplete"
                }
            };

            mockOptionsSnapshot.Setup(o => o.Value).Returns(options);

            controller = new FilesController(mockFileService.Object, mockOptionsSnapshot.Object);

            // Setup controller context
            controller.ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext()
            };
        }

        [Theory]
        [InlineData("Li4vc2VjcmV0LnR4dA==")] // "../secret.txt"
        [InlineData("Li4vLi4vZXRjL3Bhc3N3ZA==")] // "../../etc/passwd"
        [InlineData("ZG93bmxvYWRzLy4uLy4uL3NlY3JldC50eHQ=")] // "downloads/../../secret.txt"
        [InlineData("Li5cXC4uXFx3aW5kb3dzXFxzeXN0ZW0zMg==")] // "..\\..\\windows\\system32"
        public async Task DeleteDownloadFileAsync_ShouldRejectBase64TraversalPaths(string base64Traversal)
        {
            var result = await controller.DeleteDownloadFileAsync(base64Traversal);

            Assert.Equal("Invalid file path", Assert.IsType<BadRequestObjectResult>(result).Value);
            mockFileService.Verify(service => service.DeleteFilesAsync(It.IsAny<string>()), Times.Never);
        }

        [Fact]
        public async Task DeleteDownloadFileAsync_ShouldHandleInvalidBase64Gracefully()
        {
            // Arrange
            var invalidBase64 = "not-valid-base64!!!";

            // Act
            var result = await controller.DeleteDownloadFileAsync(invalidBase64);

            // Assert
            var badRequest = Assert.IsType<BadRequestObjectResult>(result);
            Assert.Equal("Invalid file path", badRequest.Value);
        }

        [Fact]
        public async Task DeleteDownloadFileAsync_ShouldAllowValidBase64Paths()
        {
            // Arrange
            var validPath = "test-file.txt";
            var base64Path = Convert.ToBase64String(Encoding.UTF8.GetBytes(validPath));

            var fullPath = Path.GetFullPath(Path.Combine("/test/downloads", validPath));
            mockFileService.Setup(s => s.DeleteFilesAsync(It.IsAny<string>()))
                .ReturnsAsync(new Dictionary<string, OneOf<bool, Exception>>
                {
                { fullPath, OneOf<bool, Exception>.FromT0(true) }
                })
                .Verifiable();

            // Act
            var result = await controller.DeleteDownloadFileAsync(base64Path);

            // Assert
            Assert.IsType<NoContentResult>(result);
        }

        [Fact]
        public async Task GetDownloadSubdirectoryContentsAsync_ShouldTrimDecodedBase64Path()
        {
            var encodedPath = Convert.ToBase64String(Encoding.UTF8.GetBytes(" subdir "));
            var expectedPath = Path.GetFullPath(Path.Combine("/test/downloads", "subdir"));

            mockFileService.Setup(s => s.ListContentsAsync(
                    It.Is<string>(path => path == expectedPath),
                    It.IsAny<EnumerationOptions>(),
                    It.IsAny<bool>()))
                .ReturnsAsync(new FilesystemDirectory())
                .Verifiable();

            var result = await controller.GetDownloadSubdirectoryContentsAsync(encodedPath);

            Assert.IsType<OkObjectResult>(result);
            mockFileService.Verify();
        }

        [Fact]
        public async Task GetDownloadSubdirectoryContentsAsync_RecursiveListingSkipsReparsePoints()
        {
            var encodedPath = Convert.ToBase64String(Encoding.UTF8.GetBytes("subdir"));
            var expectedPath = Path.GetFullPath(Path.Combine("/test/downloads", "subdir"));

            mockFileService.Setup(s => s.ListContentsAsync(
                    It.Is<string>(path => path == expectedPath),
                    It.Is<EnumerationOptions>(options =>
                        options.RecurseSubdirectories &&
                        options.AttributesToSkip.HasFlag(FileAttributes.System) &&
                        options.AttributesToSkip.HasFlag(FileAttributes.ReparsePoint)),
                    It.IsAny<bool>()))
                .ReturnsAsync(new FilesystemDirectory())
                .Verifiable();

            var result = await controller.GetDownloadSubdirectoryContentsAsync(encodedPath, recursive: true);

            Assert.IsType<OkObjectResult>(result);
            mockFileService.Verify();
        }

        [Theory]
        [InlineData("Li4vc2VjcmV0")] // "../secret"
        [InlineData("Li4vLi4vZXRj")] // "../../etc"
        public async Task ListingAndDirectoryDeletion_ShouldRejectBase64Traversal(string base64Traversal)
        {
            var listing = await controller.GetDownloadSubdirectoryContentsAsync(base64Traversal);
            var deletion = await controller.DeleteDownloadSubdirectoryAsync(base64Traversal);

            Assert.Equal("Invalid directory path", Assert.IsType<BadRequestObjectResult>(listing).Value);
            Assert.Equal("Invalid directory path", Assert.IsType<BadRequestObjectResult>(deletion).Value);
            mockFileService.Verify(service => service.ListContentsAsync(
                It.IsAny<string>(), It.IsAny<EnumerationOptions>(), It.IsAny<bool>()), Times.Never);
            mockFileService.Verify(service => service.DeleteDirectoriesAsync(It.IsAny<string>()), Times.Never);
        }

        [Theory]
        [InlineData("Li4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vc2VjcmV0LnR4dA==")] // Deep traversal
        [InlineData("Li4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vLi4vc2VjcmV0LnR4dA==")] // Very deep traversal
        public async Task DeleteDownloadFileAsync_ShouldRejectDeepTraversalPaths(string deepTraversalBase64)
        {
            var result = await controller.DeleteDownloadFileAsync(deepTraversalBase64);

            Assert.Equal("Invalid file path", Assert.IsType<BadRequestObjectResult>(result).Value);
            mockFileService.Verify(service => service.DeleteFilesAsync(It.IsAny<string>()), Times.Never);
        }

        [Fact]
        public async Task DeleteDownloadItemsAsync_ValidatesAllPathsAndReturnsPerItemOutcomes()
        {
            var directory = Path.GetFullPath(Path.Combine("/test/downloads", "album"));
            var file = Path.GetFullPath(Path.Combine("/test/downloads", "single.flac"));
            mockFileService.Setup(service => service.DeleteDirectoriesAsync(directory))
                .ReturnsAsync(new Dictionary<string, OneOf<bool, Exception>>
                {
                    [directory] = OneOf<bool, Exception>.FromT0(true),
                });
            mockFileService.Setup(service => service.DeleteFilesAsync(file))
                .ReturnsAsync(new Dictionary<string, OneOf<bool, Exception>>
                {
                    [file] = OneOf<bool, Exception>.FromT1(new IOException()),
                });

            var result = await controller.DeleteDownloadItemsAsync(new DeleteItemsRequest
            {
                Items = new[]
                {
                    new DeleteItemRequest { Path = "album", Type = "directory" },
                    new DeleteItemRequest { Path = "single.flac", Type = "file" },
                },
            });

            var partial = Assert.IsType<ObjectResult>(result);
            Assert.Equal(207, partial.StatusCode);
            var response = Assert.IsType<DeleteItemsResponse>(partial.Value);
            Assert.Equal(2, response.Results.Count);
            Assert.True(response.Results.First().Succeeded);
            Assert.False(response.Results.Last().Succeeded);
            Assert.Equal("delete-failed", response.Results.Last().Error);
            Assert.DoesNotContain("/test/downloads", response.Results.Last().Path);
        }

        [Theory]
        [InlineData("../outside.txt", "file")]
        [InlineData("album/song.flac", "file")]
        public async Task DeleteDownloadItemsAsync_RejectsUnsafeOrOverlappingPaths(string path, string type)
        {
            var items = new List<DeleteItemRequest>
            {
                new() { Path = "album", Type = "directory" },
                new() { Path = path, Type = type },
            };

            var result = await controller.DeleteDownloadItemsAsync(new DeleteItemsRequest { Items = items });

            Assert.IsType<BadRequestObjectResult>(result);
            mockFileService.Verify(service => service.DeleteDirectoriesAsync(It.IsAny<string[]>()), Times.Never);
            mockFileService.Verify(service => service.DeleteFilesAsync(It.IsAny<string[]>()), Times.Never);
        }
    }
}
