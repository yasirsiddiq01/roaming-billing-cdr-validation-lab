# Roaming Billing CDR Validation Lab

A self-directed telecom integration project that validates simplified TAP-style roaming CDR records, detects billing and settlement issues, and generates reconciliation/test reports.

> This project does not implement the proprietary GSMA TAP3 ASN.1 file format. It uses mock CSV records to demonstrate roaming billing validation logic, partner reconciliation, issue reporting, and launch-readiness thinking.

## Why this project exists

The Technical Roaming Integrations Engineer role requires understanding of roaming integrations, billing systems, Wireshark/networking tools, operator onboarding, test reports, and issue resolution. This lab focuses on the billing-validation and integration-documentation part of that workflow.

## What the project validates

- Mandatory field completeness
- Duplicate CDR detection
- IMSI format validation
- Known VPMN partner validation
- Currency validation
- Event timestamp consistency
- Service/tariff matching
- Charge rating mismatch detection
- Sequence-number consistency
- Partner reconciliation summary
- Markdown test report generation

## Project structure

```text
roaming_billing_cdr_validation_lab/
├── data/
│   └── mock_roaming_cdrs.csv
├── reports/
│   ├── validation_issues.csv
│   ├── reconciliation_summary.csv
│   └── validation_test_report.md
├── src/
│   ├── validator.py
│   ├── reconcile.py
│   └── generate_report.py
├── tests/
├── run_project.py
├── requirements.txt
└── README.md
```

## How to run

```bash
python run_project.py
```

Expected output:

```text
Validated 12 records.
Found validation issues.
Reconciliation summary written to reports/reconciliation_summary.csv
Markdown test report written to reports/validation_test_report.md
```

## Example CV bullet

Built an independent roaming billing validation lab using Python to process mock CDR/TAP-style usage records, detect missing fields, duplicate records, rating mismatches, invalid partner identifiers, currency errors, and settlement anomalies, and generate reconciliation and test reports for HPMN/VPMN-style workflows.

## Interview explanation

This project demonstrates how I would approach roaming billing integration validation before commercial launch. I created mock usage records, defined mandatory fields and partner/tariff rules, detected blocking issues, summarized settlement totals by HPMN/VPMN/service type, and generated a test report suitable for technical handover.
