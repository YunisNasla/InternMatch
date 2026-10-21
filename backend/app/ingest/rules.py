"""Pure ingest rules. No I/O here, so every rule is tested directly."""

import html
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

UNKNOWN_TERMS = ["unknown"]

# Word boundaries keep "Internal" and "International" out.
_INTERNSHIP = re.compile(r"\b(interns?|internships?|co-?ops?|apprentices?(hip)?)\b", re.IGNORECASE)
_TERM = re.compile(r"\b(spring|summer|fall|winter)\s+(20\d\d)\b", re.IGNORECASE)


def is_internship(title: str) -> bool:
    return bool(_INTERNSHIP.search(title))


def extract_terms(title: str, description: str | None) -> list[str]:
    for text in (title, description or ""):
        found = dict.fromkeys(f"{season.title()} {year}" for season, year in _TERM.findall(text))
        if found:
            return list(found)
    return list(UNKNOWN_TERMS)


# Degree levels: Simplify's curated list wins; otherwise word-bounded title keywords ("BS/MS", "Ph.D.", "Master’s").
_SIMPLIFY_LEVEL = {"Bachelor's": "undergrad", "Associate's": "undergrad", "Master's": "masters", "PhD": "phd"}
_TITLE_LEVEL = {
    "phd": re.compile(r"\bph\.?\s?d\b|\bdoctoral\b", re.IGNORECASE),
    "masters": re.compile(r"\bmaster[’']?s\b|\bm\.?s\b", re.IGNORECASE),
    "undergrad": re.compile(r"\bundergrad|\bbachelor[’']?s?\b|\bb\.?s\b", re.IGNORECASE),
}
_GREENHOUSE_URL = re.compile(r"greenhouse\.io/([\w-]+)/jobs/(\d+)")
_LEVER_URL = re.compile(r"jobs\.lever\.co/([\w-]+)/([0-9a-f-]{36})")


# shortcut: a short list of countries and hub cities seen on seed boards; extend it when non-US jobs slip through.
_NON_US = {
    "canada", "mexico", "united kingdom", "uk", "england", "scotland", "ireland", "germany", "france", "netherlands",
    "switzerland", "spain", "italy", "poland", "sweden", "denmark", "norway", "finland", "belgium", "austria",
    "portugal", "czech republic", "romania", "israel", "india", "china", "japan", "south korea", "korea", "taiwan",
    "singapore", "hong kong", "australia", "new zealand", "brazil", "argentina", "chile", "colombia",
    "united arab emirates", "uae", "philippines", "vietnam", "malaysia", "indonesia", "south africa",
    "london", "amsterdam", "dublin", "paris", "berlin", "munich", "zurich", "toronto", "vancouver", "montreal",
    "tokyo", "sydney", "bangalore", "bengaluru", "hyderabad", "shanghai", "tel aviv", "sao paulo",
}


def is_non_us(locations: list[str]) -> bool:
    """True when every location names a place outside the US. Unknown text is not proof, so it counts as US."""
    return bool(locations) and all(loc.rsplit(",", 1)[-1].strip().casefold() in _NON_US for loc in locations)


def ats_job_id_from_url(url: str) -> tuple[str, str, str] | None:
    """(ats, board, job id) from a Greenhouse or Lever apply link, else None."""
    if m := _GREENHOUSE_URL.search(url):
        return "greenhouse", m[1], m[2]
    if m := _LEVER_URL.search(url):
        return "lever", m[1], m[2]
    return None


def _iso(value: str | float | None) -> str | None:
    if value is None or value == "":
        return None
    dt = datetime.fromtimestamp(value, UTC) if isinstance(value, int | float) else datetime.fromisoformat(value)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pick_date(posted: str | float | None, updated: str | float | None) -> tuple[str | None, str]:
    """The date a card shows, as (UTC ISO time, kind). Epoch numbers are seconds."""
    if posted_iso := _iso(posted):
        return posted_iso, "posted"
    if updated_iso := _iso(updated):
        return updated_iso, "updated"
    return None, "unknown"


_LEVER_ARRANGEMENT = {"remote": "remote", "hybrid": "hybrid", "onsite": "in_person"}


def arrangement(lever_type: str | None, tagger: str | None, locations: list[str]) -> str:
    """Lever workplaceType, then the tagger, then the location text."""
    if lever_type in _LEVER_ARRANGEMENT:
        return _LEVER_ARRANGEMENT[lever_type]
    if tagger and tagger != "not_stated":
        return tagger
    text = " ".join(locations).lower()
    if "remote" in text:
        return "remote"
    if "hybrid" in text:
        return "hybrid"
    return "not_stated"


_BLOCK_END = re.compile(r"</(p|div|li|ul|ol|h\d)>|<br\s*/?>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    """Plain text from HTML. Greenhouse escapes its HTML once more, so unescape first."""
    text = _TAG.sub("", _BLOCK_END.sub("\n", html.unescape(text)))
    lines = (" ".join(html.unescape(line).split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


@dataclass
class RawPosting:
    feed: str  # "simplify" or "{ats}:{board}"
    source_id: str  # the feed's own id for this posting
    company: str
    title: str
    locations: list[str]
    terms: list[str]
    url: str
    posted_at: str | None
    date_kind: str
    ats: str | None = None
    board: str | None = None
    ats_job_id: str | None = None
    description: str | None = None
    lever_workplace: str | None = None
    degree_levels: list[str] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)

    def __post_init__(self):
        self.sources = self.sources or {self.feed}

    @property
    def id(self) -> str:
        return f"{self.ats}:{self.board}:{self.ats_job_id}" if self.ats_job_id else f"{self.feed}:{self.source_id}"

    @property
    def fallback_key(self) -> tuple:
        return (self.company.casefold(), self.title.casefold(), tuple(sorted(loc.casefold() for loc in self.locations)))


def degree_levels(simplify_degrees: list[str] | None, title: str) -> list[str]:
    """Sorted levels the posting is open to ("masters", "phd", "undergrad"), or [] when unknown."""
    levels = {_SIMPLIFY_LEVEL[d] for d in simplify_degrees or [] if d in _SIMPLIFY_LEVEL}
    return sorted(levels or {level for level, rx in _TITLE_LEVEL.items() if rx.search(title)})


def dedupe(postings: list[RawPosting]) -> list[RawPosting]:
    """Merge copies of one job. The board copy wins, since it has the description."""
    kept: list[RawPosting] = []
    by_key: dict = {}
    for p in sorted(postings, key=lambda p: p.feed == "simplify"):
        # Match on job id when there is one; two board jobs can share a title and city.
        lookup = p.id if p.ats_job_id else p.fallback_key
        if base := by_key.get(lookup):
            base.sources |= p.sources
            if base.terms == UNKNOWN_TERMS:
                base.terms = p.terms
            if p.feed == "simplify" and p.degree_levels:  # Simplify's curated list beats a title guess
                base.degree_levels = p.degree_levels
            continue
        kept.append(p)
        by_key[p.id] = by_key[p.fallback_key] = p
    return kept


def next_active(current: bool, sources: set[str], open_feeds: set[str], ok_feeds: set[str], known_feeds: set[str]) -> bool:
    """ARCHITECTURE ingest step 8. A feed no longer in companies.yaml counts as pulled with nothing listed."""
    if sources & open_feeds:
        return True
    if all(f in ok_feeds or f not in known_feeds for f in sources):
        return False
    return current
