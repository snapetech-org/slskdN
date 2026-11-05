# Independent blind semantic review — PR #409 W1003–W1027

Input is pinned to head `8c752c49281418fdd96341ed46f5c321627b625f` / tree `b930b0d82679e843849e54456f3250e422c4682c`. The only review input was the candidate-free packet at `/mnt/disks/scratch/task-scratch/slskdn-pr409-w1003-1027-20261105/candidate-free`. Its provided `SHA256SUMS.txt` was verified before review and is copied here as `input-SHA256SUMS.txt`.

`review-cells.jsonl` contains one decision for each of 300 cells. The 12 callerless cells at continuation rank 1024 are `hold` records with hashes and identifiers only; source, current-target, proposed-target, and rationale text are omitted. No primary-review files, decisions, or cross-review outputs were consulted.

Counts: 59 proposals, 229 retains, 12 holds. Baseline token evidence: 287 of 288 caller-backed current targets pass; one protected-literal mismatch (Hindi FTP). All 59 proposed targets pass the packet token checks.

Language-specific wording has moderate confidence and was not native-speaker validated.
