import pytest

from app.ingest import rules


@pytest.mark.parametrize(
    "title",
    ["Software Engineering Intern", "Full-time Intern, Propulsion", "Summer Internship - GNC",
     "Co-op: Test Engineer", "Mechanical Engineering Coop", "Apprentice Machinist", "Interns, Data"],
)
def test_internship_titles_are_kept(title):
    assert rules.is_internship(title)


@pytest.mark.parametrize("title", ["Internal Tools Engineer", "Senior Software Engineer", "International Tax Analyst"])
def test_non_internship_titles_are_dropped(title):
    assert not rules.is_internship(title)


def test_terms_come_from_title_first():
    assert rules.extract_terms("Summer 2027 Intern", "Also hiring for Fall 2026") == ["Summer 2027"]


def test_terms_fall_back_to_description_and_normalize_case():
    assert rules.extract_terms("Intern", "Start dates: FALL 2026 or spring 2027.") == ["Fall 2026", "Spring 2027"]


def test_terms_unknown_when_nothing_matches():
    assert rules.extract_terms("Intern", None) == ["unknown"]


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://job-boards.greenhouse.io/genevatrading/jobs/5085231007", ("greenhouse", "genevatrading", "5085231007")),
        ("https://boards.greenhouse.io/neuralink/jobs/6083322003?gh_jid=6083322003", ("greenhouse", "neuralink", "6083322003")),
        ("https://jobs.lever.co/hermeus/51378fa0-0327-45fd-9420-b6e7d8b56440/apply?utm_source=Simplify",
         ("lever", "hermeus", "51378fa0-0327-45fd-9420-b6e7d8b56440")),
        ("https://analogdevices.wd1.myworkdayjobs.com/External/job/R256591", None),
    ],
)
def test_ats_job_id_from_apply_link(url, expected):
    assert rules.ats_job_id_from_url(url) == expected


def test_posted_date_wins_then_updated_then_unknown():
    assert rules.pick_date("2026-07-21T19:49:28-04:00", "2026-10-14T17:51:29-04:00") == ("2026-07-21T23:49:28Z", "posted")
    assert rules.pick_date(None, "2026-10-14T17:51:29-04:00") == ("2026-10-14T21:51:29Z", "updated")
    assert rules.pick_date(None, None) == (None, "unknown")


@pytest.mark.parametrize(
    "lever, tagger, locations, expected",
    [
        ("remote", "in_person", ["Austin, TX"], "remote"),
        ("unspecified", "hybrid", ["Remote in USA"], "hybrid"),
        (None, "not_stated", ["Remote in USA"], "remote"),
        (None, "not_stated", ["Seattle, WA (Hybrid)"], "hybrid"),
        (None, None, ["Seattle, WA"], "not_stated"),
        ("onsite", None, [], "in_person"),
    ],
)
def test_arrangement_precedence(lever, tagger, locations, expected):
    assert rules.arrangement(lever, tagger, locations) == expected


def test_strip_html_handles_greenhouse_double_escaping():
    raw = "&lt;div&gt;&lt;p&gt;Build rockets &amp;amp; engines.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;C++&lt;/li&gt;&lt;/ul&gt;&lt;/div&gt;"
    assert rules.strip_html(raw) == "Build rockets & engines.\nC++"


def _posting(feed, title="Propulsion Intern", locations=("Hawthorne, CA",), job_id=None, terms=("Summer 2027",)):
    ats, board = feed.split(":") if ":" in feed else (None, None)
    return rules.RawPosting(
        feed=feed, source_id=job_id or title, company="SpaceX", title=title, locations=list(locations),
        terms=list(terms), url="", posted_at=None, date_kind="unknown",
        ats=ats or ("greenhouse" if job_id else None), board=board or ("spacex" if job_id else None), ats_job_id=job_id,
    )


def test_dedupe_merges_simplify_listing_into_board_posting_by_job_id():
    board = _posting("greenhouse:spacex", job_id="111", terms=["unknown"])
    simplify = _posting("simplify", locations=["Hawthorne, California, United States"], job_id="111")
    [merged] = rules.dedupe([simplify, board])
    assert merged is board
    assert merged.sources == {"greenhouse:spacex", "simplify"}
    assert merged.terms == ["Summer 2027"]


def test_dedupe_falls_back_to_company_title_location_without_job_id():
    board = _posting("greenhouse:spacex", job_id="111")
    simplify = _posting("simplify", locations=["hawthorne, ca"])
    assert len(rules.dedupe([board, simplify])) == 1


def test_dedupe_keeps_two_board_jobs_with_the_same_title():
    assert len(rules.dedupe([_posting("greenhouse:spacex", job_id="1"), _posting("greenhouse:spacex", job_id="2")])) == 2


B, S = "greenhouse:acme", "simplify"
KNOWN = {B, S}


@pytest.mark.parametrize(
    "case, current, sources, open_feeds, ok_feeds, known, expected",
    [
        ("board-only, board ok and lists it", False, {B}, {B}, {B, S}, KNOWN, True),
        ("board-only, board ok without it", True, {B}, set(), {B, S}, KNOWN, False),
        ("board-only, board failed", True, {B}, set(), {S}, KNOWN, True),
        ("board-only, board dropped from yaml", True, {B}, set(), {S}, {S}, False),
        ("simplify-only, open", False, {S}, {S}, {S}, KNOWN, True),
        ("simplify-only, inactive or missing", True, {S}, set(), {S}, KNOWN, False),
        ("simplify-only, simplify failed", True, {S}, set(), set(), KNOWN, True),
        ("merged, board failed, simplify inactive", True, {B, S}, set(), {S}, KNOWN, True),
        ("merged, board dropped, simplify inactive", True, {B, S}, set(), {S}, {S}, False),
        ("merged, board ok without it, simplify still open", True, {B, S}, {S}, {B, S}, KNOWN, True),
        ("closed posting comes back", False, {B}, {B}, {B}, KNOWN, True),
    ],
)
def test_next_active(case, current, sources, open_feeds, ok_feeds, known, expected):
    assert rules.next_active(current, sources, open_feeds, ok_feeds, known) is expected, case
