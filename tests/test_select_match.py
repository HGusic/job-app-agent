from src.select_match import (
    fill_candidates,
    pick_option,
    pick_option_for_degree,
    text_matches_any,
    yes_no_candidates,
)


def test_country_candidates():
    candidates = fill_candidates("country", "United States")
    assert "US" in candidates
    assert "USA" in candidates


def test_state_candidates():
    candidates = fill_candidates("state", "TX")
    assert "TX" in candidates
    assert "Texas" in candidates


def test_pick_option_exact():
    options = [("", "Select..."), ("US", "United States"), ("CA", "Canada")]
    match = pick_option(options, ["United States"])
    assert match == ("US", "United States")


def test_pick_option_by_value():
    options = [("840", "United States of America")]
    match = pick_option(options, ["US"])
    assert match is None
    match = pick_option(options, ["United States"])
    assert match == ("840", "United States of America")


def test_text_matches_any():
    assert text_matches_any("LinkedIn", ["LinkedIn"])
    assert text_matches_any("  Yes  ", ["Yes"])
    assert not text_matches_any("Indeed", ["LinkedIn"])


def test_pick_option_for_degree():
    options = [
        ("", "Please select"),
        ("MS", "Master of Science"),
        ("BS", "Bachelor of Science"),
        ("MSCS", "Master of Science in Computer Science"),
    ]
    bachelor = pick_option_for_degree(
        options,
        fill_candidates("degree", "B.S. in Computer Science"),
        "B.S. in Computer Science",
    )
    assert bachelor == ("BS", "Bachelor of Science")

    master = pick_option_for_degree(
        options,
        fill_candidates("degree", "M.S. in Computer Science"),
        "M.S. in Computer Science",
    )
    assert master == ("MS", "Master of Science")


def test_degree_candidates_exclude_bare_cs():
    candidates = fill_candidates("degree", "B.S. in Computer Science")
    assert "Computer Science" not in candidates

    bs = fill_candidates("degree", "B.S. in Computer Science")
    assert "Bachelor of Science" in bs


def test_specialization_candidates():
    candidates = fill_candidates("specialization", "Data Science / Artificial Intelligence")
    assert "Data Science" in candidates
    assert "Artificial Intelligence" in candidates


def test_source_candidates():
    candidates = fill_candidates("source", "LinkedIn")
    assert "LinkedIn" in candidates
    assert "Social Media" in candidates
