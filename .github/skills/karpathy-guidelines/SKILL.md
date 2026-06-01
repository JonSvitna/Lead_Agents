---
name: karpathy-guidelines
description: 'Behavioral workflow for coding tasks inspired by Andrej Karpathy observations. Use when implementing, debugging, reviewing, or refactoring code to surface assumptions, avoid overengineering, make surgical changes, and execute against verifiable success criteria.'
argument-hint: 'What coding task should be executed with Karpathy guidelines?'
user-invocable: true
disable-model-invocation: false
---

# Karpathy Guidelines

Use this skill to reduce common LLM coding mistakes with a strict, repeatable process for every task.

## When to Use

- You are about to implement or modify code and want fewer wrong assumptions.
- The request is ambiguous and could be interpreted in multiple ways.
- There is risk of overengineering or broad refactors.
- You need a crisp, verifiable definition of done.

## Workflow

Run all four steps for every task. Do not skip steps, even for small edits.

### Step 1: Think Before Coding

Before writing code:

- State key assumptions explicitly.
- If multiple interpretations exist, present options instead of silently choosing one.
- If unclear details block correctness, ask focused clarification questions.
- If a simpler path exists, propose it.

Exit criteria for this step:

- Scope, constraints, and target behavior are explicit enough to proceed.

### Step 2: Simplicity First

Choose the minimum solution that solves the current request:

- Do not add features that were not requested.
- Avoid abstractions for one-off behavior.
- Avoid speculative flexibility and configuration.
- Do not add defensive logic for impossible scenarios.

Decision point:

- If the solution feels heavy, rewrite it simpler before continuing.

### Step 3: Surgical Changes

When editing existing code:

- Touch only the lines required for the requested behavior.
- Match existing local style and conventions.
- Do not refactor or reformat adjacent code unless required.
- Remove only artifacts made obsolete by your own changes.

Quality check:

- Every changed line should trace directly to the user request.

### Step 4: Goal-Driven Execution

Convert the request into verifiable checks:

- Bug fix: first reproduce with a failing automated test, then make it pass.
- Feature: define acceptance checks and confirm they pass.
- Refactor: verify behavior is unchanged before and after.

If an automated bug test is temporarily impossible, record the technical blocker and use a deterministic manual repro until a test can be added.

For non-trivial work, use this structure:

1. Step and change.
2. Verification for that step.
3. Repeat until all criteria pass.

## Decision Branches

- Ambiguous task: pause and clarify before coding.
- Simple and local task: still run all four workflow steps, but keep each step brief.
- Multi-step task: publish a short plan with per-step verification.
- Failed verification: adjust only the nearest relevant code path, then re-check.

## Completion Criteria

Do not declare done until all are true:

- Assumptions and ambiguities were surfaced.
- Implementation is minimal for current requirements.
- Diff is narrow and request-aligned.
- All four workflow steps were explicitly completed.
- Success criteria were verified or any validation gap is explicitly documented.

## Example Prompts

- Use karpathy-guidelines to fix this API bug with a test-first loop.
- Apply karpathy-guidelines to implement this feature with minimal code.
- Review this diff with karpathy-guidelines and call out non-surgical edits.

## Tradeoff

This workflow biases toward correctness and minimal diffs over raw speed.