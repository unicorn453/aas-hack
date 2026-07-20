# Quickstart

## One-Time Environment Setup

Run this from the `excel-to-aasx` repository root only when `.venv` does not
exist or dependencies need to be refreshed:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Initialize reference submodules:

```bash
git submodule update --init --recursive
```

This setup does not extract Excel data and does not generate AASX output. It
only prepares the local Python environment.

## Prepare Input

For the default Schunk configuration, put the workbooks in:

```text
data/input/schunk/
```

Expected file names are defined in:

```text
configs/companies/schunk.json
```

Reusable worksheet mappings are inherited from:

```text
configs/formats/idta-schunk-workbook.json
```

For one exact workbook, copy the company config and reduce only the `workbooks`
list:

```bash
cp configs/companies/schunk.json configs/companies/schunk-single.json
```

Then edit:

```json
{
  "extends": "../formats/idta-schunk-workbook.json",
  "company": "schunk-single",
  "inputDir": "data/input/schunk",
  "outputRoot": "data/generated/schunk-single",
  "workbooks": ["EGP 40-N-N-B.xlsx"]
}
```

## Run Individual Stages

```bash
make extract COMPANY=schunk
make transform COMPANY=schunk
make validate COMPANY=schunk
make package COMPANY=schunk
```

## Run The Full Pipeline

```bash
make generate COMPANY=schunk
```

Outputs:

```text
data/generated/schunk/xlsx-json-step1/
data/generated/schunk/xlsx-json-step2/
data/generated/schunk/xlsx-json-step3/
data/generated/schunk/xlsx-json-step4/
data/generated/schunk/aasx/
```

## Inspect Reports

Important review files:

```text
data/generated/schunk/xlsx-json-step2/<workbook>/mapping-report.json
data/generated/schunk/xlsx-json-step2/<workbook>/review/<sheet>/unmapped-rows.json
data/generated/schunk/xlsx-json-step2/<workbook>/review/<sheet>/preclassified-unmapped-rows.json
data/generated/schunk/xlsx-json-step2/<workbook>/review/<sheet>/dummy-generated.json
data/generated/schunk/xlsx-json-step2/<workbook>/review/<sheet>/matched-rows.json
data/generated/schunk/xlsx-json-step3/<workbook>/validation-report.json
data/generated/schunk/xlsx-json-step4/summary.json
data/generated/schunk/aasx/summary.json
```

Read Step 2 terminal summaries as two levels of evidence:

```text
preclassified_unmapped_excel_row=2, unresolved_excel_row=0
```

`preclassified_unmapped_excel_row` means the first generic classifier did not
directly place those rows. They may still be handled by later transform logic.
`unresolved_excel_row` means rows still not placed after the full transform.
Use `review/<sheet>/unmapped-rows.json` for actual data that needs action.
Use `review/<sheet>/preclassified-unmapped-rows.json` only for diagnostics.

Every stage also writes a timestamped terminal log:

```text
data/generated/schunk/logs/
```

The latest log for each stage is also copied to:

```text
data/generated/schunk/logs/step1-extract.latest.log
data/generated/schunk/logs/step2-transform.latest.log
data/generated/schunk/logs/step3-validate.latest.log
data/generated/schunk/logs/step4-package.latest.log
```

If validation reports errors, do not package or deploy the result as trusted
data. Fix the source workbook, config, mapping logic, or template choice.
