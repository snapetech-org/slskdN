# Agent Instructions for slskdN

> This file defines how AI coding assistants should behave in this repository.

---

## Communication style

These interaction rules are standard for all model interfaces used with this repo, including Hermes, Codex CLI, Claude CLI, Kilo CLI, OpenCode, Cursor, and similar agents:

- Never praise questions or validate premises before answers.
- If the user is wrong, say so immediately and directly.
- Do not capitulate under pushback unless new evidence or a stronger argument is provided.
- Do not anchor on numbers or estimates provided by the user. Generate an independent assessment first, then compare.
- Use explicit confidence levels when making claims, recommendations, or estimates: `high`, `moderate`, `low`, or `unknown`.
- Do not add disclaimers.
- Do not give ethics lectures unless explicitly asked.
- Do not use "it is important to consider" style hedges.
- Surface negative conclusions and bad news directly.
- Optimize for accuracy, not approval.
- If you do not know, say so. Never fabricate.

## Release-note contract

Do not let user-facing behavior, security changes, operational changes, or
user-facing documentation changes reach a release without a new validated
fragment under `release-notes/`. Fragments are append-only and must capture the
audience, product area, required action (or `none`), and breaking-change status.
Internal-only work must be explicitly marked in the pull request. Preview the
range with `python3 scripts/release_notes.py preview --base <base> --head <head>`.

## 🚨 CRITICAL: Document Bugs You Fix

**If you fix a bug caused by your own implementation (or any implementation), IMMEDIATELY add it to `memory-bank/decisions/adr-0001-known-gotchas.md`.**

This is **highest priority** - do it before moving on to other work.

### When to document:
- You fixed a bug you or another AI introduced
- You fixed the same type of bug twice
- You discovered a pattern that causes crashes/errors
- You found a "gotcha" that isn't obvious

### How to document:
1. Open `memory-bank/decisions/adr-0001-known-gotchas.md`
2. Add entry under appropriate section (Critical/High/Accidental Cycles)
3. Include: What went wrong, why, and how to prevent it
4. Commit immediately with message: `docs: Add gotcha for [brief description]`

**Do NOT wait until end of session. Do NOT skip this step. Future you will thank past you.**

---

## Before Starting ANY Work

### Required Reading (in order)

1. **`docs/README.md`** - Current documentation index
2. **`memory-bank/decisions/adr-0001-known-gotchas.md`** - Critical bugs to avoid
3. **`memory-bank/decisions/adr-0002-code-patterns.md`** - Exact patterns to follow
4. **`memory-bank/decisions/adr-0003-anti-slop-rules.md`** - What NOT to do
5. **`docs/dev/testing-policy.md`** - Test selection, safe local execution, and release-gate scope
6. **`memory-bank/activeContext.md`** - Current session state

### Before Writing Code

```bash
# ALWAYS grep for existing patterns first
grep -rn "similar pattern" src/slskd/
grep -rn "similar component" src/web/src/components/
```

If you skip this step, you WILL generate slop.

---

## Core Principles

### Fork Boundary And GitHub Targeting

**This workspace writes to `snapetech/slskdN`, not upstream `slskd/slskd`.**

- Treat upstream `slskd/slskd` as read-only reference only
- Never comment on, close, label, review, or otherwise modify upstream issues / PRs from this repo workspace
- Before any GitHub issue / PR / release action, run `./scripts/verify-github-target.sh`
- Prefer passing the repo explicitly to GitHub tooling when possible (`snapetech/slskdN`)
- If the target repo is ambiguous, stop and resolve it before taking any write action

### Local Identity Privacy

**Never include private local hostnames, local OS usernames, home-directory paths, or operator-specific machine names in commit messages, changelogs, release notes, public docs, or GitHub release text.**

- Use generic wording such as "live validation host", "test host", "operator account", or "local checkout"
- Do not mention deployment hostnames, workstation names, shell usernames, or paths like `/home/<user>`
- `scripts/check-local-identity-leaks.sh` is part of the release/remediation gate and blocks known local identifiers from release-facing text and recent commit messages
- CI can pass extra private denylist terms through the `SLSKDN_LOCAL_IDENTITY_DENYLIST` GitHub secret; local-only terms can live in an untracked file such as `.local/identity-denylist.txt` and be passed with `SLSKDN_LOCAL_IDENTITY_DENYLIST_FILE`

