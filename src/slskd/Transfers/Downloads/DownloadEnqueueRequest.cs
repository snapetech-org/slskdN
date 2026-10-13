// <copyright file="DownloadEnqueueRequest.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Transfers.Downloads
{
    using System;

    /// <summary>
    ///     A request to enqueue a single file for download. Carries optional metadata
    ///     captured at request time (from search-result file attributes) so the
    ///     Transfer row can show bitrate/length/etc. before the download completes.
    /// </summary>
    public sealed record DownloadEnqueueRequest
    {
        public required string Filename { get; init; }
        public required long Size { get; init; }
        public Guid? BatchId { get; init; }
        public string? BatchExternalId { get; init; }
        public string? DestinationDirectory { get; init; }
        public Guid? SearchId { get; init; }
        public string? SearchText { get; init; }
        public int? BitRate { get; init; }
        public int? SampleRate { get; init; }
        public int? BitDepth { get; init; }
        public int? Length { get; init; }

        /// <summary>
        ///     Optional existing <see cref="DownloadRequest"/> id to attach this attempt to.
        ///     Used by the rescue/auto-replace path to swap the source under a stable request.
        ///     When null, a new DownloadRequest is created if no existing same-filename transfer
        ///     already has one to inherit.
        /// </summary>
        public Guid? RequestId { get; init; }

        /// <summary>Optional display name for a newly created DownloadRequest.</summary>
        public string? RequestName { get; init; }

        /// <summary>Originating wishlist item, if any (only used when creating a new DownloadRequest).</summary>
        public Guid? WishlistItemId { get; init; }

        /// <summary>
        ///     Number of auto-replace cycles already spent by the owning request.
        ///     This is carried onto replacement transfers so a failed search cannot
        ///     restart the same request forever after a process restart.
        /// </summary>
        public int AutoReplaceAttempts { get; init; }
    }
}
