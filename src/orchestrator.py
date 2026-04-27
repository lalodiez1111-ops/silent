"""Lightweight orchestration layer for the solo operator agent system."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .csv_import import load_lead_csv
from .validation import validate_generated_content
from .utils import (
    average_score,
    compact_lines,
    ensure_dir,
    first_sentence,
    lane_voice,
    load_json,
    load_text,
    path_from_root,
    save_json,
    save_text,
    slugify_filename,
    timestamp_slug,
    validate_against_schema,
)


@dataclass
class RunArtifacts:
    """File paths generated for a single agent run."""

    json_path: Path
    markdown_path: Path


class AgentOrchestrator:
    """Coordinates input loading, generation, validation, and output saving."""

    def __init__(self, preferences_path: str | Path, sources_path: str | Path, output_dir: str | Path) -> None:
        self.preferences = load_json(preferences_path)
        self.sources = load_json(sources_path)
        self.output_dir = ensure_dir(output_dir)

    def run(
        self,
        agent: str,
        input_path: str | Path | None = None,
        csv_path: str | Path | None = None,
        limit: int | None = None,
        output_name: str | None = None,
        input_payload: dict[str, Any] | None = None,
    ) -> tuple[Any, str, RunArtifacts]:
        """Run one supported agent and persist its outputs."""
        payload: dict[str, Any]
        if input_payload is not None:
            payload = input_payload
        elif agent == "lead" and csv_path:
            seeds, csv_metadata = load_lead_csv(csv_path, limit=limit)
            payload = {
                "target_market_notes": "Imported from CSV lead list.",
                "seed_companies": seeds,
                "csv_import": csv_metadata,
            }
        elif input_path is not None:
            payload = load_json(input_path)
        else:
            raise ValueError("An input JSON path or CSV path is required.")

        if agent == "lead":
            data, markdown = self._run_lead_sourcing(payload)
            schema_path = path_from_root("agents", "lead_sourcing", "schema.json")
        elif agent == "research":
            data, markdown = self._run_company_research(payload)
            schema_path = path_from_root("agents", "company_research", "schema.json")
        elif agent == "content":
            data, markdown = self._run_content_repurposing(payload)
            schema_path = path_from_root("agents", "content_repurposing", "schema.json")
        elif agent == "brand-content":
            data, markdown = self._run_brand_content(payload)
            schema_path = None
        else:
            raise ValueError(f"Unsupported agent: {agent}")

        if schema_path is not None:
            validate_against_schema(data, schema_path)
        artifacts = self._save_outputs(agent, data, markdown, output_name=output_name)
        return data, markdown, artifacts

    def _save_outputs(self, agent: str, data: Any, markdown: str, output_name: str | None = None) -> RunArtifacts:
        """Persist both machine-readable and human-readable output files."""
        stamp = timestamp_slug()
        name_parts = [stamp, agent]
        if output_name:
            name_parts.append(slugify_filename(output_name))
        base_name = "_".join(name_parts)
        json_path = self.output_dir / f"{base_name}.json"
        markdown_path = self.output_dir / f"{base_name}.md"
        save_json(json_path, data)
        save_text(markdown_path, markdown)
        return RunArtifacts(json_path=json_path, markdown_path=markdown_path)

    def _run_lead_sourcing(self, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        """Score lead seeds and return a prioritized shortlist."""
        # Prompt is loaded so the instructions stay editable even before a real model is plugged in.
        _prompt = load_text(path_from_root("agents", "lead_sourcing", "prompt.md"))
        weights = self.preferences.get("lead_scoring_weights", {})
        seeds = payload.get("seed_companies", [])
        if not seeds and payload.get("use_mock_data"):
            seeds = self._build_mock_lead_seeds()

        leads: list[dict[str, Any]] = []
        for seed in seeds:
            leads.append(self._score_lead(seed, weights))

        leads.sort(key=lambda item: item["priority_score"], reverse=True)
        markdown = self._render_lead_markdown(leads, payload)
        return leads, markdown

    def _build_mock_lead_seeds(self) -> list[dict[str, Any]]:
        """Return bundled mock leads for immediate local testing."""
        return [
            {
                "company_name": "Northstar Cloud",
                "website": "https://northstarcloud.example",
                "source": "mock_sample",
                "signals": [
                    "Hiring for Senior Brand Designer",
                    "Homepage and product pages use inconsistent visual language",
                    "B2B platform with growing sales complexity",
                ],
                "notes": "Strong commercial fit. Likely needs tighter brand and presentation systems before inconsistency spreads further.",
            },
            {
                "company_name": "Aperture Bio Systems",
                "website": "https://aperturebio.example",
                "source": "mock_sample",
                "signals": [
                    "Recently funded",
                    "Website messaging feels credible but fragmented across pages",
                    "Sales materials appear more mature than the public site",
                ],
                "notes": "Good opportunity for a brand and web structure cleanup tied to trust and sales clarity.",
            },
            {
                "company_name": "LedgerLane",
                "website": "https://ledgerlane.example",
                "source": "mock_sample",
                "signals": [
                    "Hiring for Product Designer and Marketing Designer",
                    "Customer stories and landing pages feel assembled from different systems",
                    "Visible growth-stage B2B motion",
                ],
                "notes": "Likely needs cross-functional design governance and a cleaner production system for marketing output.",
            },
        ]

    def _score_lead(self, seed: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
        """Apply practical heuristics to score a lead seed from observed signals."""
        signals = " ".join(seed.get("signals", []))
        notes = seed.get("notes", "")
        combined = f"{signals} {notes}".lower()

        commercial_upside = 3
        if any(keyword in combined for keyword in ["enterprise", "b2b", "funded", "growth", "sales"]):
            commercial_upside = 4
        if any(keyword in combined for keyword in ["global", "platform", "series", "multi-product"]):
            commercial_upside = 5

        urgency_signal = 2
        if any(keyword in combined for keyword in ["hiring", "rebrand", "refresh", "launch", "funded"]):
            urgency_signal = 4
        if any(keyword in combined for keyword in ["urgent", "messy", "inconsistent", "fragmented"]):
            urgency_signal = 5

        fit_with_strengths = 3
        if any(keyword in combined for keyword in ["brand", "presentation", "ux", "workflow", "design system"]):
            fit_with_strengths = 5
        elif any(keyword in combined for keyword in ["marketing", "content", "sales"]):
            fit_with_strengths = 4

        ease_of_outreach_angle = 2
        if notes or signals:
            ease_of_outreach_angle = 4
        if any(keyword in combined for keyword in ["hiring", "inconsistent", "fragmented", "rebrand"]):
            ease_of_outreach_angle = 5

        score_breakdown = {
            "commercial_upside": commercial_upside,
            "urgency_signal": urgency_signal,
            "fit_with_strengths": fit_with_strengths,
            "ease_of_outreach_angle": ease_of_outreach_angle,
        }

        source = seed.get("source", "manual")
        signal_detected = first_sentence(signals) or "Manual seed provided"
        likely_problem = seed.get(
            "likely_problem",
            "Brand and production quality may be depending on people patching inconsistencies instead of a stronger system.",
        )
        suggested_angle = seed.get(
            "suggested_angle",
            "Lead with one visible execution gap, then connect it to system-level consistency, speed, and trust.",
        )
        why_it_matters = seed.get(
            "why_it_matters",
            "Visible inconsistency usually slows production, weakens trust, and creates avoidable rework across sales and marketing.",
        )

        return {
            "company_name": seed.get("company_name", "Unknown company"),
            "website": seed.get("website", ""),
            "source": source,
            "signal_detected": signal_detected,
            "why_it_matters": why_it_matters,
            "likely_problem": likely_problem,
            "suggested_angle": suggested_angle,
            "decision_maker_guess": seed.get(
                "decision_maker_guess",
                "VP Marketing, Head of Brand, Creative Director, or Design Lead",
            ),
            "priority_score": average_score(score_breakdown, weights),
            "notes": notes or "Add a sharper observation before outreach.",
            "score_breakdown": score_breakdown,
        }

    def _render_lead_markdown(self, leads: list[dict[str, Any]], payload: dict[str, Any]) -> str:
        """Create a short, readable markdown shortlist for lead review."""
        lines = [
            "# Lead Sourcing Summary",
            "",
            f"- Target market notes: {payload.get('target_market_notes', 'Not provided')}",
            f"- Source count: {len(leads)}",
        ]
        csv_import = payload.get("csv_import")
        if csv_import:
            lines.extend(
                [
                    f"- CSV import: {csv_import.get('csv_path', 'N/A')}",
                    f"- Mapped headers: {', '.join(sorted(csv_import.get('mapped_headers', {}).keys())) or 'None'}",
                ]
            )
        lines.extend(
            [
            "",
            ]
        )
        if not leads:
            lines.extend(
                [
                    "No lead seeds were provided.",
                    "",
                    "Add `seed_companies` to your input JSON, use `--use-sample`, or import a CSV with `--csv`.",
                ]
            )
            return "\n".join(lines)

        for lead in leads:
            lines.extend(
                [
                    f"## {lead['company_name']} ({lead['priority_score']}/5)",
                    f"- Website: {lead['website'] or 'N/A'}",
                    f"- Source: {lead['source']}",
                    f"- Signal: {lead['signal_detected']}",
                    f"- Why it matters: {lead['why_it_matters']}",
                    f"- Likely problem: {lead['likely_problem']}",
                    f"- Suggested angle: {lead['suggested_angle']}",
                    f"- Decision-maker guess: {lead['decision_maker_guess']}",
                    f"- Notes: {lead['notes']}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _run_company_research(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Synthesize a concise strategic brief from supplied notes and observations."""
        _prompt = load_text(path_from_root("agents", "company_research", "prompt.md"))
        company_name = payload.get("company_name", "Unknown company")
        notes = compact_lines(payload.get("notes", []))
        combined = " ".join(notes).lower()

        brand_maturity = "Mixed"
        if any(keyword in combined for keyword in ["inconsistent", "fragmented", "uneven"]):
            brand_maturity = "Fragmented"
        elif any(keyword in combined for keyword in ["strong", "cohesive", "clear"]):
            brand_maturity = "Maturing but promising"

        website_observations = notes or ["No observation notes supplied yet."]
        messaging_issues = self._extract_issues(
            notes,
            fallback="Messaging may be too broad or too abstract to translate quickly into value.",
            keywords=["message", "claims", "positioning", "copy", "voice", "category"],
        )
        ux_issues = self._extract_issues(
            notes,
            fallback="UX friction still needs to be observed directly; start with page hierarchy, navigation, and conversion flow.",
            keywords=["ux", "navigation", "flow", "page", "journey", "friction", "homepage", "pricing"],
        )
        content_system_issues = self._extract_issues(
            notes,
            fallback="Execution may be relying on one-off page decisions rather than a repeatable content system.",
            keywords=["content", "inconsistent", "fragmented", "template", "system", "workflow", "reuse"],
        )
        presentation_gaps = self._extract_issues(
            notes,
            fallback="Sales and presentation materials may not be fully aligned with the public-facing brand layer.",
            keywords=["deck", "sales", "presentation", "enablement", "pitch"],
        )

        data = {
            "company_name": company_name,
            "business_model": payload.get("business_model", "Needs confirmation; infer from website and external materials."),
            "audience_guess": payload.get("audience_guess", "Likely B2B buyers, partners, or internal stakeholders."),
            "current_brand_maturity": brand_maturity,
            "website_observations": website_observations,
            "messaging_issues": messaging_issues,
            "UX_issues": ux_issues,
            "content_system_issues": content_system_issues,
            "presentation_or_sales_enablement_gaps": presentation_gaps,
            "likely_business_risk_from_current_state": payload.get(
                "likely_business_risk_from_current_state",
                "The current state likely creates avoidable trust loss, slower production, and weaker conversion or sales clarity.",
            ),
            "recommended_service_angle": payload.get(
                "recommended_service_angle",
                "Lead with a systems-level fix: clarify positioning, tighten page logic, and create governed presentation and content structures.",
            ),
            "sample_observation_for_outreach": payload.get(
                "sample_observation_for_outreach",
                "There seems to be a gap between the quality the company is aiming for and the consistency the current system makes easy to maintain.",
            ),
            "confidence_notes": "Higher confidence when notes come from the website, careers page, product pages, decks, or public sales materials.",
        }
        markdown = self._render_research_markdown(data, payload)
        return data, markdown

    def _extract_issues(self, notes: list[str], fallback: str, keywords: list[str]) -> list[str]:
        """Pull note lines that mention specific issue categories."""
        matched = [note for note in notes if any(keyword in note.lower() for keyword in keywords)]
        return matched or [fallback]

    def _render_research_markdown(self, data: dict[str, Any], payload: dict[str, Any]) -> str:
        """Render a short human-readable company brief."""
        return "\n".join(
            [
                f"# Company Research Brief: {data['company_name']}",
                "",
                "## What they do",
                data["business_model"],
                "",
                "## What looks weak",
                "; ".join(data["website_observations"][:3]),
                "",
                "## Why it matters commercially",
                data["likely_business_risk_from_current_state"],
                "",
                "## Best angle for me",
                data["recommended_service_angle"],
                "",
                "## One outreach line",
                data["sample_observation_for_outreach"],
                "",
                f"- Website: {payload.get('website_url', 'N/A')}",
                f"- LinkedIn: {payload.get('linkedin_url', 'N/A')}",
            ]
        )

    def _run_content_repurposing(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Repurpose a single source idea into several practical draft formats."""
        _prompt = load_text(path_from_root("agents", "content_repurposing", "prompt.md"))
        lane = payload.get("target_lane", "hernandezdiez.com")
        source_type = payload.get("source_type", "insight")
        source_text = payload.get("source_text", "").strip()
        cta = payload.get("cta") or self._default_cta(lane)
        audience = payload.get("audience", "Design, marketing, and brand leaders")
        voice = ", ".join(lane_voice(self.preferences, lane))
        thesis = first_sentence(source_text) or "Strong creative output usually depends on stronger systems than most teams realize"
        supporting_point = self._supporting_point(source_text)

        hook_options = [
            f"Most {source_type} work breaks when the system underneath it is weak.",
            f"Quality rarely collapses because people stop caring. It collapses because structure stops helping.",
            f"If the output feels inconsistent, the problem is often upstream from the design itself.",
        ]

        linkedin_post = (
            f"{thesis}.\n\n"
            f"That matters because {supporting_point}.\n\n"
            f"The teams that scale quality well usually do three things: they reduce guesswork, define reusable patterns, and make the right standard easier to repeat.\n\n"
            f"This is where design stops being decoration and starts acting like operational leverage.\n\n"
            f"Audience: {audience}.\n\n"
            f"{cta}"
        )

        short_post_sequence = [
            hook_options[0],
            f"Observation: {thesis}.",
            f"Why it matters: {supporting_point}.",
            "What helps: better templates, clearer rules, and fewer decisions that depend on memory.",
            cta,
        ]

        short_form_video_script = (
            f"Open with: {hook_options[1]}\n"
            f"Point 1: {thesis}.\n"
            f"Point 2: {supporting_point}.\n"
            "Point 3: Better systems improve speed, consistency, and trust at the same time.\n"
            f"Close with: {cta}"
        )

        case_study_outline = [
            f"Context: source type was {source_type} for the {lane} lane.",
            f"Problem: {thesis}.",
            f"Shift: Introduce structure, reusable patterns, and clearer decision rules.",
            "Execution: Show the system choices, not just the final output.",
            "Result: Higher consistency, faster production, and stronger trust in the work.",
            f"Takeaway: {supporting_point}.",
        ]

        headline_options = [
            "Why Design Quality Breaks At Scale",
            "The Real Problem Behind Inconsistent Creative Output",
            "Better Systems, Better Work, Less Rework",
        ]

        data = {
            "target_lane": lane,
            "hook_options": hook_options,
            "linkedin_post": linkedin_post,
            "short_post_sequence": short_post_sequence,
            "short_form_video_script": short_form_video_script,
            "case_study_outline": case_study_outline,
            "headline_options": headline_options,
            "cta_suggestion": cta,
        }
        markdown = self._render_content_markdown(data, voice)
        return data, markdown

    def _run_brand_content(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Run Brand Content Engine v2 flow without affecting other agent flows."""
        required = ["brand_name", "product_name", "audience", "tone", "key_points"]
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(f"Missing required brand content fields: {', '.join(missing)}")

        key_points = payload.get("key_points", [])
        if not isinstance(key_points, list) or not key_points:
            raise ValueError("key_points must be a non-empty list of strings")

        selected_template = self._select_brand_template(payload)
        template_text = load_text(path_from_root("templates", f"{selected_template}.md"))
        brand_profiles = load_json(path_from_root("config", "brandProfiles.json"))
        risky_config = load_json(path_from_root("config", "riskyWords.json"))

        generated_content = self._generate_brand_content(payload, selected_template, template_text, brand_profiles)
        validation = validate_generated_content(generated_content, risky_config)
        timestamp = timestamp_slug()
        summary = {
            "what_was_generated": {
                "ad_headlines": len(generated_content.get("ad_headlines", [])),
                "short_descriptions": len(generated_content.get("short_descriptions", [])),
                "long_descriptions": 1 if generated_content.get("long_description") else 0,
            },
            "tone_used": generated_content.get("tone_used", payload.get("tone", "Not specified")),
            "issues_found": [item.get("term", "") for item in validation.get("findings", [])],
        }
        data = {
            "metadata": {
                "engine": "brand-content-v2",
                "template": selected_template,
            },
            "input": payload,
            "generated_content": generated_content,
            "validation": validation,
            "summary": summary,
            "timestamp": timestamp,
        }
        markdown = self._render_brand_content_markdown(data)
        return data, markdown

    def _select_brand_template(self, payload: dict[str, Any]) -> str:
        """Select a known template name from payload with safe default."""
        requested = str(payload.get("template", "ad_pack")).strip().lower().replace("-", "_")
        valid_templates = {"ad_pack", "social_caption", "landing_section"}
        return requested if requested in valid_templates else "ad_pack"

    def _generate_brand_content(
        self,
        payload: dict[str, Any],
        template_name: str,
        template_text: str,
        brand_profiles: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate deterministic brand copy using template and profile constraints."""
        brand_name = str(payload["brand_name"]).strip()
        product_name = str(payload["product_name"]).strip()
        audience = str(payload["audience"]).strip()
        tone = str(payload["tone"]).strip()
        key_points = [str(point).strip() for point in payload["key_points"] if str(point).strip()]
        if not key_points:
            raise ValueError("key_points must include at least one non-empty value")

        profile_key = slugify_filename(brand_name)
        profile = brand_profiles.get(profile_key, brand_profiles.get("default", {}))
        effective_tone = profile.get("tone") if profile_key in brand_profiles and profile.get("tone") else tone

        audience_label = self._audience_label(audience)
        product_reference = self._product_reference(product_name)
        benefits = self._brand_benefits_from_key_points(key_points, effective_tone)
        primary = benefits[0]
        secondary = benefits[1] if len(benefits) > 1 else benefits[0]
        tertiary = benefits[2] if len(benefits) > 2 else benefits[0]

        ad_headlines = [
            self._polish_brand_copy(f"{brand_name}: Compare With Clarity", effective_tone),
            self._polish_brand_copy(f"Clear Guidance for {audience_label}", effective_tone),
            self._polish_brand_copy(self._headline_from_benefit(primary), effective_tone),
        ]
        short_descriptions = [
            self._polish_brand_copy(
                f"{product_reference} gives {audience_label.lower()} a clearer way to compare coverage options.",
                effective_tone,
            ),
            self._polish_brand_copy(
                f"Built by {brand_name}, it supports {secondary} and {tertiary} without pressure.",
                effective_tone,
            ),
        ]
        long_description = (
            f"{brand_name} introduces {product_name} for {audience_label.lower()}. "
            f"Using a {effective_tone} voice, the offer centers on {primary}, {secondary}, and {tertiary}. "
            f"It keeps the path to a quote or consultation clear, educational, and easier to review."
        )
        return {
            "template_used": template_name,
            "template_preview": template_text.splitlines()[:8],
            "tone_used": effective_tone,
            "ad_headlines": ad_headlines,
            "short_descriptions": short_descriptions,
            "long_description": long_description,
            "applied_constraints": profile.get("constraints", []),
        }

    def _product_reference(self, product_name: str) -> str:
        """Return a readable product reference for sentence copy."""
        lowered = product_name.lower()
        if "coverage" in lowered and "comparison" in lowered and "experience" in lowered:
            return "The comparison experience"
        return product_name

    def _headline_from_benefit(self, benefit: str) -> str:
        """Convert a benefit phrase into a compact headline."""
        lowered = benefit.lower()
        if "coverage" in lowered and "comparison" in lowered:
            return "Clearer Coverage Choices"
        if "state-agnostic" in lowered:
            return "Guidance That Travels"
        if "review-ready" in lowered:
            return "Review-Ready Education"
        return benefit.title()

    def _audience_label(self, audience: str) -> str:
        """Condense long audience notes into copy-friendly labels."""
        cleaned = " ".join(audience.replace("/", " ").split()).strip(" .,")
        lowered = cleaned.lower()
        if "insurance" in lowered and any(word in lowered for word in ["people", "consumer", "personal"]):
            return "Insurance Shoppers"
        if "brand" in lowered and "leader" in lowered:
            return "Brand Leaders"
        if "marketing" in lowered and "leader" in lowered:
            return "Marketing Leaders"
        if "team" in lowered:
            return "Teams"

        words = cleaned.split()
        if len(words) <= 4:
            return cleaned.title()
        return " ".join(words[:4]).title()

    def _brand_benefits_from_key_points(self, key_points: list[str], tone: str) -> list[str]:
        """Turn raw constraints and notes into concise benefit phrases."""
        benefits: list[str] = []
        for point in key_points:
            benefit = self._benefit_from_key_point(point)
            benefit = self._polish_brand_copy(benefit, tone).strip(" .")
            if benefit and benefit.lower() not in [item.lower() for item in benefits]:
                benefits.append(benefit)

        fallback = ["clearer coverage comparison", "review-ready guidance", "a calmer quote path"]
        for item in fallback:
            if len(benefits) >= 3:
                break
            if item.lower() not in [benefit.lower() for benefit in benefits]:
                benefits.append(item)
        return benefits

    def _benefit_from_key_point(self, key_point: str) -> str:
        """Map common raw proof-brand notes into safer benefit language."""
        lowered = " ".join(key_point.lower().split())
        if "compare" in lowered and "coverage" in lowered:
            return "clearer coverage comparison"
        if "state-agnostic" in lowered or "unsupported claims" in lowered:
            return "state-agnostic guidance"
        if "quote" in lowered or "consultation" in lowered:
            return "a calm path to next steps"
        if "educational" in lowered or "review-ready" in lowered or "regulated" in lowered:
            return "review-ready education"

        cleaned = key_point.strip(" .")
        replacements = {
            "Help people ": "",
            "Use ": "",
            "Guide users toward ": "",
            "Keep messaging ": "",
        }
        for source, replacement in replacements.items():
            cleaned = cleaned.replace(source, replacement)
        return cleaned[:80].strip(" ,.")

    def _polish_brand_copy(self, copy: str, tone: str) -> str:
        """Apply tone-aware cleanup without changing output structure."""
        cleaned = " ".join(copy.split())
        if "compliance-aware" in tone.lower():
            replacements = {
                "guaranteed approval": "approval expectations",
                "guaranteed": "specific",
                "guarantee": "support",
                "best": "strong",
                "no risk": "lower uncertainty",
                "lowest": "competitive",
                "instant approval": "streamlined review",
            }
            lowered = cleaned.lower()
            for risky, safer in replacements.items():
                while risky in lowered:
                    start = lowered.index(risky)
                    end = start + len(risky)
                    cleaned = f"{cleaned[:start]}{safer}{cleaned[end:]}"
                    lowered = cleaned.lower()
        return cleaned

    def _render_brand_content_markdown(self, data: dict[str, Any]) -> str:
        """Render brand-content output into a client-ready markdown deliverable."""
        template_titles = {
            "ad_pack": "Ad Pack",
            "social_caption": "Social Caption",
            "landing_section": "Landing Section",
        }
        generated = data["generated_content"]
        validation = data["validation"]
        template_key = data["metadata"]["template"]
        template_title = template_titles.get(template_key, template_key.replace("_", " ").title())
        findings = validation.get("findings", [])
        overall_status = validation.get("overall_status", validation.get("status", "approved"))
        overall_risk = validation.get("risk_level", "low")
        finding_terms = [item.get("term", "") for item in findings if item.get("term")]

        summary_lines = [
            "## Summary",
            f"- Generated: 3 ad headlines, 2 short descriptions, and 1 long description for {data['input']['product_name']}.",
            f"- Tone used: {generated.get('tone_used', data['input'].get('tone', 'Not specified'))}.",
            f"- Validation: {overall_status} ({overall_risk} risk).",
        ]
        if finding_terms:
            summary_lines.append(f"- Issues found: {', '.join(finding_terms)}.")
        else:
            summary_lines.append("- Issues found: none.")

        lines = [
            f"# {template_title}",
            "",
            "## Content Brief",
            f"- Brand: {data['input'].get('brand_name', 'N/A')}",
            f"- Product: {data['input'].get('product_name', 'N/A')}",
            f"- Audience: {data['input'].get('audience', 'N/A')}",
            f"- Template type: {template_title}",
            "",
            "## Tone Summary",
            f"- Requested tone: {data['input'].get('tone', 'N/A')}",
            f"- Applied tone: {generated.get('tone_used', data['input'].get('tone', 'N/A'))}",
            "",
            "## Validation Review",
            f"- Status: {overall_status}",
            f"- Risk level: {overall_risk}",
            f"- Flagged terms: {', '.join(finding_terms) or 'None'}",
            "",
            "## Validation Findings",
        ]
        if findings:
            for item in findings:
                alternatives = ", ".join(item.get("alternatives", [])) or "results can vary"
                risk = str(item.get("risk_level", "medium")).capitalize()
                lines.extend(
                    [
                        f"- Term: \"{item.get('term', '')}\"",
                        f"  Risk: {risk}",
                        f"  Reason: {item.get('reason', 'Language may create compliance risk.')}",
                        f"  Suggested alternatives: {alternatives}",
                        f"  Occurrences: {item.get('occurrences', 1)}",
                    ]
                )
        else:
            lines.append("- No risky terms were detected.")

        lines.extend(
            [
                "",
                "## Ad Headlines",
            ]
        )
        lines.extend(f"- {item}" for item in generated["ad_headlines"])
        lines.extend(["", "## Short Descriptions"])
        lines.extend(f"- {item}" for item in generated["short_descriptions"])
        lines.extend(["", "## Long Description", generated["long_description"], ""])
        lines.extend(summary_lines)
        return "\n".join(lines)

    def _supporting_point(self, source_text: str) -> str:
        """Pull a concise supporting observation from the source text."""
        words = " ".join(source_text.split()).split()
        if len(words) < 12:
            return "teams lose time and quality when structure is vague"
        excerpt = " ".join(words[:20]).strip(" .,")
        return excerpt[0].lower() + excerpt[1:] if excerpt else "teams lose time and quality when structure is vague"

    def _default_cta(self, lane: str) -> str:
        """Return a lane-appropriate default call to action."""
        if lane == "SilentStudio":
            return "If this pattern is showing up in your team, I can usually tell where to start within a short review."
        return "If this is relevant to the way you work, I can share more detailed breakdowns like this."

    def _render_content_markdown(self, data: dict[str, Any], voice: str) -> str:
        """Render the content outputs in a compact review format."""
        lines = [
            f"# Content Repurposing Output ({data['target_lane']})",
            "",
            f"- Voice anchors: {voice or 'Not configured'}",
            "",
            "## Hook Options",
        ]
        lines.extend(f"- {hook}" for hook in data["hook_options"])
        lines.extend(
            [
                "",
                "## LinkedIn Post",
                data["linkedin_post"],
                "",
                "## Short Post Sequence",
            ]
        )
        lines.extend(f"- {item}" for item in data["short_post_sequence"])
        lines.extend(
            [
                "",
                "## Short-Form Video Script",
                data["short_form_video_script"],
                "",
                "## Case Study Outline",
            ]
        )
        lines.extend(f"- {item}" for item in data["case_study_outline"])
        lines.extend(
            [
                "",
                "## Headline Options",
            ]
        )
        lines.extend(f"- {item}" for item in data["headline_options"])
        lines.extend(
            [
                "",
                "## CTA Suggestion",
                data["cta_suggestion"],
            ]
        )
        return "\n".join(lines)


def placeholder_collect_external_signals() -> None:
    """Placeholder for future scraping or API integration."""
    # TODO: Add a lead source connector here for LinkedIn jobs, funding databases, or manual exports.
    return None
