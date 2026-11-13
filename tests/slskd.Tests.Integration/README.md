# Integration Test Configuration

## Test Categories

Tests are organized by levels (L0-L3) for CI/CD flexibility:

### L0: Unit Tests
- Fast, isolated, no external dependencies
- Run on every commit
- Example: Model validation, business logic

### L1: Protocol Contract Tests
- Test basic Soulseek protocol compliance
- Require Soulfind binary
- Run on PR builds
- Trait: `[Trait("Category", "L1-Protocol")]`

### L2: Multi-Client Integration Tests
- Test multi-node interactions (Alice/Bob/Carol topology)
- Require Soulfind + multiple slskdn instances
- Run on nightly builds
- Trait: `[Trait("Category", "L2-MultiClient")]`

### L3: Disaster Mode & Mesh Tests
- Test disaster scenarios, pure mesh operation
- Require full test infrastructure
- Run weekly or on-demand
- Traits: `[Trait("Category", "L3-DisasterMode")]`, `[Trait("Category", "L3-MeshOnly")]`

## Running Tests

### Run All Tests
```bash
dotnet test
```

### Run Specific Category
```bash
# L1 protocol tests only
dotnet test --filter "Category=L1-Protocol"

# L2 multi-client tests
dotnet test --filter "Category=L2-MultiClient"

# L3 disaster mode tests
dotnet test --filter "Category=L3-DisasterMode"

# L3 mesh-only tests
dotnet test --filter "Category=L3-MeshOnly"
```

### Run Without Soulfind
```bash
# Skip tests that require Soulfind
dotnet test --filter "Category!=L1-Protocol&Category!=L2-MultiClient&Category!=L3-DisasterMode"
```

## CI/CD Configuration

Continuous integration is defined in `.github/workflows/ci.yml`. Build, test,
scan, package, and release jobs run on private per-run JIT workers; the
workflow has no hosted-runner fallback. PR validation is started through the
repository's trusted owner-PR route, and the release gate runs on the exact
`main` commit before a release tag is created.

## Environment Variables

- `SOULFIND_PATH`: Path to Soulfind binary (auto-discovered if not set)
- `SLSKDN_TEST_TIMEOUT`: Test timeout in seconds (default: 300)
- `SLSKDN_TEST_LOG_LEVEL`: Logging level (Debug, Information, Warning, Error)
- `SLSKDN_RUN_LIVE_MESH_ACCOUNT_TESTS`: Set to `1`, `true`, or `yes` to run the live Soulseek-account mesh smoke. This test also requires two configured `SLSKDN_MESH_ACCOUNT_*` username/password pairs or the local ignored `local-mesh-account*.env` files. Leave unset for release preflight; the normal full-instance mesh tests do not require Soulseek login.
- `SLSKDN_RUN_LIVE_SOULSEEK_INTEROP_TESTS`: Set to `1`, `true`, or `yes` to run the live slskdN/Soulseek.NET runtime transfer smoke. This test uses two configured `SLSKDN_MESH_ACCOUNT_*` accounts, starts one full slskdN instance, and verifies a raw `SoulseekClient` can browse and download a tiny slskdN-hosted probe over the native Soulseek transfer path. Leave unset for release preflight.
- `SLSKDN_RUN_UPSTREAM_SLSKD_COMPAT_TESTS`: Set to `1`, `true`, or `yes` to run the live upstream slskd compatibility smoke. This test starts one upstream `slskd/slskd` daemon and one slskdN daemon, then verifies slskdN can enqueue and download an upstream-hosted probe over the native Soulseek transfer path. This requires the upstream daemon to be able to open a transfer connection back to slskdN using the endpoint reported by the live Soulseek server, so same-host NAT/firewall environments without a routable slskdN listen port can fail even though login, browse, and enqueue work.
- `SLSKDN_UPSTREAM_SLSKD_BINARY_PATH`: Optional path to an upstream `slskd` binary for `SLSKDN_RUN_UPSTREAM_SLSKD_COMPAT_TESTS`.
- `SLSKDN_BUILD_UPSTREAM_SLSKD`: Set to `1`, `true`, or `yes` to let the upstream compatibility runner clone/build `https://github.com/slskd/slskd.git` under `/tmp/slskdn-upstream-compat/slskd` when no upstream binary path is provided.
- `SLSKDN_UPSTREAM_SLSKD_SOURCE_DIR`: Optional source directory override for the upstream clone/build cache.
- `SLSKDN_FULL_INSTANCE_VPN_WRAPPER`: Optional wrapper script for full-instance live tests. The wrapper must accept `<namespace> <wireguard-conf> <command> [args...]`.
- `SLSKDN_FULL_INSTANCE_VPN_CONFIGS`: Comma-separated WireGuard configs. Each full-instance runner leases the next config so each live test credential set can run through a distinct VPN connection.
- `SLSKDN_FULL_INSTANCE_VPN_CLAIM_PORT_FORWARDING`: Set to `1` to have the VPN namespace entrypoint run `natpmpc` before daemon startup and claim the daemon's Soulseek TCP listen port. This is required for upstream app-to-app transfer compatibility when the peers are isolated behind VPNs. For providers such as Proton that return a random public port, the harness rewrites `soulseek.listen_port` to the public port and redirects the provider-mapped private port to that listener inside the namespace. Config files marked `NAT-PMP (Port Forwarding) = off` are skipped when this flag is enabled.
- `SLSKDN_VPN_TEST_FORWARD_GATEWAY`: NAT-PMP gateway for `SLSKDN_FULL_INSTANCE_VPN_CLAIM_PORT_FORWARDING` (default: `10.2.0.1`).
- `SLSKDN_FULL_INSTANCE_VPN_NAMESPACE_PREFIX`: Optional namespace prefix for the per-process VPN wrappers (default: `sln`).

