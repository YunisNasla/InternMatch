from datetime import UTC, datetime

import pytest

from app.matching import filters, prefilter
from app.schemas import FilterState, Profile

NOW = datetime(2026, 10, 19, tzinfo=UTC)


def row(**kw):
    base = {"id": "p", "company": "Acme", "title": "Intern", "description": "work", "has_description": 1,
            "industry": "space", "role_type": "software", "terms": ["Summer 2027"], "posted_at": "2026-10-15T00:00:00Z",
            "date_kind": "posted", "work_arrangement": "in_person", "locations": ["Los Angeles, CA"], "degree_levels": []}
    return base | kw


def kept(rows, **f):
    return [r["id"] for r in filters.hard_filter(rows, FilterState(**f), NOW)[0]]


@pytest.mark.parametrize(
    "posting, f, passes",
    [
        (row(industry="other"), {}, True),  # empty industry filter means all, other included
        (row(industry=None), {"industries": ["space"]}, False),
        (row(role_type=None), {}, True),
        (row(role_type=None), {"role_types": ["software"]}, False),  # untagged excluded once role types are set
        (row(terms=["unknown"]), {"terms": ["Fall 2026"]}, True),
        (row(terms=["Summer 2027"]), {"terms": ["Fall 2026"]}, False),
        (row(posted_at="2026-09-01T00:00:00Z"), {"posted_within_days": 30}, False),
        (row(date_kind="updated"), {"posted_within_days": 7}, True),  # an updated date counts
        (row(posted_at=None, date_kind="unknown"), {"posted_within_days": 30}, False),
        (row(posted_at=None, date_kind="unknown"), {}, True),
        (row(work_arrangement="not_stated"), {"work_arrangements": ["remote"]}, True),
        (row(work_arrangement="in_person"), {"work_arrangements": ["remote"]}, False),
        (row(company="ACME"), {"exclude_companies": ["acme"]}, False),
        (row(description="We use Python daily"), {"include_keywords": ["python"]}, True),
        (row(description="We use Java"), {"include_keywords": ["python"]}, False),
        (row(title="Sales Intern"), {"exclude_keywords": ["sales"]}, False),
        (row(locations=["Boston, MA"]), {"home_city": "Pomona, CA", "max_distance_miles": 50}, False),
        (row(locations=["Boston, MA"], work_arrangement="remote"), {"home_city": "Pomona, CA", "max_distance_miles": 50}, True),
    ],
)
def test_hard_filters(posting, f, passes):
    assert kept([posting], **f) == (["p"] if passes else [])


def test_unplaceable_postings_are_hidden_and_counted_only_with_a_limit():
    rows = [row(id="a", locations=["Multiple Locations"]), row(id="b")]
    assert filters.hard_filter(rows, FilterState(home_city="Pomona, CA", max_distance_miles=50), NOW)[1] == 1
    assert filters.hard_filter(rows, FilterState(), NOW)[1] == 0


PROFILE = Profile(is_stem=True, class_standing="junior", coursework=["Embedded Systems", "Digital Logic"],
                  skills={"programming_languages": ["C", "Verilog"], "hardware_fabrication": ["oscilloscope"]})


def test_rank_puts_the_closest_description_first_and_skips_title_only():
    rows = [
        row(id="bio", description="Run PCR and cell culture assays in a biology lab"),
        row(id="emb", description="Write C firmware for embedded systems, verify with an oscilloscope"),
        row(id="web", description="Build React web pages"),
        row(id="title", description=None, has_description=0),
    ]
    assert [r["id"] for r in prefilter.rank(PROFILE, rows)][:1] == ["emb"]
    assert "title" not in [r["id"] for r in prefilter.rank(PROFILE, rows)]


def test_page_sizes_and_has_more():
    ranked = list(range(45))
    assert prefilter.page(ranked, 0) == (list(range(20)), True)
    assert prefilter.page(ranked, 20) == (list(range(20, 30)), True)
    assert prefilter.page(ranked, 40) == (list(range(40, 45)), False)


def test_also_open_is_title_only_newest_first_unknown_last():
    rows = [row(id="old", has_description=0, posted_at="2026-09-01T00:00:00Z"),
            row(id="none", has_description=0, posted_at=None), row(id="new", has_description=0),
            row(id="described")]
    assert [r["id"] for r in prefilter.also_open(rows)] == ["new", "old", "none"]


ALL = {"open", "ug_ms", "unknown", "ms_phd", "phd", "ug"}


@pytest.mark.parametrize(
    "standing, expected",
    [("junior", {"open", "ug_ms", "unknown", "ug"}),
     ("senior", {"open", "ug_ms", "unknown", "ug"}),
     ("masters", {"open", "ug_ms", "unknown", "ms_phd"}),
     ("phd", {"open", "unknown", "ms_phd", "phd"}),
     ("unknown", ALL)],
)
def test_degree_level_follows_class_standing(standing, expected):
    rows = [row(id="open", degree_levels=["masters", "phd", "undergrad"]), row(id="ug_ms", degree_levels=["masters", "undergrad"]),
            row(id="unknown"), row(id="ms_phd", degree_levels=["masters", "phd"]), row(id="phd", degree_levels=["phd"]),
            row(id="ug", degree_levels=["undergrad"])]
    level = filters.LEVEL_BY_STANDING.get(standing)
    assert {r["id"] for r in filters.hard_filter(rows, FilterState(), NOW, level)[0]} == expected
