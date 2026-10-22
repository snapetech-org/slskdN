# slskNet.Runtime

slskNet.Runtime is a slskdN-maintained .NET Standard runtime transport library for the Soulseek network.

This is a modified version of Soulseek.NET. It is not maintained by, endorsed by, or affiliated with the Soulseek.NET project or its author(s).

## Runtime Changes

- Package and repository branding changed to `slskNet.Runtime`.
- Optional Soulseek type-1 peer/distributed/transfer obfuscation metadata is supported in `SetListenPort`, peer-address responses, and `ConnectToPeer` responses.
- A dedicated type-1 obfuscated peer/distributed/transfer listener can be configured.
- Outbound peer/distributed/transfer dials can prefer compatible obfuscated endpoints while keeping regular direct and indirect fallback paths.
- slskdN peer capability descriptors can be exchanged over reserved peer-message envelopes and tracked in a runtime registry.
- Ed25519 descriptor signing and verification helpers are available for applications that need signed slskdN capability metadata.
- Mesh rendezvous helpers can use native Soulseek interests and similar-user lookups without adding a new distributed wire format.
- Wishlist search scheduling can honor server-provided wishlist interval information.
- Server interest and recommendation protocol messages are exposed through first-class client APIs.
- Multi-user private-message sends are exposed through a bounded, deduplicated client API.
- `CannotCreateRoom` server responses are surfaced as room join failures instead of being ignored.
- New protocol parsers validate collection counts before allocating or reading repeated values.

Type-1 obfuscation is not encryption. It is a compatibility/privacy posture for peer-message (`P`), distributed-message (`D`), and file-transfer (`F`) streams with regular fallback retained.

## Feature Summary

| Area | Public API / Type | Wire behavior | Default impact |
| ---- | ----------------- | ------------- | -------------- |
| Type-1 peer/distributed/transfer obfuscation | `PeerObfuscationOptions`, `SoulseekClientOptions.PeerObfuscationOptions` | Advertises type-1 metadata, opens a dedicated obfuscated peer/distributed/transfer listener, and can prefer compatible obfuscated peer/distributed/transfer dials | Off by default in this runtime; regular fallback is mandatory when enabled |
| slskdN capability handshake | `PeerCapabilityEnvelope`, `PeerCapabilityDescriptor`, `PeerCapabilityRegistry`, `SendPeerCapabilityAsync`, `PeerCapabilityReceived` | Sends and receives reserved slskdN peer-message envelopes after normal Soulseek peer connection setup | No descriptor is advertised unless the application configures one and sends or enables the handshake |
| Descriptor signing | `IPeerDescriptorSigner`, `IPeerDescriptorVerifier`, `Ed25519PeerDescriptorSigner` | Signs and verifies canonical slskdN capability descriptors outside the Soulseek server protocol | Optional helper; key custody remains with the application |
| Mesh rendezvous helper | `MeshRendezvousService` | Uses ordinary Soulseek interest and similar-user commands around the public `slskdn-mesh-v1` rendezvous tag | No interest is published or probed unless the application calls the helper |
| Wishlist scheduling | Wishlist-scoped search helpers and interval models | Uses server wishlist search semantics and server-provided interval information where available | Normal searches are unchanged |
| User interests | `AddInterestAsync`, `RemoveInterestAsync`, `AddHatedInterestAsync`, `RemoveHatedInterestAsync` | Sends the native Soulseek interest management server commands | No command is sent unless the application calls the API |
| Recommendations | `GetRecommendationsAsync`, `GetGlobalRecommendationsAsync`, `RecommendationList`, `Recommendation` | Requests personal/global recommendation lists from the Soulseek server | Read-only request; no effect on search/browse/transfer behavior |
| User interest lookup | `GetUserInterestsAsync`, `UserInterests` | Requests another user's liked and hated interest strings | Read-only request; caller controls when it runs |
| Similar users | `GetSimilarUsersAsync`, `SimilarUser` | Requests users with interests similar to the current logged-in user | Read-only request; caller controls when it runs |
| Item discovery | `GetItemRecommendationsAsync`, `ItemRecommendations`, `GetItemSimilarUsersAsync`, `ItemSimilarUsers` | Requests recommendation branches or similar users for a specific item string | Read-only request; item strings are not verified metadata identities |
| Multi-user private message | `SendPrivateMessageAsync(IEnumerable<string>, string, CancellationToken?)` | Sends the native `MessageUsers` command once for multiple recipients | Only the overload emits this command; single-recipient messaging is unchanged |
| Room failure surfacing | `CannotCreateRoom` handling | Completes the pending room join waiter with `RoomException` | Passive response handling; join request format is unchanged |
| Parser hardening | `ProtocolCountReader` and updated response parsers | Rejects negative or impossible collection counts before allocation/read loops | Malformed responses fail closed instead of producing partial results |

