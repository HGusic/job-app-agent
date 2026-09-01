#!/usr/bin/env python3
"""Answer a screening question using LangChain + Ollama + your profile."""

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from src.llm.chain import answer_question


def check_ollama(base_url: str = "http://localhost:11434") -> None:
    try:
        urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=3)
    except (urllib.error.URLError, TimeoutError):
        print("Error: Ollama is not running or not reachable.")
        print("  1. Install from https://ollama.com")
        print("  2. Pull a model:  ollama pull llama3.2")
        print("  3. Start Ollama (usually runs automatically after install)")
        sys.exit(1)


def main() -> None:
    load_dotenv()
    import os

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    check_ollama(base_url)

    parser = argparse.ArgumentParser(description="Answer a job application question")
    parser.add_argument("question", help='e.g. "Why do you want to work here?"')
    parser.add_argument(
        "--job",
        type=Path,
        help="Path to a job description text file (optional)",
    )
    args = parser.parse_args()

    job_description = ""
    if args.job:
        job_description = args.job.read_text().strip()

    question = args.question.strip().rstrip("~")
    print(f"Model: {model}")
    print(f"Question: {question}\n")

    try:
        answer = answer_question(question, job_description=job_description)
    except Exception as exc:
        err = str(exc)
        if "not found" in err.lower() or "404" in err:
            print(f"Error: model {model!r} not found in Ollama.")
            print(f"Run: ollama pull {model}")
            sys.exit(1)
        if "connection" in err.lower():
            print("Error: could not connect to Ollama.")
            print("Make sure Ollama is running: https://ollama.com")
            sys.exit(1)
        raise

    print(f"Answer:\n{answer}")


if __name__ == "__main__":
    main()
