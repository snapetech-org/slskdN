# slskdN PR #409 W75 independent primary review

This packet reviews ranks 753–777 (queue ranks 653–677), covering all 25 selected source strings and 300 cells across the 12 direct locales. It is pinned to PR head `99d6afbfb8cca4dccc018e72c01950bc304240db` and tree `f21cb5cde009ac35f5531ddc40612821aee6f471`.

The primary ledger records 268 accept-current decisions, 20 correction recommendations, and 12 text-free holds. The 12 rank-754 cells remain unchanged because pinned callsites use `x` as a mix of icon names, visualizer/data keys, delimiters, and failure glyphs, not as an established user-facing phrase. There are no callerless selected sources.

The input baseline has 23 protected-literal flags for `Wishlist` at ranks 757 and 759. These are classifier false positives: the exact UI callers identify Wishlist features and each pinned locale catalog translates the standalone `Wishlist` label. The review records that exception explicitly. Proposal checks report no placeholder, markup, numeric, or protected-literal mismatches; Hindi at rank 767 additionally preserves the exact ASCII MBID example `83d91898-...`.

This is a primary-only review. It contains no blind or cross-review material and makes no native-speaker or browser-review claim. No source rewrite is recommended.

Run `python3 verify_primary.py --repo /path/to/pinned-checkout` from this directory to revalidate input pins, row coverage, hashes, proposal token parity, text-free holds, live PR refs, and packet checksums.