## Compatibility

The forked runtime remains wire-compatible with legacy Soulseek clients when default options are used. New protocol behavior is opt-in or passive:

- Peer/distributed-message obfuscation is disabled by default.
- When obfuscation is enabled, the regular Soulseek listen port must still be advertised. This keeps legacy clients able to connect by normal peer-message, distributed-message, and file-transfer paths.
- Outbound obfuscated dials are attempted only when `PeerObfuscationOptions.PreferOutbound` is enabled and the remote peer has advertised a compatible type-1 obfuscated endpoint.
- Regular direct and indirect peer/distributed/transfer connection attempts remain available as fallback paths.
- If an obfuscated distributed or transfer candidate connects first but fails setup negotiation, regular fallback candidates are still allowed to complete before the operation fails.
- slskdN capability envelopes use a reserved custom peer-message code. They are sent only by slskdN-aware callers, and capability records are discovery hints rather than authorization decisions.
- Mesh rendezvous uses the normal Soulseek interest graph. Publishing the public `slskdn-mesh-v1` interest is an application choice and is not implied by constructing the runtime client.
- Interest, recommendation, similar-user, item-recommendation, hated-interest, and multi-user private-message commands are only sent when the application explicitly calls the corresponding API.
- Passive handling of `CannotCreateRoom` only changes local error reporting for a failed room join; it does not alter room join wire format.

The practical result is that legacy clients that do not understand obfuscation metadata can continue to use the regular listener, and clients that do not use the added recommendation or interest APIs will not emit those server commands.

## Added Protocol APIs

### Peer/distributed/transfer obfuscation

`PeerObfuscationOptions` controls Soulseek type-1 rotated peer/distributed/transfer obfuscation:

```csharp
var options = new SoulseekClientOptions(
    listenPort: 2234,
    peerObfuscationOptions: new PeerObfuscationOptions(
        enabled: true,
        listenPort: 2235,
        preferOutbound: true));
```

This advertises the regular Soulseek listen port and the type-1 obfuscated listen port. Incoming obfuscated peer-message (`P`), distributed-message (`D`), and file-transfer (`F`) handshakes are decoded by the dedicated obfuscated listener. Outbound peer/distributed/transfer connection setup can prefer a compatible cached obfuscated endpoint, while preserving regular direct and indirect fallback behavior.

Operational notes:

- Use a different port for the regular and obfuscated listeners.
- Keep `advertiseRegularPort` enabled. The constructor rejects obfuscated-only advertising because it would break legacy-client reachability.
- `preferOutbound` changes connection ordering only for peers that advertised compatible type-1 metadata.
- Obfuscation applies to peer-message (`P`), distributed-message (`D`), and file-transfer (`F`) streams. Regular paths remain available for fallback.

Validation notes:

- Local loopback matrix tests exercise obfuscated and regular peer-message (`P`) roundtrips.
- Local loopback matrix tests exercise obfuscated and regular distributed-message (`D`) roundtrips.
- Local loopback matrix tests exercise obfuscated file-transfer (`F`) byte and stream payloads plus regular transfer fallback.
- Manager-level tests cover obfuscated inbound transfer handoff, inbound indirect transfer fallback, outbound transfer preference/fallback, and distributed parent preference/fallback.
- These tests prove runtime framing and fallback behavior over real local TCP sockets; live third-party client interoperability still needs live-network validation.

### Interests and recommendations

The runtime exposes the server-side interest and recommendation messages used by Soulseek clients:

```csharp
await client.AddInterestAsync("ambient");
await client.RemoveInterestAsync("ambient");
await client.AddHatedInterestAsync("noise");
await client.RemoveHatedInterestAsync("noise");

var recommendations = await client.GetRecommendationsAsync();
var globalRecommendations = await client.GetGlobalRecommendationsAsync();
var userInterests = await client.GetUserInterestsAsync("username");
var similarUsers = await client.GetSimilarUsersAsync();
var itemRecommendations = await client.GetItemRecommendationsAsync("ambient");
var itemSimilarUsers = await client.GetItemSimilarUsersAsync("ambient");
```

