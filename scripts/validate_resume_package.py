#!/usr/bin/env python3
"""Run deterministic content, evidence, HTML, and optional PDF checks."""

from __future__ import annotations

import argparse
from html import escape as html_escape
import json
import re
import shutil
import subprocess
from zipfile import BadZipFile, ZipFile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|\[\s*(?:TODO|TBD|待补|待确认|占位)\s*\]", re.I)
SUSPICIOUS_RE = re.compile(r"(?:lorem ipsum|your name|example\.com)", re.I)
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def word_tag(tag: str) -> str:
    return f"{{{WORD_NS}}}{tag}"


def walk_strings(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)
    elif isinstance(value, str):
        yield value


def collect_evidence_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence_ids" and isinstance(child, list):
                found.update(str(item) for item in child)
            else:
                found.update(collect_evidence_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_evidence_ids(child))
    return found


def ledger_ids(ledger: Any) -> set[str]:
    if isinstance(ledger, dict):
        records = ledger.get("records", ledger.get("evidence", []))
        if isinstance(records, dict):
            return {str(key) for key in records}
        if isinstance(records, list):
            return {str(item.get("id")) for item in records if isinstance(item, dict) and item.get("id")}
    if isinstance(ledger, list):
        return {str(item.get("id")) for item in ledger if isinstance(item, dict) and item.get("id")}
    return set()


