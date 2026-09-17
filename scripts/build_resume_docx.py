#!/usr/bin/env python3
"""Build an editable DOCX resume from the compiled JSON manifest.

The writer uses only the Python standard library and emits ordinary editable
Word paragraphs. It intentionally keeps the compiled text identical across
ATS, Modern, and Research styles; only typography, color, spacing, and light
paragraph shading change.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CORE_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("w", WORD_NS)
ET.register_namespace("r", DOC_REL_NS)
ET.register_namespace("cp", CORE_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("xsi", XSI_NS)
ET.register_namespace("ct", CT_NS)


STYLE_CONFIG = {
    "ats": {
        "font": "Arial",
        "accent": "000000",
        "heading_fill": None,
        "body_size": 20,
        "section_size": 22,
        "spacing": 80,
    },
    "modern": {
        "font": "Aptos",
        "accent": "0F766E",
        "heading_fill": "E6F4F1",
        "body_size": 20,
        "section_size": 22,
        "spacing": 100,
    },
    "research": {
        "font": "Cambria",
        "accent": "1E3A5F",
        "heading_fill": "E8EEF5",
        "body_size": 21,
        "section_size": 22,
        "spacing": 110,
    },
}


def w(tag: str) -> str:
    return f"{{{WORD_NS}}}{tag}"


def r_attr(tag: str) -> str:
    return f"{{{DOC_REL_NS}}}{tag}"


def esc(value: Any) -> str:
    return str(value or "")


def add_onoff(parent: ET.Element, tag: str) -> None:
    ET.SubElement(parent, w(tag))


def add_run(
    paragraph: ET.Element,
    text: Any,
    *,
    bold: bool = False,
    italic: bool = False,
    color: str | None = None,
    size: int | None = None,
    font: str | None = None,
) -> None:
    value = esc(text)
    if not value:
        return
    run = ET.SubElement(paragraph, w("r"))
    rpr = ET.SubElement(run, w("rPr"))
    if font:
        fonts = ET.SubElement(rpr, w("rFonts"))
        fonts.set(w("ascii"), font)
        fonts.set(w("hAnsi"), font)
        fonts.set(w("eastAsia"), font)
    if bold:
        add_onoff(rpr, "b")
    if italic:
        add_onoff(rpr, "i")
    if color:
        color_node = ET.SubElement(rpr, w("color"))
        color_node.set(w("val"), color)
    if size:
        sz = ET.SubElement(rpr, w("sz"))
        sz.set(w("val"), str(size))
        sz_cs = ET.SubElement(rpr, w("szCs"))
        sz_cs.set(w("val"), str(size))
    node = ET.SubElement(run, w("t"))
    if value[:1].isspace() or value[-1:].isspace():
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = value


def add_paragraph(
    body: ET.Element,
    *,
    style: str = "Normal",
    text: str | None = None,
    bold: bool = False,
    italic: bool = False,
    color: str | None = None,
    size: int | None = None,
    font: str | None = None,
    before: int = 0,
    after: int = 80,
    keep_next: bool = False,
    shading: str | None = None,
    align: str | None = None,
) -> ET.Element:
    paragraph = ET.SubElement(body, w("p"))
    ppr = ET.SubElement(paragraph, w("pPr"))
    pstyle = ET.SubElement(ppr, w("pStyle"))
    pstyle.set(w("val"), style)
    spacing = ET.SubElement(ppr, w("spacing"))
    spacing.set(w("before"), str(before))
    spacing.set(w("after"), str(after))
    spacing.set(w("line"), "240")
    spacing.set(w("lineRule"), "auto")
    if keep_next:
        add_onoff(ppr, "keepNext")
    if shading:
        shd = ET.SubElement(ppr, w("shd"))
        shd.set(w("val"), "clear")
        shd.set(w("fill"), shading)
    if align:
        alignment = ET.SubElement(ppr, w("jc"))
        alignment.set(w("val"), align)
    if text:
        add_run(paragraph, text, bold=bold, italic=italic, color=color, size=size, font=font)
    return paragraph


def add_bullet(body: ET.Element, text: str, config: dict[str, Any]) -> None:
    paragraph = add_paragraph(body, style="ListParagraph", after=45, font=config["font"], size=config["body_size"])
    ppr = paragraph.find(w("pPr"))
    if ppr is None:
        ppr = ET.SubElement(paragraph, w("pPr"))
    numpr = ET.SubElement(ppr, w("numPr"))
    ilvl = ET.SubElement(numpr, w("ilvl"))
    ilvl.set(w("val"), "0")
    numid = ET.SubElement(numpr, w("numId"))
    numid.set(w("val"), "1")
    add_run(paragraph, text, font=config["font"], size=config["body_size"])


def add_section_heading(body: ET.Element, title: str, config: dict[str, Any]) -> None:
    add_paragraph(
        body,
        style="SectionHeading",
        text=title,
        bold=True,
        color=config["accent"],
        size=config["section_size"],
        font=config["font"],
        before=160,
        after=70,
        keep_next=True,
        shading=config["heading_fill"],
    )


def add_entry_heading(body: ET.Element, title: str, meta: str, config: dict[str, Any]) -> None:
    paragraph = add_paragraph(body, style="EntryHeading", after=20, keep_next=True)
    add_run(paragraph, title, bold=True, color=config["accent"], size=config["body_size"], font=config["font"])
    if meta:
        add_run(paragraph, f" | {meta}", color="444444", size=config["body_size"], font=config["font"])


def join_text(values: Any, separator: str = " · ") -> str:
    if not isinstance(values, list):
        return ""
    return separator.join(esc(value) for value in values if esc(value).strip())


def render_body(data: dict[str, Any], style: str) -> ET.Element:
    config = STYLE_CONFIG[style]
    body = ET.Element(w("body"))

    name = esc(data.get("name")) or "候选人"
    add_paragraph(body, style="Title", text=name, bold=True, color=config["accent"], size=36, font=config["font"], after=40)
    add_paragraph(body, style="Subtitle", text=esc(data.get("headline")), bold=True, color="333333", size=24, font=config["font"], after=45)

    contact = join_text(data.get("contact", []))
    if contact:
        add_paragraph(body, style="Contact", text=contact, color="555555", size=config["body_size"], font=config["font"], after=30)
    target_role = esc(data.get("target_role"))
    if target_role:
        add_paragraph(body, style="Contact", text=f"目标岗位: {target_role}", color="555555", size=config["body_size"], font=config["font"], after=75)

    summary = esc(data.get("summary"))
    if summary:
        add_section_heading(body, "SUMMARY", config)
        add_paragraph(body, style="Normal", text=summary, italic=style == "research", font=config["font"], size=config["body_size"], after=config["spacing"])

    skills = data.get("skills", [])
    if isinstance(skills, list) and skills:
        add_section_heading(body, "SKILLS", config)
        for group in skills:
            if not isinstance(group, dict):
                continue
            label = esc(group.get("label"))
            items = join_text(group.get("items", []))
            if label or items:
                paragraph = add_paragraph(body, style="Normal", after=35, font=config["font"], size=config["body_size"])
                if label:
                    add_run(paragraph, f"{label}: ", bold=True, color=config["accent"], font=config["font"], size=config["body_size"])
                add_run(paragraph, items, font=config["font"], size=config["body_size"])

    experiences = data.get("experience", [])
    if isinstance(experiences, list) and experiences:
        add_section_heading(body, "EXPERIENCE", config)
        for item in experiences:
            if not isinstance(item, dict):
                continue
            title = esc(item.get("role"))
            meta = " · ".join(part for part in (esc(item.get("org")), esc(item.get("location")), esc(item.get("date"))) if part)
            if title or meta:
                add_entry_heading(body, title, meta, config)
            bullets = item.get("bullets", [])
            if isinstance(bullets, list):
                for bullet in bullets:
                    if esc(bullet).strip():
                        add_bullet(body, esc(bullet), config)

    projects = data.get("projects", [])
    if isinstance(projects, list) and projects:
        add_section_heading(body, "PROJECTS", config)
        for item in projects:
            if not isinstance(item, dict):
                continue
            title = esc(item.get("name"))
            meta = " · ".join(part for part in (esc(item.get("context")), esc(item.get("date"))) if part)
            if title or meta:
                add_entry_heading(body, title, meta, config)
            tags = join_text(item.get("tags", []), " / ")
            if tags:
                add_paragraph(body, style="Muted", text=tags, italic=True, color="666666", font=config["font"], size=config["body_size"], after=25)
            bullets = item.get("bullets", [])
            if isinstance(bullets, list):
                for bullet in bullets:
                    if esc(bullet).strip():
                        add_bullet(body, esc(bullet), config)

    education = data.get("education", [])
    if isinstance(education, list) and education:
        add_section_heading(body, "EDUCATION", config)
        for item in education:
            if not isinstance(item, dict):
                continue
            school = esc(item.get("school"))
            meta = esc(item.get("period"))
            if school or meta:
                add_entry_heading(body, school, meta, config)
            degree = esc(item.get("degree"))
            detail = esc(item.get("detail"))
            if degree:
                add_paragraph(body, style="Normal", text=degree, font=config["font"], size=config["body_size"], after=25)
            if detail:
                add_paragraph(body, style="Muted", text=detail, color="666666", font=config["font"], size=config["body_size"], after=35)

    footer = esc(data.get("footer"))
    if footer:
        add_paragraph(body, style="FooterText", text=footer, color="777777", size=16, font=config["font"], before=180, after=0)

    sectpr = ET.SubElement(body, w("sectPr"))
    pg_sz = ET.SubElement(sectpr, w("pgSz"))
    pg_sz.set(w("w"), "11906")
    pg_sz.set(w("h"), "16838")
    pg_mar = ET.SubElement(sectpr, w("pgMar"))
    pg_mar.set(w("top"), "720")
    pg_mar.set(w("right"), "840")
    pg_mar.set(w("bottom"), "720")
    pg_mar.set(w("left"), "840")
    return body


def build_styles(style: str) -> bytes:
    config = STYLE_CONFIG[style]
    styles = ET.Element(w("styles"))
    doc_defaults = ET.SubElement(styles, w("docDefaults"))
    rpr_defaults = ET.SubElement(doc_defaults, w("rPrDefault"))
    rpr = ET.SubElement(rpr_defaults, w("rPr"))
    fonts = ET.SubElement(rpr, w("rFonts"))
    for key in ("ascii", "hAnsi", "eastAsia"):
        fonts.set(w(key), config["font"])
    sz = ET.SubElement(rpr, w("sz"))
    sz.set(w("val"), str(config["body_size"]))

    style_defs = [
        ("Normal", "Normal", config["body_size"]),
        ("Title", "Title", 36),
        ("Subtitle", "Subtitle", 24),
        ("Contact", "Contact", config["body_size"]),
        ("SectionHeading", "Section Heading", config["section_size"]),
        ("EntryHeading", "Entry Heading", config["body_size"]),
        ("Muted", "Muted", config["body_size"]),
        ("ListParagraph", "List Paragraph", config["body_size"]),
        ("FooterText", "Footer Text", 16),
    ]
    for style_id, name, size in style_defs:
        node = ET.SubElement(styles, w("style"))
        node.set(w("type"), "paragraph")
        node.set(w("styleId"), style_id)
        if style_id == "Normal":
            node.set(w("default"), "1")
        name_node = ET.SubElement(node, w("name"))
        name_node.set(w("val"), name)
        ppr = ET.SubElement(node, w("pPr"))
        spacing = ET.SubElement(ppr, w("spacing"))
        spacing.set(w("after"), "80")
        rpr_node = ET.SubElement(node, w("rPr"))
        style_fonts = ET.SubElement(rpr_node, w("rFonts"))
        for key in ("ascii", "hAnsi", "eastAsia"):
            style_fonts.set(w(key), config["font"])
        style_sz = ET.SubElement(rpr_node, w("sz"))
        style_sz.set(w("val"), str(size))
    return ET.tostring(styles, encoding="utf-8", xml_declaration=True)


def build_numbering() -> bytes:
    numbering = ET.Element(w("numbering"))
    abstract = ET.SubElement(numbering, w("abstractNum"))
    abstract.set(w("abstractNumId"), "0")
    lvl = ET.SubElement(abstract, w("lvl"))
    lvl.set(w("ilvl"), "0")
    start = ET.SubElement(lvl, w("start"))
    start.set(w("val"), "1")
    fmt = ET.SubElement(lvl, w("numFmt"))
    fmt.set(w("val"), "bullet")
    text = ET.SubElement(lvl, w("lvlText"))
    text.set(w("val"), "•")
    ppr = ET.SubElement(lvl, w("pPr"))
    ind = ET.SubElement(ppr, w("ind"))
    ind.set(w("left"), "360")
    ind.set(w("hanging"), "180")
    num = ET.SubElement(numbering, w("num"))
    num.set(w("numId"), "1")
    abstract_id = ET.SubElement(num, w("abstractNumId"))
    abstract_id.set(w("val"), "0")
    return ET.tostring(numbering, encoding="utf-8", xml_declaration=True)


def build_document(data: dict[str, Any], style: str) -> bytes:
    document = ET.Element(w("document"))
    document.append(render_body(data, style))
    return ET.tostring(document, encoding="utf-8", xml_declaration=True)


def build_relationships() -> bytes:
    rels = ET.Element(f"{{{REL_NS}}}Relationships")
    relationship = ET.SubElement(rels, f"{{{REL_NS}}}Relationship")
    relationship.set("Id", "rId1")
    relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument")
    relationship.set("Target", "word/document.xml")
    return ET.tostring(rels, encoding="utf-8", xml_declaration=True)


def build_document_relationships() -> bytes:
    rels = ET.Element(f"{{{REL_NS}}}Relationships")
    for relationship_id, relationship_type, target in (
        ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml"),
        ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering", "numbering.xml"),
    ):
        relationship = ET.SubElement(rels, f"{{{REL_NS}}}Relationship")
        relationship.set("Id", relationship_id)
        relationship.set("Type", relationship_type)
        relationship.set("Target", target)
    return ET.tostring(rels, encoding="utf-8", xml_declaration=True)


def build_content_types() -> bytes:
    types = ET.Element(f"{{{CT_NS}}}Types")
    default_xml = ET.SubElement(types, f"{{{CT_NS}}}Default")
    default_xml.set("Extension", "xml")
    default_xml.set("ContentType", "application/xml")
    default_rels = ET.SubElement(types, f"{{{CT_NS}}}Default")
    default_rels.set("Extension", "rels")
    default_rels.set("ContentType", "application/vnd.openxmlformats-package.relationships+xml")
    overrides = [
        ("/word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
        ("/word/styles.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"),
        ("/word/numbering.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
        ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
    ]
    for part, content_type in overrides:
        override = ET.SubElement(types, f"{{{CT_NS}}}Override")
        override.set("PartName", part)
        override.set("ContentType", content_type)
    return ET.tostring(types, encoding="utf-8", xml_declaration=True)


def build_core_properties(style: str) -> bytes:
    root = ET.Element(f"{{{CORE_NS}}}coreProperties")
    title = ET.SubElement(root, f"{{{DC_NS}}}title")
    title.text = f"Resume - {style}"
    creator = ET.SubElement(root, f"{{{DC_NS}}}creator")
    creator.text = "skill-resume"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_app_properties() -> bytes:
    root = ET.Element("Properties", {"xmlns": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"})
    app = ET.SubElement(root, "Application")
    app.text = "skill-resume"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_docx(data: dict[str, Any], style: str, output: Path) -> None:
    required = ("headline", "summary")
    missing = [key for key in required if not esc(data.get(key)).strip()]
    if missing:
        raise ValueError(f"missing required manifest fields: {', '.join(missing)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", build_content_types())
        archive.writestr("_rels/.rels", build_relationships())
        archive.writestr("word/document.xml", build_document(data, style))
        archive.writestr("word/_rels/document.xml.rels", build_document_relationships())
        archive.writestr("word/styles.xml", build_styles(style))
        archive.writestr("word/numbering.xml", build_numbering())
        archive.writestr("docProps/core.xml", build_core_properties(style))
        archive.writestr("docProps/app.xml", build_app_properties())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="compiled resume JSON manifest")
    parser.add_argument("--style", choices=tuple(STYLE_CONFIG), default="modern")
    parser.add_argument("--all-styles", action="store_true", help="write resume-ats.docx, resume-modern.docx, and resume-research.docx")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.all_styles:
        args.output.mkdir(parents=True, exist_ok=True)
        outputs = []
        data = json.loads(args.input.read_text(encoding="utf-8"))
        for style in STYLE_CONFIG:
            path = args.output / f"resume-{style}.docx"
            write_docx(data, style, path)
            outputs.append(str(path.resolve()))
        print(json.dumps({"outputs": outputs, "styles": list(STYLE_CONFIG)}, ensure_ascii=False))
        return 0

    data = json.loads(args.input.read_text(encoding="utf-8"))
    write_docx(data, args.style, args.output)
    print(json.dumps({"output": str(args.output.resolve()), "style": args.style}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
