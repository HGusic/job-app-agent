from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "profile.yaml"


def load_profile(path: Path | None = None) -> dict[str, Any]:
    profile_path = path or DEFAULT_PROFILE_PATH
    with profile_path.open() as f:
        data = yaml.safe_load(f) or {}

    return {
        "contact": data.get("contact", {}),
        "summary": data.get("summary", ""),
        "work_history": data.get("work_history", []),
        "education": data.get("education", []),
        "certifications": data.get("certifications", []),
        "screening": data.get("screening", {}),
        "preferences": data.get("preferences", {}),
        "heard_about": data.get("heard_about", []),
        "skills": data.get("skills", []),
        "auto_fill": {
            "eeo": False,
            "legal_attestations": False,
            **data.get("auto_fill", {}),
        },
    }


def get_section_value(profile: dict[str, Any], section: str, key: str) -> Any:
    if section == "heard_about":
        items = profile.get("heard_about", [])
        return items[0] if items else None
    if section in {"skills"}:
        return profile.get(section, [])
    return profile.get(section, {}).get(key)
