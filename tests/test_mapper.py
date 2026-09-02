"""Tests for contact field label mapping."""

from src.mapper import (
    is_eeo_field,
    is_legal_field,
    map_label_to_field,
    map_label_to_key,
    normalize_label,
    should_skip_field,
)


def test_normalize_label():
    assert normalize_label("E-Mail") == "e mail"
    assert normalize_label("First_Name") == "first name"


def test_name_mapping():
    assert map_label_to_key("First Name") == "first_name"
    assert map_label_to_key("Middle Name") == "middle_name"
    assert map_label_to_key("Middle Name*") == "middle_name"
    assert map_label_to_key("Last Name") == "last_name"
    assert map_label_to_key("Full Name") == "full_name"
    assert map_label_to_key("Name") == "full_name"
    assert map_label_to_key("Middle Name") != "full_name"


def test_contact_mapping():
    assert map_label_to_key("Email Address") == "email"
    assert map_label_to_key("E-mail") == "email"
    assert map_label_to_key("Mobile Phone") == "phone"
    assert map_label_to_key("City") == "city"
    assert map_label_to_key("ZIP Code") == "postal_code"
    assert map_label_to_key("LinkedIn URL") == "linkedin"


def test_screening_mapping():
    mapping = map_label_to_field("Are you authorized to work in the US?")
    assert mapping is not None
    assert mapping.section == "screening"
    assert mapping.key == "work_authorization"

    assert map_label_to_field("Are you at least 18 years of age?").key == "over_18"
    assert map_label_to_field("Are you a U.S. Citizen?").key == "us_citizen"
    assert map_label_to_field("Will you require visa sponsorship?").key == "requires_sponsorship"
    assert map_label_to_field("Do you currently have a work visa?").key == "has_visa"
    assert map_label_to_field("Are you legally eligible to work in the United States?").key == "work_authorization"


def test_preferences_mapping():
    mapping = map_label_to_field("I agree to the privacy policy")
    assert mapping is not None
    assert mapping.section == "preferences"
    assert mapping.key == "agree_privacy_policy"


def test_preferred_name_mapping():
    mapping = map_label_to_field("I have a preferred name")
    assert mapping is not None
    assert mapping.key == "has_preferred_name"


def test_company_name_not_full_name():
    assert map_label_to_field("Company Name") is None
    assert map_label_to_field("Company Name*") is None


def test_heard_about_mapping():
    mapping = map_label_to_field("How did you hear about us?")
    assert mapping is not None
    assert mapping.section == "heard_about"
    assert mapping.key == "source"


def test_phone_code_mapping():
    mapping = map_label_to_field("Country Phone Code*")
    assert mapping is not None
    assert mapping.key == "phone_country_code"


def test_phone_extension_mapping():
    assert map_label_to_key("Phone Extension") == "phone_extension"


def test_worked_here_before_mapping():
    assert map_label_to_field("Have you worked here before?").key == "worked_here_before"
    assert map_label_to_field("Have you previously worked for this company?").key == "worked_here_before"
    assert map_label_to_field("Have you previously worked for, or been on assignment with us?").key == "worked_here_before"


def test_employer_affiliate_screening():
    q = (
        "Are you now, or have you ever been employed by, or at, any Acme entity, "
        "affiliate or subsidiary, or any dealer of Acme products?"
    )
    assert map_label_to_field(q).key == "employed_by_parent_company"
    assert map_label_to_field("Have you ever been employed by this company or its subsidiaries?").key == (
        "employed_by_parent_company"
    )


def test_related_to_employee_screening():
    q = "Are you related to anyone employed by the company or its affiliates?"
    assert map_label_to_field(q).key == "related_to_employee"


def test_restrictive_agreement_screening():
    q = (
        "Are you under an agreement with a current or former employer that prohibits "
        "or impacts your ability to work for another employer?"
    )
    assert map_label_to_field(q).key == "restrictive_employment_agreement"


def test_immigration_authorization_screening():
    q = "Are you required to be authorized by DHS or USCIS prior to starting work?"
    mapping = map_label_to_field(q)
    assert mapping.key == "requires_immigration_authorization"
    assert mapping.key != "work_authorization"


def test_skip_extension():
    profile = {"auto_fill": {"eeo": False, "legal_attestations": False}}
    assert should_skip_field("Phone Extension", profile) is None


def test_device_type_mapping():
    assert map_label_to_key("Device Type") == "phone_type"
    assert map_label_to_key("Device Type*") == "phone_type"
    assert map_label_to_key("County") == "county"
    assert map_label_to_key("County*") == "county"


def test_confirm_email_mapping():
    mapping = map_label_to_field("Confirm Email Address")
    assert mapping is not None
    assert mapping.key == "email"


def test_long_screening_text_does_not_map_to_country():
    blob = (
        "Are you required to be authorized by DHS prior to starting work? "
        "Country of citizenship Please select Are you under an agreement with a former employer?"
    )
    assert map_label_to_field(blob) is not None
    assert map_label_to_field(blob).key != "country"
    assert map_label_to_field(blob).section == "screening"


def test_united_states_label_is_not_state():
    assert map_label_to_field("United States") is None
    assert map_label_to_field("Country") is not None
    assert map_label_to_field("Country").key == "country"
    assert map_label_to_field("State") is not None
    assert map_label_to_field("State").key == "state"


def test_skip_rules():
    profile = {"auto_fill": {"eeo": False, "legal_attestations": False}}
    assert should_skip_field("Gender", profile) == "EEO field (auto_fill.eeo is false)"
    assert should_skip_field("I certify the information is true", profile) is not None
    assert should_skip_field("Email", profile) is None
