import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMapping:
    section: str
    key: str


EEO_KEYWORDS = (
    "race",
    "ethnicity",
    "gender",
    "veteran",
    "disability",
    "eeo",
    "equal opportunity",
    "hispanic",
    "latino",
)

LEGAL_KEYWORDS = (
    "i certify",
    "i confirm",
    "certify that",
    "attest",
    "under penalty",
    "information provided is true",
    "information is accurate",
)


def normalize_label(label: str) -> str:
    text = label.lower().strip()
    text = re.sub(r"[-_]", " ", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[*:]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def is_contact_style_label(text: str) -> bool:
    """Contact fields are short labels, not long screening questions."""
    if not text:
        return False
    if "?" in text:
        return False
    if len(text) > 80:
        return False
    if len(text.split()) > 10:
        return False
    return True


def is_eeo_field(label: str) -> bool:
    text = normalize_label(label)
    return any(keyword in text for keyword in EEO_KEYWORDS)


def is_legal_field(label: str) -> bool:
    text = normalize_label(label)
    return any(keyword in text for keyword in LEGAL_KEYWORDS)


def map_label_to_field(label: str) -> FieldMapping | None:
    """Map a form field label to a profile section and key."""
    text = normalize_label(label)
    if not text:
        return None

    if "preferred name" in text:
        return FieldMapping("screening", "has_preferred_name")

    if ("over" in text or "least" in text or "older" in text) and "18" in text:
        return FieldMapping("screening", "over_18")
    if "years of age" in text and "18" in text:
        return FieldMapping("screening", "over_18")

    if "sponsor" in text:
        return FieldMapping("screening", "requires_sponsorship")
    if "visa" in text and "sponsor" not in text:
        return FieldMapping("screening", "has_visa")

    if any(
        keyword in text
        for keyword in (
            "dhs",
            "uscis",
            "sevis",
            "dso",
            "homeland security",
            "designated school official",
            "immigration services",
        )
    ):
        return FieldMapping("screening", "requires_immigration_authorization")

    if "citizen" in text:
        return FieldMapping("screening", "us_citizen")

    if "agreement" in text and any(
        keyword in text
        for keyword in ("employer", "prohibits", "impacts", "restrict", "non compete", "noncompete")
    ):
        return FieldMapping("screening", "restrictive_employment_agreement")

    if "related" in text and any(
        keyword in text for keyword in ("employ", "employee", "in law", "inlaw", "relationship", "live with")
    ):
        return FieldMapping("screening", "related_to_employee")

    if any(keyword in text for keyword in ("affiliate", "subsidiary", "dealer")) and "employ" in text:
        return FieldMapping("screening", "employed_by_parent_company")
    if "ever been employed by" in text or ("employed by" in text and "entity" in text):
        return FieldMapping("screening", "employed_by_parent_company")

    if "relocat" in text:
        return FieldMapping("screening", "willing_to_relocate")
    if "previously worked" in text or ("worked" in text and ("before" in text or "here" in text)):
        return FieldMapping("screening", "worked_here_before")
    if "ever been employed" in text:
        return FieldMapping("screening", "worked_here_before")

    if ("authorized" in text or "authoris" in text or "authoriz" in text or "eligib" in text) and (
        "work" in text or "employ" in text
    ):
        return FieldMapping("screening", "work_authorization")
    if "legally authorized" in text or "legal right to work" in text:
        return FieldMapping("screening", "work_authorization")

    if (
        "hear" in text
        and ("about" in text or "job" in text or "position" in text or contains_word(text, "us"))
    ) or text in {
        "source",
        "referral source",
        "how did you hear",
    }:
        return FieldMapping("heard_about", "source")

    # Contact mappings only on short field labels — never on long screening questions.
    if is_contact_style_label(text):
        if "phone code" in text or (contains_word(text, "country") and "phone" in text):
            return FieldMapping("contact", "phone_country_code")

        if "first" in text and "name" in text:
            return FieldMapping("contact", "first_name")
        if "middle" in text and "name" in text:
            return FieldMapping("contact", "middle_name")
        if "last" in text and "name" in text:
            return FieldMapping("contact", "last_name")
        if "full" in text and "name" in text:
            return FieldMapping("contact", "full_name")
        if text == "name" or (
            contains_word(text, "name")
            and "first" not in text
            and "middle" not in text
            and "last" not in text
            and "user" not in text
            and "preferred" not in text
            and "company" not in text
            and "school" not in text
            and "employer" not in text
        ):
            return FieldMapping("contact", "full_name")

        if "confirm" in text and ("email" in text or "e mail" in text):
            return FieldMapping("contact", "email")
        if "email" in text or "e mail" in text:
            return FieldMapping("contact", "email")
        if "extension" in text:
            return FieldMapping("contact", "phone_extension")
        if any(word in text for word in ("phone", "mobile", "cell", "telephone")):
            if "code" not in text:
                return FieldMapping("contact", "phone")
        if "phone type" in text or text == "phone type" or "device type" in text:
            return FieldMapping("contact", "phone_type")

        if "address" in text and ("2" in text or "line 2" in text or "apt" in text):
            return FieldMapping("contact", "address_line2")
        if any(word in text for word in ("address", "street", "address line 1")):
            return FieldMapping("contact", "address_line1")

        if contains_word(text, "city"):
            return FieldMapping("contact", "city")
        if contains_word(text, "county"):
            return FieldMapping("contact", "county")
        if contains_word(text, "state") or contains_word(text, "province"):
            return FieldMapping("contact", "state")
        if "zip" in text or "postal" in text:
            return FieldMapping("contact", "postal_code")
        if contains_word(text, "country") and "phone" not in text:
            return FieldMapping("contact", "country")

        if "linkedin" in text:
            return FieldMapping("contact", "linkedin")
        if "github" in text:
            return FieldMapping("contact", "github")
        if "portfolio" in text:
            return FieldMapping("contact", "portfolio")
        if "website" in text or "personal site" in text:
            return FieldMapping("contact", "website")

    if "privacy" in text:
        return FieldMapping("preferences", "agree_privacy_policy")
    if "terms" in text or "conditions" in text:
        return FieldMapping("preferences", "agree_terms")
    if "job alert" in text or "subscribe" in text or "marketing" in text:
        return FieldMapping("preferences", "job_alerts")

    return None


def map_label_to_key(label: str) -> str | None:
    """Backward-compatible contact-only mapping."""
    mapping = map_label_to_field(label)
    if mapping and mapping.section == "contact":
        return mapping.key
    return None


def should_skip_field(label: str, profile: dict) -> str | None:
    """Return skip reason if this field should not be auto-filled."""
    auto_fill = profile.get("auto_fill", {})
    if not auto_fill.get("eeo", False) and is_eeo_field(label):
        return "EEO field (auto_fill.eeo is false)"
    if not auto_fill.get("legal_attestations", False) and is_legal_field(label):
        return "legal attestation (auto_fill.legal_attestations is false)"
    return None
