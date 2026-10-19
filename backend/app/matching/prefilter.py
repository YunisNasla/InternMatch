"""TF-IDF ranking of postings with descriptions, paging, and the unscored "Also open" list."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from app.schemas import Profile

FIRST_PAGE, NEXT_PAGE = 20, 10


def profile_text(p: Profile) -> str:
    """What the student knows and did. Name and location are left out on purpose."""
    parts = [*(v for values in p.skills.model_dump().values() for v in values), *p.coursework, *p.certifications]
    parts += [f"{e.degree or ''} {e.major or ''}" for e in p.education]
    parts += [f"{x.title} {' '.join(x.highlights)}" for x in p.experience]
    parts += [f"{x.name} {' '.join(x.tech)} {x.summary}" for x in p.projects]
    return " ".join(parts)


def rank(profile: Profile, rows: list[dict]) -> list[dict]:
    """Postings with a description, most similar to the profile first. Title-only postings never get here."""
    described = [r for r in rows if r["has_description"]]
    if not described:
        return []
    matrix = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(
        [profile_text(profile), *(f"{r['title']} {r['description']}" for r in described)]
    )
    scores = linear_kernel(matrix[0], matrix[1:]).ravel()
    return [r for _, r in sorted(zip(scores, described), key=lambda pair: -pair[0])]


def page(ranked: list, offset: int) -> tuple[list, bool]:
    """20 postings first, then 10 per "Score 10 more"."""
    end = offset + (FIRST_PAGE if offset == 0 else NEXT_PAGE)
    return ranked[offset:end], end < len(ranked)


def also_open(rows: list[dict]) -> list[dict]:
    """Title-only postings, newest first, "Date unknown" last."""
    return sorted((r for r in rows if not r["has_description"]), key=lambda r: r["posted_at"] or "", reverse=True)
