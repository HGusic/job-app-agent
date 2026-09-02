# Architecture

How `job-app-agent` is structured, what each layer does, and how LangChain fits in.

## High-level picture

The tool has **two halves** that share one profile:

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│  Load profile → open browser → fill page(s) → pause for you │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌─────────────────────┐               ┌─────────────────────┐
│  Rule-based filler  │               │  LangChain + Ollama │
│  (most fields)      │               │  (essay textareas)  │
└─────────────────────┘               └─────────────────────┘
         │                                       │
         ▼                                       ▼
   data/profile.yaml  ◄──────────────────────────┘
```

| Half | Technology | Responsibility |
|------|------------|----------------|
| Browser filler | Playwright | Find fields, map labels → profile keys, type/select values |
| LLM answers | LangChain + Ollama | Generate first-person answers for open-ended questions |

There is **no LangGraph agent loop yet**. Navigation and field choice are scripted; the LLM only answers text questions.

---

## Directory layout

```
job-app-agent/
├── main.py                 # CLI entry: open URL, multi-page fill loop
├── ask.py                  # CLI entry: answer one question (no browser)
├── data/
│   └── profile.yaml        # Your facts (contact, jobs, screening, …)
├── src/
│   ├── profile.py          # Load YAML → dict
│   ├── mapper.py           # Label text → FieldMapping (section + key)
│   ├── experience_mapper.py# Work / education label mapping
│   ├── filler.py           # Orchestrates all fill passes on a page
│   ├── dropdown_fill.py    # Native <select> + custom comboboxes
│   ├── select_match.py     # Option matching + aliases (TX→Texas, etc.)
│   ├── repeater_fill.py    # Multi-entry work history / education
│   ├── navigation.py       # Next-button helpers (not auto-clicked)
│   ├── job_description.py  # Optional job posting text for LLM
│   └── llm/
│       ├── chain.py        # LangChain prompt → Ollama → string
│       └── context.py      # profile.yaml → readable LLM context
└── tests/                  # Unit tests for mappers, matching, etc.
```

---

## Runtime flow (`main.py`)

```
1. load_profile() + optional job description
2. Launch Chromium, goto URL
3. For each page (up to --max-pages):
     a. fill_form_fields(page, profile, job_description)
     b. Print filled / skipped actions
     c. Wait: you click Next in the browser, then Enter in the terminal
