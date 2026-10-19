import pytest

from app.matching import distance

LA = distance.lookup("Los Angeles, CA")


@pytest.mark.parametrize(
    "text",
    ["Los Angeles, CA", "Los Angeles, California", "los angeles, ca, USA", "Los Angeles, CA, United States", "LA",
     "Los Angeles, CA (Hybrid)"],
)
def test_lookup_forms_of_one_city(text):
    assert distance.lookup(text) == LA


def test_saint_and_st_match():
    assert distance.lookup("St. Louis, Missouri") == distance.lookup("Saint Louis, MO") is not None


@pytest.mark.parametrize("text", ["NYC", "SF Bay Area", "South SF", "Washington, DC", "Nashville, TN", "Boise, ID", "La Jolla, San Diego, CA"])
def test_aliases_and_consolidated_cities(text):
    assert distance.lookup(text) is not None


@pytest.mark.parametrize("text", ["Remote in USA", "Multiple Locations", "London, UK", "Pamona, CA", ""])
def test_unplaceable(text):
    assert distance.lookup(text) is None


def test_haversine_la_to_sf():
    assert 340 < distance.haversine_miles(LA, distance.lookup("San Francisco, CA")) < 360


HOME = "Pomona, CA"


@pytest.mark.parametrize(
    "locations, arrangement, home, max_miles, expected",
    [
        (["Boston, MA"], "in_person", HOME, None, "pass"),  # no limit
        (["Boston, MA"], "remote", HOME, 30, "pass"),  # remote skips the check
        (["Boston, MA", "Irvine, CA"], "hybrid", HOME, 30, "pass"),  # any location in range
        (["Boston, MA"], "not_stated", HOME, 30, "fail"),
        (["Multiple Locations"], "in_person", HOME, 30, "unplaceable"),
        (["Multiple Locations", "Boston, MA"], "in_person", HOME, 30, "fail"),
        (["Boston, MA"], "in_person", "Pamona, CA", 30, "pass"),  # unknown home city skips the check
        (["Boston, MA"], "in_person", None, 30, "pass"),
    ],
)
def test_check(locations, arrangement, home, max_miles, expected):
    assert distance.check(locations, arrangement, home, max_miles) == expected
