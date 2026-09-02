"""Map work history and education form labels to profile keys."""

from src.mapper import normalize_label


def map_work_field(label: str) -> str | None:
    text = normalize_label(label)
    if not text:
        return None

    if "job title" in text or text in {"title", "position", "role"}:
        return "title"
    if "company name" in text or "company" in text or "employer" in text:
        return "company"
    if text == "from" or "start date" in text or "date from" in text:
        return "start"
    if text == "to" or "end date" in text or "date to" in text:
        return "end"
    if "role description" in text or "job description" in text:
        return "description"
    if "description" in text and ("role" in text or "responsibilit" in text):
        return "description"
    if "currently work" in text or ("current" in text and "work" in text):
        return "current"

    return None


def map_education_field(label: str) -> str | None:
    text = normalize_label(label)
    if not text:
        return None

    if "school" in text or "university" in text or "institution" in text or "college" in text:
        return "school"
    if "degree" in text:
        return "degree"
    if "field of study" in text or "major" in text or "discipline" in text:
        return "specialization"
    if "area of study" in text or "program of study" in text or text == "concentration":
        return "specialization"
    if "graduation" in text or "grad date" in text:
        return "graduation"

    return None


def work_entry_value(entry: dict, key: str) -> str | bool:
    if key == "description":
        highlights = entry.get("highlights", [])
        if not highlights:
            return ""
        return "\n".join(f"• {item}" for item in highlights)
    if key == "current":
        return bool(entry.get("current", False))
    value = entry.get(key, "")
    return str(value) if value is not None else ""


def education_entry_value(entry: dict, key: str) -> str:
    if key == "specialization":
        if entry.get("specialization"):
            return str(entry["specialization"])
        degree = str(entry.get("degree", "") or "")
        if "computer science" in degree.casefold():
            return "Computer Science"
    return str(entry.get(key, "") or "")
