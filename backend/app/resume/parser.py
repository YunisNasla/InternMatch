"""Prompt 1: resume text to a Profile (Few-Shot + structured output)."""

import json
from datetime import date

import anthropic

from app.llm import PROMPTS_DIR, SONNET, call_json, load_prompt
from app.schemas import Profile


async def parse_resume(llm: anthropic.AsyncAnthropic, text: str) -> Profile:
    examples = [(e["user"], e["assistant"]) for e in json.loads((PROMPTS_DIR / "parser_examples.json").read_text())]
    return await call_json(
        llm, SONNET, load_prompt("parser_system.txt", today=date.today().isoformat()),
        load_prompt("parser_user.txt", resume_text=text), Profile, label="resume", examples=examples, max_tokens=16000,
    )
