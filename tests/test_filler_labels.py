from src.filler import is_weak_label
from src.mapper import map_label_to_field


def test_is_weak_label():
    assert is_weak_label("")
    assert is_weak_label("Please select")
    assert is_weak_label("Select...")
    assert not is_weak_label("Are you a U.S. Citizen?")
    assert not is_weak_label("Country")


def test_screening_questions_from_container_style_labels():
    immigration = (
        "Are you required to be authorized by the Department of Homeland Security (DHS), "
        "U.S. Citizenship and Immigration Services (USCIS), Student and Exchange Visitor "
        "Information System (SEVIS), or your Designated School Official (DSO) prior to "
        "starting work with Example Corp?"
    )
    agreement = (
        "Are you under an agreement with a current or former employer that prohibits or "
        "impacts your ability to work for another employer?"
    )
    assert map_label_to_field(immigration).key == "requires_immigration_authorization"
    assert map_label_to_field(agreement).key == "restrictive_employment_agreement"
    assert map_label_to_field(immigration).key != "country"
    assert map_label_to_field(agreement).key != "country"
