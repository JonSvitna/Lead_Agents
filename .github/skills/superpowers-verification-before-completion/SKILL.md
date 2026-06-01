---
name: superpowers-verification-before-completion
description: 'Use when implementation appears finished and you want the Superpowers-style final review in VS Code: run focused checks, look for gaps between the request and the result, and report remaining risk clearly.'
argument-hint: 'What completed change should be verified before sign-off?'
user-invocable: true
disable-model-invocation: false
---

# Superpowers Verification Before Completion

Use this skill after implementation and before declaring the task complete.

## When to Use

- Code changes are done but confidence is not yet earned.
- You need to check behavior, not just diff shape.
- The request had edge cases or subtle constraints.
- The environment limits full testing and you need a precise risk statement.

## Outcome

Produce:

- The validations that were actually run.
- Any mismatch between the requested behavior and the current result.
- Remaining risks, assumptions, or untested paths.
- A concise go/no-go summary.

## Procedure

### Step 1: Re-read the request

Compare the implemented behavior to the actual request, not to the plan alone.

### Step 2: Run focused checks

Prefer in this order:

1. The cheapest behavior-scoped check that can falsify success.
2. A narrow test for the touched slice.
3. A narrow compile, lint, or type check.
4. Diff review only if no executable validation exists.

### Step 3: Look for quiet regressions

Check whether the change:

- Broke adjacent call sites.
- Changed config, prompts, or docs that now need updates.
- Added assumptions that are not enforced anywhere.

### Step 4: Report with precision

State clearly:

- What is verified.
- What is likely but unverified.
- What still needs user attention.

## Quality Gates

Do not sign off until:

- At least one focused validation was run, or the lack of one was explained.
- The request-to-result comparison is explicit.
- Remaining risk is separated from completed work.

## Example Prompts

- Use `superpowers-verification-before-completion` to check a completed API change.
- Use `superpowers-verification-before-completion` before closing a bug fix.
- Use `superpowers-verification-before-completion` to make sure a refactor did not silently widen scope.