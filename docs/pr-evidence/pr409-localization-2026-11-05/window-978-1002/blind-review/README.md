# Independent blind semantic review — slskdN PR #409 W978–W1002

Pinned review head: `1c2fe3be2c720693cbcb12d377bf1177804f4e77`  
Pinned tree: `808501cbc3b6ed873a47d7188189d486f0673f5e`  
Window: W84, continuation ranks 978–1002, 25 sources × 12 locales = 300 cells.

This packet contains one disposition for every cell: **240 retain** and **60 propose**. Proposed strings appear only on proposed rows, each with a short rationale. Every row preserves the exact current target and its SHA256, source/source-ID hashes, catalog path/blob/file hash, locale/ranks, and caller count/context hash. `source-caller-bindings.jsonl` preserves all exact-head caller references and surrounding lines from candidate-free input. There are no callerless rows.

The five protected-literal mismatches in the candidate-free baseline are addressed. All final strings pass the recorded placeholder, markup, numeric, and protected-literal checks.

Review input: `/mnt/disks/scratch/task-scratch/slskdn-pr409-w978-1002-20261105/candidate-free/input`. No primary-review outputs were read. The packet does not edit any source or catalog. Candidate-free input hashes were checked before review. No build, test, scan, or CI job was run.

## Verify

```sh
python3 verifier.py --input-dir /mnt/disks/scratch/task-scratch/slskdn-pr409-w978-1002-20261105/candidate-free/input
```

The verifier checks packet SHA256s, exact-head current-cell and caller bindings, full caller-binding preservation, the 300-cell matrix, dispositions, final-string hashes, and token/protected-literal preservation.
