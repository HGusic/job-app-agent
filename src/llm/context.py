"""Format profile data as LLM context."""

from typing import Any


def format_profile(profile: dict[str, Any]) -> str:
    """Turn profile.yaml data into readable context for prompts."""
    lines: list[str] = []

    summary = profile.get("summary", "")
    if summary:
        lines.append("Summary:")
        lines.append(f"  {summary.strip()}")

    contact = profile.get("contact", {})
    if contact:
        lines.append("Contact:")
        for key, value in contact.items():
            if value:
                lines.append(f"  {key}: {value}")

    work_history = profile.get("work_history", [])
    if work_history:
        lines.append("Work history:")
        for job in work_history:
            dates = f"{job.get('start', '')} – {job.get('end', 'Present')}"
            lines.append(f"  {job.get('title', '')} at {job.get('company', '')} ({dates})")
            for highlight in job.get("highlights", []):
                lines.append(f"    - {highlight}")

    education = profile.get("education", [])
    if education:
        lines.append("Education:")
        for edu in education:
            line = f"  {edu.get('degree', '')}, {edu.get('school', '')}"
            if edu.get("graduation"):
                line += f" (graduated {edu['graduation']})"
            lines.append(line)
            if edu.get("specialization"):
                lines.append(f"    Specialization: {edu['specialization']}")
            if edu.get("honors"):
                lines.append(f"    Honors: {edu['honors']}")

    certifications = profile.get("certifications", [])
    if certifications:
        lines.append("Certifications:")
        for cert in certifications:
            line = f"  {cert.get('name', '')}"
            if cert.get("issued"):
                line += f" (issued {cert['issued']})"
            lines.append(line)

    screening = profile.get("screening", {})
    if screening:
        lines.append("Screening answers:")
        for key, value in screening.items():
            if value is not None and value != "":
                lines.append(f"  {key}: {value}")

    skills = profile.get("skills", [])
    if skills:
        lines.append(f"Skills: {', '.join(skills)}")

    return "\n".join(lines) if lines else "(empty profile)"
