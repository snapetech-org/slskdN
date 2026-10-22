#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test_root=$(mktemp -d)
agent_pid=
cleanup() {
  if [[ -n "$agent_pid" ]]; then
    kill "$agent_pid" 2>/dev/null || true
    wait "$agent_pid" 2>/dev/null || true
  fi
  rm -rf -- "$test_root"
}
trap cleanup EXIT

mkdir -p "$test_root/bin" "$test_root/state"
printf '%s\n%s\n' \
  'current-relay-test-placeholder-00000000000000000000' \
  'previous-relay-test-placeholder-00000000000000000000' >"$test_root/api-keys"
printf '%s\n' \
  'public_ip=203.0.113.10' \
  'public_port=50300' \
  'target_port=50300' \
  'home_ip=10.77.0.2' >"$test_root/state/relay.env"

printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf "peer-key %s\\n" "${TEST_RELAY_HANDSHAKE:-0}"' >"$test_root/bin/wg"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf "tailscale %s\\n" "$*" >>"$TEST_RELAY_COMMAND_LOG"' \
  'case "${1:-}" in' \
  '  status)' \
  '    if [[ -n "${TEST_TAILSCALE_STATUS:-}" ]]; then' \
  '      printf "%s\\n" "$TEST_TAILSCALE_STATUS"' \
  '    else' \
  '      printf "%s\\n" "{\"BackendState\":\"Stopped\"}"' \
  '    fi' \
  '    ;;' \
  '  ping)' \
  '    if [[ "${TEST_TAILSCALE_ONLINE:-0}" == 1 ]]; then' \
  '      printf "pong from home (100.64.0.2) via DERP(tor) in 14.5ms\\n"' \
  '    else' \
  '      exit 1' \
  '    fi' \
  '    ;;' \
  '  ip) printf "100.64.0.1\\n" ;;' \
  'esac' >"$test_root/bin/tailscale"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf "64 bytes from 10.77.0.2: time=12.5 ms\\n"' >"$test_root/bin/ping"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'exit 0' >"$test_root/bin/conntrack"
for command in ip iptables sysctl tc; do
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'printf "%s %s\\n" "$(basename "$0")" "$*" >>"$TEST_RELAY_COMMAND_LOG"' \
    'exit 0' >"$test_root/bin/$command"
done
chmod +x "$test_root/bin/"*

dotnet build "$repo_root/src/slskdN.VpnAgent/slskdN-vpn-agent.csproj" --no-restore >/dev/null
agent="$repo_root/src/slskdN.VpnAgent/bin/Debug/net10.0/slskdN-vpn-agent"
port=18010
export PATH="$test_root/bin:$PATH"
export TEST_RELAY_HANDSHAKE
TEST_RELAY_HANDSHAKE=$(date +%s)
export SLSKDN_RELAY_API_KEY_FILE="$test_root/api-keys"
export SLSKDN_VPN_STATE_DIR="$test_root/state"
export SLSKDN_RELAY_API_HOST=127.0.0.1
export SLSKDN_RELAY_API_PORT=$port
export SLSKDN_RELAY_PUBLIC_IP=203.0.113.10
export TEST_RELAY_COMMAND_LOG="$test_root/commands.log"

"$agent" relay-apply >/dev/null
grep -q 'iptables -t nat -A SLSKDN-RELAY-NAT -i eth0 -p tcp --dport 50300 -j DNAT --to-destination 10.77.0.2:50300' "$TEST_RELAY_COMMAND_LOG"
grep -q 'iptables -A SLSKDN-RELAY-FWD -i slskdN-relay -o eth0 -s 10.77.0.0/30' "$TEST_RELAY_COMMAND_LOG"
grep -q 'tc qdisc replace dev slskdN-relay root tbf rate 100mbit' "$TEST_RELAY_COMMAND_LOG"
grep -q 'tc filter replace dev slskdN-relay parent ffff:' "$TEST_RELAY_COMMAND_LOG"

"$agent" relay-api --host 127.0.0.1 >"$test_root/agent.log" 2>&1 &
agent_pid=$!
for _ in $(seq 1 50); do
  if curl -fs -H 'X-API-Key: current-relay-test-placeholder-00000000000000000000' "http://127.0.0.1:$port/v1/slskdn/relay" >"$test_root/status.json"; then
    break
  fi
  sleep 0.1
