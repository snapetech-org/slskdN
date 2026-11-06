# Root adjudication — W1028–W1052

The 300-cell root ledger is pinned to input head `624e27d8bb108a764df6daab5cfb1c517ebac96d` / tree `d139a16988e23046ccb09f519db2d3b7ae0b86d1`. Root retained 244 current values, selected 42 corrections and 2 refinements, and kept 12 callerless values hash-only. The single root override refines the French W1045 sentence to use `examen du contrat`, matching the exact “Review Contract” UI action without implying formal contract validation.

Independent review confirmed all 44 selected target hashes. It withdrew the W1050 and W1031 concerns after the broader exact-head source context and actual selected Arabic abbreviation were checked. The W1050 adjacent source context is preserved in the sibling `source-context-supplement.jsonl`.

`build_root_adjudication.py` records the full ledger and selection plan from the sealed cross packet. Re-run it from a clean worktree at the pinned input head:

```sh
python3 -B build_root_adjudication.py --repo /path/to/slskdN
```

The guarded catalog application and full 300-cell readback are in the sibling `root-application/` directory.
