import pytest

from app.matching import refine
from app.schemas import FilterState, RefineChange

STATE = FilterState(role_types=["software"], home_city="Pomona, CA")


def change(field, action, value):
    return RefineChange(field=field, action=action, value=value)


def apply(*changes, mode="refine", state=STATE):
    return refine.apply_changes(state, list(changes), mode)


def test_valid_changes_apply_in_order():
    state, applied, dropped, _ = apply(
        change("industries", "set", ["space"]), change("role_types", "add", "data_ml"),
        change("role_types", "remove", "software"), change("max_distance_miles", "set", 30),
    )
    assert (state.industries, state.role_types, state.max_distance_miles) == (["space"], ["data_ml"], 30)
    assert len(applied) == 4 and dropped == []


@pytest.mark.parametrize(
    "bad",
    [
        change("salary", "set", 100),  # unknown field
        change("sort_by", "add", "posted"),  # action not allowed for a scalar
        change("industries", "add", "astrology"),  # value outside the taxonomy
        change("industries", "set", "space"),  # set on a list needs the whole list
        change("role_types", "add", ["software"]),  # add takes one item
        change("max_distance_miles", "set", -5),
        change("posted_within_days", "set", 14),
        change("work_arrangements", "set", []),  # can't be emptied
        change("terms", "remove", "Summer 2027"),  # would empty terms
        change("role_types", "remove", "physics"),  # not in the list
    ],
)
def test_invalid_changes_are_dropped(bad):
    state, applied, dropped, _ = apply(bad)
    assert state == STATE and applied == [] and dropped == [bad]


def test_unknown_home_city_is_dropped_and_named():
    state, _, _, city = apply(change("home_city", "set", "Pamona, CA"))
    assert state.home_city == "Pomona, CA" and city == "Pamona, CA"


def test_initial_mode_drops_chat_only_fields():
    emphasis = change("emphasis", "set", "controls work")
    state, _, dropped, _ = apply(emphasis, change("industries", "set", ["space"]), mode="initial")
    assert state.emphasis is None and state.industries == ["space"] and dropped == [emphasis]


def test_emphasis_can_be_set_and_cleared_in_refine_mode():
    state, *_ = apply(change("emphasis", "set", "controls work"))
    assert state.emphasis == "controls work"
    state, *_ = apply(change("emphasis", "set", None), state=state)
    assert state.emphasis is None


def test_fix_reply_replaces_when_nothing_applied_and_adds_otherwise():
    msg = "I couldn't find Pamona, CA, so your home city didn't change. Try 'City, ST'."
    assert refine.fix_reply("Moved you to Pamona.", applied=[], dropped_city="Pamona, CA") == msg
    applied = [change("max_distance_miles", "set", 30)]
    assert refine.fix_reply("Within 30 miles.", applied, "Pamona, CA") == f"Within 30 miles. {msg}"
    assert refine.fix_reply("Within 30 miles.", applied, None) == "Within 30 miles."


def test_keyword_and_company_lists_are_capped():
    from pydantic import ValidationError

    from app.schemas import FilterState

    FilterState(include_keywords=["x"] * 50)
    for field in ("include_keywords", "exclude_keywords", "exclude_companies"):
        with pytest.raises(ValidationError):
            FilterState(**{field: ["x"] * 51})


def test_fixed_value_lists_are_capped_at_their_option_count():
    from pydantic import ValidationError

    from app import taxonomy
    from app.schemas import FilterState

    FilterState(role_types=list(taxonomy.ROLE_TYPES))
    for field, value in (("industries", "space"), ("role_types", "software"), ("work_arrangements", "remote"),
                         ("terms", "Summer 2027")):
        with pytest.raises(ValidationError):
            FilterState(**{field: [value] * 30})
