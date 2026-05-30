"""Generate a reconciliation summary for mock roaming CDR usage records."""

from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def build_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], dict[str, Decimal | int | str]] = defaultdict(
        lambda: {
            "record_count": 0,
            "total_duration_sec": 0,
            "total_data_volume_mb": Decimal("0"),
            "total_charge_amount": Decimal("0"),
        }
    )

    for row in rows:
        key = (row.get("hpmn", "UNKNOWN"), row.get("vpmn", "UNKNOWN"), row.get("service_type", "UNKNOWN"))
        item = groups[key]
        item["record_count"] = int(item["record_count"]) + 1
        item["total_duration_sec"] = int(item["total_duration_sec"]) + int(row.get("duration_sec") or 0)
        item["total_data_volume_mb"] = parse_decimal(item["total_data_volume_mb"]) + parse_decimal(row.get("data_volume_mb", "0"))
        item["total_charge_amount"] = parse_decimal(item["total_charge_amount"]) + parse_decimal(row.get("charge_amount", "0"))

    output: list[dict[str, str]] = []
    for (hpmn, vpmn, service_type), metrics in sorted(groups.items()):
        output.append(
            {
                "hpmn": hpmn,
                "vpmn": vpmn,
                "service_type": service_type,
                "record_count": str(metrics["record_count"]),
                "total_duration_sec": str(metrics["total_duration_sec"]),
                "total_data_volume_mb": str(parse_decimal(metrics["total_data_volume_mb"]).quantize(Decimal("0.01"))),
                "total_charge_amount": str(parse_decimal(metrics["total_charge_amount"]).quantize(Decimal("0.01"))),
                "currency": "EUR",
            }
        )
    return output


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["hpmn", "vpmn", "service_type", "record_count", "total_duration_sec", "total_data_volume_mb", "total_charge_amount", "currency"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    input_path = Path("data/mock_roaming_cdrs.csv")
    output_path = Path("reports/reconciliation_summary.csv")
    rows = read_csv(input_path)
    summary = build_summary(rows)
    write_csv(summary, output_path)
    print(f"Reconciliation summary written to {output_path}")
