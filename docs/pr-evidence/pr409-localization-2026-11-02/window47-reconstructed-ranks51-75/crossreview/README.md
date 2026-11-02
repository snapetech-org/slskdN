# slskdN PR #409 W47 independent cross-review

## Scope and pins

Cross-review of the sealed primary packet at `/mnt/disks/scratch/task-scratch/slskdn-pr409-window47-primary-20261102`. Scope is 25 reconstructed stable-ID ranks (51–75) × 12 locales = 300 target cells. These are pending-set ranks; no historical source ordinal is claimed.

Exact reviewed head/tree: `cb6739864b3651d72412b6aeb4590537cbf23d4e` / `a0946207555e494a558707008ba051013964b447`. PR #409 was OPEN/DRAFT at both all-seven PR snapshots. Start query: `2026-11-02T22:13:13.256367+00:00..2026-11-02T22:13:14.144176+00:00`. End query: `2026-11-02T22:18:12.662157+00:00..2026-11-02T22:18:14.253802+00:00`. All seven head/tree pairs were unchanged between snapshots.

The primary packet’s 20 SHA256 entries passed. I independently reattested all 25 selected source hashes, 300 current target values and hashes, 12 locale catalog blob/file pins, 92 caller references, and the source/caller evidence pins. All 300 placeholder, markup, and registered protected-literal checks pass. The worktree is clean; this review packet is scratch-only.

## Independent language review

- Confirmed all 28 primary correction candidates and all 12 W71 holds.
- Reaffirmed 252 current targets.
- Identified 6 missed correction candidates and 2 refinements in cells the primary accepted; exact values and hashes are in `missed-items.jsonl`.
- Every cell carries an independent disposition, exact source/current hashes, caller references, confidence, and rationale in `crossreview-ledger.jsonl`.
- Native-speaker approval is not claimed. This is a machine-assisted review with moderate overall confidence; row confidence is recorded individually. No external official terminology sources were consulted in this independent pass.

The missed corrections are:

| Rank | Locale | Current | Candidate |
| --- | --- | --- | --- |
| 63 | ko | 내보낼 수 있는 기본 사전 설정이 없습니다. | 내보낼 수 있는 네이티브 프리셋이 없습니다. |
| 66 | de | neuere Versuche | Letzte Versuche |
| 70 | ar | Lidarr wanted-album relationship is unclear | State the wanted albums are in Lidarr |
| 70 | fr | albums recherchés Lidarr | albums recherchés dans Lidarr |
| 70 | hi | Lidarr वांछित-एल्बम सिंक | Lidarr में वांछित एल्बमों का सिंक |
| 70 | ko | Lidarr 원하는 앨범 동기화 | Lidarr의 원하는 앨범 동기화 |

The refinements are Japanese W56 (`地域設定` → `地域形式`) and Korean W67 (remove the space before the colon). See the ledger for full candidate strings and rationale.

## Runtime findings

- **W54 confirmed gap:** the hook stores a plain English string. `LocalizedOutputText` only translates branded output objects; plain strings only receive bidi wrapping. The reviewed locale values are not used on this path.
- **W55 cleared:** `RoomJoinModal` uses a local helper that calls `t(source, parameters)` from `useInterfaceLanguage`; the scanner missed the helper wrapper.
- **W57 confirmed gap:** the contacts fallback is a branded `interfaceTextOutput` object but is rendered directly at two paragraphs. This bypasses localized rendering and is not a valid React child.
- **W71 confirmed hold:** one partial source sentence is concatenated with separately localized “Mesh” and verification fragments. Keep all 12 cells held until a rich-text source/caller owns the full sentence and a tab-label slot.

No catalog, repository, or PR changes were made. No tests, builds, scans, CI, or browser work were run.

## Packet files

- `crossreview-ledger.jsonl`: all 300 independent cell decisions.
- `missed-items.jsonl`: six correction candidates and two refinements.
- `runtime-gap-crossreview.jsonl`: independent W54/W55/W57/W71 findings.
- `input-reattestation.json`: source, target, caller, catalog, and primary-packet integrity verification.
- `crossreview-summary.json`: counts, confidence, and snapshot attestations.
- `snapshots/start-all-seven-pr-heads.json`, `snapshots/end-all-seven-pr-heads.json`: timed all-seven head/tree queries.
- `manifest.json`, `SHA256SUMS.txt`: packet inventory and integrity seal.
