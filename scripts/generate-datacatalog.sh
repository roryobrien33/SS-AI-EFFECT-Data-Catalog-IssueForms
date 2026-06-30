#!/bin/bash
set -euo pipefail

uv run linkml-convert \
    -s simple_data_catalog_model/src/simple_data_catalog_model/data-catalog.yaml \
    -t ttl \
    -o data-catalog/data-catalog.ttl \
    --prefix-file data-catalog/prefix.yaml \
    data-catalog/data-catalog.yaml

uv run python -m simple_data_catalog_generator.create_data_catalog

uv run python scripts/add_dataset_identifiers_to_pages.py
