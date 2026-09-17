#!/usr/bin/env python3
"""Convert an edited DOCX to PDF without rewriting its content.

The converter prefers LibreOffice in headless mode and falls back to Microsoft
Word automation on Windows. It intentionally consumes the user's edited DOCX
directly, so the conversion mode does not rebuild the resume from an old JSON
manifest or silently undo Word edits.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    return None


def convert_with_soffice(input_path: Path, output_path: Path, executable: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [executable, "--headless", "--convert-to", "pdf", "--outdir", str(output_path.parent), str(input_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "LibreOffice conversion failed")
    produced = output_path.parent / f"{input_path.stem}.pdf"
    if not produced.is_file():
        raise RuntimeError("LibreOffice completed without producing the expected PDF")
    if produced.resolve() != output_path.resolve():
        if output_path.exists():
            output_path.unlink()
        produced.replace(output_path)


def convert_with_word(input_path: Path, output_path: Path) -> None:
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Microsoft Word automation is unavailable: install pywin32 or provide LibreOffice") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    word = None
    document = None
    pythoncom.CoInitialize()
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        document = word.Documents.Open(str(input_path.resolve()), ReadOnly=True, AddToRecentFiles=False)
        document.ExportAsFixedFormat(str(output_path.resolve()), 17)
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()
    if not output_path.is_file():
        raise RuntimeError("Microsoft Word completed without producing the expected PDF")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="edited DOCX file")
    parser.add_argument("--output", required=True, type=Path, help="PDF destination")
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        parser.error(f"input DOCX does not exist: {input_path}")
    if input_path.suffix.lower() != ".docx":
        parser.error("--input must be a .docx file")
    if output_path.suffix.lower() != ".pdf":
        parser.error("--output must be a .pdf file")

    executable = find_soffice()
    try:
        if executable:
            convert_with_soffice(input_path, output_path, executable)
            method = "libreoffice"
        elif sys.platform == "win32":
            convert_with_word(input_path, output_path)
            method = "microsoft_word"
        else:
            raise RuntimeError("No supported DOCX-to-PDF converter found; provide LibreOffice or Microsoft Word")
    except RuntimeError as exc:
        print(f"conversion failed: {exc}", file=sys.stderr)
        return 2

    print(f'{{"input": "{input_path}", "output": "{output_path}", "method": "{method}", "source_preserved": true}}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
