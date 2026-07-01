from pathlib import Path
import re
import sys
import yaml


CATALOG_PATH = Path("data-catalog/data-catalog.yaml")
DATASET_PAGES_DIR = Path("modules/dataset/pages")


def slug_from_identifier(identifier: str) -> str:
    """
    Convert a CURIE-like dataset identifier into the generated page filename stem.

    Examples:
      ex:test-o5 -> test-o5
      ex:uc1-training-dataset -> uc1-training-dataset
    """
    value = str(identifier or "").strip()

    if ":" in value:
        value = value.split(":", 1)[1]

    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")

    return value


def read_text_fallback(path: Path) -> str:
    """
    Read generated .adoc files robustly.

    Some generated files may contain Windows-encoded characters such as em dash.
    Try UTF-8 first, then fall back to Windows-1252.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def write_text_utf8(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def insert_identifier_into_overview(page_text: str, identifier: str) -> str:
    """
    Insert the identifier row into the existing Overview table.
    """

    if "a| Identifier" in page_text:
        return page_text

    overview_match = re.search(
        r"(== Overview\s*\n\s*\[cols=\"1,1\"\]\s*\n\s*\|===\s*\n)",
        page_text,
        flags=re.MULTILINE,
    )

    if not overview_match:
        return page_text

    insert_text = f"a| Identifier\na| {identifier}\n"
    insert_position = overview_match.end()

    return page_text[:insert_position] + insert_text + page_text[insert_position:]


def main() -> int:
    if not CATALOG_PATH.exists():
        print(f"Catalog file not found: {CATALOG_PATH}", file=sys.stderr)
        return 1

    if not DATASET_PAGES_DIR.exists():
        print(f"Dataset pages directory not found: {DATASET_PAGES_DIR}", file=sys.stderr)
        return 1

    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
    datasets = catalog.get("datasets") or []

    if not isinstance(datasets, list):
        print("Expected top-level 'datasets' to be a list.", file=sys.stderr)
        return 1

    updated_count = 0
    missing_pages = []

    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue

        identifier = str(dataset.get("identifier", "")).strip()

        if not identifier:
            continue

        page_stem = slug_from_identifier(identifier)
        page_path = DATASET_PAGES_DIR / f"{page_stem}.adoc"

        if not page_path.exists():
            missing_pages.append((identifier, str(page_path)))
            continue

        original_text = read_text_fallback(page_path)
        updated_text = insert_identifier_into_overview(original_text, identifier)

        if updated_text != original_text:
            write_text_utf8(page_path, updated_text)
            updated_count += 1
            print(f"Added identifier to {page_path}: {identifier}")

    print(f"Dataset pages updated: {updated_count}")

    if missing_pages:
        print("Dataset pages not found for these identifiers:")
        for identifier, page_path in missing_pages:
            print(f"  - {identifier} -> {page_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
