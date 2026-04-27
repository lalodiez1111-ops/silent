# Solo Operator Agent System

This project is a lean Python scaffold for a solo-operator agent system that supports two separate business lanes:

- `SilentStudio`: outbound opportunity generation, lead qualification, research, and outreach preparation.
- `hernandezdiez.com`: authority building through content repurposing, case-study publishing, and thought leadership drafts.

The system is built for real execution, not demos. It keeps strategic judgment with you and gives AI or structured logic the repeatable production work around sourcing, research synthesis, and content repurposing.

## What The System Does

- Runs three modular agents from one entrypoint.
- Loads editable prompts and JSON schemas from disk.
- Saves every run to `/output` with timestamps.
- Produces both machine-friendly JSON and human-readable Markdown.
- Keeps sourcing, research, and content lanes separated unless you explicitly merge them later.

## Agents

1. `Lead Sourcing Agent`
   Finds and scores companies that show likely need for brand systems, presentation systems, web UX cleanup, content production systems, or cross-format design execution.

2. `Company Research Agent`
   Builds a concise strategic brief so you can show up sharper for outreach, calls, or qualification.

3. `Content Repurposing Agent`
   Turns one idea, case study, insight, or teardown into multiple content drafts while keeping the positioning practical and commercially aware.

## Project Structure

```text
agents/
  lead_sourcing/
    sample_input.json
    prompt.md
    schema.json
    examples.md
  company_research/
    sample_input.json
    prompt.md
    schema.json
    examples.md
  content_repurposing/
    sample_input.json
    prompt.md
    schema.json
    examples.md
config/
  sources.example.json
  preferences.example.json
templates/
  outreach_message_templates.md
  content_templates.md
src/
  csv_import.py
  __init__.py
  main.py
  orchestrator.py
  utils.py
output/
  .gitkeep
README.md
requirements.txt
```

## Setup

1. Use Python 3.10+.
2. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the example config files and edit them for your workflow:

```bash
cp config/preferences.example.json config/preferences.json
cp config/sources.example.json config/sources.json
```

## How To Run

The project uses a single entry command:

```bash
python3 -m src.main run <agent> --input <path-to-input-json>
```

Or use the bundled sample input:

```bash
python3 -m src.main run <agent> --use-sample
```

Available agents:

- `lead`
- `research`
- `content`

Optional flags:

- `--preferences config/preferences.json`
- `--sources config/sources.json`
- `--output-dir output`
- `--use-sample`
- `--csv path/to/file.csv`
- `--limit 25`
- `--output-name weekly-prospects`

### Run The Lead Agent

```bash
python3 -m src.main run lead --input lead_input.json
```

### Run The Lead Agent With A CSV File

```bash
python3 -m src.main run lead --csv agents/lead_sourcing/sample_leads.csv
```

### Limit CSV Rows And Name The Output

```bash
python3 -m src.main run lead --csv agents/lead_sourcing/sample_leads.csv --limit 2 --output-name weekly-prospects
```

### Test The Lead Agent Immediately With Sample Data

```bash
python3 -m src.main run lead --use-sample
```

If you want the exact bundled sample file path:

```bash
python3 -m src.main sample lead
```

### Run The Research Agent

```bash
python3 -m src.main run research --input research_input.json
```

### Run The Content Agent

```bash
python3 -m src.main run content --input content_input.json
```

## Input Shape

Inputs are plain JSON files so you can create them manually, generate them elsewhere, or later connect them to Notion, Airtable, Clay, or a spreadsheet export.

See each agent's `examples.md` for example payloads and notes.

Bundled sample files are included for immediate testing:

- `agents/lead_sourcing/sample_input.json`
- `agents/lead_sourcing/sample_leads.csv`
- `agents/company_research/sample_input.json`
- `agents/content_repurposing/sample_input.json`

## Lead CSV Import

The Lead Sourcing Agent can now ingest real exported prospect lists through CSV without changing the scoring architecture.

Supported command:

```bash
python3 -m src.main run lead --csv path/to/file.csv
```

Optional CSV flags:

- `--limit` to cap imported rows
- `--output-name` to label output files

Flexible header mapping is supported for common variations, for example:

- `company`, `company_name`, `account` -> `company_name`
- `website`, `url`, `domain` -> `website`
- `source`, `origin`, `list_source` -> `source`
- `signal`, `trigger`, `reason` -> `signal_detected`
- `notes`, `comments`, `observation` -> `notes`

Additional supported columns include:

- `decision_maker_guess`
- `geography`
- `industry`
- `hiring_signal`
- `funding_signal`
- `brand_observation`

The CSV importer normalizes rows into the same internal lead seed structure already used by the lead scorer. Missing columns are handled gracefully.

## Prompt And Schema Customization

- Edit `agents/*/prompt.md` to change the agent instructions and voice.
- Edit `agents/*/schema.json` to change or extend the structured output contract.
- The Python layer validates outputs against these schemas when possible.

This makes the project easy to swap from heuristic logic to a real model provider later without changing the surrounding structure.

## How To Connect Later To Notion Or Airtable

Keep this system as the generation layer and add a connector in `src/utils.py` or a future `src/connectors.py`.

Suggested pattern:

1. Run agent locally.
2. Save validated JSON output.
3. Map fields to your target database.
4. Push records using the provider SDK or HTTP API.

Examples of future integrations:

- Notion database item creation from lead or research outputs.
- Airtable row creation for lead pipelines or content planning.
- Google Sheets append for quick shortlist tracking.

## Suggested Next Improvements

Small, useful steps in the right order:

1. Add one real provider integration for research and drafting.
2. Add CSV export or spreadsheet sync after lead review.
3. Add a Notion or Airtable export command.
4. Add a light review queue so you can approve, reject, or rewrite outputs before they move anywhere else.
5. Add a small prompt registry so lane-specific voice rules can be versioned independently.

## Practical Notes

- This scaffold does not invent API credentials.
- External web scraping or model calls are intentionally abstracted behind placeholder functions.
- The Lead Sourcing Agent works now with manual seeds, bundled mock data, and CSV imports. Live lead collection from job boards or funding sources still needs a connector later.
- Final strategy, taste, and outreach voice remain with you by design.
