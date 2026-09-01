from src.profile import get_section_value, load_profile


def test_load_profile_sections():
    profile = load_profile()
    assert profile["contact"]["first_name"] == "XXX"
    assert profile["screening"]["work_authorization"] == "Yes"
    assert len(profile["work_history"]) == 2
    assert profile["work_history"][0]["company"] == "XXX"
    assert len(profile["education"]) == 2
    assert profile["auto_fill"]["eeo"] is False


def test_get_section_value():
    profile = load_profile()
    assert get_section_value(profile, "contact", "email") == "XXX"
    assert get_section_value(profile, "heard_about", "source") == "LinkedIn"
