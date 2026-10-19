"""The two ingest taggers (PROMPTS.md "Ingest taggers"). Both run on Haiku at low effort."""

import anthropic

from app.ingest.rules import RawPosting
from app.llm import HAIKU, MAX_DESCRIPTION, call_json, load_prompt
from app.schemas import CompanyTagResult, TagResult


async def tag_posting(llm: anthropic.AsyncAnthropic, p: RawPosting) -> TagResult:
    values = {"company": p.company, "title": p.title, "locations": "; ".join(p.locations)}
    if p.description:
        user = load_prompt("tag_posting_user.txt", **values, description_text=p.description[:MAX_DESCRIPTION])
    else:
        user = load_prompt("tag_posting_title_user.txt", **values)
    return await call_json(llm, HAIKU, load_prompt("tag_posting_system.txt"), user, TagResult, label=p.id, effort="low")


async def tag_company(llm: anthropic.AsyncAnthropic, name: str, titles: list[str]) -> CompanyTagResult:
    user = load_prompt("tag_company_user.txt", company=name, sample_titles="\n".join(f"- {t}" for t in titles[:5]))
    return await call_json(
        llm, HAIKU, load_prompt("tag_company_system.txt"), user, CompanyTagResult, label=f"company:{name}", effort="low",
    )
