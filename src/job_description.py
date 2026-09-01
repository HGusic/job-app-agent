"""Load optional job description for LLM context."""

import os
from pathlib import Path

DEFAULT_JOB_FILE = Path(__file__).resolve().parent.parent / "data" / "job-description.txt"


def load_job_description(path: Path | None = None) -> str:
    if path and path.is_file():
        return path.read_text().strip()

    env_path = os.environ.get("JOB_DESCRIPTION_FILE", "")
    if env_path and Path(env_path).is_file():
        return Path(env_path).read_text().strip()

    if DEFAULT_JOB_FILE.is_file():
        return DEFAULT_JOB_FILE.read_text().strip()

    return ""
