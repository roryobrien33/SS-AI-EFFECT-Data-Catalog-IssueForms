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


def insert_identifier_into_overview(page_text: str, identifier: str) -> str:
    """
    Insert the identifier row into the existing Overview table.

    Expected generated pattern:

      == Overview

      [cols="1,1"]
      |===
      a| Title
      a| ...
      ...
      |===

    The script inserts:

      a| Identifier
      a| ex:...

    directly after the table start marker.
    """

    if "a| Identifier" in page_text:
        return page_text

    overview_match = re.search(
        r"(== Overview\s*\n\s*\[cols=\"1,1\"\]\s*\n\s*\|===\s*\n)",
        page_text,
     *  flags=re.MULTILINE,
    )

    i* not overview_match:
        retur* page_text

    insert_text = f"a|*Identifier\na| {identifier}\n"

  * insert_position = overview_match.*nd()

    return page_text[:insert_position] + insert_text + page_tex*[insert_position:]


def main() ->*int:
    if not CATALOG_PATH.exist*():
        print(f"Catalog file n*t found: {CATALOG_PATH}", file=sys*stderr)
        return 1

    if n*t DATASET_PAGES_DIR.exists():
    *   print(f"Dataset pages directory*not found: {DATASET_PAGES_DIR}", f*le=sys.stderr)
        return 1

 *  catalog = yaml.safe_load(CATALOG*PATH.read_text(encoding="utf-8")) *r {}
    datasets = catalog.get("d*tasets") or []

    if not isinsta*ce(datasets, list):
        print(*Expected top-level 'datasets' to b* a list.", file=sys.stderr)
      * return 1

    updated_count = 0
 *  missing_pages = []

    for data*et in datasets:
        if not isi*stance(dataset, dict):
           *continue

        identifier = str*dataset.get("identifier", "")).str*p()

        if not identifier:
  *         continue

        page_st*m = slug_from_identifier(identifie*)
        page_path = DATASET_PAGE*_DIR / f"{page_stem}.adoc"

      * if not page_path.exists():
      *     missing_pages.append((identif*er, str(page_path)))
            c*ntinue

        original_text = pa*e_path.read_text(encoding="utf-8")*        updated_text = insert_iden*ifier_into_overview(original_text,*identifier)

        if updated_te*t != original_text:
            pa*e_path.write_text(updated_text, en*oding="utf-8")
            updated*count += 1
            print(f"Add*d identifier to {page_path}: {iden*ifier}")

    print(f"Dataset page* updated: {updated_count}")

    i* missing_pages:
        print("Dat*set pages not found for these iden*ifiers:")
        for identifier, *age_path in missing_pages:
       *    print(f"  - {identifier} -> {p*ge_path}")

    return 0


if __na*e__ == "__main__":
    raise Syste*Exit(main())
