#!/usr/bin/env python3
"""Inventory resume/JD source files without modifying them.

This deliberately performs lightweight inspection only. Rich extraction of PDF/DOCX
content should be handled by the host agent's document capabilities when available.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".csv"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".rtf", ".odt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def classify(path: Path) -> str:
    name = path.name.lower()
    if any(token in name for token in ("jd", "job", "职位", "岗位", "招聘", "description")):
        return "job_description"
    if any(token in name for token in ("resume", "cv", "简历", "履历")):
        return "candidate_resume"
    if any(token in name for token in ("portfolio", "作品", "项目", "project", "paper", "论文")):
        return "supporting_evidence"
    if path.suffix.lower() in DOCUMENT_EXTENSIONS:
        return "document"
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return "image"
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return "text"
    return "other"


def preview(path: Path, limit: int) -> str | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return " ".join(text.split())[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-preview-chars", type=int, default=240)
    args = parser.parse_args()

    root = args.source_dir.resolve()
    if not root.is_dir():
        parser.error(f"source directory does not exist: {root}")

    files = []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p).lower()):
        try:
            stat = path.stat()
        except OSError:
            continue
        files.append(
            {
                "path": str(path),
                "relative_path": str(path.relative_to(root)),
                "name": path.name,
                "extension": path.suffix.lower(),
                "category": classify(path),
                "bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "text_preview": preview(path, max(0, args.max_preview_chars)),
                "requires_rich_extraction": path.suffix.lower() in DOCUMENT_EXTENSIONS,
            }
        )

    payload = {
        "schema_version": "1.0",
        "source_root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "file_count": len(files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

