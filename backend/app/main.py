from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db, taxonomy
from app.config import settings
from app.ingest import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs = scheduler.start()
    yield
    jobs.shutdown(wait=False)


app = FastAPI(title="InternMatch", lifespan=lifespan)
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


if settings.enable_admin_routes:

    @app.post("/api/ingest")
    async def ingest():
        return {"status": "started" if scheduler.start_in_background() else "already running"}
