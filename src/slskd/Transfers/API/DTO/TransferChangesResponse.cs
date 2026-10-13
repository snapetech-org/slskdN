// <copyright file="TransferChangesResponse.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Transfers.API;

using System.Collections.Generic;
using System;

/// <summary>
///     A server-watermarked transfer snapshot or incremental change set.
/// </summary>
public class TransferChangesResponse
{
    /// <summary>
    ///     Gets the Unix-millisecond cursor for the next request.
    /// </summary>
    public long Cursor { get; set; }

    /// <summary>
    ///     Gets total non-removed transfer counts by direction.
    /// </summary>
    public TransferCounts Counts { get; set; } = new();

    /// <summary>
    ///     Gets whether another page exists for a paged initial snapshot.
    /// </summary>
    public bool HasMore { get; set; }

    /// <summary>
    ///     Gets the request-time component of the continuation cursor.
    /// </summary>
    public DateTimeOffset? NextAfterRequestedAt { get; set; }

    /// <summary>
    ///     Gets the transfer-ID component of the continuation cursor.
    /// </summary>
    public Guid? NextAfterId { get; set; }

    /// <summary>
    ///     Gets non-removed transfers for an initial request, or all changed records for a cursor request.
    /// </summary>
    public IEnumerable<global::slskd.Transfers.Transfer> Transfers { get; set; } = [];
}

/// <summary>
///     Total non-removed transfer counts by direction.
/// </summary>
public class TransferCounts
{
    /// <summary>
    ///     Gets the total non-removed downloads.
    /// </summary>
    public int Download { get; set; }

    /// <summary>
    ///     Gets the total non-removed uploads.
    /// </summary>
    public int Upload { get; set; }
}
