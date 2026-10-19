"""Prompt 4 (iterative refinement): the model proposes filter changes, code checks and applies them."""

import json

import anthropic
from pydantic import ValidationError

from app.llm import PROMPTS_DIR, SONNET, call_json, load_prompt
from app.matching import distance
from app.schemas import REFINE_FIELDS, FilterState, RefineChange, RefineResult

CITY_NOT_FOUND = "I couldn't find {city}, so your home city didn't change. Try 'City, ST'."


def _apply_one(state: FilterState, c: RefineChange) -> FilterState | None:
    """The state after one change, or None when the change is invalid."""
    actions, _ = REFINE_FIELDS[c.field]
    current = getattr(state, c.field)
    if c.action not in actions:
        return None
    if c.action == "set":
        value = c.value
    elif isinstance(c.value, list | dict):  # add and remove take one item
        return None
    elif c.action == "add":
        value = current if c.value in current else [*current, c.value]
    elif c.value in current:
        value = [v for v in current if v != c.value]
    else:
        return None
    try:
        return FilterState.model_validate({**state.model_dump(), c.field: value})
    except ValidationError:
        return None


def apply_changes(
    state: FilterState, changes: list[RefineChange], mode: str,
) -> tuple[FilterState, list[RefineChange], list[RefineChange], str | None]:
    """(new state, applied, dropped, home city that couldn't be found). Each change is checked against the state so far."""
    applied, dropped, missing_city = [], [], None
    for c in changes:
        known = c.field in REFINE_FIELDS
        if not known or (mode == "initial" and not REFINE_FIELDS[c.field][1]):
            dropped.append(c)
            continue
        if c.field == "home_city" and c.value is not None and distance.lookup(str(c.value)) is None:
            dropped.append(c)
            missing_city = str(c.value)
            continue
        new = _apply_one(state, c)
        if new is None:
            dropped.append(c)
        else:
            state = new
            applied.append(c)
    return state, applied, dropped, missing_city


def fix_reply(reply: str, applied: list[RefineChange], dropped_city: str | None) -> str:
    """The model wrote its reply before code checked the city, so code corrects it."""
    if not dropped_city:
        return reply
    message = CITY_NOT_FOUND.format(city=dropped_city)
    return f"{reply} {message}" if applied else message


async def refine(
    llm: anthropic.AsyncAnthropic, mode: str, state: FilterState, message: str,
    results_summary: str = "", recent_turns: str = "",
) -> dict:
    examples = [(e["user"], e["assistant"]) for e in json.loads((PROMPTS_DIR / "refine_examples.json").read_text())]
    user = load_prompt(
        "refine_user.txt", mode=mode, filter_state_json=state.model_dump_json(indent=2),
        results_summary=results_summary, recent_turns=recent_turns, user_message=message,
    )
    result = await call_json(
        llm, SONNET, load_prompt("refine_system.txt"), user, RefineResult, label=f"refine:{mode}", examples=examples,
    )
    new_state, applied, dropped, missing_city = apply_changes(state, result.changes, mode)
    return {
        "intent": result.intent, "changes": applied, "dropped": dropped,
        "reply": fix_reply(result.reply, applied, missing_city), "filters": new_state,
    }
