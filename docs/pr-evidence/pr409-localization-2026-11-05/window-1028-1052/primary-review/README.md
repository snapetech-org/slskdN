# slskdN PR #409 W1028-W1052 primary review

This packet reviews 300 locale cells at head `624e27d8bb108a764df6daab5cfb1c517ebac96d` / tree `d139a16988e23046ccb09f519db2d3b7ae0b86d1`. The primary ledger contains 44 proposals, 244 retains, and 12 hash-only holds.

The review used the candidate-free source keys, exact caller contexts, current targets, and catalog pins in `../candidate-free`. It also carries the 421 active-hold hash-only reattestation and the 300-row W1003 product readback hash-only reattestation.

The provenance note records a prior-window inspection mistake; those prior records were outside this window and were not used. Verify with `python3 verify_primary_review.py` and `sha256sum -c SHA256SUMS.txt`.
