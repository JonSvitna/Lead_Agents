---
name: superpowers-brainstorming
description: 'Use when a task is still fuzzy and you want the Superpowers-style pre-coding phase in VS Code: clarify goals, compare options, surface risks, and exit with an approach that is ready for planning or implementation.'
argument-hint: 'What idea, bug, or feature needs refinement before coding?'
user-invocable: true
disable-model-invocation: false
---

# Superpowers Brainstorming

Use this skill before writing code when the user request is real but the implementation path is not yet sharp.

## When to Use

- The request is underspecified.
- Multiple implementation approaches look plausible.
- The tradeoffs matter more than raw speed.
- You need agreement on direction before planning or coding.

## Outcome

Exit this phase with:

- A crisp restatement of the problem.
- The best current approach and why it wins.
- The main risks, unknowns, and assumptions.
- A clear next action: plan, implement, or ask one more question.

## Procedure

### Step 1: Restate the problem

Summarize the task in one or two sentences.

List the hard constraints, implied constraints, and unknowns.

### Step 2: Identify options

Generate a short list of realistic options.

For each option, note:

- Why it could work.
- What it costs in complexity, risk, or maintenance.
- What evidence in the codebase would confirm or weaken it.

### Step 3: Compare quickly

Prefer direct, technical comparisons over abstract pros and cons.

Choose the option that best fits the existing codebase, has the smallest risky surface area, and offers a clear validation path.

### Step 4: Exit with a decision

If the direction is clear and multi-step, move to `superpowers-writing-plans`.

If the direction is clear and tiny, implement directly with immediate validation.

If one missing fact blocks the decision, ask one targeted question.

## Quality Gates

Do not leave brainstorming until:

- The preferred option is explicit.
- At least one alternative was considered and rejected.
- The next action is unambiguous.

## Example Prompts

- Use `superpowers-brainstorming` to decide how the lead scoring flow should evolve.
- Use `superpowers-brainstorming` to compare API-first versus agent-first orchestration.
- Use `superpowers-brainstorming` to refine a bug report into a concrete implementation approach.