### Network Health First 🌐

**slskdn prioritizes Soulseek network health in ALL design decisions.**

- Features like passive FLAC discovery, backfill scheduling, and hash probing are **intentionally conservative**
- When implementing features that contact remote peers (browsing, downloading headers, probing files):
  - Always consider **rate limiting** and **bandwidth impact**
  - Be a **good network citizen** - don't overwhelm peers
  - **Manual triggers** (like buttons) are preferred over automatic aggressive scanning
  - Give users **control** over network impact

### UI Buttons Need Tooltips 💬

Every button must have a helpful mouseover tooltip (using Semantic UI's `Popup` component) explaining:
- What the button does
- Why a user might want to click it

---

## During Development

### Code Style

**Backend (C#)**:
- Follow existing patterns in `src/slskd/`
- Use file-scoped namespaces (C# 10+)
- Use `_privateField` naming for injected dependencies
- Prefer `ILogger<T>` over `Serilog.Log.ForContext`
- Run `./bin/lint` before committing

**Frontend (React/JSX)**:
- Follow patterns in `src/web/src/components/`
- Use Semantic UI React components
- Maintain compatibility with the React major version declared in `src/web/package.json`
- Keep state management simple (no Redux unless already used)
- **Never introduce lint errors.** Fix any lint issues immediately before running builds/tests. Avoid disabling lint rules unless there is a documented, unavoidable reason.

### Copyright Headers [[memory:11969255]]

**New files for slskdN features**:
```csharp
// <copyright file="MyNewFeature.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
```

**Existing upstream files**: Keep original `company="slskd Team"` attribution.

**Fork-specific directories** (always use slskdN headers):
- `Capabilities/`
- `HashDb/`
- `Mesh/`
- `Backfill/`
- `Transfers/MultiSource/`
- `Transfers/Ranking/`
- `Users/Notes/`

---

## After Completing Work

### 1. Deferred and Follow-up (plan-driven work)

When the work comes from a plan that has a **Deferred and Follow-up Work** table (e.g. `docs/dev/40-fixes-plan.md`):

- **If you intentionally leave out** optional, out-of-scope, or “do later” items: **add a row** to that table before considering the PR/task done. Columns: **Source** (e.g. PR-08), **Item** (short name), **Action** (what to do).
- **If nothing was left out** for that PR/item, no new deferred row is needed.
- **When you later complete a deferred item:** remove that row from the Deferred table and do the usual doc updates below (progress, tasks, activeContext).

### 2. Docs to update on completion

| Doc | When / What |
|-----|-------------|
| **`docs/dev/40-fixes-plan.md`** | If doing dev/40-fixes work: Deferred table (add rows for left-out work; remove rows when deferred items are completed). Update checklists or Implementation Ticket Index if the plan has them. |
| **`config/slskd.example.yml`** | If you added or changed options: add or update the commented example. |
| **`memory-bank/tasks.md`** | Mark task complete with date; add any new follow-up tasks. |
| **`memory-bank/progress.md`** | Append a short, timestamped summary of what was done; note surprises or decisions. |
| **`memory-bank/activeContext.md`** | Clear the current task if finished; set “Next Steps”. |

### 3. Validation and lint

- Read `docs/dev/testing-policy.md` before selecting a validation path.
- The repository validation engine owns test discovery, task selection, isolation, receipts, and result accounting. Use the entry points documented there; `--plan` is discovery only.
- Local planning and test tasks for an unreviewed branch must run through the trusted Linux bubblewrap launcher described by the testing policy. Use a launcher copied from a reviewed revision outside the checkout.
- For code that is release-ready or is gating CI, use the documented release gate. Run focused tests for changed behavior inside the trusted disposable environment when available.
- Do not run tests against live configuration, credentials, accounts, queues, libraries, or databases. Use the disposable fixtures created by the test suite.
- A plan does not prove tests ran. Report actual task execution, native case totals, skips, exclusions, blocked tasks, and missing prerequisites separately.
- Run `./bin/lint` for code changes. For documentation-only changes, run `git diff --check` and applicable documentation checks; do not report code tests that were not run.
- If the trusted launcher or pinned toolchain is unavailable, report the specific unavailable prerequisite and rely on the pull-request hosted validation. Do not claim a complete local gate.
- Record visual inspection separately from automated results. A build or source check does not prove the rendered interface works.

## Decision Records

For significant architectural decisions:
1. Create `memory-bank/decisions/adr-NNNN-title.md`
2. Use the ADR template format (Context, Decision, Consequences)
3. Reference the ADR in relevant code comments

---

## What NOT To Do

See `memory-bank/decisions/adr-0003-anti-slop-rules.md` for the full list.

**Critical**:
- ❌ **Stubs, placeholders, or `NotImplementedException`** (create tasks in `memory-bank/tasks.md` instead)
- ❌ Factory/wrapper/builder patterns (use DI directly)
- ❌ Defensive null checks on internal code
- ❌ Swallowing exceptions with catch-return-null
- ❌ Logging method entry/exit
- ❌ `async Task.FromResult()` for sync operations
- ❌ Class components in React (use function + hooks)
- ❌ Returning `undefined` from API lib functions (return `[]`)
- ❌ `async void` without try-catch (crashes the process)

**General**:
- Don't silently overwrite human-written notes; append with timestamps
- Don't create new abstractions without checking if similar patterns exist
- Don't add dependencies without documenting why
- Don't break API compatibility with upstream slskd
- Don't modify upstream files unnecessarily (prefer extending)

---

## Release and package build boundaries

- `ci.yml` runs for pull requests targeting `main`, version-tag pushes, and manual dispatch. It does not run for ordinary branch pushes.
- `build-on-tag.yml` runs for `build-main-*` and `build-dev-*` tags and manual dispatch. Separate package and release workflows run on published GitHub releases or their own manual dispatch; inspect each workflow's current triggers before relying on it.
- Read `docs/dev/release-checklist.md`, `memory-bank/decisions/adr-0005-tagging-system.md`, and the current workflow definitions for release formats and required steps.
- Do not create tags, publish packages or artifacts, release, or announce without explicit maintainer authorization. A request to commit, push, or open a PR does not authorize those actions.
- Do not change workflow triggers solely to make validation run. Use `docs/dev/testing-policy.md` and the repository validation engine for PR and release checks.

## Quick Reference

| Action | Command |
|--------|---------|
| Run backend | `./bin/watch` |
| Run frontend | `pnpm --filter @slskdn/web start` |
| Run tests | Validation engine through the trusted launcher; see docs/dev/testing-policy.md |
| Lint | `./bin/lint` |
| Build release | `./bin/build` |

## Key repository files

| File | Purpose |
|------|---------|
| `memory-bank/decisions/adr-0001-known-gotchas.md` | **READ FIRST** - Critical bugs |
| `memory-bank/decisions/adr-0002-code-patterns.md` | **READ FIRST** - Exact patterns |
| `memory-bank/decisions/adr-0003-anti-slop-rules.md` | **READ FIRST** - What not to do |
| `memory-bank/decisions/adr-0004-pr-checklist.md` | Pre-commit validation |
| `memory-bank/projectbrief.md` | Project overview & constraints |
| `memory-bank/tasks.md` | Task backlog (source of truth) |
| `memory-bank/activeContext.md` | Current work context |
| `memory-bank/progress.md` | Work log |
| `memory-bank/scratch.md` | Temporary notes, commands |
| `docs/dev/40-fixes-plan.md` | dev/40-fixes security plan; **Deferred and Follow-up Work** table — add rows when leaving work out; remove when completing deferred items. See AGENTS.md § After Completing Work. |
| `docs/archive/FORK_VISION.md` | Feature roadmap |
| `docs/archive/DEVELOPMENT_HISTORY.md` | Release history |
