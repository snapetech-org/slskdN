# slskd Bug Council Negative-Space Gate

This document declares slskd's trust boundaries and the validator each one must run, so a missing validator is itself a CI failure. The gate is enforced by `scripts/check-council-negative-space.sh`.

Semgrep and Trivy handle broad source, dependency, secret, and configuration scans. This gate serves a narrower purpose: it lists known trust boundaries and asserts that their validators remain wired.

slskd already runs many topic-specific check scripts (`check-controller-csrf.sh`, `check-anonymous-endpoints.sh`, `check-path-containment.sh`, etc). The negative-space gate complements those by recording the **boundaries** themselves as a single declarative list, instead of leaving each guard's existence implicit in a separate script.

## Boundaries

| Boundary | Source | Sink file(s) | Required validator |
| --- | --- | --- | --- |
| Mutating API endpoints | HTTP from clients | `src/slskd/**/API` and `src/slskd/**/*Controller.cs` | `[Authorize]`, explicit write roles, and CSRF token validation |
| Anonymous-friendly endpoints | HTTP from clients | `src/slskd/**/API` and `src/slskd/**/*Controller.cs` | `[AllowAnonymous]` allowlist must match `check-anonymous-endpoints.sh` |
| Shared-file path resolution | Configuration + caller paths | `src/slskd/**/API` and file/path services | path containment helpers per `check-path-containment.sh` |
| Outbound HTTP fetches | Application code | `src/slskd` | guarded factory per `check-outbound-http-guards.sh` |
| Durable state writes | Application code | `src/slskd` | atomic-write helpers per `check-durable-state-atomic-writes.sh` |
| Soulseek runtime crossings | Embedded slskNet.Runtime | `src/slskd/Soulseek` | event/handler observation per `check-async-task-observation.sh` |

## Adding a new boundary

1. Add a row to the table above.
2. Add an `assert_validator_present` line to `scripts/check-council-negative-space.sh`.
3. Add a behavior-pinned test per `docs/dev/bug-council-behavior-pinning.md`.

## Removing a boundary

Removing a row requires a short rationale explaining why the boundary no longer exists. Update the remediation baseline in the same change.

## Relationship to slskd's existing checks

The existing topic-specific scripts enforce boundary invariants in detail. The negative-space gate records the known boundaries; if a script disappears or stops being run, it still asserts that the validator symbol is present at the sink. These focused checks protect the listed fixes and boundaries. They do not replace broad scanning by Semgrep and Trivy.
