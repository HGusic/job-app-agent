from pathlib import Path

from src.job_description import DEFAULT_JOB_FILE, load_job_description


def test_load_job_description_from_file(tmp_path: Path):
    job_file = tmp_path / "job.txt"
    job_file.write_text("Software engineer role at Acme Corp")
    assert load_job_description(job_file) == "Software engineer role at Acme Corp"


def test_load_job_description_empty_when_missing():
    assert load_job_description(Path("/nonexistent/job.txt")) == ""


def test_default_job_file_path():
    assert DEFAULT_JOB_FILE.name == "job-description.txt"
