"""Claude calls: prompt loading, JSON validation with one retry."""

import json
import logging
import re
from pathlib import Path

import anthropic
from pydantic import BaseModel, ValidationError

from app import taxonomy
from app.config import settings

log = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
HAIKU = "claude-haiku-5-5"
# shortcut: posting text sent to the taggers and the scorer is cut here; raise it if late requirements get missed.
MAX_DESCRIPTION = 6000
SONNET = "claude-sonnet-5-5"

TAXONOMY_VARS = {
    "role_types": ", ".join(taxonomy.ROLE_TYPES),
    "role_types_with_non_stem": ", ".join([*taxonomy.ROLE_TYPES, taxonomy.NON_STEM]),
    "industries": ", ".join(taxonomy.INDUSTRIES),
    "industries_with_other": ", ".join([*taxonomy.INDUSTRIES, taxonomy.OTHER]),
    "supported_terms": ", ".join(f'"{t}"' for t in taxonomy.SUPPORTED_TERMS),
}
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class LLMError(Exception):
    """The model's output failed validation twice."""


def load_prompt(name: str, **values: str) -> str:
    """A prompt file with its placeholders filled in one pass, so filled-in text is never re-scanned."""
    values = {**TAXONOMY_VARS, **values}
    text = (PROMPTS_DIR / name).read_text()
    return _PLACEHOLDER.sub(lambda m: values.get(m[1], m[0]), text)


def load_examples(name: str) -> list[tuple[str, str]]:
    """Few-shot examples as (user, assistant) pairs."""
    return [(e["user"], e["assistant"]) for e in json.loads((PROMPTS_DIR / name).read_text())]


def client() -> anthropic.AsyncAnthropic:
    # The SDK default waits 10 minutes per try; a stuck call must fail fast so search can fall back to the cache.
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None, timeout=60, max_retries=1)


async def call_json[T: BaseModel](
    llm: anthropic.AsyncAnthropic, model: str, system: str, user: str, schema: type[T],
    *, label: str, effort: str | None = None, max_tokens: int = 4000, examples: list[tuple[str, str]] = (),
) -> T:
    """One call validated against `schema`, retried once with the error appended. `label` is logged, never content.

    Few-shot `examples` go first as alternating user and assistant turns (PROMPTS.md rules for every call).
    """
    messages: list[dict] = [
        {"role": role, "content": text} for pair in examples for role, text in zip(("user", "assistant"), pair)
    ]
    messages.append({"role": "user", "content": user})
    extra = {"output_config": {"effort": effort}} if effort else {}
    for attempt in (1, 2):
        response = await llm.messages.create(model=model, system=system, messages=messages, max_tokens=max_tokens, **extra)
        log.info("llm %s %s: %s in, %s out", label, model, response.usage.input_tokens, response.usage.output_tokens)
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        try:
            return schema.model_validate(json.loads(_FENCE.sub("", text)))
        except (json.JSONDecodeError, ValidationError) as error:
            if attempt == 2:
                raise LLMError(f"{label}: output failed validation twice") from error
            messages += [
                {"role": "assistant", "content": text or "(empty)"},
                {"role": "user", "content": load_prompt("retry.txt", error=str(error))},
            ]
    raise AssertionError("unreachable")