Returned values are deliberately close to the Soulseek protocol:

- `RecommendationList.Recommendations` and `RecommendationList.Unrecommendations` contain raw item strings plus integer scores.
- `UserInterests.Liked` and `UserInterests.Hated` contain raw interest strings reported by the server.
- `SimilarUser.Rating` is the server-provided similarity rating.
- `ItemRecommendations.Item` and `ItemSimilarUsers.Item` echo the requested item string after server response parsing.

Parser implementations reject negative or impossible collection counts before building result lists, so malformed server responses fail closed instead of silently producing partial data.

### slskdN capability descriptors and rendezvous

The runtime includes the protocol pieces slskdN uses to discover compatible peers without changing standard Soulseek search, browse, room, or transfer messages.

`PeerCapabilityEnvelope` reserves a slskdN-only peer-message code for descriptor exchange. `PeerCapabilityDescriptor` carries a signed feature statement, endpoint hints, and validity timestamps, while `PeerCapabilityRegistry` records the latest descriptor seen per Soulseek username.

Applications that opt into this path can:

- Configure a local descriptor and send a capability hello over a normal peer-message connection.
- Subscribe to `PeerCapabilityReceived` or inspect `SoulseekClient.PeerCapabilities`.
- Sign and verify descriptors with the runtime Ed25519 helpers while keeping key storage and trust policy outside the runtime.
- Fall back to any application-level legacy capability discovery when no signed descriptor is available.

`MeshRendezvousService` is a helper over existing Soulseek interest and similar-user messages. It can publish the public `slskdn-mesh-v1` interest tag and discover similar users who may be slskdN peers. Publishing the tag is explicit and should be presented as a privacy-visible operation by applications.

### Multi-user private messages

`SendPrivateMessageAsync(IEnumerable<string>, string, CancellationToken?)` sends one private message to multiple users using the Soulseek `MessageUsers` server command:

```csharp
await client.SendPrivateMessageAsync(new[] { "alice", "bob" }, "hello");
```

Recipients are deduplicated case-insensitively and capped at 100 recipients per call to avoid accidentally creating oversized packets or duplicate sends.

The overload validates all recipients before writing the packet. Null, empty, and whitespace-only usernames are rejected; duplicate usernames differing only by case are sent once. Applications that need local conversation history should persist one outbound message per normalized recipient after the call succeeds.

### Room creation failures

`CannotCreateRoom` server responses now complete the pending join-room wait with a `RoomException`. This makes failed room creation/join attempts visible to callers instead of requiring applications to infer failure from timeout behavior.

### Authentication hash

Soulseek login requests include the protocol-required MD5 hash of `username + password`. The runtime emits that field for wire compatibility only; it is not used as password storage, password verification, or a general-purpose security primitive.

## License

This software is licensed under the GNU General Public License v3.0 with Additional Terms pursuant to Section 7 of the GPLv3. The complete license text is in [LICENSE](LICENSE), and the required notices are in [NOTICE](NOTICE).

Original Soulseek.NET copyright and license notices are preserved in source files. Modified source files include slskdN modification notices.

## Reserved Minor Version Ranges

Applications using this library are required, as a condition of the license, to use a unique minor version number when logging in to the Soulseek network.

- `760-7699999`: slskd
- `7700000+`: reserved by slskdN/slskNet.Runtime deployments unless coordinated otherwise

## References

- [Fork runtime changes](docs/fork-runtime-changes.md)
- [Nicotine+ protocol documentation](https://nicotine-plus.org/doc/SLSKPROTOCOL.html)
- [SoulseekProtocol - Museek+](https://www.museek-plus.org/wiki/SoulseekProtocol)
- Original project: Soulseek.NET by JP Dillingham

## Local security scanning

Run `./scripts/security-scan-local.sh` for local Semgrep CE and the Trivy scanners that fit this repository. The installed pre-commit hook runs Semgrep on staged source/config files only; Trivy runs on demand or in CI. This public repository also runs Semgrep CE in GitHub Actions on changes and weekly. See [security-scanning.md](docs/security-scanning.md). Use `./scripts/update-security-tools.sh` to refresh local scanner data and the Trivy database.
