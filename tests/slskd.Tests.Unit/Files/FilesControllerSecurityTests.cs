// <copyright file="FilesControllerSecurityTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Tests.Unit.Files
{
    using System;
    using System.Collections.Generic;
    using System.IO;
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
        private readonly string downloadsDirectory;

        public FilesControllerSecurityTests()
        {
            mockFileService = new Mock<FileService>(Mock.Of<IOptionsMonitor<slskd.Options>>());
            mockOptionsSnapshot = new Mock<IOptionsSnapshot<slskd.Options>>();

            var options = new slskd.Options
            {
                RemoteFileManagement = true,
                Directories = new slskd.Options.DirectoriesOptions
                {
                    Downloads = Path.Combine(Path.GetTempPath(), "slskdn-files-tests", "downloads"),
                    Incomplete = Path.Combine(Path.GetTempPath(), "slskdn-files-tests", "incomplete")
                }
            };
            downloadsDirectory = options.Directories.Downloads;

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

            var fullPath = Path.GetFullPath(Path.Combine(downloadsDirectory, "test-file.txt"));
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
            var expectedPath = Path.GetFullPath(Path.Combine(downloadsDirectory, "subdir"));

            mockFileService.Setup(s => s.ListContentsAsync(
                    It.Is<string>(path => path == expectedPath),
                    It.IsAny<EnumerationOptions>()))
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
            var expectedPath = Path.GetFullPath(Path.Combine(downloadsDirectory, "subdir"));

            mockFileService.Setup(s => s.ListContentsAsync(
                    It.Is<string>(path => path == expectedPath),
                    It.Is<EnumerationOptions>(options =>
                        options.RecurseSubdirectories &&
                        options.AttributesToSkip.HasFlag(FileAttributes.System) &&
                        options.AttributesToSkip.HasFlag(FileAttributes.ReparsePoint))))
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
                It.IsAny<string>(), It.IsAny<EnumerationOptions>()), Times.Never);
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
    }
}
