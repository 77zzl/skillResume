# Output contract and quality gates

## Compiled manifest

The renderer accepts a JSON manifest with this minimum shape:

```json
{
  "name": "Candidate name",
  "headline": "Targeted professional headline",
  "contact": ["phone", "email", "city"],
  "target_role": "Target role",
  "summary": "Short evidence-backed summary",
  "skills": [
    {"label": "Python / backend", "items": ["Python", "Django", "Docker"]}
  ],
  "experience": [
    {
      "role": "Role",
      "org": "Organization",
      "date": "2024.01 - 2025.01",
      "bullets": ["Action + method + sourced result"],
      "evidence_ids": ["E-001"]
    }
  ],
  "projects": [],
  "education": [],
  "audit": {
    "jd_id": "JD-2026-001",
    "intake": {
      "asked": true,
      "generation_mode": "full",
      "fields": [
        {"field": "target_jd", "status": "provided", "impact": "high"},
        {"field": "contact", "status": "missing", "impact": "medium"}
      ],
      "missing_critical": [],
      "missing_high_value": ["contact"],
      "follow_up_questions": ["如需投递，请补充希望展示的邮箱或电话"]
    },
    "research": {
      "as_of": "2026-09-16",
      "market": "中国大陆",
      "route": ["employer_careers", "domestic_platforms", "career_guidance", "template_references"],
      "role_sources": [
        {"title": "Source title", "url": "https://example.org/job", "signal": "Python + deployment experience", "scope": "AI application roles", "source_type": "domestic_platform_posting", "limitations": []}
      ],
      "template_sources": [
        {"title": "Source title", "url": "https://example.org/template", "signal": "single-column, standard headings", "scope": "ATS"}
      ],
      "signals_applied": ["put proven Python experience in summary and first project"]
    },
    "company_recommendations": {
      "requested": true,
      "default_count": 20,
      "requested_count": 20,
      "returned_count": 20,
      "market": "中国大陆",
      "locations": ["上海"],
      "source_route": ["employer_careers", "domestic_platforms"],
      "as_of": "2026-09-16",
      "items": [
        {
          "rank": 1,
          "company": "Example Company",
          "city": "上海",
          "market": "中国大陆",
          "status": "open",
          "matching_role": "Backend Engineer",
          "fit_score": 78,
          "why_fit": ["后端服务经验与岗位要求相交"],
          "evidence_ids": ["E-001"],
          "gaps": ["未提供生产环境 Docker 经验"],
          "sources": [
            {
              "title": "Example Company careers",
              "url": "https://example.org/jobs/1",
              "source_type": "employer_careers",
              "platform": "company website",
              "retrieved_at": "2026-09-16"
            }
          ]
        }
      ],
      "limitations": []
    },
    "styles_rendered": ["ats", "modern", "research"],
    "selected_style": "ats",
    "deliverables": {
      "text_identity": {
        "source_manifest": "compiled_resume.json",
        "same_text_across_styles": true
      },
      "styles": [
        {"style": "ats", "html": "resume-ats.html", "docx": "resume-ats.docx", "pdf": "resume-ats.pdf"},
        {"style": "modern", "html": "resume-modern.html", "docx": "resume-modern.docx", "pdf": "resume-modern.pdf"},
        {"style": "research", "html": "resume-research.html", "docx": "resume-research.docx", "pdf": "resume-research.pdf"}
      ]
    },
    "conversion": {
      "mode": "new_generation | edited_docx_to_pdf",
      "source_docx": null,
      "output_pdf": null,
      "content_preserved": true
    },
    "evidence_ids_used": ["E-001"],
    "missing_information": [],
    "assumptions": [],
    "excluded_claims": []
  }
}
```

Optional fields such as `location`, `tags`, `context`, and `footer` are supported by the renderer. Keep the content source-language consistent with the JD unless the user asks for bilingual output.

## Visual contract

