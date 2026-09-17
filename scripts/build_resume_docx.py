#!/usr/bin/env python3
"""Build an editable DOCX resume from the compiled JSON manifest.

The writer uses only the Python standard library and emits ordinary editable
Word paragraphs. It intentionally keeps the compiled text identical across
ATS, Modern, and Research styles; only typography, color, spacing, and light
paragraph shading change.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes
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
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("w", WORD_NS)
ET.register_namespace("r", DOC_REL_NS)
ET.register_namespace("cp", CORE_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("xsi", XSI_NS)
ET.register_namespace("ct", CT_NS)
ET.register_namespace("wp", WP_NS)
ET.register_namespace("a", A_NS)
ET.register_namespace("pic", PIC_NS)


STYLE_CONFIG = {
    "ats": {
        "font": "Arial",
        "accent": "1F2933",
        "heading_fill": "EEF1F2",
        "body_size": 18,
        "section_size": 28,
        "entry_size": 21,
        "headline_size": 24,
        "name_size": 52,
        "spacing": 72,
        "layout": "single",
    },
    "modern": {
        "font": "Aptos",
        "accent": "0F766E",
        "heading_fill": "E6F4F1",
        "body_size": 18,
        "section_size": 29,
        "entry_size": 21,
        "headline_size": 25,
        "name_size": 54,
        "spacing": 88,
        "layout": "split",
    },
    "research": {
        "font": "Cambria",
        "accent": "1E3A5F",
        "heading_fill": "E8EEF5",
        "body_size": 18,
        "section_size": 29,
        "entry_size": 21,
        "headline_size": 24,
        "name_size": 54,
        "spacing": 96,
        "layout": "split",
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


def add_bottom_border(paragraph: ET.Element, color: str, size: str = "10", space: str = "3") -> None:
    ppr = paragraph.find(w("pPr"))
    if ppr is None:
        ppr = ET.SubElement(paragraph, w("pPr"))
    borders = ppr.find(w("pBdr"))
    if borders is None:
        borders = ET.SubElement(ppr, w("pBdr"))
    bottom = ET.SubElement(borders, w("bottom"))
    bottom.set(w("val"), "single")
    bottom.set(w("sz"), size)
    bottom.set(w("space"), space)
    bottom.set(w("color"), color)


def set_cell_width(cell: ET.Element, width: int) -> None:
    tcpr = cell.find(w("tcPr"))
    if tcpr is None:
        tcpr = ET.SubElement(cell, w("tcPr"))
    tcw = tcpr.find(w("tcW"))
    if tcw is None:
        tcw = ET.SubElement(tcpr, w("tcW"))
    tcw.set(w("w"), str(width))
    tcw.set(w("type"), "dxa")


def set_cell_margins(cell: ET.Element, top: int = 0, start: int = 0, bottom: int = 0, end: int = 0) -> None:
    tcpr = cell.find(w("tcPr"))
    if tcpr is None:
        tcpr = ET.SubElement(cell, w("tcPr"))
    margins = tcpr.find(w("tcMar"))
    if margins is None:
        margins = ET.SubElement(tcpr, w("tcMar"))
    for tag, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(w(tag))
        if node is None:
            node = ET.SubElement(margins, w(tag))
        node.set(w("w"), str(value))
        node.set(w("type"), "dxa")


def set_cell_border(cell: ET.Element, side: str, color: str, size: str = "6") -> None:
    tcpr = cell.find(w("tcPr"))
    if tcpr is None:
        tcpr = ET.SubElement(cell, w("tcPr"))
    borders = tcpr.find(w("tcBorders"))
    if borders is None:
        borders = ET.SubElement(tcpr, w("tcBorders"))
    node = borders.find(w(side))
    if node is None:
        node = ET.SubElement(borders, w(side))
    node.set(w("val"), "single")
    node.set(w("sz"), size)
    node.set(w("space"), "0")
    node.set(w("color"), color)


def set_cell_shading(cell: ET.Element, fill: str) -> None:
    tcpr = cell.find(w("tcPr"))
    if tcpr is None:
        tcpr = ET.SubElement(cell, w("tcPr"))
    shd = tcpr.find(w("shd"))
    if shd is None:
        shd = ET.SubElement(tcpr, w("shd"))
    shd.set(w("val"), "clear")
    shd.set(w("fill"), fill)


def add_layout_table(body: ET.Element, widths: tuple[int, ...], border_color: str | None = None) -> list[ET.Element]:
    table = ET.SubElement(body, w("tbl"))
    tblpr = ET.SubElement(table, w("tblPr"))
    tblw = ET.SubElement(tblpr, w("tblW"))
    tblw.set(w("w"), str(sum(widths)))
    tblw.set(w("type"), "dxa")
    layout = ET.SubElement(tblpr, w("tblLayout"))
    layout.set(w("type"), "fixed")
    borders = ET.SubElement(tblpr, w("tblBorders"))
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = ET.SubElement(borders, w(side))
        node.set(w("val"), "nil")
    grid = ET.SubElement(table, w("tblGrid"))
    for width in widths:
        col = ET.SubElement(grid, w("gridCol"))
        col.set(w("w"), str(width))
    row = ET.SubElement(table, w("tr"))
    cells: list[ET.Element] = []
    for index, width in enumerate(widths):
        cell = ET.SubElement(row, w("tc"))
        set_cell_width(cell, width)
        set_cell_margins(cell, top=0, start=0 if index == 0 else 360, bottom=0, end=360 if index == 0 else 0)
        if border_color and index == 0 and len(widths) == 2:
            set_cell_border(cell, "right", border_color)
        ET.SubElement(cell, w("p"))
        cells.append(cell)
    return cells


def cell_body(cell: ET.Element) -> ET.Element:
    paragraphs = cell.findall(w("p"))
    if paragraphs and len(paragraphs) == 1 and len(paragraphs[0]) == 0:
        cell.remove(paragraphs[0])
    if len(cell) == 0:
        ET.SubElement(cell, w("p"))
    return cell


def image_spec(data: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    images = data.get("images", {})
    if isinstance(images, dict):
        for alias in aliases:
            if images.get(alias):
                return images[alias]
    for alias in aliases:
        if data.get(alias):
            return data[alias]
    return None


def image_value(spec: Any, *keys: str) -> str:
    if isinstance(spec, dict):
        for key in keys:
            value = spec.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    return str(spec or "").strip()


def load_image_asset(spec: Any, label: str, media: list[dict[str, Any]]) -> dict[str, Any] | None:
    source = image_value(spec, "data_uri", "src", "path", "data")
    if not source:
        return None
    mime = ""
    suffix = ""
    if source.startswith("data:image/"):
        header, payload = source.split(",", 1)
        mime = header[5:].split(";", 1)[0]
        raw = base64.b64decode(payload)
        suffix = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/gif": "gif"}.get(mime, "")
    else:
        path = Path(source).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"{label} image not found: {path}")
        mime = mimetypes.guess_type(path.name)[0] or ""
        raw = path.read_bytes()
        suffix = path.suffix.lower().lstrip(".")
        if mime == "image/jpg":
            mime = "image/jpeg"
        if suffix == "jpeg":
            suffix = "jpg"
    if mime not in {"image/jpeg", "image/png", "image/gif"} or suffix not in {"jpg", "png", "gif"}:
        raise ValueError(f"{label} image format is not supported: {suffix or mime}")
    index = len(media) + 1
    asset = {
        "rid": f"rId{index + 2}",
        "target": f"media/image{index}.{suffix}",
        "filename": f"image{index}.{suffix}",
        "mime": mime,
        "data": raw,
        "label": label,
        "alt": image_value(spec, "alt") or label,
    }
    media.append(asset)
    return asset


def image_dimensions(raw: bytes, suffix: str) -> tuple[int, int]:
    if suffix == "png" and raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
        return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    if suffix == "gif" and raw[:6] in (b"GIF87a", b"GIF89a") and len(raw) >= 10:
        return int.from_bytes(raw[6:8], "little"), int.from_bytes(raw[8:10], "little")
    if suffix == "jpg" and raw[:2] == b"\xff\xd8":
        position = 2
        while position + 9 < len(raw):
            if raw[position] != 0xFF:
                position += 1
                continue
            marker = raw[position + 1]
            position += 2
            if marker in (0xD8, 0xD9):
                continue
            if position + 2 > len(raw):
                break
            length = int.from_bytes(raw[position:position + 2], "big")
            if marker in range(0xC0, 0xC4) or marker in range(0xC5, 0xC8) or marker in range(0xC9, 0xCC) or marker in range(0xCD, 0xD0):
                if position + 7 <= len(raw):
                    return int.from_bytes(raw[position + 5:position + 7], "big"), int.from_bytes(raw[position + 3:position + 5], "big")
            position += max(length, 2)
    return 1, 1


def add_picture(paragraph: ET.Element, asset: dict[str, Any], *, max_width: int, max_height: int, name: str) -> None:
    suffix = asset["filename"].rsplit(".", 1)[-1]
    width, height = image_dimensions(asset["data"], suffix)
    scale = min(max_width / max(width, 1), max_height / max(height, 1))
    cx = max(1, int(width * scale))
    cy = max(1, int(height * scale))
    run = ET.SubElement(paragraph, w("r"))
    drawing = ET.SubElement(run, w("drawing"))
    inline = ET.SubElement(drawing, f"{{{WP_NS}}}inline")
    extent = ET.SubElement(inline, f"{{{WP_NS}}}extent")
    extent.set("cx", str(cx))
    extent.set("cy", str(cy))
    doc_pr = ET.SubElement(inline, f"{{{WP_NS}}}docPr")
    doc_pr.set("id", str(len(name) + 1))
    doc_pr.set("name", name)
    doc_pr.set("descr", image_value(asset, "alt") or name)
    graphic = ET.SubElement(inline, f"{{{A_NS}}}graphic")
    graphic_data = ET.SubElement(graphic, f"{{{A_NS}}}graphicData")
    graphic_data.set("uri", PIC_NS)
    pic = ET.SubElement(graphic_data, f"{{{PIC_NS}}}pic")
    nv = ET.SubElement(pic, f"{{{PIC_NS}}}nvPicPr")
    c_nv_pr = ET.SubElement(nv, f"{{{PIC_NS}}}cNvPr")
    c_nv_pr.set("id", "0")
    c_nv_pr.set("name", asset["filename"])
    ET.SubElement(nv, f"{{{PIC_NS}}}cNvPicPr")
    blip_fill = ET.SubElement(pic, f"{{{PIC_NS}}}blipFill")
    blip = ET.SubElement(blip_fill, f"{{{A_NS}}}blip")
    blip.set(r_attr("embed"), asset["rid"])
    stretch = ET.SubElement(blip_fill, f"{{{A_NS}}}stretch")
    ET.SubElement(stretch, f"{{{A_NS}}}fillRect")
    sp_pr = ET.SubElement(pic, f"{{{PIC_NS}}}spPr")
    xfrm = ET.SubElement(sp_pr, f"{{{A_NS}}}xfrm")
    off = ET.SubElement(xfrm, f"{{{A_NS}}}off")
    off.set("x", "0")
    off.set("y", "0")
    ext = ET.SubElement(xfrm, f"{{{A_NS}}}ext")
    ext.set("cx", str(cx))
    ext.set("cy", str(cy))
    geometry = ET.SubElement(sp_pr, f"{{{A_NS}}}prstGeom")
    geometry.set("prst", "rect")
    ET.SubElement(geometry, f"{{{A_NS}}}avLst")


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
    paragraph = add_paragraph(
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
    add_bottom_border(paragraph, config["accent"], size="12", space="4")


def add_entry_heading(body: ET.Element, title: str, meta: str, config: dict[str, Any]) -> None:
    paragraph = add_paragraph(body, style="EntryHeading", after=20, keep_next=True)
    add_run(paragraph, title, bold=True, color=config["accent"], size=config["entry_size"], font=config["font"])
    if meta:
        add_run(paragraph, f" | {meta}", color="66757A", size=config["body_size"], font=config["font"])


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


def add_target_section(body: ET.Element, data: dict[str, Any], config: dict[str, Any]) -> None:
    target_role = esc(data.get("target_role"))
    if not target_role:
        return
    add_section_heading(body, "目标方向", config)
    add_paragraph(body, style="Normal", text=target_role, font=config["font"], size=config["body_size"], after=config["spacing"])


def add_skills_section(body: ET.Element, data: dict[str, Any], config: dict[str, Any]) -> None:
    skills = data.get("skills", [])
    if not isinstance(skills, list) or not skills:
        return
    rows: list[tuple[str, str]] = []
    for group in skills:
        if not isinstance(group, dict):
            continue
        label = esc(group.get("label"))
        items = join_text(group.get("items", []))
        if label or items:
            rows.append((label, items))
    if not rows:
        return
    add_section_heading(body, "核心能力", config)
    for label, items in rows:
        paragraph = add_paragraph(body, style="Normal", after=35, font=config["font"], size=config["body_size"])
        if label:
            add_run(paragraph, f"{label}: ", bold=True, color=config["accent"], font=config["font"], size=config["entry_size"])
        add_run(paragraph, items, font=config["font"], size=config["body_size"])


def add_education_section(body: ET.Element, data: dict[str, Any], config: dict[str, Any]) -> None:
    education = data.get("education", [])
    if not isinstance(education, list) or not education:
        return
    valid_items = [item for item in education if isinstance(item, dict) and (esc(item.get("school")) or esc(item.get("degree")))]
    if not valid_items:
        return
    add_section_heading(body, "教育经历", config)
    for item in valid_items:
        school = esc(item.get("school"))
        meta = esc(item.get("period"))
        if school or meta:
            add_entry_heading(body, school, meta, config)
        degree = esc(item.get("degree"))
        detail = esc(item.get("detail"))
        if degree:
            add_paragraph(body, style="Normal", text=degree, font=config["font"], size=config["body_size"], after=25)
        if detail:
            add_paragraph(body, style="Muted", text=detail, color="66757A", font=config["font"], size=config["body_size"], after=35)


def add_summary_section(body: ET.Element, data: dict[str, Any], config: dict[str, Any], style: str) -> None:
    summary = esc(data.get("summary"))
    if not summary:
        return
    add_section_heading(body, "个人概览", config)
    add_paragraph(body, style="Summary", text=summary, italic=style == "research", font=config["font"], size=config["body_size"], after=config["spacing"], shading=config["heading_fill"] if style != "ats" else None)


def add_experience_section(body: ET.Element, data: dict[str, Any], config: dict[str, Any]) -> None:
    experiences = data.get("experience", [])
    if not isinstance(experiences, list) or not experiences:
        return
    valid_items = [item for item in experiences if isinstance(item, dict)]
    if not valid_items:
        return
    add_section_heading(body, "工作经历", config)
    for item in valid_items:
        title = esc(item.get("role"))
        meta = " · ".join(part for part in (esc(item.get("org")), esc(item.get("location")), esc(item.get("date"))) if part)
        if title or meta:
            add_entry_heading(body, title, meta, config)
        bullets = item.get("bullets", [])
        if isinstance(bullets, list):
            for bullet in bullets:
                if esc(bullet).strip():
                    add_bullet(body, esc(bullet), config)


def add_projects_section(body: ET.Element, data: dict[str, Any], config: dict[str, Any]) -> None:
    projects = data.get("projects", [])
    if not isinstance(projects, list) or not projects:
        return
    valid_items = [item for item in projects if isinstance(item, dict)]
    if not valid_items:
        return
    add_section_heading(body, "项目经历", config)
    for item in valid_items:
        title = esc(item.get("name"))
        meta = " · ".join(part for part in (esc(item.get("context")), esc(item.get("date"))) if part)
        if title or meta:
            add_entry_heading(body, title, meta, config)
        tags = join_text(item.get("tags", []), " / ")
        if tags:
            add_paragraph(body, style="Muted", text=tags, italic=True, color="66757A", font=config["font"], size=config["body_size"], after=25)
        bullets = item.get("bullets", [])
        if isinstance(bullets, list):
            for bullet in bullets:
                if esc(bullet).strip():
                    add_bullet(body, esc(bullet), config)


def add_sections(body: ET.Element, data: dict[str, Any], config: dict[str, Any], style: str, section_names: tuple[str, ...]) -> None:
    renderers = {
        "target": lambda: add_target_section(body, data, config),
        "skills": lambda: add_skills_section(body, data, config),
        "education": lambda: add_education_section(body, data, config),
        "summary": lambda: add_summary_section(body, data, config, style),
        "experience": lambda: add_experience_section(body, data, config),
        "projects": lambda: add_projects_section(body, data, config),
    }
    for section_name in section_names:
        renderers[section_name]()


def add_header(body: ET.Element, data: dict[str, Any], config: dict[str, Any], media: list[dict[str, Any]]) -> None:
    header_cells = add_layout_table(body, (7200, 3300), None)
    identity = cell_body(header_cells[0])
    visuals = cell_body(header_cells[1])
    name = esc(data.get("name")) or "候选人"
    add_paragraph(identity, style="Title", text=name, bold=True, color=config["accent"], size=config["name_size"], font=config["font"], after=35)
    headline = esc(data.get("headline"))
    if headline:
        add_paragraph(identity, style="Subtitle", text=headline, bold=True, color=config["accent"], size=config["headline_size"], font=config["font"], after=35)
    contact = join_text(data.get("contact", []))
    if contact:
        add_paragraph(identity, style="Contact", text=contact, color="66757A", size=config["body_size"], font=config["font"], after=0)

    avatar = load_image_asset(image_spec(data, ("avatar", "photo")), "avatar", media)
    qr_code = load_image_asset(image_spec(data, ("qr_code", "wechat_qr", "qr", "qrcode")), "qr_code", media)
    if avatar or qr_code:
        visual_cells = add_layout_table(visuals, (1550, 1550), None)
        if avatar:
            avatar_paragraph = cell_body(visual_cells[0])
            paragraph = add_paragraph(avatar_paragraph, style="Image", after=0, align="center")
            add_picture(paragraph, avatar, max_width=900000, max_height=1200000, name="avatar")
        if qr_code:
            qr_paragraphs = cell_body(visual_cells[1])
            paragraph = add_paragraph(qr_paragraphs, style="Image", after=0, align="center")
            add_picture(paragraph, qr_code, max_width=980000, max_height=980000, name="qr_code")
            label = image_value(image_spec(data, ("qr_code", "wechat_qr", "qr", "qrcode")), "label") or "微信联系"
            add_paragraph(qr_paragraphs, style="ImageLabel", text=label, color="66757A", size=14, font=config["font"], after=0, align="center")
        ET.SubElement(visuals, w("p"))
    rule = add_paragraph(body, style="HeaderRule", after=100)
    add_bottom_border(rule, config["accent"], size="16", space="2")


def render_body_v2(data: dict[str, Any], style: str, media: list[dict[str, Any]]) -> ET.Element:
    config = STYLE_CONFIG[style]
    body = ET.Element(w("body"))
    add_header(body, data, config, media)

    section_order = ("target", "skills", "education", "summary", "experience", "projects")
    if config["layout"] == "split":
        cells = add_layout_table(body, (3300, 7200), config["accent"])
        add_sections(cell_body(cells[0]), data, config, style, section_order[:3])
        add_sections(cell_body(cells[1]), data, config, style, section_order[3:])
    else:
        add_sections(body, data, config, style, section_order)

    footer = esc(data.get("footer"))
    if footer:
        add_paragraph(body, style="FooterText", text=footer, color="777777", size=15, font=config["font"], before=120, after=0, align="right")

    sectpr = ET.SubElement(body, w("sectPr"))
    pg_sz = ET.SubElement(sectpr, w("pgSz"))
    pg_sz.set(w("w"), "11906")
    pg_sz.set(w("h"), "16838")
    pg_mar = ET.SubElement(sectpr, w("pgMar"))
    pg_mar.set(w("top"), "680")
    pg_mar.set(w("right"), "760")
    pg_mar.set(w("bottom"), "680")
    pg_mar.set(w("left"), "760")
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
        ("Title", "Title", config["name_size"]),
        ("Subtitle", "Subtitle", config["headline_size"]),
        ("Contact", "Contact", config["body_size"]),
        ("SectionHeading", "Section Heading", config["section_size"]),
        ("EntryHeading", "Entry Heading", config["entry_size"]),
        ("Muted", "Muted", config["body_size"]),
        ("ListParagraph", "List Paragraph", config["body_size"]),
        ("Summary", "Summary", config["body_size"]),
        ("Image", "Image", config["body_size"]),
        ("ImageLabel", "Image Label", 14),
        ("HeaderRule", "Header Rule", 2),
        ("FooterText", "Footer Text", 15),
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


def build_document(data: dict[str, Any], style: str, media: list[dict[str, Any]]) -> bytes:
    document = ET.Element(w("document"))
    document.append(render_body_v2(data, style, media))
    return ET.tostring(document, encoding="utf-8", xml_declaration=True)


def build_relationships() -> bytes:
    rels = ET.Element(f"{{{REL_NS}}}Relationships")
    relationship = ET.SubElement(rels, f"{{{REL_NS}}}Relationship")
    relationship.set("Id", "rId1")
    relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument")
    relationship.set("Target", "word/document.xml")
    return ET.tostring(rels, encoding="utf-8", xml_declaration=True)


def build_document_relationships(media: list[dict[str, Any]]) -> bytes:
    rels = ET.Element(f"{{{REL_NS}}}Relationships")
    relationships = [
        ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml"),
        ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering", "numbering.xml"),
    ]
    relationships.extend(
        (asset["rid"], "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", asset["target"])
        for asset in media
    )
    for relationship_id, relationship_type, target in relationships:
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
    for extension, content_type in (
        ("png", "image/png"),
        ("jpg", "image/jpeg"),
        ("gif", "image/gif"),
    ):
        default_image = ET.SubElement(types, f"{{{CT_NS}}}Default")
        default_image.set("Extension", extension)
        default_image.set("ContentType", content_type)
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
    media: list[dict[str, Any]] = []
    document_xml = build_document(data, style, media)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", build_content_types())
        archive.writestr("_rels/.rels", build_relationships())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", build_document_relationships(media))
        archive.writestr("word/styles.xml", build_styles(style))
        archive.writestr("word/numbering.xml", build_numbering())
        archive.writestr("docProps/core.xml", build_core_properties(style))
        archive.writestr("docProps/app.xml", build_app_properties())
        for asset in media:
            archive.writestr(f"word/{asset['target']}", asset["data"])


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
