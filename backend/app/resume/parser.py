"""Prompt 1: resume text to a Profile (Few-Shot + structured output)."""

from datetime import date

import anthropic

from app.llm import SONNET, call_json, load_examples, load_prompt
from app.schemas import Profile


async def parse_resume(llm: anthropic.AsyncAnthropic, text: str) -> Profile:
    return await call_json(
        llm, SONNET, load_prompt("parser_system.txt", today=date.today().isoformat()),
        load_prompt("parser_user.txt", resume_text=text), Profile, label="resume", examples=load_examples("parser_examples.json"),
        max_tokens=16000,
    )
