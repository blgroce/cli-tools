# Bug Mode

Focus: Find root cause, fix properly, prevent regression.

## Guidelines

- Read the bug description carefully
- Reproduce the issue first (if possible)
- Identify the root cause before fixing
- Fix the underlying issue, not just symptoms
- Consider edge cases that might cause similar bugs

## Verification

- Confirm the bug is fixed
- Ensure no regression in related functionality
- Run existing tests
- Add a test for the bug if appropriate

## Commit Style

```
git commit -m "fix: [what was broken and how it was fixed]"
```
