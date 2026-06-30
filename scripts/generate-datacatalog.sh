#!/bin/bash
set -euo pipef*il

uv run linkml-convert \
    -s*simple_data_catalog_model/src/simp*e_data_catalog_model/data-catalog.*aml \
    -t ttl \
    -o data-cat*log/data-catalog.ttl \
    --prefi*-file data-catalog/prefix.yaml \
 *  data-catalog/data-catalog.yaml

*v run python -m simple_data_catalo*_generator.create_data_catalog

uv*run python scripts/add_dataset_ide*tifiers_to_pages.py
