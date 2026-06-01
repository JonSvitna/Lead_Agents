# Project Guidelines

## Workflow

For non-trivial tasks, prefer the local Superpowers skill set before broad editing:

- Use `superpowers-workflow` to choose the right phase.
- Use `superpowers-brainstorming` when the request or implementation path is still fuzzy.
- Use `superpowers-writing-plans` when the direction is clear but the work spans multiple steps or files.
- Use `superpowers-verification-before-completion` before declaring larger changes done.

For tiny, local tasks, work directly from the nearest controlling file or symbol and keep validation close to the edit.

## Architecture

This repository is a Python lead-intelligence backend centered on the `sentinel_lead_agent/` package.

Key areas:

- `sentinel_lead_agent/main.py` is the current entrypoint.
- `sentinel_lead_agent/agents/` contains the agent orchestration modules.
- `sentinel_lead_agent/api/` contains API routes.
- `sentinel_lead_agent/models/` contains data models.
- `sentinel_lead_agent/services/` contains service integrations such as OpenAI.
- `sentinel_lead_agent/tools/` contains reusable tools such as scraping, search, and scoring.
- `sentinel_lead_agent/prompts/` contains prompt text that should stay aligned with the corresponding agent behavior.

When changing agent behavior, check both the Python module and the related prompt file.

## Conventions

Keep changes modular and localized to the owning layer.

- Put orchestration logic in `agents/`, not in route handlers.
- Keep integration details in `services/` or `tools/` rather than spreading them across agents.
- Update prompt files when an agent's responsibilities, inputs, or outputs change.
- Preserve the existing simple Python style and avoid introducing framework-heavy abstractions without a clear need.

## Build and Test

Primary dependencies live in `sentinel_lead_agent/requirements.txt`.

When validation is possible, prefer the narrowest check for the touched slice. If Python execution is unavailable in the environment, rely on editor diagnostics and state that limitation explicitly.