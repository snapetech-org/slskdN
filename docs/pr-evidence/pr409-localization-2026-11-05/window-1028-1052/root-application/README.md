# Guarded exact-hash application

The apply script verifies all 300 root rows, all 44 selected target hashes, all 12 catalog file hashes, and every hash-only hold before writing. The 12 callerless cells stay text-free in the final readback.

The recorded preflight and application used the clean input worktree at `624e27d8bb108a764df6daab5cfb1c517ebac96d`. Product commit `acbb05f03a858c6b4f3d67bdc431fc3a2b802e6f` has tree `a99f9ef3e00854e77ac7a2a84bddab4e79356184`; `product-pin.json` records the final catalog hashes. Post-commit verification read back all 300 cells and confirmed each complete catalog matches the pinned product commit.

For a replay from the exact input head:

```sh
python3 -B apply_root_application.py --repo /path/to/slskdN --preflight
python3 -B apply_root_application.py --repo /path/to/slskdN --apply
```

After committing the catalogs and recording the product pin, run:

```sh
python3 -B apply_root_application.py --repo /path/to/slskdN --verify-after
```