4. Screenshot → data/last-run.png
5. Leave browser open until you press Enter
```

The script **never** clicks Next or Submit. You stay in control of submission.

---

## How a page gets filled (`filler.fill_form_fields`)

Passes run in a fixed order:

```
1. Radio groups          (Yes/No screening)
2. Checkboxes            (preferences, heard_about, skills)
3. Text + native selects (contact, etc.)
4. Custom dropdowns      (combobox / listbox widgets)
5. Work history repeater
6. Education repeater
7. Essay textareas       ← LangChain here
8. Late contact fields   (email, address, city, zip — last so React
                          forms don't wipe them)
```

### Label → value path (rule-based)

```
DOM control
   → accessible name / nearby question text
   → map_label_to_field()  (or experience_mapper for jobs/school)
   → get_section_value(profile, section, key)
   → fill text / select option / check radio
```

Examples:

| Form label | Mapping | Profile value |
|------------|---------|---------------|
| First Name | `contact.first_name` | from YAML |
| Middle Name | `contact.middle_name` | `""` → leave blank |
| Require sponsorship? | `screening.requires_sponsorship` | `"No"` |
| How did you hear about us? | `heard_about.source` | `"LinkedIn"` |
| Company Name | work repeater `company` | from `work_history[]` |

Matching is **not** LLM-based. It uses keyword rules, aliases (`M.S.` → Master of Science), and Yes/No variants.

### What gets skipped

- EEO fields (race, gender, veteran, …) unless `auto_fill.eeo: true`
- Legal attestations unless `auto_fill.legal_attestations: true`
- Fields with no mapping
- Empty profile values (e.g. blank middle name)

---

## LangChain process

LangChain is used **only** for open-ended questions (essay textareas and `ask.py`).

### Components

| Piece | Package / file | Role |
|-------|----------------|------|
| Prompt | `langchain_core.prompts.ChatPromptTemplate` | System + human message template |
| Model | `langchain_ollama.ChatOllama` | Local Ollama chat model (default `llama3.2`) |
| Parser | `langchain_core.output_parsers.StrOutputParser` | Model message → plain string |
| Context | `src/llm/context.py` | Turns `profile.yaml` into readable text |
| Chain | `src/llm/chain.py` | Wires prompt \| model \| parser (LCEL) |

### LCEL chain

```
ChatPromptTemplate  →  ChatOllama  →  StrOutputParser
       │                    │                │
   inserts profile,    calls Ollama      returns answer
   job text, question  at localhost      as str
```

In code:

```python
PROMPT | get_llm() | StrOutputParser()
```

That is LangChain Expression Language (LCEL): pipe runnable stages together.

### Prompt contents

**System:** answer screening/essay questions; use only profile facts; first person; concise.

**Human template:**

```
Candidate profile:
{profile}

Job description:
{job_description}

Question:
{question}

Answer:
```

- `{profile}` — output of `format_profile()` (summary, contact, jobs, education, screening, skills)
- `{job_description}` — optional posting text, or `(not provided)`
- `{question}` — usually the textarea’s accessible label on the form

### When the browser calls it

In `fill_essay_fields()`:

1. Find visible `<textarea>`s
2. Skip if already mapped to a profile value, already filled, or blocked by skip rules
3. Treat the field label as the question
4. Call `answer_question(question, job_description)` (sync, run in a thread executor)
5. Type the returned string into the textarea with React-aware fill

Requires:

- `pip install -e ".[llm]"`
- `ollama serve` + `ollama pull llama3.2` (or whatever `OLLAMA_MODEL` is)
- `auto_fill.essay: true` in the profile (default)

### Standalone path (`ask.py`)

Same chain, no Playwright:

```bash
python ask.py "Why do you want to work here?"
python ask.py "Describe a challenge" --job data/job-description.txt
```

Useful for testing prompts without opening a form.

### Config

From `.env` / environment (see `.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `OLLAMA_MODEL` | `llama3.2` | Model name in Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama HTTP API |

---

## Data model (`data/profile.yaml`)

**Required setup:** `data/profile.yaml` in the repo is a **template** filled with `XXX` placeholders. Replace those with your real contact info, work history, education, and screening answers before running `main.py` or `ask.py`. Empty strings (`""`) mean leave the form field blank.

```
contact          → text / dropdown contact fields
work_history[]   → repeater (company, title, dates, highlights)
education[]      → repeater (school, degree, specialization, …)
screening        → Yes/No radios & dropdowns
preferences      → single checkboxes
heard_about[]    → “how did you hear” dropdown / checkboxes
skills[]         → skill checkboxes
auto_fill        → feature flags (eeo, legal, essay)
summary          → fed to LLM context
```

The rule-based filler reads **keys**. The LLM reads a **formatted dump** of the same file. If values are still `XXX`, forms and essay answers will contain placeholders.

---

## Design boundaries (intentional)

| Concern | Approach today | Not yet |
|---------|----------------|---------|
| Field identity | Keyword mapper | LLM / vision field detection |
| Values for known fields | Profile YAML | LLM invention |
| Essay answers | LangChain + Ollama | Multi-turn agent |
| Multi-page | User clicks Next | Auto-navigation agent |
| Orchestration | Linear `main.py` loop | LangGraph state machine |

That split keeps deterministic fills reliable and cheap, and reserves the LLM for writing where rules cannot help.

---

## Related docs

- [README.md](README.md) — setup and how to run
- `src/llm/chain.py` — chain implementation
- `src/filler.py` — page fill orchestration
