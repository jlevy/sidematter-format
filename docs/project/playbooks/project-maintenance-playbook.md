---
title: Project Maintenance Playbook
description: Full maintenance cycle — template upgrade, dependency upgrades, lint/test/build, engineering review, PR with CI
category: review
---
End-to-end project maintenance: upgrade the copier template, upgrade all deps,
verify everything is clean, perform a full engineering review, push a PR, and
monitor CI.

Reference: [docs/development.md](../../development.md) for dev workflows and
Makefile targets.

## Instructions

Create a to-do list from the steps below, then execute each one. Commit after
each logical group of changes (not one giant commit).

### 1. Upgrade copier template

```bash
copier update --defaults --trust
```

- Resolve any merge conflicts in `pyproject.toml` or other files.
- Review every changed file — don't blindly accept. Verify docs moves, deleted
  files, and config changes make sense.
- Commit with a message listing key template changes.

### 2. Upgrade all dependencies

```bash
make upgrade   # uv sync --upgrade --all-extras --dev
```

- Commit the updated `uv.lock` (and `pyproject.toml` if bounds changed).

### 3. Verify everything is clean

```bash
make            # install + lint + test
uv build        # confirm wheel builds
```

- If lint or type-check fails after upgrades, fix issues before proceeding.

### 4. Full engineering review

Load guidelines, then review **all source files** (not just the diff):

```bash
tbd guidelines general-coding-rules
tbd guidelines general-comment-rules
tbd guidelines error-handling-rules
tbd guidelines general-testing-rules
tbd guidelines python-rules
tbd guidelines python-modern-guidelines
```

Check for:

- Broken, stale, or incomplete docstrings
- Inconsistent behavior between similar functions (e.g. trailing newlines,
  error handling conventions)
- Type annotation gaps or `Any` leaks
- Dead code, stale TODO comments, unnecessary abstractions
- Security issues at system boundaries

Fix issues found, run `make` again, commit.

### 5. Second review pass

Re-read the full branch diff (`git diff origin/main...HEAD`) as a final
sanity check. Confirm no regressions, no files accidentally deleted, and
commit messages are clean.

### 6. Push and create PR

```bash
git push -u origin <branch>
```

Create PR via `gh pr create` with:

- Bullet-point summary of each commit group
- Test plan checklist (tests, lint, build, CI matrix)

### 7. Monitor CI and address review comments

```bash
gh pr checks <number> --watch
```

- **Wait for all jobs to finish.** Do not report success until confirmed.
- If CI fails: fix, re-run `make`, commit, push, re-watch.
- Check for review comments (`gh pr view`, `gh api .../pulls/<n>/comments`).
  Address each comment, balancing severity against maintainability.
