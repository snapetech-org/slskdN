# Portable slskdN W70 cross-audit packet

Third-party cross-audit evidence for snapetech-org/slskdN PR #409 at head 335a96a9ec125b30c20c31be219da4e27db1ab03 / tree 7168de556608115be3b7e16b9ceb30b977df904b, continuation ranks 628–652.

The packet contains byte-preserved candidate-free, primary and blind packets; before/after live PR/ref attestations; a 300-cell exact-hash reconciliation ledger; all target and disposition disagreements; selected changes; 140 carried-hold attestations; and a portable verifier.

Run the verifier with the pinned checkout (direct file/hash reattestation only):

    python3 verify_cross_audit.py --repo /path/to/pinned/slskdN/checkout
    sha256sum -c SHA256SUMS.txt

The candidate-free and primary packet verifiers were run before cross reconciliation. The PR API still reports base SHA f25d263a2a7cdb2c8f76c40c346cb10f749a9356 (142 ahead, 0 behind), while live refs/heads/main is bc6251ff4ea5a7e59f2d86e2400c90520601f46e; against that current main tip the pinned head is 142 ahead and 4 behind, with the same merge base. The PR branch and pull refs remain at the pinned head, and the pinned checkout's source/catalog/caller preimages have no drift. No catalog values are applied by this packet. The hold ledger is hash-only; native-speaker and browser review were not performed.
