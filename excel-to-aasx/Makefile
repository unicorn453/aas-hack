SHELL := /bin/bash

COMPANY ?= schunk
COMPANY_CONFIG ?= configs/companies/$(COMPANY).json
COMPANY_OUTPUT_ROOT ?= data/generated/$(COMPANY)
REFERENCE_DIR ?= third_party/admin-shell-io/submodel-templates
EXTRACTION_ROOT ?= data/extraction

.DEFAULT_GOAL := help

.PHONY: help extract transform validate package generate collect test

help:
	@awk 'BEGIN {FS = ":.*##"; printf "excel-to-aasx commands:\n\n"} /^[a-zA-Z_-]+:.*?##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

extract: ## Step 1: Extract complete workbook JSON from configured Excel files
	@bash scripts/run-stage.sh step1-extract $(COMPANY_OUTPUT_ROOT) python3 -m excel_to_aasx.extract \
		--company-config $(COMPANY_CONFIG) \
		--output-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step1

transform: extract ## Step 2: Map extracted JSON into official-template-shaped AAS JSON
	@bash scripts/run-stage.sh step2-transform $(COMPANY_OUTPUT_ROOT) python3 -m excel_to_aasx.transform \
		--company-config $(COMPANY_CONFIG) \
		--input-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step1 \
		--reference-dir $(REFERENCE_DIR) \
		--output-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step2

validate: transform ## Step 3: Validate generated AAS JSON
	@bash scripts/run-stage.sh step3-validate $(COMPANY_OUTPUT_ROOT) python3 -m excel_to_aasx.validate \
		--company-config $(COMPANY_CONFIG) \
		--input-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step2 \
		--reference-dir $(REFERENCE_DIR) \
		--output-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step3

package: validate ## Step 4: Package validated AAS JSON as AASX
	@bash scripts/run-stage.sh step4-package $(COMPANY_OUTPUT_ROOT) python3 -m excel_to_aasx.package \
		--input-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step2 \
		--validation-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step3 \
		--output-dir $(COMPANY_OUTPUT_ROOT)/xlsx-json-step4

generate: package ## Run extraction through AASX packaging
	@echo "AASX files generated under $(COMPANY_OUTPUT_ROOT)/xlsx-json-step4"

collect: extract ## Collect Step 1 JSON outputs into one review folder
	@bash scripts/run-stage.sh collect-extraction $(COMPANY_OUTPUT_ROOT) python3 -m excel_to_aasx.collect_extraction \
		--company-config $(COMPANY_CONFIG) \
		--output-root $(EXTRACTION_ROOT)

test: ## Run tests
	@python3 -m pytest tests
