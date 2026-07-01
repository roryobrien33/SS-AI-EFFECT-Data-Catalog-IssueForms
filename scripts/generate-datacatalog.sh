#!/bin/bash
set -euo pipefail

uv run linkml-convert \
    -s simple_data_catalog_model/src/simple_data_catalog_model/data-catalog.yaml \
    -t ttl \
    -o data-catalog/data-catalog.ttl \
    --prefix-file data-catalog/prefix.yaml \
    data-catalog/data-catalog.yaml

# Clean generated catalog pages and navigation before regenerating.
# This prevents stale pages and duplicated sidebar entries.
rm -rf modules/data-catalog/pages
rm -rf modules/dataset/pages
rm -rf modules/dataset-series/pages
rm -rf modules/dataservice/pages
rm -rf modules/concept/pages
rm -rf modules/metric/pages
rm -rf modules/policy/pages

rm -f modules/data-catalog/nav.adoc
rm -f modules/dataset/nav.adoc
rm -f modules/dataset-series/nav.adoc
rm -f modules/dataservice/nav.adoc
rm -f modules/concept/nav.adoc
rm -f modules/metric/nav.adoc
rm -f modules/policy/nav.adoc

uv run python -m simple_data_catalog_generator.create_data_catalog

uv run python scripts/patch_generated_catalog_pages.py
