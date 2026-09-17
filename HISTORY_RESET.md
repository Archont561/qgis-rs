# How to Reset Git History

This document explains how to reset the repository history to start fresh with a single initial commit.

## Why Reset History?

You might want to reset history if:

- The current history contains sensitive information (secrets, credentials)
- You want to start with a clean slate
- The history is messy (many experimental commits)
- You're preparing for a public release

## ⚠️ Warning

**This is a destructive operation.** You will lose all commit history. Make sure you:

1. Have a backup of the current repository
2. Have coordinated with all collaborators
3. Understand that this will break existing clones/forks

## Method 1: Orphan Branch (Recommended)

This method creates a new branch with no history, then replaces `main`.

### Steps

```bash
# 1. Create a backup
cd ..
cp -r qgis-rs qgis-rs-backup
cd qgis-rs

# 2. Create an orphan branch (no history)
git checkout --orphan new-main

# 3. Stage all files
git add -A

# 4. Create initial commit
git commit -m "Initial commit: qgis-rs - Safe Rust bindings for QGIS"

# 5. Delete old main branch
git branch -D main

# 6. Rename new branch to main
git branch -m main

# 7. Force push to remote (this will overwrite remote history)
git push -f origin main

# 8. Clean up old references
git gc --prune=now
```

### What This Does

- Creates a new branch with no parent commits (orphan)
- Commits all current files as a single initial commit
- Replaces the `main` branch with this new branch
- Force-pushes to remote, overwriting the old history

## Method 2: Squash All Commits

This method keeps one commit with all changes squashed together.

### Steps

```bash
# 1. Create a backup
cd ..
cp -r qgis-rs qgis-rs-backup
cd qgis-rs

# 2. Find the first commit
FIRST_COMMIT=$(git rev-list --max-parents=0 HEAD)

# 3. Reset to before the first commit (keeps all files)
git reset --soft $FIRST_COMMIT^

# 4. Amend the first commit with all changes
git commit --amend -m "Initial commit: qgis-rs - Safe Rust bindings for QGIS"

# 5. Force push to remote
git push -f origin main

# 6. Clean up
git gc --prune=now
```

### What This Does

- Resets to the state before the first commit
- Amends the first commit to include all changes
- Results in a single commit with all files

## Method 3: Fresh Repository

This method creates a completely new repository.

### Steps

```bash
# 1. Create a backup
cd ..
cp -r qgis-rs qgis-rs-backup

# 2. Remove .git directory
cd qgis-rs
rm -rf .git

# 3. Initialize new repository
git init
git add -A
git commit -m "Initial commit: qgis-rs - Safe Rust bindings for QGIS"

# 4. Add remote
git remote add origin https://github.com/Archont561/qgis-rs.git

# 5. Force push to remote
git push -f origin main

# 6. Clean up
git gc --prune=now
```

### What This Does

- Removes all git history
- Creates a brand new repository
- Commits all files as initial commit
- Force-pushes to remote

## After Resetting History

### Update Local Clones

All collaborators must reset their local clones:

```bash
# Option 1: Delete and re-clone
cd ..
rm -rf qgis-rs
git clone https://github.com/Archont561/qgis-rs.git

# Option 2: Reset existing clone (if no local changes)
cd qgis-rs
git fetch origin
git reset --hard origin/main
git clean -fd
```

### Update Forks

Forks will be out of sync. Fork owners must:

```bash
# Delete and re-fork, or:
git fetch upstream
git reset --hard upstream/main
git push -f origin main
```

### Update CI/CD

If you use branch protection rules or required status checks:

1. Temporarily disable branch protection
2. Force push the reset history
3. Re-enable branch protection

### Update References

Update any references to specific commits:

- Documentation links to commits
- CI/CD configurations
- Deployment scripts
- Issue/PR references

## Verification

After resetting, verify the history:

```bash
# Should show only one commit
git log --oneline

# Should match remote
git log origin/main --oneline

# Should have no dangling objects
git fsck --full
```

## Troubleshooting

### "refusing to update checked out branch"

If you get this error when force-pushing:

```bash
# Make sure you're on main
git checkout main

# Force push again
git push -f origin main
```

### "updates were rejected because the tip of your current branch is behind"

This means the remote has commits you don't have. Force push anyway:

```bash
git push -f origin main
```

### Lost Important Commits

If you realize you lost important commits:

```bash
# Check the backup
cd ../qgis-rs-backup
git log --oneline

# Cherry-pick commits from backup
cd ../qgis-rs
git remote add backup ../qgis-rs-backup
git fetch backup
git cherry-pick <commit-hash>
```

### Large Repository Size

If the repository is still large after reset:

```bash
# Remove all unreachable objects
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Check size
du -sh .git
```

## Best Practices

1. **Always backup first** — Keep a copy of the old repository
2. **Coordinate with team** — Make sure everyone knows about the reset
3. **Update documentation** — Remove references to old commits
4. **Test thoroughly** — Make sure everything still works after reset
5. **Consider alternatives** — Maybe you just need to squash recent commits, not reset everything

## Alternatives to Full Reset

### Squash Recent Commits Only

```bash
# Squash last 10 commits into one
git reset --soft HEAD~10
git commit -m "Squash: implement feature X"
git push -f origin main
```

### Interactive Rebase

```bash
# Interactively rebase last 20 commits
git rebase -i HEAD~20

# Mark commits as 'squash' or 'fixup' to combine them
# Save and exit editor
git push -f origin main
```

### Create a New Branch

Instead of resetting `main`, create a new branch:

```bash
git checkout --orphan v1.0
git add -A
git commit -m "v1.0 release"
git push origin v1.0
```

## Resources

- [Git Documentation: git-checkout](https://git-scm.com/docs/git-checkout#Documentation/git-checkout.txt---orphanltnewbranchgt)
- [Git Documentation: git-reset](https://git-scm.com/docs/git-reset)
- [Atlassian: Rewriting History](https://www.atlassian.com/git/tutorials/rewriting-history)
- [GitHub: Changing a commit message](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/changing-a-commit-message)

---

**Last Updated**: September 17, 2026
