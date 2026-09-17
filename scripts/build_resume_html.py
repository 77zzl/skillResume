#!/usr/bin/env python3
"""Render a compiled resume manifest into the bundled semantic HTML template."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


STYLE_TEMPLATES = {
    "ats": "resume_template_ats.html",
    "modern": "resume_template.html",
    "research": "resume_template_research.html",
}


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def text_list(values: Any, separator: str = " · ") -> str:
    if not isinstance(values, list):
        return ""
    return separator.join(esc(item) for item in values if str(item).strip())


def render_skills(groups: Any) -> str:
    if not isinstance(groups, list):
        return ""
    blocks = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = esc(group.get("label"))
        items = text_list(group.get("items", []))
        if label or items:
            blocks.append(f'<div class="skill-group"><h3>{label}</h3><p>{items}</p></div>')
    return "".join(blocks)


def render_experience(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    blocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = esc(item.get("role"))
        org = esc(item.get("org"))
        date = esc(item.get("date"))
        location = esc(item.get("location"))
        raw_bullets = item.get("bullets", [])
        bullets = "".join(f"<li>{esc(bullet)}</li>" for bullet in raw_bullets if str(bullet).strip()) if isinstance(raw_bullets, list) else ""
        if title or org or bullets:
            meta = " · ".join(part for part in (org, location) if part)
            blocks.append(
                '<article class="entry">'
                f'<div class="entry-heading"><h3>{title}</h3><span>{date}</span></div>'
                f'<p class="muted">{meta}</p><ul>{bullets}</ul></article>'
            )
    return "".join(blocks)


def render_projects(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    blocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = esc(item.get("name"))
        context = esc(item.get("context"))
        date = esc(item.get("date"))
        tags = text_list(item.get("tags", []), "  /  ")
        raw_bullets = item.get("bullets", [])
        bullets = "".join(f"<li>{esc(bullet)}</li>" for bullet in raw_bullets if str(bullet).strip()) if isinstance(raw_bullets, list) else ""
        if name or bullets:
            meta = " · ".join(part for part in (context, date) if part)
            tag_line = f'<p class="tags">{tags}</p>' if tags else ""
            blocks.append(
                '<article class="entry">'
                f'<div class="entry-heading"><h3>{name}</h3><span>{date}</span></div>'
                f'<p class="muted">{meta}</p>{tag_line}<ul>{bullets}</ul></article>'
            )
    return "".join(blocks)


def render_education(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    blocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        school = esc(item.get("school"))
        degree = esc(item.get("degree"))
        period = esc(item.get("period"))
        detail = esc(item.get("detail"))
        if school or degree:
            blocks.append(
                '<div class="education-item">'
                f'<div class="entry-heading"><h3>{school}</h3><span>{period}</span></div>'
                f'<p>{degree}</p><p class="muted">{detail}</p>'
                '</div>'
            )
    return "".join(blocks)


def render_manifest(data: dict[str, Any], template_path: Path) -> str:
    required = ("name", "headline", "summary")
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise ValueError(f"missing required manifest fields: {', '.join(missing)}")

    template = template_path.read_text(encoding="utf-8")
    skills = render_skills(data.get("skills", []))
    experience = render_experience(data.get("experience", []))
    projects = render_projects(data.get("projects", []))
    education = render_education(data.get("education", []))
    replacements = {
        "{{NAME}}": esc(data.get("name")),
        "{{HEADLINE}}": esc(data.get("headline")),
        "{{CONTACT}}": text_list(data.get("contact", [])),
        "{{TARGET_ROLE}}": esc(data.get("target_role")),
        "{{SUMMARY}}": esc(data.get("summary")),
        "{{SKILLS}}": skills,
        "{{EXPERIENCE}}": experience,
        "{{PROJECTS}}": projects,
        "{{EDUCATION}}": education,
        "{{FOOTER}}": esc(data.get("footer", "Evidence-backed resume · skill-resume")),
        "{{SKILLS_CLASS}}": "" if skills else "hidden",
        "{{EXPERIENCE_CLASS}}": "" if experience else "hidden",
        "{{PROJECTS_CLASS}}": "" if projects else "hidden",
        "{{EDUCATION_CLASS}}": "" if education else "hidden",
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    if "{{" in template or "}}" in template:
        raise ValueError("unresolved template token remains")
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="compiled resume JSON manifest")
    parser.add_argument("--template", type=Path, help="custom HTML template; cannot be used with --all-styles")
    parser.add_argument("--style", choices=tuple(STYLE_TEMPLATES), default="modern")
    parser.add_argument("--all-styles", action="store_true", help="render ats, modern, and research into --output directory")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.all_styles and args.template:
        parser.error("--template cannot be combined with --all-styles")

    data = json.loads(args.input.read_text(encoding="utf-8"))
    asset_dir = Path(__file__).resolve().parent.parent / "assets"
    if args.all_styles:
        args.output.mkdir(parents=True, exist_ok=True)
        outputs = []
        for style, filename in STYLE_TEMPLATES.items():
            output = args.output / f"resume-{style}.html"
            output.write_text(render_manifest(data, asset_dir / filename), encoding="utf-8")
            outputs.append(str(output.resolve()))
        print(json.dumps({"outputs": outputs}, ensure_ascii=False))
        return 0

    template_path = args.template or asset_dir / STYLE_TEMPLATES[args.style]
    rendered = render_manifest(data, template_path)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "style": args.style}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
