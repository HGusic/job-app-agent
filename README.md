# job-app-agent

Personal job application auto-filler. Opens a real browser, fills forms from `data/profile.yaml`, and pauses so you click **Next** yourself.

**Before first run:** fill in `data/profile.yaml` (replace all `XXX` placeholders). See [Configure your profile](#configure-your-profile-required).

For system design and how LangChain is wired, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) (optional — only for essay / long-text answers)

## Setup (once)

```bash
cd ~/Projects/job-app-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,llm]"
playwright install chromium
```

For essay answers, also install and pull a local model:

```bash
# install Ollama from https://ollama.com, then:
ollama pull llama3.2
cp .env.example .env   # optional — defaults work
```

## Configure your profile (required)

**You must fill out `data/profile.yaml` before running.** The repo ships with placeholder `XXX` values only — nothing will fill correctly until you replace them with your real details.

1. Open `data/profile.yaml`
2. Replace every `XXX` with your information
3. Use `""` for fields you want left blank on forms (e.g. `middle_name` if you have none)
4. Set screening answers to `"Yes"` / `"No"` (not `XXX`)
5. Review `preferences`, `heard_about`, and `auto_fill`

| Section | What it fills |
|---------|----------------|
| `contact` | Name, email, phone, address, LinkedIn, etc. |
| `summary` | Context for LLM essay answers |
| `work_history` | Job titles, companies, dates, descriptions |
| `education` | Schools, degrees, field of study |
| `certifications` | Cert names / dates |
| `screening` | Yes/No questions (work auth, sponsorship, citizenship, …) |
| `preferences` | Privacy / terms checkboxes |
| `heard_about` | “How did you hear about us?” |
| `skills` | Skills checkboxes / tags |
| `auto_fill` | Set `eeo` / `legal_attestations` to `true` only if you want those filled |

Do not commit a filled-in profile with personal data if the repo is shared or public.

## How to run

**1. Activate the venv**

```bash
cd ~/Projects/job-app-agent
source .venv/bin/activate
```

**2. (Optional) Start Ollama** — needed only if the form has essay textareas:

```bash
# in a separate terminal
ollama serve
```

**3. Open the application form in your normal browser** and copy the form URL (not just the job listing).

**4. Run the filler**

```bash
python main.py "https://your-job-application-form-url"
```

A Chromium window opens, loads the URL, and fills matching fields from your profile.

### Multi-page forms

The script **never clicks Next or Submit**. Workflow:

1. Script fills the current page and prints what it did
2. You review in the browser and click **Next**
3. Press **Enter** in the terminal to fill the next page
4. Type `q` + Enter to stop early

Limit pages if you want:

```bash
python main.py "https://..." --max-pages 5
```

### Job description for essays

Save the posting text, then pass it so LLM answers can be tailored:

```bash
# default location (auto-loaded if present):
# data/job-description.txt

python main.py "https://..." --job path/to/job.txt
```

## What gets filled

- **Contact / screening / preferences** — rule-based from `profile.yaml`
- **Work history & education** — repeater sections (Add Experience / Add Education)
- **Dropdowns & radios** — matched by label + aliases (e.g. `TX` → Texas, `M.S.` → Master of Science)
- **Essay textareas** — LangChain + Ollama (requires `ollama serve`)

EEO and legal attestation fields are skipped unless you opt in via `auto_fill` in the profile.

## Standalone LLM Q&A

Answer a question from the terminal without opening a browser:

```bash
python ask.py "Why do you want to work here?"
python ask.py "Describe a technical challenge you solved" --job data/job-description.txt
```

## Tests

```bash
source .venv/bin/activate
pytest
```

## Tips / troubleshooting

- **Run as your normal user**, not root — root can show a blank browser on some window managers.
- **Email / address cleared by React forms** — the script fills those last and retries; if they still clear, click the field once and re-run that page.
- **Wrong field values** — check the terminal “Filled” / “Skipped” output; most issues are label mapping in `src/mapper.py`.
- **Headless mode** (no visible browser):

  ```bash
  HEADLESS=1 python main.py "https://..."
  # screenshot saved to data/last-run.png
  ```

- **Browser not visible on i3** — check other workspaces (`Mod+1`…`9`) or floating windows.
