# Company Research Agent Examples

## Example Input

```json
{
  "company_name": "ExampleCo",
  "website_url": "https://example.com",
  "linkedin_url": "https://linkedin.com/company/exampleco",
  "notes": [
    "Homepage leads with broad claims before showing category context.",
    "Pricing page uses a different voice than product pages.",
    "Sales deck screenshots look more mature than the public website."
  ]
}
```

## Example Run

```bash
python3 -m src.main run research --input research_input.json
```

## Notes

- Treat `notes` as the current observation layer until you connect live research sources.
- This keeps the system useful immediately while leaving a clear place to add web or LinkedIn connectors later.
