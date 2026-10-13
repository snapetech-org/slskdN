# slskdn Helm Chart (Generic Kubernetes)

Helm chart for [slskdN](https://github.com/snapetech/slskdn) on any Kubernetes cluster. No TrueCharts or TrueNAS-specific dependencies.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.10+
- PV provisioner (if not using a default `storageClass`)

## Install

```bash
# Add repo (when published) or install from path
helm install slskdn ./packaging/helm/slskdn

# With a values file
helm install slskdn ./packaging/helm/slskdn -f my-values.yaml

# Override key options
helm install slskdn ./packaging/helm/slskdn \
  --set env.SLSKD_SLSK_USERNAME=myuser \
  --set env.SLSKD_SLSK_PASSWORD=mypass \
  --set image.tag=2026101222-slskdn.350
```

## Main values

| Section | Key | Default | Description |
|--------|-----|---------|-------------|
| **image** | `repository` | `ghcr.io/snapetech/slskdn` | Image |
| | `tag` | (Chart `appVersion`) | Override tag |
| | `pullPolicy` | `IfNotPresent` | Pull policy |
| **service** | `main.port` | `5030` | HTTP port |
| | `https.enabled` | `false` | Expose HTTPS 5031 |
| **persistence** | `config.enabled` | `true` | PVC for `/app/config` |
| | `config.size` | `1Gi` | Size (and optional `storageClass`) |
| | `downloads` | `10Gi` | `/app/downloads` |
| | `shares` | `10Gi` | `/app/shared`, mounted read-only by default |
| | `incomplete` | `5Gi` | `/app/incomplete` |
| **env** | `SLSKD_*` | (see `values.yaml`) | Soulseek, API, mesh, privacy, etc. |
| **ingress** | `enabled` | `false` | Create Ingress |
| | `hosts[].host` | `slskdn.local` | Host(s) and paths |
| | `tls` | `[]` | TLS entries |
| **networkPolicy** | `enabled` | `false` | Create opt-in NetworkPolicy |
| | `ingress.web.from` | `[]` | Optional Web UI source selectors |
| | `ingress.soulseek.from` | `[]` | Optional Soulseek source selectors |
| | `egress.enabled` | `false` | Enable explicit egress policy |

## Required env (override in `env` or via `--set`)

- `SLSKD_SLSK_USERNAME` – Soulseek username
- `SLSKD_SLSK_PASSWORD` – Soulseek password

Use a Secret and `env` / `envFrom` in a custom values file for production.

## Optional NetworkPolicy

`networkPolicy.enabled` is off by default to avoid changing network behavior on
clusters without a policy controller. When enabled, the chart creates an ingress
policy for the Web UI and Soulseek listen port. Leave `from: []` to allow any
source to that port, or set Kubernetes `podSelector`, `namespaceSelector`, or
`ipBlock` entries to restrict access.

Be careful with `networkPolicy.egress.enabled`: Soulseek clients need outbound
TCP to the Soulseek server and remote peers, plus DNS if the cluster requires
it. Only enable egress policy when those destinations are explicitly allowed.

## Upgrade / Uninstall

```bash
helm upgrade slskdn ./packaging/helm/slskdn -f my-values.yaml
helm uninstall slskdn
```

## Links

- [slskdN](https://github.com/snapetech/slskdn)
- [slskd configuration](https://github.com/slskd/slskd/wiki/Configuration)
