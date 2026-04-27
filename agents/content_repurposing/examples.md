# Content Repurposing Agent Examples

## Example Input

```json
{
  "source_type": "insight",
  "source_text": "Most design problems at scale are not creative problems. They are system problems. Quality falls apart when the workflow depends on memory instead of structure.",
  "target_lane": "hernandezdiez.com",
  "audience": "Marketing leaders and design leads",
  "cta": "If this is showing up in your team, I can share how I diagnose it."
}
```

## Example Run

```bash
python3 -m src.main run content --input content_input.json
```

## Notes

- Keep the source text high-signal. The quality of the repurposed drafts depends on the strength of the source idea.
- This agent is intentionally separated from outbound messaging logic.
