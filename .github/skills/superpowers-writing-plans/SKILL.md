---
name: superpowers-writing-plans
description: 'Use when direction is approved and you want a Superpowers-style implementation plan in VS Code: break the work into concrete steps, tie each step to likely files, and attach a focused verification action.'
argument-hint: 'What approved change should be turned into an execution plan?'
user-invocable: true
disable-model-invocation: false
---

# Superpowers Writing Plans

Use this skill after the direction is clear and before making broad edits.

## When to Use

- The implementation touches multiple files.
- The work is large enough to benefit from sequencing.
- You want validation attached to each major step.
- The task is too big for a single edit without risking drift.

## Outcome

Produce a short execution plan where each step includes:

- The concrete goal.
- Likely files or symbols.
- The smallest useful validation.
- Any dependency or documentation follow-up.

## Procedure

### Step 1: Frame the work

Restate the approved direction.

Identify the core behavior being added, changed, or fixed.

### Step 2: Break it into slices

Create small tasks that can be completed and checked independently.

Prefer tasks that are:

- Narrow in scope.
- Ordered by dependency.
- Easy to validate in isolation.

### Step 3: Add verification to each step

Attach the narrowest possible check to each task.

Examples:

- A targeted unit or behavior test.
- A focused route or command check.
- A compile or lint check for the touched slice.

### Step 4: Check plan quality

Before execution, confirm:

- No task is vague enough to invite broad wandering.
- Validation exists for the risky steps.
- The plan does not assume hidden context.

## Quality Gates

Do not start implementation until:

- The plan is ordered.
- The risky steps have explicit checks.
- The files or code areas are concrete enough to start local routing.

## Example Prompts

- Use `superpowers-writing-plans` to plan a refactor of the scraping and search tools.
- Use `superpowers-writing-plans` to break a new lead qualification flow into testable tasks.
- Use `superpowers-writing-plans` to turn an approved design into a file-by-file execution plan.