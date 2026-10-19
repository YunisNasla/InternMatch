"""Build data/us_cities.csv (city,state,lat,lng) from the public-domain Census Gazetteer places file.

Run once from backend/: .venv/bin/python -m scripts.build_cities
"""

import csv
import io
import re
import zipfile

import httpx

from app.config import REPO_ROOT

URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_place_national.zip"
OUT = REPO_ROOT / "backend/data/us_cities.csv"
# Census appends the place type to the name: "Los Angeles city", "Nashville-Davidson metropolitan government (balance)".
SUFFIX = re.compile(
    r"\s+(city and borough|metropolitan government|metro government|consolidated government|unified government|"
    r"urban county|city|town|village|cdp|borough|municipality|zona urbana|comunidad)(\s*\(balance\))?$",
    re.IGNORECASE,
)

# shortcut: Census internal points are off for cities with island territory; add any other outlier found here.
OVERRIDES = {("San Francisco", "CA"): ("37.7749", "-122.4194")}


def main() -> None:
    data = zipfile.ZipFile(io.BytesIO(httpx.get(URL, timeout=60).raise_for_status().content))
    rows = csv.DictReader(io.TextIOWrapper(data.open(data.namelist()[0]), encoding="utf-8"), delimiter="|")
    best: dict[tuple[str, str], tuple[int, str, str]] = {}
    for r in rows:
        name = SUFFIX.sub("", r["NAME"].strip()).strip()
        names = {name}
        if "-" in name or "/" in name:  # "Nashville-Davidson" is also "Nashville"
            names.add(re.split(r"[-/]", name)[0].strip())
        for city in names:
            key = (city, r["USPS"])
            land = int(r["ALAND"])
            if key not in best or land > best[key][0]:  # same name twice in a state: keep the bigger place
                best[key] = (land, r["INTPTLAT"].strip(), r["INTPTLONG"].strip())
    for key, (lat, lng) in OVERRIDES.items():
        best[key] = (best[key][0], lat, lng)
    with OUT.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["city", "state", "lat", "lng"])
        for (city, state), (_, lat, lng) in sorted(best.items()):
            out.writerow([city, state, lat, lng])
    print(f"wrote {len(best)} places to {OUT}")


if __name__ == "__main__":
    main()
