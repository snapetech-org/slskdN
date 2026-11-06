# slskdN W34 exact-hash catalog corrections

Applied the 33 root-final W34 target changes to PR #409: 32 accepted as proposed and one refined. The root also resolved the packet’s French transfer-policy uncertainty as keep-current, supported by the adjacent `Upload Slots` / `Download Slots` labels (`Emplacements d’envoi` / `Emplacements de téléchargement`).

The catalog-only commit is `10fc341aa2bada1f0ee5be6d6119e31858c36aca`, a direct child of reviewed head `dc8ed2406a2247600d487df1ae3128ce08cc7faa`; its tree is `58cf85492948a6d0dfc6775fa69c539deb54a019`. The review tree was `9909f5d6e32dfcc78ba53aa0c838f95e9ba246d3`; source/caller subtree remains `594e56c3f439bad476b1bd57e0de1665c62fa1bb`.

Changes touch 33 values across 11 locale catalogs; every locale catalog retains 6,169 keys. Spanish has no W34 correction cells. The root ledger SHA-256 is `da7bccd982e54172209375534b9a9309b04a2a6c3a20ce87a4b9df4e08a7cc59`; the independent ledger SHA-256 is `7a9da225deb033f6cacfa7306c0051e0d66dd899df11051249c50fe600a4fc40`. The exact apply-plan SHA-256 is recorded in `application-manifest.json`; the applied-row ledger SHA-256 is `b75f7de69ae63f8ce95f37b1f24072fe999bfca9c7291dc0d2df4b5fecc80810`.

`verify_application_window34.py` checks the catalog diff, exact targets and hashes, placeholders, protected literals, source subtree, workflow paths, evidence checksums, and application commit parent. The post-apply report confirms 33 exact changes across 11 locales and no workflow changes.

Cumulative manual review is 34 windows / 10,052 cells / 847 source keys. Cumulative applied corrections are 1,373 across 324 source keys. The packet’s one French uncertain cell was resolved unchanged; 267 other uncertain rows, six earlier exact-context correction holds, and eleven W33 context-mismatched cells remain unchanged. The formal-review overlap claim could not be independently reconstructed because raw formal result rows were not in the supplied packet. Native-speaker and headed-browser review remain outstanding.

No tests, builds, scans, CI, workflow changes, releases, tags, or merges were run or made. PR #409 remains open and draft.
