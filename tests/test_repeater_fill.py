from src.repeater_fill import entry_already_on_page


def test_entry_match_pairs_by_index():
    """School/degree lists must align by row index."""
    entry = {
        "school": "UT Dallas",
        "degree": "B.S. in Computer Science",
    }
    schools = ["UT Dallas", "UT Dallas"]
    degrees = ["M.S. in Computer Science", "B.S. in Computer Science"]

    assert entry_already_on_page(entry, schools, degrees, "school", "degree")

    wrong_degrees = ["M.S. in Computer Science", "M.S. in Computer Science"]
    assert not entry_already_on_page(entry, schools, wrong_degrees, "school", "degree")
