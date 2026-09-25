# Repository Guide for Agents

## Project Overview

This repository builds a PDF CV from Markdown using Python-Markdown and WeasyPrint. The project requires Python 3.14 or newer.

## Repository Map

- `cv_generator/cli.py` contains the command-line interface, CSS validation, Markdown conversion, page-break handling, and PDF rendering.
- `cv_generator/styles/default.css` provides the bundled print stylesheet.
- `examples/sample_cv.md` and `examples/sample_cv.css` are an anonymized sample CV and its custom layout.
- `tests/test_cli.py` covers CLI behavior and PDF generation.
- `pyproject.toml` defines dependencies and tool configuration.

## Environment and Commands

Use the project virtual environment and install development tools with:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run formatting, linting, type checking, and tests with:

```sh
.venv/bin/python -m black cv_generator tests
.venv/bin/python -m ruff check cv_generator tests
.venv/bin/python -m mypy
.venv/bin/coverage run -m unittest discover -s tests -v
.venv/bin/coverage report -m
```

Black and Ruff use a 120-character line length. Ruff checks pycodestyle errors, pyflakes, and import order. Mypy is configured to ignore missing third-party stubs for Markdown, tinycss2, and WeasyPrint.

## Working with CV Content and PDFs

- Preserve source hyperlinks as Markdown links: `[label](https://example.com)`. Plain text such as `LinkedIn` does not become a clickable PDF link.
- Preserve the standalone `<!-- pagebreak -->` marker when editing a CV that has a deliberate page boundary.
- The custom stylesheet is applied on top of the bundled print stylesheet. Resolve relative assets from the Markdown or CSS file that references them.
- After changing links or rendering behavior, regenerate the PDF and inspect its annotations with `pdfinfo -url path/to/cv.pdf` when available.
- Use the project CLI to render a CV, for example:

  ```sh
  .venv/bin/cv-generator examples/sample_cv.md \
    --css examples/sample_cv.css \
    --output build/sample-cv.pdf
  ```

## Change Guidance

- Keep dependency and tool configuration in `pyproject.toml` and keep user-facing commands in `README.md` accurate.
- When editing sample CV content or link destinations, preserve the source document's details; do not guess missing URLs or facts.
- For layout changes, check page-break warnings and inspect the generated PDF when possible.
- Keep generated coverage data and HTML reports out of source control; `.coverage` and `htmlcov/` are ignored.
- The actual CV lives under the ignored `david_kiss/` directory; do not expose its contents in tracked examples or documentation.