## Test Data

Test fixtures are generated dynamically:
- Audio files: See `AudioFixtures.cs`
- MusicBrainz data: See `MusicBrainzFixtures.cs`
- No large binary files committed to repo

## Debugging Tests

### Enable Debug Logging
```bash
export SLSKDN_TEST_LOG_LEVEL=Debug
dotnet test --filter "Category=L1-Protocol" --logger "console;verbosity=detailed"
```

### Run Single Test
```bash
dotnet test --filter "FullyQualifiedName~Should_Login_And_Handshake"
```

### Keep Test Artifacts
Test harness creates temporary directories under `/tmp/slskdn-test/`.
To keep artifacts for debugging, set:
```bash
export SLSKDN_TEST_KEEP_ARTIFACTS=1
```

## Troubleshooting

### Build errors (API/type drift)
As of 2026-01, this project has ~30 build errors (ObfuscatedTransportIntegration, ModerationIntegration, TorIntegration, PerformanceBenchmarks; types/options renamed or missing: WebSocketOptions, HttpTunnelOptions, Obfs4Options, MeekOptions, IContentBackend, ContentDescriptor.Filename, PlanStatus.Success, TestContext, etc.). `dotnet test` at solution root and `./bin/build --dotnet-only` will fail at the Integration step until tests are aligned with current slskd APIs. See `docs/dev/40-fixes-plan.md` § Deferred.

### Soulfind Not Found
1. Check `SOULFIND_PATH` environment variable
2. Install from: https://github.com/slskd/soulfind
3. Ensure binary is executable: `chmod +x soulfind`

### Port Already in Use
Tests use ephemeral ports, but if conflicts occur:
```bash
# Kill any lingering Soulfind processes
pkill -9 soulfind
```

### Tests Timeout
Increase timeout:
```bash
export SLSKDN_TEST_TIMEOUT=600
```

### Flaky Tests
L2/L3 tests involve network timing and may be flaky. Retry:
```bash
dotnet test --filter "Category=L2-MultiClient" -- RunConfiguration.MaxCpuCount=1
```
