# W80 review packet index

The review artifacts are copied byte-for-byte from the task's sealed packets and retain their own checksum manifests:

- `candidate-free-input/` — input and prior selected/held lineage, without candidate translations.
- `primary-review/` — sealed primary semantic review and its verifier.
- `independent-blind/` — independent blind decisions and checksum list.
- `cross-review/` — sealed contextual cross-review, audited suggestions, exact-hash proposal plan, and verifier.
- `root-manual-review/` — root review attestation accepting the 81 final exact-hash targets.

Each nested checksum list is preserved unchanged. The top-level window manifest also inventories every copied file.
