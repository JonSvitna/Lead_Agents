---
name: superpowers-workflow
description: 'Use when you want to apply the obra/superpowers methodology from VS Code: choose the right phase, follow an advisory workflow, and hand off to brainstorming, planning, or verification skills as needed.'
argument-hint: 'What task are you trying to approach with the Superpowers method?'
user-invocable: true
disable-model-invocation: false
---

# Superpowers Workflow

Use this skill when you want to apply the Superpowers way of working inside GitHub Copilot in VS Code.

This is a workspace adaptation of `obra/superpowers`, simplified for GitHub Copilot in VS Code and split into advisory phases rather than strict automation.

## When to Use

- You want a repeatable method for approaching coding tasks.
- You are not sure whether to brainstorm, plan, implement, or verify first.
- The request is large enough that a single freeform edit would be risky.
- You want a VS Code friendly version of the upstream Superpowers workflow.

## Outcome

Produce all of the following before declaring completion:

- A clear phase choice for the current task.
- A short path from ambiguity to implementation.
- One or more focused skill invocations for the current phase.
- A final summary that separates facts, checks, and remaining risk.

## Companion Skills

Use these local skills as the phase-specific counterparts to this overview:

- `superpowers-brainstorming` for refining rough ideas before code changes.
- `superpowers-writing-plans` for turning an approved direction into executable tasks.
- `superpowers-verification-before-completion` for checking the work before declaring it done.

If the task is tiny and obvious, you can skip directly to implementation while still preserving focused validation.

## Procedure

### Step 1: Classify the task

State the requested outcome in one or two sentences, then decide which phase fits best.

Choose the first matching phase:

- Unclear goal or competing options: use `superpowers-brainstorming`.
- Clear direction but non-trivial execution: use `superpowers-writing-plans`.
- Code already changed and you need confidence: use `superpowers-verification-before-completion`.
- Very small and local task: implement directly, then validate.

### Step 2: Set working boundaries

Before editing, identify:

- The likely owning file, symbol, or command.
- The smallest useful validation.
- Whether branch or worktree isolation is warranted.

Treat branch or worktree isolation as recommended for broad refactors, prompt changes, dependency changes, or risky multi-file work.

### Step 3: Run the current phase skill

Invoke the phase-specific skill and follow its procedure.

Keep the workflow advisory:

- Prefer lightweight process over ceremony.
- Ask only the smallest clarifying question that changes the next action.
- Keep edits grounded in the nearest controlling code path.
- Validate after each substantive change when possible.

### Step 4: Reassess after each phase

After brainstorming, either decide the change is ready for implementation or move to `superpowers-writing-plans`.

After planning, execute tasks one by one and keep validation close to the edit.

After implementation, use `superpowers-verification-before-completion` before declaring success.

## Decision Points

Use these branches during execution:

| Situation | Action |
|-----------|--------|
| Goal is still fuzzy after one pass | Continue brainstorming, not coding |
| Direction is clear but work is multi-step | Write a plan before editing |
| Plan step is tiny and local | Implement directly, then validate |
| Validation contradicts the current hypothesis | Step closer to the controlling code |
| Scope expands mid-task | Pause and restate the plan |

## Quality Gates

Do not mark the task complete until these are true:

- The chosen phase matched the actual task.
- The change was grounded in a concrete file, symbol, or failing behavior.
- At least one focused validation was run, or the gap was explicitly stated.
- The final response distinguishes completed work from follow-up ideas.

## Example Prompts

- Use `superpowers-workflow` to decide how to approach a new multi-file feature.
- Use `superpowers-workflow` to apply the Superpowers method to a bug fix in VS Code.
- Use `superpowers-workflow` to decide whether a change needs brainstorming, planning, or just verification.

## Notes

- Upstream Superpowers includes more specialized and stricter skills than this local adaptation.
- This local set is intentionally compact and advisory so it fits VS Code usage without excessive ceremony.