done

curl -fsS -H 'X-API-Key: previous-relay-test-placeholder-00000000000000000000' "http://127.0.0.1:$port/v1/slskdn/relay" >/dev/null
unauthorized=$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/v1/slskdn/relay")
[[ "$unauthorized" == 401 ]]
grep -q '"connected":true' "$test_root/status.json"
grep -q '"latencyMs":12.5' "$test_root/status.json"

kill "$agent_pid"
wait "$agent_pid" 2>/dev/null || true
agent_pid=
TEST_RELAY_HANDSHAKE=1
"$agent" relay-api >"$test_root/agent.log" 2>&1 &
agent_pid=$!
for _ in $(seq 1 50); do
  stale=$(curl -s -o "$test_root/public-ip.json" -w '%{http_code}' \
    -H 'X-API-Key: current-relay-test-placeholder-00000000000000000000' \
    "http://127.0.0.1:$port/v1/publicip/ip" || true)
  [[ "$stale" == 200 ]] && break
  sleep 0.1
done
[[ "$stale" == 200 ]]
grep -q '"public_ip":""' "$test_root/public-ip.json"

kill "$agent_pid"
wait "$agent_pid" 2>/dev/null || true
agent_pid=
export SLSKDN_RELAY_TUNNEL_TYPE=tailscale
export SLSKDN_RELAY_HOME_IP=100.64.0.2
unset SLSKDN_RELAY_API_HOST SLSKDN_RELAY_TUNNEL_CIDR
export TEST_TAILSCALE_ONLINE=1
export TEST_TAILSCALE_STATUS='{"BackendState":"Running","Peer":{"node-key":{"TailscaleIPs":["100.64.0.2"],"Online":true,"RxBytes":3145728,"TxBytes":4194304,"LastSeen":"2026-07-30T15:00:00Z"}}}'
: >"$TEST_RELAY_COMMAND_LOG"
"$agent" relay-apply >/dev/null
grep -q 'iptables -A SLSKDN-RELAY-FWD -i tailscale0 -o eth0 -s 100.64.0.2/32' "$TEST_RELAY_COMMAND_LOG"
grep -q 'tailscale status --json' "$TEST_RELAY_COMMAND_LOG"

export SLSKDN_RELAY_TUNNEL_CIDR=100.64.0.0/10
if "$agent" relay-apply >"$test_root/broad-cidr.log" 2>&1; then
  echo "Tailscale relay accepted a broad tailnet CIDR" >&2
  exit 1
fi
grep -q 'must match the exact Tailscale home node /32' "$test_root/broad-cidr.log"
unset SLSKDN_RELAY_TUNNEL_CIDR

"$agent" relay-api --host 127.0.0.1 >"$test_root/agent.log" 2>&1 &
agent_pid=$!
for _ in $(seq 1 50); do
  if curl -fs -H 'X-API-Key: current-relay-test-placeholder-00000000000000000000' "http://127.0.0.1:$port/v1/slskdn/relay" >"$test_root/tailscale-status.json"; then
    break
  fi
  sleep 0.1
done
grep -q '"transport":"tailscale"' "$test_root/tailscale-status.json"
grep -q '"connected":true' "$test_root/tailscale-status.json"
grep -q '"latencyMs":14.5' "$test_root/tailscale-status.json"
grep -q '"rxBytes":3145728' "$test_root/tailscale-status.json"
grep -q '"txBytes":4194304' "$test_root/tailscale-status.json"
grep -q '"path":"pong from home' "$test_root/tailscale-status.json"

export TEST_TAILSCALE_STATUS='{'
kill "$agent_pid"
wait "$agent_pid" 2>/dev/null || true
agent_pid=
"$agent" relay-api --host 127.0.0.1 >"$test_root/agent.log" 2>&1 &
agent_pid=$!
sleep 0.2
malformed=$(curl --max-time 5 -sS -o "$test_root/malformed-status.json" -w '%{http_code}' \
  -H 'X-API-Key: current-relay-test-placeholder-00000000000000000000' \
  "http://127.0.0.1:$port/v1/slskdn/relay")
[[ "$malformed" == 500 ]]
grep -q '"error":"relay status unavailable"' "$test_root/malformed-status.json"

echo "Self-hosted WireGuard/Tailscale relay forwarding, limits, authentication, rotation, status, and fail-closed checks passed."
