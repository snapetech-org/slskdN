# Release-note fragments

For any user-facing change, add one structured fragment under `release-notes/` describing it. A
single fragment may cover related user-facing changes in the same pull request. Keep shipped fragments unchanged.

For internal-only work, no fragment is needed. In a pull request, either select the internal-only
option in the template or put `release-note: none` on its own line in the description. When a
direct push or merge check reads commit messages, put the same marker on its own line in the
commit message.

Each fragment contains YAML-style frontmatter with exactly these fields:

```yaml
---
category: added|changed|fixed|security|removed|deprecated
audience: users, operators
area: lowercase-area-slug
action: none
breaking: false
---
Describe the user or operator impact in 30-400 characters.
```

`audience` may contain `users`, `operators`, or both exactly once. `area` is a
2-32 character lowercase slug. Use `action: none` when no action is required;
breaking changes must describe the upgrade or operator action.

Preview a range locally with:

```sh
python3 scripts/release_notes.py preview --base <base> --head <head>
```

The preview is grouped by category for the GitHub release and Discord
announcement. Pull-request checks also append capture metadata showing the
fragment, audience, area, action, and breaking status.
