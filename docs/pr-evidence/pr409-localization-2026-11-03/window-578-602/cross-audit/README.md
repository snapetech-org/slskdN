# slskdN PR #409 W68 cross-audit

This report reconciles the sealed primary review, blind review ledger, and exact candidate-free packet for ranks 578–602 at head 973a65312a475de4d8aa39aee837249553fd884e and tree 2a7b200dd1fe96f894bfdb663f656d6ffd48f487.

cross-audit-ledger.jsonl contains one row per locale cell, with both review decisions and suggestions, source/catalog/caller pins, selected final target, adjudication, and independent placeholder, markup, numeric, and protected-literal checks. Corrections use the primary proposal after reconciliation; accepted rows retain the current target. hold-cross-audit.jsonl compares all 128 prior target hashes from the candidate-free packet and sealed blind hold ledger and records the primary packet's aggregate unchanged claim.

The reviews agree on 271 accepts and 27 corrections. Two additional primary corrections are upheld from caller evidence (Indonesian dry-run notice and French failed-download retention field). Among the 27 shared corrections, 16 proposed strings differ; each is resolved in the cell row with a selected target and rationale. Final counts: 271 accept-current, 29 corrections, and zero holds.

The primary packet has no row-level carried-hold ledger. Its aggregate count and unchanged claim agree with the 128 per-cell candidate-free/blind hash checks; this limitation is recorded in the summary.

No repository or PR changes were made. No native-speaker or browser review was performed.

Run python3 verify_cross_audit.py here. By default it verifies report checksums and, when sibling evidence folders are present, cross-checks the report against the candidate-free input, blind ledger, and primary packet. The evidence root can be supplied as the first argument.
