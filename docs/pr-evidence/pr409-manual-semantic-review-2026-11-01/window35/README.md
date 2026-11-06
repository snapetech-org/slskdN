# slskdN W35 manual review and exact-hash cross-review

This bundle retains the frozen W35 populated-catalog packet, the 274-row independent semantic review, and root’s exact 38-row cross-review. The reviewed base is PR #409 head `917273260c49cca1c14576a0720fc84998d2846d`, tree `1cdd8c831d224a5706ac6f3e465add4fd249d2be`; caller/source subtree `src/web/src` is `594e56c3f439bad476b1bd57e0de1665c62fa1bb`.

W35 covers 25 source keys / 274 populated locale cells. The independent full review recorded 236 keep-current rows and accepted 38 corrections. Root independently reviewed all 38 candidates and accepted each final target as proposed; there were no refinements, keeps, or holds among candidates. All root and independent final-target hashes match. Native-speaker approval is not claimed.

The exact-head preflight confirmed zero overlap with 4,800 formal-review cells, 10,052 prior manual cells across 847 source keys, and 1,373 previously applied correction rows. The selected W35 rows contain 445 caller references across 8 source files. All 12 current catalog file hashes, current values, source/current/proposed hashes, placeholders, protected literals, and caller lines were rechecked before application. The review packet preserves the original manual-stage checksums; the independent and root ledgers are provided in sibling directories with their own checksum files.

- Manual candidate plan SHA-256: `938f53404562111e77d388336c8756a21f90fb65323650164cb47c3ecbbc7b0f`
- All-cell manual decisions SHA-256: `f8cab36f2d4bb8b059f01920a8b64cd12e4569e720f55f539b7bacb6ecfac069`
- Root ledger SHA-256: `9370973a90aaef1e6a597a4aa31d6bd21fedd4b7f8ded71f4d93ee0533d0f749`
- Independent 274-row ledger SHA-256: `6053ad16c8c19ecccfcfb330987810b6f3fd30c19538b67e48488195e190a36f`

No catalog changes are included in this manual-review directory. The 38 exact target applications and their catalog hashes are recorded in the adjacent [W35 application bundle](../../pr409-catalog-correction-application-window35-2026-11-02/README.md). The current PR remains a draft. Native-speaker review remains outstanding.

Each subdirectory preserves its own original `SHA256SUMS.txt`; this top-level file covers every file in this W35 review bundle, including the nested checksum files.
