# Lead Sourcing Agent Examples

## Example Input

```json
{
  "target_market_notes": "B2B SaaS and professional services companies with visible sales, product marketing, or growth complexity.",
  "keywords": ["design systems", "brand designer", "sales enablement", "rebrand"],
  "geography_constraints": ["US", "UK"],
  "seed_companies": [
    {
      "company_name": "ExampleCo",
      "website": "https://example.com",
      "source": "LinkedIn jobs",
      "signals": [
        "Hiring for brand designer",
        "Recently refreshed homepage",
        "Product pages feel inconsistent"
      ],
      "notes": "Looks enterprise-facing. Presentation layer feels fragmented."
    }
  ]
}
```

## Example Run

```bash
python3 -m src.main run lead --input lead_input.json
```

## Sample Run

```bash
python3 -m src.main run lead --use-sample
```

## CSV Run

```bash
python3 -m src.main run lead --csv agents/lead_sourcing/sample_leads.csv --limit 3 --output-name weekly-prospects
```

## Notes

- `seed_companies` can come from manual research, a spreadsheet export, or a future connector.
- `use_mock_data` can be set to `true` in the input JSON to use bundled sample seeds for immediate testing.
- CSV import supports flexible headers and normalizes rows into the same internal lead structure used by the scorer.
- If you later wire in a real sourcing provider, keep the output contract the same.
