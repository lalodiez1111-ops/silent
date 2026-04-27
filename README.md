# Silent Studio Brand Engine

A modular production engine for structured brand-content generation, templates, validation, and audit-ready outputs.

## Positioning

This repository is positioned as the **Silent Studio production engine**.

- It is the execution layer for repeatable brand-content output.
- It is not positioned as a multi-brand personal-content system.
- `hernandezdiez.com` positioning has been removed from this repository scope.

## Primary Scope: Brand Engine Production System

The production path is the Brand Content Engine v2 flow:

`input -> template selection -> generation -> validation -> formatted output`

Core artifacts:

- `src/` for runtime logic and orchestration
- `templates/` for generation templates
- `config/` for brand profiles and risky-word validation settings
- `agents/brand_content/` for sample brand-content inputs

Primary command:

```bash
python3 -m src.main run brand-content --use-sample
```

Alias:

```bash
python3 -m src.main run brand --use-sample
```

## Legacy / Adjacent Capabilities (Kept Temporarily)

The following capabilities currently remain in this repo as **legacy or adjacent modules**:

- `lead` (lead sourcing)
- `research` (company research)
- `content` (content repurposing)

They are still runnable and supported for now, but they are not the core positioning of this repository.

Temporary compatibility command example:

```bash
python3 -m src.main run lead --use-sample
```

### Recommendation (No Move Applied In This Pass)

If you want strict business-lane separation later, move lead/research/content capabilities into a dedicated workspace module (for example `lead-sourcing/`) in a future migration pass. This cleanup pass intentionally keeps code in place for safety.

## Output Location

Generated artifacts are written outside the repo by default:

- `../outputs/brand-engine`

This keeps production outputs and run history out of git-tracked source.

## Repository Structure

```text
agents/
  brand_content/
  lead_sourcing/
  company_research/
  content_repurposing/
config/
  brandProfiles.json
  riskyWords.json
  preferences.example.json
  sources.example.json
templates/
  ad_pack.md
  social_caption.md
  landing_section.md
  outreach_message_templates.md
  content_templates.md
src/
  main.py
  orchestrator.py
  validation.py
  csv_import.py
  utils.py
README.md
requirements.txt
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional local config copies:

```bash
cp config/preferences.example.json config/preferences.json
cp config/sources.example.json config/sources.json
```
