"""Command-line interface for generating PDF CVs."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import markdown
import tinycss2
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from weasyprint import CSS, HTML

DEFAULT_CSS = Path(__file__).parent / "styles" / "default.css"


class InputError(Exception):
    """An input file could not be read or parsed."""


PAGEBREAK_PATTERN = re.compile(r"\s*<!--\s*pagebreak\s*-->\s*", re.IGNORECASE)
PAGE_ORIGIN_ID = "cv-page-origin"


class PageBreakPreprocessor(Preprocessor):
    def __init__(self, md: markdown.Markdown, extension: "PageBreakExtension") -> None:
        """Keep the extension that collects page-break marker IDs."""
        super().__init__(md)
        self.extension = extension

    def run(self, lines: list[str]) -> list[str]:
        """Replace standalone page-break comments with marker elements."""
        output = []
        for line in lines:
            if PAGEBREAK_PATTERN.fullmatch(line):
                marker_id = f"cv-page-break-{len(self.extension.marker_ids) + 1}"
                self.extension.marker_ids.append(marker_id)
                output.append(f'<div class="cv-page-break" id="{marker_id}"></div>')
            else:
                output.append(line)
        return output


class PageBreakExtension(Extension):
    def __init__(self) -> None:
        """Initialize storage for page-break marker IDs."""
        super().__init__()
        self.marker_ids: list[str] = []

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Register the page-break preprocessor with Markdown."""
        md.preprocessors.register(PageBreakPreprocessor(md, self), "cv_pagebreak", 35)


def _page_break_warnings(document, marker_ids: list[str]) -> list[str]:
    """Report markers that did not render at the top of a PDF page."""
    warnings = []
    for index, marker_id in enumerate(marker_ids, start=1):
        found = False
        for page_number, page in enumerate(document.pages, start=1):
            if marker_id not in page.anchors:
                continue
            found = True
            origin = page.anchors.get(PAGE_ORIGIN_ID)
            marker = page.anchors[marker_id]
            if origin is None or abs(marker[1] - origin[1]) > 1:
                warnings.append(
                    f"Page break {index} was not honored at a page boundary "
                    f"(it rendered partway down page {page_number}). Check the CSS rules."
                )
            break
        if not found:
            warnings.append(f"Page break {index} could not be located in the rendered document.")
    return warnings


def _read_text(path: Path, description: str) -> str:
    """Read UTF-8 text and convert file or decoding errors to InputError."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError(f"{description} not found: {path}") from exc
    except (OSError, UnicodeError) as exc:
        raise InputError(f"Could not read {description} {path}: {exc}") from exc


def _check_css(path: Path) -> None:
    """Parse a stylesheet and raise InputError when it contains syntax errors."""
    source = _read_text(path, "CSS file")
    rules = tinycss2.parse_stylesheet(source, skip_comments=True, skip_whitespace=True)
    errors = [token for token in rules if token.type == "error"]
    nested_rule_at_rules = {"container", "document", "layer", "media", "supports"}
    for rule in rules:
        if rule.type == "qualified-rule":
            declarations = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
            errors.extend(token for token in declarations if token.type == "error")
        elif rule.type == "at-rule" and rule.content is not None:
            if rule.lower_at_keyword in nested_rule_at_rules:
                nested_rules = tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True)
                errors.extend(token for token in nested_rules if token.type == "error")
            else:
                declarations = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
                errors.extend(token for token in declarations if token.type == "error")
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise InputError(f"Invalid CSS in {path}: {detail}")


def generate_pdf(markdown_path: Path, output_path: Path, css_path: Path | None = None) -> list[str]:
    """Convert a Markdown CV to PDF and return any page-layout warnings."""
    source = _read_text(markdown_path, "Markdown input")
    if css_path is not None:
        _check_css(css_path)

    pagebreak_extension = PageBreakExtension()
    md = markdown.Markdown(extensions=["extra", "sane_lists", pagebreak_extension])
    html_body = md.convert(source)
    html = (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "</head>\n<body>\n"
        f'<span id="{PAGE_ORIGIN_ID}" style="position: fixed !important; top: 0 !important; '
        'left: 0 !important; width: 0 !important; height: 0 !important; overflow: hidden !important"></span>\n'
        f"{html_body}\n"
        "</body>\n</html>"
    )

    try:
        stylesheets = [CSS(filename=str(DEFAULT_CSS))]
        if css_path is not None:
            stylesheets.append(CSS(filename=str(css_path)))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document = HTML(string=html, base_url=str(markdown_path.resolve().parent)).render(stylesheets=stylesheets)
        page_warnings = _page_break_warnings(document, pagebreak_extension.marker_ids)
        document.write_pdf(target=str(output_path))
    except Exception as exc:
        raise InputError(f"Could not generate PDF {output_path}: {exc}") from exc
    return page_warnings


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser and define supported arguments."""
    parser = argparse.ArgumentParser(
        prog="cv-generator",
        description="Generate a polished PDF CV from a Markdown file.",
    )
    parser.add_argument("input", type=Path, help="Markdown CV file")
    parser.add_argument("--css", type=Path, help="optional CSS stylesheet")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="PDF output path (default: input filename with .pdf extension)",
    )
    return parser


def main() -> int:
    """Parse arguments, generate the PDF, and report errors or warnings."""
    args = _parser().parse_args()
    output = args.output or args.input.with_suffix(".pdf")
    try:
        warnings = generate_pdf(args.input, output, args.css)
    except InputError as exc:
        logging.error("%s", exc)
        return 1
    for warning in warnings:
        logging.warning("%s", warning)
    print(f"Generated {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
