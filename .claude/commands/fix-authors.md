Rewrite git history so every commit's author and committer match the repo's configured git identity.

$ARGUMENTS

---

**Instructions:**

1. Read the target identity from the repo's git config:
   - `git config user.name`
   - `git config user.email`
   - If either is unset, stop and tell the user to configure them first.

2. Audit the current state — run these commands to find all distinct identities:
   - `git log --format='%an <%ae>' | sort -u` (authors)
   - `git log --format='%cn <%ce>' | sort -u` (committers)

3. If the only identity found is already the target identity, report that no rewrite is needed and stop.

4. Show the findings to the user:
   - List every foreign identity with its commit count (`git log --format='%an <%ae>' | sort | uniq -c | sort -rn`)
   - State the target identity that all commits will be rewritten to
   - Ask for explicit confirmation before proceeding

5. Create a backup branch: `git branch backup-before-rewrite`

6. Run the rewrite using `git filter-branch --env-filter` across all branches. The env-filter should unconditionally set all four fields:
   - `GIT_AUTHOR_NAME`
   - `GIT_AUTHOR_EMAIL`
   - `GIT_COMMITTER_NAME`
   - `GIT_COMMITTER_EMAIL`
     to the target identity read in step 1.

7. Verify by re-running the audit from step 2. Confirm only the target identity remains.

8. Clean up:
   - Remove `refs/original/*` refs left by filter-branch (`git for-each-ref --format='%(refname)' refs/original/ | xargs -n 1 git update-ref -d`)
   - Delete the backup branch (`git branch -D backup-before-rewrite`)

9. Print the force-push command the user needs to run, but do **not** execute it:
   ```
   git push --force-with-lease origin <current-branch>
   ```
   Explain that this is destructive and the user should run it manually when ready.
