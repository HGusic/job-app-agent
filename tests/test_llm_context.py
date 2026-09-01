from src.llm.context import format_profile


def test_format_profile_includes_contact_and_screening():
    profile = {
        "contact": {"first_name": "Haris", "email": "haris@example.com"},
        "work_history": [{"company": "Fujitsu", "title": "SDE III", "start": "2025", "end": "2026", "highlights": []}],
        "education": [{"degree": "M.S. CS", "school": "UT Dallas", "graduation": "2022"}],
        "screening": {"work_authorization": "Yes"},
        "skills": [],
    }
    text = format_profile(profile)
    assert "Haris" in text
    assert "Fujitsu" in text
    assert "UT Dallas" in text
    assert "work_authorization" in text
