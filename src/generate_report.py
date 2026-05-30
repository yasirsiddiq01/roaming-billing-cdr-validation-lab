"""Generate a Markdown test report for the mock roaming billing validation lab."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generate_markdown_report(cdrs: list[dict[str, str]], issues: list[dict[str, str]], summary: list[dict[str, str]]) -> str:
    issue_counter = Counter(issue["rule_id"] for issue in issues)
    severity_counter = Counter(issue["severity"] for issue in issues)

    lines = [
        "# Roaming Billing CDR Validation Test Report",
        "",
        "## 1. Objective",
        "Validate a simplified set of TAP-style roaming usage records for billing readiness, partner settlement checks, and integration-test reporting.",
        "",
        "## 2. Scope",
        "This lab uses mock CSV CDRs. It is not a proprietary TAP3 ASN.1 decoder. The goal is to demonstrate understanding of roaming billing validation workflows.",
        "",
        "## 3. Dataset Summary",
        f"- Total CDR records tested: {len(cdrs)}",
        f"- Total validation issues found: {len(issues)}",
        f"- Error count: {severity_counter.get('ERROR', 0)}",
        f"- Warning count: {severity_counter.get('WARNING', 0)}",
        "",
        "## 4. Validation Rules Covered",
        "- Mandatory field completeness",
        "- Duplicate CDR detection",
        "- IMSI format validation",
        "- Known VPMN partner validation",
        "- Currency validation",
        "- Event timestamp consistency",
        "- Service/tariff matching",
        "- Charge rating mismatch detection",
        "- Sequence-number consistency",
        "",
        "## 5. Issue Breakdown",
        "| Rule ID | Count |",
        "|---|---:|",
    ]

    for rule_id, count in sorted(issue_counter.items()):
        lines.append(f"| {rule_id} | {count} |")

    lines.extend([
        "",
        "## 6. Reconciliation Summary",
        "| HPMN | VPMN | Service | Records | Duration sec | Data MB | Charge | Currency |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ])

    for row in summary:
        lines.append(
            f"| {row['hpmn']} | {row['vpmn']} | {row['service_type']} | {row['record_count']} | "
            f"{row['total_duration_sec']} | {row['total_data_volume_mb']} | {row['total_charge_amount']} | {row['currency']} |"
        )

    lines.extend([
        "",
        "## 7. Launch Readiness Interpretation",
        "The mock file is not ready for settlement because it contains blocking ERROR-level issues including duplicate CDRs, rating mismatches, invalid currency, missing IMSI, unknown roaming partner, negative charge, and timestamp inconsistency.",
        "",
        "## 8. Recommended Actions",
        "- Reject or quarantine records with ERROR-level defects.",
        "- Send partner-facing issue report for UNKNOWN_ROAMING_PARTNER and rating mismatch cases.",
        "- Re-run validation after corrected records are received.",
        "- Confirm tariff table, currency, partner identifiers, and mandatory field mapping before commercial launch.",
        "",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    cdrs = read_csv(Path("data/mock_roaming_cdrs.csv"))
    issues = read_csv(Path("reports/validation_issues.csv"))
    summary = read_csv(Path("reports/reconciliation_summary.csv"))
    report = generate_markdown_report(cdrs, issues, summary)
    output_path = Path("reports/validation_test_report.md")
    output_path.write_text(report, encoding="utf-8")
    print(f"Markdown test report written to {output_path}")
