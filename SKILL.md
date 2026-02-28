---
name: recent-changes-first
description: Use when encountering any error message, test failure, build breakage, or unexpected behavior before proposing a fix or writing any code
---

# Recent Changes First

## Overview

Before writing any fix, check recent git history. Many bugs are immediately explained by "oh, we just changed X." This saves hours of unnecessary debugging.

## The Protocol

When you encounter any error, test failure, or unexpected behavior:

1. **FIRST — check recent changes:**
   ```bash
   git log --oneline -10
   git diff HEAD~1
   ```
   Or diff against the last known-good commit/tag. Ask yourself: does any recent change obviously explain this error?

2. **SECOND — read the error location:**
   Read the failing file/line and surrounding context.

3. **ONLY THEN — write a fix.**

## Red Flags (You're About to Skip This)

| Thought | Reality |
|--------|---------|
| "I know what's wrong" | Check git first. You might be wrong. |
| "This is obviously X" | Verify. Many "obvious" diagnoses waste hours. |
| "Let me just look at the error" | Git history is 10 seconds. Do it first. |
| "The error message is clear" | The cause may still be a recent change. |

## Why This Matters

Skipping this step is the most common source of wasted debugging time. A recent refactor, config change, or dependency bump will cause errors that look like deep bugs but are trivially obvious once you see the commit.

**Real examples of what this catches immediately:**
- A flag changed from `true` to `false` → tests expect old behavior
- A struct field was renamed → read at wrong offset
- A dependency was bumped → API changed silently
- A default was changed → downstream test assumptions break

## Common Mistake

Running `git diff HEAD~1` and only skimming it. Read the diff carefully, especially changes to structs, defaults, flags, and config values — these are the most common sources of cascading test failures.
