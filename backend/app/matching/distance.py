"""City-to-city distance from the offline Census cities file (ARCHITECTURE.md "Location and distance")."""

import csv
import math
import re
import unicodedata
from functools import cache

from app.config import REPO_ROOT

CITIES_FILE = REPO_ROOT / "backend/data/us_cities.csv"
Point = tuple[float, float]

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "puerto rico": "PR", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}
CODES = set(STATES.values())

# Short names people and job boards use, mapped to a "City, ST" the file knows.
ALIASES = {
    "la": "Los Angeles, CA", "los angeles area": "Los Angeles, CA", "greater los angeles": "Los Angeles, CA",
    "sf": "San Francisco, CA", "south sf": "South San Francisco, CA", "sf bay area": "San Francisco, CA", "bay area": "San Francisco, CA",
    "san francisco bay area": "San Francisco, CA", "nyc": "New York, NY", "new york city": "New York, NY",
    "dc": "Washington, DC", "washington dc": "Washington, DC", "washington d c": "Washington, DC",
    "boise, id": "Boise City, ID", "honolulu, hi": "Urban Honolulu, HI",
}
_COUNTRY_SUFFIX = re.compile(r",\s*(usa|us|united states( of america)?)$")
_PAREN = re.compile(r"\([^)]*\)")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = re.sub(r"\bst\.?\s", "saint ", re.sub(r"\bft\.?\s", "fort ", re.sub(r"\bmt\.?\s", "mount ", text)))
    return " ".join(re.sub(r"[^a-z0-9, ]+", " ", text).split())


@cache
def _cities() -> dict[tuple[str, str], Point]:
    with CITIES_FILE.open() as f:
        return {(_norm(r["city"]), r["state"]): (float(r["lat"]), float(r["lng"])) for r in csv.DictReader(f)}


def lookup(text: str | None) -> Point | None:
    """(lat, lng) for "City, ST", "City, State" or a known alias, else None."""
    if not text:
        return None
    key = _COUNTRY_SUFFIX.sub("", _norm(_PAREN.sub("", text))).strip(" ,")
    key = _norm(ALIASES.get(key, key))
    *places, state = [p.strip() for p in key.split(",")]
    state = state.upper() if state.upper() in CODES else STATES.get(state)
    # "La Jolla, San Diego, CA": either place name may be the one the file knows.
    return next((pt for place in places if state and (pt := _cities().get((place, state)))), None)


def haversine_miles(a: Point, b: Point) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def check(locations: list[str], arrangement: str, home: str | None, max_miles: float | None) -> str:
    """"pass", "fail" or "unplaceable". No limit, an unknown home city or a remote posting always pass."""
    home_point = lookup(home)
    if max_miles is None or home_point is None or arrangement == "remote":
        return "pass"
    points = [p for p in map(lookup, locations) if p]
    if not points:
        return "unplaceable"
    return "pass" if any(haversine_miles(home_point, p) <= max_miles for p in points) else "fail"
