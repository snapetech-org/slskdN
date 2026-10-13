// <copyright file="DeleteItemsRequest.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Files.API;

using System;
using System.Collections.Generic;

/// <summary>
///     A bounded, multi-item file operation request.
/// </summary>
public sealed record DeleteItemsRequest
{
    /// <summary>
    ///     Gets the relative file and directory paths to delete.
    /// </summary>
    public IReadOnlyCollection<DeleteItemRequest> Items { get; init; } = Array.Empty<DeleteItemRequest>();
}

/// <summary>
///     A path and item type in a multi-item delete request.
/// </summary>
public sealed record DeleteItemRequest
{
    /// <summary>
    ///     Gets the path relative to the selected files root.
    /// </summary>
    public string Path { get; init; } = string.Empty;

    /// <summary>
    ///     Gets the item type: <c>file</c> or <c>directory</c>.
    /// </summary>
    public string Type { get; init; } = string.Empty;
}

/// <summary>
///     The outcome for one requested file operation.
/// </summary>
public sealed record DeleteItemResult(
    string Path,
    string Type,
    bool Succeeded,
    string? Error);

/// <summary>
///     Results from a multi-item delete request.
/// </summary>
public sealed record DeleteItemsResponse
{
    /// <summary>
    ///     Gets one result for each requested item, in request order.
    /// </summary>
    public IReadOnlyCollection<DeleteItemResult> Results { get; init; } = Array.Empty<DeleteItemResult>();
}
