from src.profile import get_section_value, load_profile


def test_load_profile_sections():
    profile = load_profile()
    assert "contact" in profile
    assert "first_name" in profile["contact"]
    assert "screening" in profile
    assert len(profile["work_history"]) >= 1
    assert "company" in profile["work_history"][0]
    assert len(profile["education"]) >= 1
    assert profile["auto_fill"]["eeo"] is False


def test_get_section_value():
    profile = load_profile()
    assert get_section_value(profile, "contact", "email") is not None
    assert get_section_value(profile, "heard_about", "source") is not None
