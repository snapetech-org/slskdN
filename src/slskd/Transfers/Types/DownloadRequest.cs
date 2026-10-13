// <copyright file="DownloadRequest.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Transfers.Downloads
{
    using System;
    using System.ComponentModel.DataAnnotations;

    /// <summary>
    ///     A user-facing download request. One request can be fulfilled by one or more
    ///     <see cref="Transfer"/> attempts (e.g. when the rescue path swaps to an alternative source).
    ///     The Request is the stable user-facing entity; Transfers are attempts under it.
    /// </summary>
    public class DownloadRequest
    {
        [Key]
        public Guid Id { get; init; } = Guid.NewGuid();

        /// <summary>Display label. Defaults to the basename of the originating filename; user-renamable.</summary>
        public string Name { get; set; } = string.Empty;

        /// <summary>The filename as first requested (audit/debug; mutates across attempts).</summary>
        public string OriginalFilename { get; init; } = string.Empty;

        /// <summary>First-known size of the request.</summary>
        public long? Size { get; set; }

        public Guid? BatchId { get; init; }
        public string? BatchExternalId { get; init; }
        public string? DestinationDirectory { get; init; }

        /// <summary>Aggregate state across all attempts.</summary>
        public DownloadRequestState State { get; set; } = DownloadRequestState.Active;

        /// <summary>Stringified <see cref="State"/> for SQLite legibility; do not set in code.</summary>
        public string? StateDescription { get; set; }

        public DateTime CreatedAt { get; init; } = DateTime.UtcNow;
        public DateTime? CompletedAt { get; set; }

        /// <summary>Originating wishlist item, if any.</summary>
        public Guid? WishlistItemId { get; init; }

        /// <summary>Originating search response, if available.</summary>
        public Guid? SearchResponseId { get; init; }

        /// <summary>Originating search, if available.</summary>
        public Guid? SearchId { get; init; }

        /// <summary>Search text captured when the request was created, if available.</summary>
        public string? SearchText { get; init; }

        // Cached metadata that survives across attempts.
        public int? BitRate { get; set; }
        public int? SampleRate { get; set; }
        public int? BitDepth { get; set; }
        public int? Length { get; set; }
        public string? Artist { get; set; }
        public string? Album { get; set; }
        public string? Title { get; set; }
        public int? TrackNumber { get; set; }
        public int? Year { get; set; }
    }

    public enum DownloadRequestState
    {
        Active = 0,
        Completed = 1,
        Failed = 2,
        Cancelled = 3,
    }
}
