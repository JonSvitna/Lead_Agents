from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(prompt_name: str) -> str:
    return (PROMPTS_DIR / prompt_name).read_text(encoding="utf-8").strip()


def build_agent_instructions(prompt_name: str, include_scoring_rules: bool = False) -> str:
    parts = [load_prompt("master_system_prompt.txt"), load_prompt(prompt_name)]
    if include_scoring_rules:
        parts.append(load_prompt("scoring_rules.txt"))
    return "\n\n".join(parts)