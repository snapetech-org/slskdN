# PR #409 exact-hash correction application — window 24

This bundle records the application of the 45 window24 targets after root’s independent exact-hash cross-review. The review and application were pinned to PR base head `805246b87e208cedcbdd0e2f33a83f912f4ad84b` / tree `4377ade660fa379731a41b54ba387c4eff2bcf32`; the source/catalog subtree before applying catalog values was `c3d06e298da7f7e04e69bee3c2596805a03d1e4b`.

## Independent cross-review

Root reviewed all 45 exact source/current/proposal hash rows, caller pins, and placeholders: 43 accepted as proposed, 2 refined and accepted, 0 held. The independent review ledger, summary, and exact apply plan are separate files. The two refinements are Arabic `إعداد الظهور` and Vietnamese `chế độ hiển thị`. The original proposal plan remains separate in the window24 review bundle.

An earlier mapping draft had a proposal bound to the wrong source key. It was caught before catalog edits, superseded, and excluded from this application evidence. The corrected proposal and root-reviewed exact apply plan were re-bound and checked by source ID, catalog key, source hash, current-target hash, caller context, and placeholders.

## Applied values

The exact-hash application commit is `00ee3b76686a3b4cdafd4d9a24a02342d5f36bb2` (tree `d0a640b4716f3363264cf96ee5fa9aea0e417a20`), based directly on the reviewed head. It changes 45 values across all 12 locale catalogs plus the changelog count. Per-locale cell counts: ar 4, de 3, es 6, fr 3, hi 2, id 2, ja 4, ko 4, pt-BR 4, vi 5, zh-Hans 4, zh-Hant 4.

## Reconciliation

After this window the exact-hash catalog correction total is 979 values across 238 source keys. The full manual ledger covers 24 disjoint windows / 600 source keys / 7,200 cells: 6,007 keep, 973 correction decisions, and 220 originally uncertain. The separate window20 Realm review resolves 12 uncertain cells. Overall there are 985 correction dispositions (973 manual plus 12 independently resolved): 979 applied and six held for missing exact source context; 208 uncertain values remain unchanged. The frozen preexisting-catalog backlog has 59,880 cells remaining unreviewed.

The post-application verifier reconciles all locale values against the frozen catalog baseline and all applied/held ledgers, rechecks the formal accumulator and manual overlap, and confirms no non-catalog source or workflow change. Semantic confidence is high; locale-quality confidence is moderate; native-speaker review remains outstanding. No tests, builds, CI jobs, releases, or tags were run. The PR must remain open and draft.
