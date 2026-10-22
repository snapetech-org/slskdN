#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

bash scripts/check-release-branch-sync.sh
bash packaging/scripts/validate-packaging-metadata.sh
python3 scripts/test_release_notes.py
python3 scripts/test_hosted_release_gate.py
python3 scripts/test_verify_github_target.py

pnpm install --frozen-lockfile
pnpm --filter @slskdn/web test

dotnet test tests/slskd.Tests.Unit/slskd.Tests.Unit.csproj \
    -c Release --blame-hang --blame-hang-timeout 5m \
    --blame-hang-dump-type none --logger 'console;verbosity=normal'
dotnet test tests/slskd.Tests/slskd.Tests.csproj \
    -c Release --blame-hang --blame-hang-timeout 5m \
    --blame-hang-dump-type none --logger 'console;verbosity=normal'
bash packaging/scripts/run-release-integration-smoke.sh

pnpm --filter @slskdn/web build
pnpm --filter @slskdn/web check:bundle
node src/web/scripts/verify-build-output.mjs
node src/web/scripts/smoke-subpath-build.mjs
