## Merge

Use `main` as the target. Open a pull request only when current GitHub rules require one; push directly
when they allow it. Keep a pull request current with `main` only when those rules require it. Merge
after the checks and approvals required by current rules are satisfied. An explicit maintainer's
direction to merge is sufficient; no additional review or approval is required beyond those rules.
Use any merge method enabled in GitHub.

## Release Notes

For any user-facing change, add one structured fragment under `release-notes/` describing it. A
single fragment may cover related user-facing changes in the same pull request.

- [ ] I added a validated release-note fragment under `release-notes/` for this user-facing change.
- [ ] This change is internal-only and needs no release-note fragment.

For internal-only work, select the second option or put `release-note: none` on its own line in
the PR description. For direct pushes or merge checks that read commit messages, put the same
marker on its own line in the commit message.

Preview the rendered release text with `python3 scripts/release_notes.py preview` if useful.

## Testing

Describe the validation performed for this change.
