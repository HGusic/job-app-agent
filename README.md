# job-app-agent

Personal job application auto-filler. Contact info first.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## Run

Paste a job application URL (must already be on the form page):

```bash
python main.py "https://example.com/apply"
```

Multi-page: fills each step, **you** click Next in the browser, then press Enter in the terminal to fill the next page.

```bash
python main.py "https://example.com/apply" --max-pages 5
```

Optional job description for **LLM essay answers** on the form:

```bash
# Save job posting text to data/job-description.txt, or:
python main.py "https://example.com/apply" --job path/to/job.txt
```

The browser opens and fills:
- **Contact / screening** — from `profile.yaml` via rules (`mapper.py`)
- **Essay textareas** — LangChain + Ollama generates answers (`ask.py` logic, wired in `filler.py`)

Requires Ollama running for essay fields: `ollama serve` + `ollama pull llama3.2`

Profile sections in `data/profile.yaml`:

- `contact` — name, email, phone, address, links
- `screening` — Yes/No answers (work authorization, sponsorship, relocation)
- `preferences` — single checkboxes (privacy policy, terms, job alerts)
- `heard_about` / `skills` — checkbox groups (checks matching labels)
- `auto_fill` — set `eeo` or `legal_attestations` to `true` to allow filling those fields

## Tests

```bash
pytest
```

## LangChain — screening questions (Ollama)

Uses a **local** model via [Ollama](https://ollama.com) — free, no API key.

**1. Install Ollama** from https://ollama.com

**2. Pull a model:**

```bash
ollama pull llama3.2
```

**3. Install Python LLM deps:**

```bash
pip install -e ".[llm]"
cp .env.example .env   # optional — defaults work
```

**4. Ask a question:**

```bash
python ask.py "Why do you want to work here?"
python ask.py "Describe a technical challenge you solved" --job data/job-description.txt
```

Chain is the same LangChain pattern: **prompt → Ollama model → text**.
