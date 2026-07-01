from pathlib import Path
import re
import sys
import yaml


CATALOG_PATH = Path("data-catalog/data-catalog.yaml")

DATASET_PAGES_DIR = Path("modules/dataset/pages")
CONCEPT_PAGES_DIR = Path("modules/concept/pages")
METRIC_PAGES_DIR = Path("modules/metric/pages")
POLICY_PAGES_DIR = Path("modules/policy/pages")
DATA_CATALOG_NAV_PATH = Path("modules/data-catalog/nav.adoc")


METRIC_USAGE_START = "// BEGIN GENERATED METRIC USAGE"
METRIC_USAGE_END = "// END GENERATED METRIC USAGE"


def slug_from_identifier(identifier: str) -> str:
    """
    Convert a CURIE-like identifier into the generated page filename stem.

    Examples:
      ex:test-o5 -> test-o5
      ex:forecast-data -> forecast-data
      plcy:open-information -> open-information
    """
    value = str(identifier or "").strip()

    if ":" in value:
        value = value.split(":", 1)[1]

    value = value.lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")

    return value


def read_text_fallback(path: Path) -> str:
    """
    Read generated .adoc files robustly.

    Some generated files may contain Windows-encoded characters.
    Try UTF-8 first, then fall back to Windows-1252.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def write_text_utf8(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def insert_after_page_title(page_text: str, line_to_insert: str) -> str:
    """
    Insert a line immediately after the AsciiDoc page title.

    Example:

      = forecast data

      Identifier: `ex:forecast-data`
    """
    if line_to_insert in page_text:
        return page_text

    lines = page_text.splitlines()

    if not lines:
        return line_to_insert + "\n"

    if lines[0].startswith("= "):
        return "\n".join([lines[0], "", line_to_insert] + lines[1:]).rstrip() + "\n"

    return line_to_insert + "\n\n" + page_text.rstrip() + "\n"


def insert_identifier_into_dataset_overview(page_text: str, identifier: str) -> str:
    """
    Insert dataset identifier into the existing dataset Overview table.

    Expected generated pattern:

      == Overview

      [cols="1,1"]
      |===
      a| Title
      a| ...
      |===
    """
    if f"a| {identifier}" in page_text and "a| Identifier" in page_text:
        return page_text

    overview_match = re.search(
        r"(== Overview\s*\n\s*\[cols=\"1,1\"\]\s*\n\s*\|===\s*\n)",
        page_text,
        flags=re.MULTILINE,
    )

    if not overview_match:
        return insert_after_page_title(page_text, f"Identifier: `{identifier}`")

    insert_text = f"a| Identifier\na| {identifier}\n"
    insert_position = overview_match.end()

    return page_text[:insert_position] + insert_text + page_text[insert_position:]


def remove_existing_metric_usage_sections(page_text: str) -> str:
    """
    Remove usage sections generated either by this script or by the upstream generator.

    The upstream generator currently creates a simple section like:

      Datasets with quality measurements using this metric:

      [cols="1"]
      |===
      ...
      |===

    This script replaces that with a richer table.
    """
    text = page_text

    generated_block_pattern = re.compile(
        rf"\n?{re.escape(METRIC_USAGE_START)}.*?{re.escape(METRIC_USAGE_END)}\n?",
        flags=re.DOTALL,
    )
    text = generated_block_pattern.sub("\n", text).rstrip() + "\n"

    upstream_table_pattern = re.compile(
        r"\n?Datasets with quality measurements using this metric:\s*\n+"
        r"\[cols=\"1\"\]\s*\n"
        r"\|===.*?\|===\s*",
        flags=re.DOTALL,
    )
    text = upstream_table_pattern.sub("\n", text).rstrip() + "\n"

    upstream_empty_pattern = re.compile(
        r"\n?No datasets found with quality measurements using this metric\.\s*",
        flags=re.DOTALL,
    )
    text = upstream_empty_pattern.sub("\n", text).rstrip() + "\n"

    return text.rstrip() + "\n"


def build_metric_usage_lookup(catalog: dict) -> dict:
    """
    Build lookup:

      metric identifier -> list of usage rows

    Each usage row contains:
      dataset title
      dataset identifier
      dataset page stem
      quality measurement identifier
      value
      generated date
    """
    datasets = catalog.get("datasets") or []
    metrics = catalog.get("metrics") or []
    quality_measurements = catalog.get("qualityMeasurements") or []

    dataset_lookup = {}

    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue

        dataset_identifier = str(dataset.get("identifier", "")).strip()

        if not dataset_identifier:
            continue

        dataset_lookup[dataset_identifier] = {
            "title": str(dataset.get("title", dataset_identifier)).strip(),
            "page": slug_from_identifier(dataset_identifier),
        }

    metric_usage = {}

    for metric in metrics:
        if not isinstance(metric, dict):
            continue

        metric_identifier = str(metric.get("identifier", "")).strip()

        if metric_identifier:
            metric_usage[metric_identifier] = []

    for quality_measurement in quality_measurements:
        if not isinstance(quality_measurement, dict):
            continue

        metric_identifier = str(quality_measurement.get("isMeasurementOf", "")).strip()
        dataset_identifier = str(quality_measurement.get("computedOn", "")).strip()

        if not metric_identifier or not dataset_identifier:
            continue

        if metric_identifier not in metric_usage:
            continue

        dataset_info = dataset_lookup.get(
            dataset_identifier,
            {
                "title": dataset_identifier,
                "page": slug_from_identifier(dataset_identifier),
            },
        )

        usage = {
            "dataset_title": dataset_info["title"],
            "dataset_identifier": dataset_identifier,
            "dataset_page": dataset_info["page"],
            "quality_measurement_identifier": str(
                quality_measurement.get("identifier", "")
            ).strip(),
            "value": quality_measurement.get("value", "—"),
            "generated_at_time": quality_measurement.get("generatedAtTime", ""),
        }

        metric_usage[metric_identifier].append(usage)

    return metric_usage


def build_metric_usage_block(metric_identifier: str, usages: list[dict]) -> str:
    block_lines = [
        METRIC_USAGE_START,
        "",
        "== Quality measurement usage",
        "",
    ]

    if not usages:
        block_lines.extend(
            [
                "No datasets found with quality measurements using this metric.",
                "",
                METRIC_USAGE_END,
                "",
            ]
        )
        return "\n".join(block_lines)

    block_lines.extend(
        [
            '[cols="2,2,2,1,1"]',
            "|===",
            "a| Dataset",
            "a| Dataset identifier",
            "a| Quality measurement identifier",
            "a| Value",
            "a| Generated date",
            "",
        ]
    )

    for usage in usages:
        dataset_title = usage["dataset_title"]
        dataset_identifier = usage["dataset_identifier"]
        dataset_page = usage["dataset_page"]
        quality_measurement_identifier = usage["quality_measurement_identifier"]
        value = usage["value"]
        generated_at_time = usage["generated_at_time"]

        dataset_link = f"xref:dataset:{dataset_page}.adoc[{dataset_title}]"

        block_lines.extend(
            [
                f"a| {dataset_link}",
                f"a| `{dataset_identifier}`",
                f"a| `{quality_measurement_identifier or '—'}`",
                f"a| {value}",
                f"a| {generated_at_time or '—'}",
                "",
            ]
        )

    block_lines.extend(
        [
            "|===",
            "",
            METRIC_USAGE_END,
            "",
        ]
    )

    return "\n".join(block_lines)


def patch_dataset_pages(catalog: dict) -> int:
    datasets = catalog.get("datasets") or []

    if not isinstance(datasets, list):
        print("Expected top-level 'datasets' to be a list.", file=sys.stderr)
        return 1

    if not DATASET_PAGES_DIR.exists():
        print(f"Dataset pages directory not found: {DATASET_PAGES_DIR}", file=sys.stderr)
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
        updated_text = insert_identifier_into_dataset_overview(original_text, identifier)

        if updated_text != original_text:
            write_text_utf8(page_path, updated_text)
            updated_count += 1
            print(f"Patched dataset page: {page_path} ({identifier})")

    print(f"Dataset pages patched: {updated_count}")

    if missing_pages:
        print("Dataset pages not found for these identifiers:")
        for identifier, page_path in missing_pages:
            print(f"  - {identifier} -> {page_path}")

    return 0


def patch_concept_pages(catalog: dict) -> int:
    concepts = catalog.get("concepts") or []

    if not isinstance(concepts, list):
        print("Expected top-level 'concepts' to be a list.", file=sys.stderr)
        return 1

    if not CONCEPT_PAGES_DIR.exists():
        print(f"Concept pages directory not found: {CONCEPT_PAGES_DIR}", file=sys.stderr)
        return 1

    updated_count = 0
    missing_pages = []

    for concept in concepts:
        if not isinstance(concept, dict):
            continue

        identifier = str(concept.get("identifier", "")).strip()

        if not identifier:
            continue

        page_stem = slug_from_identifier(identifier)
        page_path = CONCEPT_PAGES_DIR / f"{page_stem}.adoc"

        if not page_path.exists():
            missing_pages.append((identifier, str(page_path)))
            continue

        original_text = read_text_fallback(page_path)
        updated_text = insert_after_page_title(original_text, f"Identifier: `{identifier}`")

        if updated_text != original_text:
            write_text_utf8(page_path, updated_text)
            updated_count += 1
            print(f"Patched concept page: {page_path} ({identifier})")

    print(f"Concept pages patched: {updated_count}")

    if missing_pages:
        print("Concept pages not found for these identifiers:")
        for identifier, page_path in missing_pages:
            print(f"  - {identifier} -> {page_path}")

    return 0


def patch_metric_pages(catalog: dict) -> int:
    metrics = catalog.get("metrics") or []

    if not isinstance(metrics, list):
        print("Expected top-level 'metrics' to be a list.", file=sys.stderr)
        return 1

    if not METRIC_PAGES_DIR.exists():
        print(f"Metric pages directory not found: {METRIC_PAGES_DIR}", file=sys.stderr)
        return 1

    metric_usage = build_metric_usage_lookup(catalog)

    updated_count = 0
    missing_pages = []

    for metric in metrics:
        if not isinstance(metric, dict):
            continue

        identifier = str(metric.get("identifier", "")).strip()

        if not identifier:
            continue

        page_stem = slug_from_identifier(identifier)
        page_path = METRIC_PAGES_DIR / f"{page_stem}.adoc"

        if not page_path.exists():
            missing_pages.append((identifier, str(page_path)))
            continue

        original_text = read_text_fallback(page_path)

        updated_text = original_text
        updated_text = insert_after_page_title(updated_text, f"Identifier: `{identifier}`")
        updated_text = remove_existing_metric_usage_sections(updated_text)

        usage_block = build_metric_usage_block(
            identifier,
            metric_usage.get(identifier, []),
        )

        updated_text = updated_text.rstrip() + "\n\n" + usage_block

        if updated_text != original_text:
            write_text_utf8(page_path, updated_text)
            updated_count += 1
            print(f"Patched metric page: {page_path} ({identifier})")

    print(f"Metric pages patched: {updated_count}")

    if missing_pages:
        print("Metric pages not found for these identifiers:")
        for identifier, page_path in missing_pages:
            print(f"  - {identifier} -> {page_path}")

    return 0


def patch_policy_pages(catalog: dict) -> int:
    policies = catalog.get("policies") or []

    if not isinstance(policies, list):
        print("Expected top-level 'policies' to be a list.", file=sys.stderr)
        return 1

    if not POLICY_PAGES_DIR.exists():
        print(f"Policy pages directory not found: {POLICY_PAGES_DIR}", file=sys.stderr)
        return 1

    updated_count = 0
    missing_pages = []

    for policy in policies:
        if not isinstance(policy, dict):
            continue

        uid = str(policy.get("uid", "")).strip()

        if not uid:
            continue

        page_stem = slug_from_identifier(uid)
        page_path = POLICY_PAGES_DIR / f"{page_stem}.adoc"

        if not page_path.exists():
            missing_pages.append((uid, str(page_path)))
            continue

        original_text = read_text_fallback(page_path)
        updated_text = insert_after_page_title(original_text, f"UID: `{uid}`")

        if updated_text != original_text:
            write_text_utf8(page_path, updated_text)
            updated_count += 1
            print(f"Patched policy page: {page_path} ({uid})")

    print(f"Policy pages patched: {updated_count}")

    if missing_pages:
        print("Policy pages not found for these UIDs:")
        for uid, page_path in missing_pages:
            print(f"  - {uid} -> {page_path}")

    return 0


def deduplicate_policy_nav_entries() -> int:
    """
    Remove duplicate policy navigation entries from modules/data-catalog/nav.adoc.

    The upstream generator currently appears to append the full policy list once
    for each policy, causing each policy to appear multiple times in the sidebar.

    This function keeps the first occurrence of each policy xref and removes
    repeated occurrences.
    """
    if not DATA_CATALOG_NAV_PATH.exists():
        print(f"Data catalog nav file not found: {DATA_CATALOG_NAV_PATH}", file=sys.stderr)
        return 1

    original_text = read_text_fallback(DATA_CATALOG_NAV_PATH)
    lines = original_text.splitlines()

    seen_policy_xrefs = set()
    updated_lines = []
    removed_count = 0

    policy_xref_pattern = re.compile(
        r"^\s*\*+\s+xref:policy:([^.\]]+)\.adoc\[[^\]]+\]\s*$"
    )

    for line in lines:
        match = policy_xref_pattern.match(line)

        if match:
            policy_page = match.group(1)

            if policy_page in seen_policy_xrefs:
                removed_count += 1
                continue

            seen_policy_xrefs.add(policy_page)

        updated_lines.append(line)

    updated_text = "\n".join(updated_lines).rstrip() + "\n"

    if updated_text != original_text:
        write_text_utf8(DATA_CATALOG_NAV_PATH, updated_text)
        print(f"Removed duplicate policy nav entries: {removed_count}")
    else:
        print("Removed duplicate policy nav entries: 0")

    return 0


def main() -> int:
    if not CATALOG_PATH.exists():
        print(f"Catalog file not found: {CATALOG_PATH}", file=sys.stderr)
        return 1

    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}

    exit_code = 0

    exit_code = max(exit_code, patch_dataset_pages(catalog))
    exit_code = max(exit_code, patch_concept_pages(catalog))
    exit_code = max(exit_code, patch_metric_pages(catalog))
    exit_code = max(exit_code, patch_policy_pages(catalog))
    exit_code = max(exit_code, deduplicate_policy_nav_entries())

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
