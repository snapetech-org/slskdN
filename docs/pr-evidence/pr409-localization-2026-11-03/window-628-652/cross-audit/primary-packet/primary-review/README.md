# slskdN PR #409 W70 primary semantic review

This packet independently reviews 300 cells across 25 sources and 12 locales at exact PR head 335a96a9ec125b30c20c31be219da4e27db1ab03 and tree 7168de556608115be3b7e16b9ceb30b977df904b, continuation ranks 628–652 (remaining-queue ranks 528–552). Decisions were made from the sealed candidate-free input and its exact caller contexts.

Disposition counts: accept-current: 252, correction: 32, refinement: 16. The review proposes 48 target changes (32 corrections and 16 refinements), retains all other values, and adds no holds. The callerless set is empty. The three baseline token issues are repaired: Arabic Type-1 numeric 1 at rank 638 and protected GPU/ MilkDrop literals at rank 631 (Arabic and Hindi). Placeholder, markup, numeric-token, and protected-literal checks pass at all selected targets.

All 140 prior held cells were reattested unchanged; the complete input also records the 1,732 prior/excluded IDs. No blind or cross-audit output was accessed. No repository or PR files were edited. Qualified native-speaker and browser reviews were not performed.

Run python3 verify_primary.py in this directory to validate checksums, input pins, decisions, tokens, holds, and live refs.
