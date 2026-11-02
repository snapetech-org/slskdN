# slskdN W32 independent root cross-review

This root cross-review covers the 29 exact-hash correction candidates from the pinned W32 packet.

- PR #409 head/tree: `dfb9707f946bf2686210bcf1072b9d70c8442a62` / `9458e836ae12c02573535b5c9dc052f055b7820d`.
- Source subtree: `469e060d9e0a3fd6f54bc75a69993ee2651d3e4b`.
- Frozen 266-cell review input SHA-256: `09d534acad981c383c42c2da15b0c26a667af529cf108430ae7c388294c1f988`.
- 29-candidate plan SHA-256: `ac67de5559bea50e815a729f95ff8a3c6e54bdd4751fc3d1278fd4add7808109`.
- Independent reviewer ledger SHA-256: `18dcbf5ae633336bf3cb423dc7c470adc38636aba9b2f17eb66c1d1d65f8204a`.

Root dispositions agree with the independent reviewer: 22 accepted proposals and 7 refinements; 0 keeps, holds, or unresolved candidates. The refinements replace literal “filling” translations with the feature’s missed-message meaning in French, Brazilian Portuguese, Arabic, Korean, Vietnamese, and Indonesian, and improve Indonesian maximum-retry word order. All source/current/proposed/final hashes, locale catalog values, 38 caller pins, placeholders, and protected literals were checked against the exact PR head. The no-write verifier passed; no catalog values were changed in this review. Native-speaker approval remains false.

The final target text and rationale for every candidate are in `root-disposition-ledger.jsonl`; exact checks are summarized in `verification-report.json`. The independent reviewer’s original evidence is retained at `/mnt/disks/scratch/task-scratch/slskdn-window32-independent-crossreview-20261102/`.
