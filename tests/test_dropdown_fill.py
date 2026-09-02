from src.dropdown_fill import candidates_for_field, is_placeholder_value
from src.experience_mapper import education_entry_value


def test_placeholder_values():
    assert is_placeholder_value("Please select")
    assert is_placeholder_value("Select...")
    assert not is_placeholder_value("Computer Science")


def test_specialization_candidates_from_degree():
    entry = {"degree": "B.S. in Computer Science"}
    candidates = candidates_for_field("specialization", "Computer Science", entry=entry)
    assert "Computer Science" in candidates
    assert "CS" in candidates


def test_education_entry_specialization_fallback():
    entry = {"degree": "B.S. in Computer Science"}
    assert education_entry_value(entry, "specialization") == "Computer Science"


def test_yes_no_dropdown_candidates():
    candidates = candidates_for_field("worked_here_before", "No")
    lowered = {c.casefold() for c in candidates}
    assert "no" in lowered
    assert "n" in lowered
