import asyncio
import logging
from contextlib import asynccontextmanager, closing
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

import anthropic
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from starlette.formparsers import MultiPartParser

from app import db, llm, taxonomy
from app.config import settings
from app.ingest import scheduler
from app.matching import distance, filters, prefilter, refine, scorer
from app.resume.extract import MAX_BYTES, extract_text
from app.resume.parser import parse_resume
from app.schemas import FilterState, Profile

log = logging.getLogger(__name__)
get_llm = cache(llm.client)  # one Claude client per process; tests override it
LLM_DOWN = "We couldn't reach the AI service. Try again in a minute."
ALSO_OPEN_LIMIT = 50
MAX_PROFILE_CHARS = 20_000  # a real profile is about 4,000; it goes into all 20 scorer prompts
# Keep any accepted resume in memory: Starlette writes uploads over 1 MB to a temp file by default.
MultiPartParser.spool_max_size = MAX_BYTES + 64 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs = scheduler.start()
    yield
    jobs.shutdown(wait=False)


app = FastAPI(title="InternMatch", lifespan=lifespan)


@app.middleware("http")
async def refuse_big_uploads(request: Request, call_next):
    """Refuse an oversized resume before any of it is read or spooled."""
    if request.url.path == "/api/parse":
        size = request.headers.get("content-length")
        if not size or not size.isdigit() or int(size) > MAX_BYTES + 64 * 1024:
            return JSONResponse({"detail": "That file is over 5 MB. Upload a smaller PDF or Word file."}, status_code=413)
    return await call_next(request)


# Added last so it wraps the upload guard: the browser can only read the 413 message with CORS headers on it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/meta")
def meta():
    with closing(db.connect()) as conn:
        last_ingest = db.last_ingest(conn)
    return {
        "industries": [{"code": c, "label": l} for c, l in taxonomy.INDUSTRIES.items()],
        "role_type_groups": [
            {"group": g, "role_types": [{"code": c, "label": l} for c, l in roles.items()]}
            for g, roles in taxonomy.ROLE_TYPE_GROUPS.items()
        ],
        "work_arrangements": [{"code": c, "label": l} for c, l in taxonomy.WORK_ARRANGEMENTS.items()],
        "terms": list(taxonomy.SUPPORTED_TERMS),
        "last_ingest": last_ingest,
    }


@app.get("/api/city")
def city(q: Annotated[str, Query(max_length=100)]):
    """Page 2 checks the home city as the student types it."""
    return {"found": distance.lookup(q) is not None}


if settings.enable_admin_routes:

    @app.post("/api/ingest")
    async def ingest():
        return {"status": "started" if scheduler.start_in_background() else "already running"}


@app.post("/api/parse")
async def parse(
    file: Annotated[UploadFile, File()],
    claude: Annotated[anthropic.AsyncAnthropic, Depends(get_llm)],
    text: Annotated[str, Form(max_length=1000)] = "",
):
    """Resume in, profile and starting filters out. The file stays in memory and is never logged or saved."""
    data = await file.read(MAX_BYTES + 1)
    try:
        resume_text = await asyncio.to_thread(extract_text, file.filename or "", data)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    try:
        profile = await parse_resume(claude, resume_text)
        city, state = profile.location.city, profile.location.state
        filters = FilterState(
            role_types=profile.suggested_role_types, home_city=f"{city}, {state}" if city and state else None,
        )
        reply = ""
        if text.strip():
            result = await refine.refine(claude, "initial", filters, text.strip())
            filters, reply = result["filters"], result["reply"]
    except (llm.LLMError, anthropic.APIError) as error:
        log.warning("parse failed: %s", type(error).__name__)
        raise HTTPException(502, LLM_DOWN) from error
    log.info("parsed a resume: %s bytes, %s characters", len(data), len(resume_text))
    return {
        "profile": profile, "filters": filters, "reply": reply, "is_stem": profile.is_stem,
        "home_city_found": distance.lookup(filters.home_city) is not None,
    }


class SearchRequest(BaseModel):
    profile: Profile
    filters: FilterState
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def profile_is_resume_sized(self):
        if len(self.profile.model_dump_json()) > MAX_PROFILE_CHARS:
            raise ValueError("profile is too large")
        return self


CARD_FIELDS = ("id", "company", "title", "locations", "url", "posted_at", "date_kind", "work_arrangement", "terms",
               "industry", "role_type")


@app.post("/api/search")
async def search(req: SearchRequest, claude: Annotated[anthropic.AsyncAnthropic, Depends(get_llm)]):
    """One page of scored cards. Offset 0 also returns "Also open"; later offsets return only the next 10."""
    with closing(db.connect()) as conn:
        kept, hidden = filters.hard_filter(filters.load_active(conn), req.filters, datetime.now(UTC))
        # shortcut: each page re-ranks, so an ingest between pages can skip a posting; cache the ranking if ingest runs often.
        batch, has_more = prefilter.page(prefilter.rank(req.profile, kept), req.offset)
        results, unscored = await scorer.score(claude, conn, req.profile, batch, req.filters.emphasis)
    cards = [{k: r[k] for k in CARD_FIELDS} | {"score": results[r["id"]]} for r in batch if r["id"] in results]
    if req.filters.sort_by == "posted":
        cards.sort(key=lambda c: c["posted_at"] or "", reverse=True)
    else:
        cards.sort(key=lambda c: c["score"].fit_score, reverse=True)
    also_open = prefilter.also_open(kept) if req.offset == 0 else []
    return {
        "cards": cards,
        "also_open": [{k: r[k] for k in CARD_FIELDS} for r in also_open[:ALSO_OPEN_LIMIT]],
        "also_open_total": len(also_open),
        "home_city_found": distance.lookup(req.filters.home_city) is not None,
        "hidden_count": hidden,
        "has_more": has_more,
        "unscored": [{k: r[k] for k in ("id", "company", "title", "url")} for r in batch if r["id"] in unscored],
    }


class RefineRequest(BaseModel):
    filters: FilterState
    message: str = Field(min_length=1, max_length=500)
    results_summary: str = Field(default="", max_length=6000)
    recent_turns: str = Field(default="", max_length=3000)


@app.post("/api/refine")
async def refine_route(req: RefineRequest, claude: Annotated[anthropic.AsyncAnthropic, Depends(get_llm)]):
    """Page 3 chat. The client reruns /api/search with the new filters; a new emphasis gives a new cache key."""
    try:
        return await refine.refine(claude, "refine", req.filters, req.message, req.results_summary, req.recent_turns)
    except (llm.LLMError, anthropic.APIError) as error:
        log.warning("refine failed: %s", type(error).__name__)
        raise HTTPException(502, LLM_DOWN) from error