def pdf_pages(path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # type: ignore

        return len(PdfReader(str(path)).pages)
    except Exception:
        pass
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return None
    try:
        result = subprocess.run([pdfinfo, str(path)], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.M)
    return int(match.group(1)) if match else None


def docx_text(path: Path) -> str | None:
    """Extract visible Word text for a lightweight editability/content check."""
    try:
        with ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
    except (BadZipFile, KeyError, OSError, ET.ParseError):
        return None
    texts = [node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
    return " ".join(texts)


def validate_docx(path: Path, manifest: dict[str, Any], errors: list[str], label: str) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"DOCX file not found: {path}")
        return None
    content = docx_text(path)
    if content is None:
        errors.append(f"DOCX is not a readable OOXML package: {label}")
        return None
    anchors = [manifest.get("name", ""), manifest.get("headline", ""), manifest.get("summary", "")]
    for section_name in ("experience", "projects", "education"):
        entries = manifest.get(section_name, [])
        if isinstance(entries, list):
            anchors.extend(entry.get("role", entry.get("name", entry.get("school", ""))) for entry in entries if isinstance(entry, dict))
    for anchor in (str(item) for item in anchors if str(item).strip()):
        if anchor not in content:
            errors.append(f"DOCX is missing compiled text '{anchor}': {label}")
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "editable": True}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def validate_company_recommendations(
    recommendations: Any,
    errors: list[str],
    warnings: list[str],
    required: bool = False,
) -> dict[str, Any] | None:
    """Validate the auditable shape of the optional company recommendation mode."""
    if not isinstance(recommendations, dict) or recommendations.get("requested") is not True:
        if required:
            errors.append("company recommendation validation was requested but audit.company_recommendations.requested is not true")
        return None

    if recommendations.get("default_count") != 20:
        errors.append("company recommendations must declare default_count=20")

    requested_count = recommendations.get("requested_count")
    returned_items = recommendations.get("items", [])
    if not isinstance(requested_count, int) or requested_count < 1:
        errors.append("company recommendations requested_count must be a positive integer")
    if not isinstance(returned_items, list):
        errors.append("company recommendations items must be a list")
        returned_items = []
    if recommendations.get("returned_count") != len(returned_items):
        errors.append("company recommendations returned_count must equal the number of items")
    if isinstance(requested_count, int) and len(returned_items) < requested_count:
        limitations = recommendations.get("limitations", [])
        if not isinstance(limitations, list) or not limitations:
            errors.append("company recommendation shortfall requires a non-empty limitations list")

    valid_statuses = {"open", "recent", "potential_fit"}
    valid_markets = {"中国大陆", "港澳台/区域", "international", "mixed"}
    seen_companies: set[str] = set()
    seen_ranks: set[int] = set()
    for index, item in enumerate(returned_items, start=1):
        label = f"company recommendation #{index}"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        company = normalize_text(str(item.get("company", ""))).casefold()
        if not company:
            errors.append(f"{label} is missing company")
        elif company in seen_companies:
            errors.append(f"duplicate company recommendation: {item.get('company')}")
        else:
            seen_companies.add(company)
        rank = item.get("rank")
        if not isinstance(rank, int) or rank < 1:
            errors.append(f"{label} has an invalid rank")
        elif rank in seen_ranks:
            errors.append(f"duplicate company recommendation rank: {rank}")
        else:
            seen_ranks.add(rank)
        for field in ("city", "market", "status", "matching_role", "why_fit", "evidence_ids", "gaps", "sources"):
            if field not in item:
                errors.append(f"{label} is missing {field}")
        if item.get("market") not in valid_markets:
            errors.append(f"{label} has an unsupported market")
        if item.get("status") not in valid_statuses:
            errors.append(f"{label} has an unsupported status")
        score = item.get("fit_score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append(f"{label} fit_score must be between 0 and 100")
        if not isinstance(item.get("why_fit"), list) or not item.get("why_fit"):
            errors.append(f"{label} must include at least one why_fit explanation")
        if not isinstance(item.get("evidence_ids"), list) or not item.get("evidence_ids"):
            errors.append(f"{label} must include resume evidence_ids")
        sources = item.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{label} must include at least one public source")
            continue
        for source in sources:
            if not isinstance(source, dict) or not str(source.get("url", "")).startswith(("http://", "https://")):
                errors.append(f"{label} contains a source without an http(s) URL")
            if not isinstance(source, dict) or not str(source.get("retrieved_at", "")).strip():
                errors.append(f"{label} contains a source without retrieved_at")

    if not str(recommendations.get("as_of", "")).strip():
        errors.append("company recommendations are missing top-level as_of")
    if recommendations.get("market") not in valid_markets:
        errors.append("company recommendations have an unsupported top-level market")
    if not isinstance(recommendations.get("locations"), list) or not recommendations.get("locations"):
        warnings.append("company recommendations do not list normalized target locations")
    if not isinstance(recommendations.get("limitations", []), list):
        errors.append("company recommendations limitations must be a list")
    return {
        "requested_count": requested_count,
        "returned_count": len(returned_items),
        "market": recommendations.get("market"),
        "locations": recommendations.get("locations", []),
    }


def image_keys(manifest: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    images = manifest.get("images", {})
    if isinstance(images, dict):
        for key in ("avatar", "photo", "qr_code", "wechat_qr", "qr", "qrcode"):
            if images.get(key):
                canonical = "avatar" if key in {"avatar", "photo"} else "qr_code"
                if canonical not in keys:
                    keys.append(canonical)
    for key in ("avatar", "photo", "qr_code", "wechat_qr", "qr", "qrcode"):
        if manifest.get(key):
            canonical = "avatar" if key in {"avatar", "photo"} else "qr_code"
            if canonical not in keys:
                keys.append(canonical)
    return keys


def inspect_docx_layout(path: Path) -> dict[str, Any] | None:
    try:
        with ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
            styles_xml = archive.read("word/styles.xml")
            media = [name for name in archive.namelist() if name.startswith("word/media/")]
        document_root = ET.fromstring(document_xml)
        styles_root = ET.fromstring(styles_xml)
    except (BadZipFile, KeyError, OSError, ET.ParseError):
        return None
    sizes: dict[str, int] = {}
    for style_node in styles_root.findall(f".//{word_tag('style')}"):
        style_id = style_node.get(word_tag("styleId"))
        size_node = style_node.find(f".//{word_tag('sz')}")
        if style_id and size_node is not None and size_node.get(word_tag("val")):
            try:
                sizes[style_id] = int(size_node.get(word_tag("val"), "0"))
            except ValueError:
                pass
    return {
        "tables": len(document_root.findall(f".//{word_tag('tbl')}")),
        "drawings": len(document_root.findall(f".//{word_tag('drawing')}")),
        "media": len(media),
        "style_sizes": sizes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evidence-ledger", type=Path)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--styles-dir", type=Path, help="directory containing resume-ats.html, resume-modern.html, resume-research.html")
    parser.add_argument("--docx", type=Path, help="single editable DOCX to validate")
    parser.add_argument("--docx-dir", type=Path, help="directory containing resume-ats.docx, resume-modern.docx, resume-research.docx")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--pdf-dir", type=Path, help="directory containing resume-ats.pdf, resume-modern.pdf, resume-research.pdf")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--require-research", action="store_true", help="require role and template web-research records")
    parser.add_argument("--require-company-recommendations", action="store_true", help="require and validate the company recommendation record")
    parser.add_argument("--require-layout", action="store_true", help="require the modern/research two-column layout, heading hierarchy, and supplied image embedding")
    parser.add_argument("--require-all-formats", action="store_true", help="require all three HTML, editable DOCX, and PDF outputs")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    for key in ("name", "headline", "summary"):
        if not str(manifest.get(key, "")).strip():
            errors.append(f"missing required field: {key}")

    strings = list(walk_strings(manifest))
    for value in strings:
        if PLACEHOLDER_RE.search(value):
            errors.append(f"placeholder or unresolved claim found: {value[:100]}")
        if SUSPICIOUS_RE.search(value):
            errors.append(f"scaffold text found: {value[:100]}")

    referenced = collect_evidence_ids(manifest)
    if args.evidence_ledger:
        ledger = json.loads(args.evidence_ledger.read_text(encoding="utf-8"))
        available = ledger_ids(ledger)
        missing = sorted(referenced - available)
        if missing:
            errors.append(f"manifest references missing evidence IDs: {', '.join(missing)}")
    elif referenced:
        warnings.append("evidence IDs exist but no ledger was supplied for cross-checking")
    else:
        warnings.append("no evidence IDs found in manifest")

    summary_length = len(str(manifest.get("summary", "")))
    if summary_length > 600:
        warnings.append(f"summary is long ({summary_length} characters); one-page layout may be crowded")

    audit = manifest.get("audit", {}) if isinstance(manifest.get("audit", {}), dict) else {}
    research = audit.get("research", {}) if isinstance(audit.get("research", {}), dict) else {}
    if args.require_research:
        role_sources = research.get("role_sources", [])
        template_sources = research.get("template_sources", [])
        if not str(research.get("as_of", "")).strip():
            errors.append("required web research is missing as_of")
        for label, sources in (("role_sources", role_sources), ("template_sources", template_sources)):
            if not isinstance(sources, list) or not sources:
                errors.append(f"required web research is missing {label}")
                continue
            for source in sources:
                if not isinstance(source, dict) or not str(source.get("url", "")).startswith(("http://", "https://")):
                    errors.append(f"{label} contains a source without an http(s) URL")
        if not isinstance(research.get("signals_applied", []), list) or not research.get("signals_applied"):
            warnings.append("web research has no recorded signals_applied decisions")

    company_recommendations = audit.get("company_recommendations")
    company_recommendation_result = validate_company_recommendations(
        company_recommendations,
        errors,
        warnings,
        required=args.require_company_recommendations,
    )
    expected_images = image_keys(manifest)
    assets_audit = audit.get("assets", {}) if isinstance(audit.get("assets", {}), dict) else {}
    if args.require_layout and expected_images:
        embedded = assets_audit.get("embedded", [])
        if not isinstance(embedded, list) or not set(expected_images).issubset({str(item) for item in embedded}):
            errors.append("audit.assets must record every supplied image as embedded")

    if args.styles_dir:
        expected_styles = ("ats", "modern", "research")
        rendered_styles = audit.get("styles_rendered", [])
        for style in expected_styles:
            path = args.styles_dir / f"resume-{style}.html"
            if not path.is_file():
                errors.append(f"style output not found: {path}")
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            if PLACEHOLDER_RE.search(content):
                errors.append(f"style output contains unresolved placeholder: {style}")
            anchors = [manifest.get("name", ""), manifest.get("headline", ""), manifest.get("summary", "")]
            for section_name in ("experience", "projects", "education"):
                entries = manifest.get(section_name, [])
                if isinstance(entries, list):
                    anchors.extend(entry.get("role", entry.get("name", entry.get("school", ""))) for entry in entries if isinstance(entry, dict))
            for anchor in (str(item) for item in anchors if str(item).strip()):
                if anchor not in content and html_escape(anchor, quote=True) not in content:
                    errors.append(f"style output is missing compiled text '{anchor}': {style}")
        if sorted(str(style) for style in rendered_styles) != sorted(expected_styles):
            warnings.append("audit styles_rendered does not list all three built-in styles")
        if args.require_layout:
            for style in ("modern", "research"):
                path = args.styles_dir / f"resume-{style}.html"
                if path.is_file():
                    content = path.read_text(encoding="utf-8", errors="replace")
                    if "grid-template-columns:58mm 1fr" not in content:
                        errors.append(f"HTML style is missing the required two-column grid: {style}")
            if expected_images:
                for style in expected_styles:
                    path = args.styles_dir / f"resume-{style}.html"
                    if path.is_file():
                        html_content = path.read_text(encoding="utf-8", errors="replace")
                        if html_content.count("<img ") < len(expected_images):
                            errors.append(f"HTML style is missing supplied images: {style}")

    docx_result = None
    if args.docx:
        docx_result = validate_docx(args.docx, manifest, errors, "single")

    docx_styles: dict[str, str] = {}
    if args.docx_dir:
        expected_styles = ("ats", "modern", "research")
        docx_layouts: dict[str, dict[str, Any]] = {}
        for style in expected_styles:
            path = args.docx_dir / f"resume-{style}.docx"
            validate_docx(path, manifest, errors, style)
            content = docx_text(path) if path.is_file() else None
            if content is not None:
                docx_styles[style] = normalize_text(content)
            if args.require_layout and path.is_file():
                layout = inspect_docx_layout(path)
                if layout is None:
                    errors.append(f"DOCX layout inspection failed: {style}")
                else:
                    docx_layouts[style] = layout
        if len(docx_styles) == len(expected_styles) and len(set(docx_styles.values())) != 1:
            errors.append("DOCX style outputs do not contain identical text")
        if args.require_layout:
            for style in ("modern", "research"):
                layout = docx_layouts.get(style)
                if layout and layout["tables"] < 2:
                    errors.append(f"DOCX style is missing the required two-column body table: {style}")
            for style in expected_styles:
                layout = docx_layouts.get(style)
                if layout:
                    sizes = layout["style_sizes"]
                    if not (sizes.get("Title", 0) > sizes.get("Subtitle", 0) > sizes.get("EntryHeading", 0) >= sizes.get("Normal", 0)):
                        errors.append(f"DOCX style has weak title hierarchy: {style}")
                    if layout["media"] < len(expected_images):
                        errors.append(f"DOCX style is missing supplied images: {style}")

    if args.pdf_dir:
        expected_styles = ("ats", "modern", "research")
        for style in expected_styles:
            path = args.pdf_dir / f"resume-{style}.pdf"
            if not path.is_file():
                errors.append(f"PDF file not found: {path}")
                continue
            pages = pdf_pages(path)
            if pages is not None and pages > args.max_pages:
                errors.append(f"PDF has {pages} pages; maximum is {args.max_pages}: {style}")

    if args.require_all_formats:
        if not args.styles_dir:
            errors.append("all-format validation requires --styles-dir")
        if not args.docx_dir:
            errors.append("all-format validation requires --docx-dir")
        if not args.pdf_dir:
            errors.append("all-format validation requires --pdf-dir")
        deliverables = audit.get("deliverables", {}) if isinstance(audit.get("deliverables", {}), dict) else {}
        identity = deliverables.get("text_identity", {}) if isinstance(deliverables.get("text_identity", {}), dict) else {}
        if identity.get("same_text_across_styles") is not True:
            errors.append("audit deliverables must confirm same_text_across_styles=true")

    html_result = None
    if args.html:
        if not args.html.is_file():
            errors.append(f"HTML file not found: {args.html}")
        else:
            content = args.html.read_text(encoding="utf-8", errors="replace")
            for marker in ("<html", "<h1", "<main", "</html>"):
                if marker not in content.lower():
                    errors.append(f"HTML missing semantic marker: {marker}")
            if PLACEHOLDER_RE.search(content):
                errors.append("HTML contains unresolved placeholder")
            html_result = {"path": str(args.html.resolve()), "bytes": args.html.stat().st_size}

    pdf_result = None
    if args.pdf:
        if not args.pdf.is_file():
            errors.append(f"PDF file not found: {args.pdf}")
        else:
            pages = pdf_pages(args.pdf)
            pdf_result = {"path": str(args.pdf.resolve()), "bytes": args.pdf.stat().st_size, "pages": pages}
            if pages is None:
                warnings.append("PDF page count unavailable; install pypdf or provide pdfinfo")
            elif pages > args.max_pages:
                errors.append(f"PDF has {pages} pages; maximum is {args.max_pages}")

    report = {
        "schema_version": "1.0",
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "evidence_ids_checked": sorted(referenced),
        "html": html_result,
        "docx": docx_result,
        "pdf": pdf_result,
        "company_recommendations": company_recommendation_result,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