- A4 portrait, one page by default.
- Use a restrained accent color, strong typographic hierarchy, consistent spacing, and sufficient contrast.
- Keep body text around 9.5–10.5 pt when density requires it, but never reduce readability to force a page fit.
- Use ordinary text headings and bullet lists so ATS extraction remains meaningful.
- Use a two-column visual hierarchy only for the `modern` preview and only when the export path preserves reading order; the `ats` style is the safe default for portal upload.
- Avoid icons that replace words, skill bars, charts, photos, multi-column tables, and decorative claims.

## Style set

The same manifest must be rendered into three text-identical styles, and every style must have both DOCX and PDF output:

- `ats`: single column, standard headings, minimal decoration; safest for large-company portals and unknown parsers.
- `modern`: compact sidebar, restrained accent color, clear visual grouping; useful when a human will review the PDF directly.
- `research`: deep-blue academic hierarchy, method-focused project blocks, citation/publication-friendly spacing; useful for research and graduate roles.

The corresponding filenames are `resume-ats.docx` + `resume-ats.pdf`, `resume-modern.docx` + `resume-modern.pdf`, and `resume-research.docx` + `resume-research.pdf`. HTML previews are useful intermediates but do not replace the editable Word and PDF deliverables.

## Edited DOCX conversion contract

When the user supplies an edited DOCX and explicitly asks for PDF:

- set `audit.conversion.mode` to `edited_docx_to_pdf`;
- use the uploaded DOCX as the sole conversion source;
- preserve user edits to text, order, fonts, spacing, and layout;
- do not rebuild from `compiled_resume.json`;
- do not run role research or rewrite content unless the user asks for both editing and conversion;
- create a PDF with the same base filename and set `content_preserved` to `true` after checking the output.

If the environment has no DOCX-to-PDF converter, report the limitation and provide the exact manual fallback: open the DOCX in Word and choose “另存为” → “PDF”. Never change the file extension without conversion.

The Skill may research external templates for inspiration, but it should not copy proprietary assets or download a third-party template into the package without a license. External research informs design decisions; the bundled templates remain reproducible and local.

## Company recommendation contract

When `audit.company_recommendations.requested` is `true`:

- `default_count` must be `20`; `requested_count` is the user's explicit count or `20` when no count was given.
- `returned_count` must equal the number of items actually returned. The list must be deduplicated by normalized company name and official domain.
- Every item must include a rank, company, city, market, status, matching role, fit score, match explanation, `evidence_ids`, gaps, at least one public `http(s)` source URL, source type, and retrieval date.
- `market` and `source_route` must correspond to the requested city. Mainland Chinese cities use `中国大陆` and domestic Chinese-language sources; overseas cities use `international` and local/international sources; Hong Kong, Macau, and Taiwan use `港澳台/区域` unless the user explicitly defines another route.
- `status` may be `open`, `recent`, or `potential_fit`. `potential_fit` is required when a current opening could not be verified; it must not be described as an active vacancy.
- If `returned_count` is lower than `requested_count`, `limitations` must explain the shortfall. Never fill the list with duplicates or unsupported companies.
- Scores rank evidence-backed fit only. The report must not promise interview success, an offer, or a universal HR preference.
- Include the retrieval date at the top-level and per source, because public job postings can change or close after generation.

## Delivery checklist

Before delivery, confirm:

1. No placeholder, unresolved claim, source token, or unexplained internal name remains.
2. Every material factual bullet has at least one evidence ID.
3. Every hard JD requirement is labeled proven, adjacent, unknown, or absent.
4. Keywords appear naturally and only when supported.
5. Contact details are consistent across variants.
6. All three styles have editable DOCX files and corresponding PDFs; the text content is identical across styles.
7. PDF page count and text extraction pass; there is no clipping, overlap, blank page, broken glyph, or accidental whitespace.
8. An edited DOCX conversion, when requested, uses the edited DOCX as its source and does not overwrite its edits.
9. The audit report records intake questions asked, missing fields, generation mode, deliverables, conversion mode, assumptions, excluded claims, and validation warnings.

Missing information is not a reason to stop generation. Omit unsupported resume sections or weaken wording, and put the completion checklist in the audit rather than inserting fake placeholders into the resume.
