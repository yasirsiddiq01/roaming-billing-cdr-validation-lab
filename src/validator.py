"""Mock roaming CDR/TAP-style billing validation.

This is not an implementation of the proprietary GSMA TAP3 ASN.1 format.
It is a learning lab that validates simplified CSV usage records inspired by
operator-to-operator roaming billing workflows.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

MANDATORY_FIELDS = [
    "record_id",
    "imsi",
    "hpmn",
    "vpmn",
    "service_type",
    "event_start_utc",
    "event_end_utc",
    "duration_sec",
    "charge_amount",
    "currency",
    "tariff_id",
    "sequence_number",
]

VALID_SERVICE_TYPES = {"VOICE", "SMS", "DATA"}
VALID_CURRENCIES = {"EUR"}
VALID_ROAMING_PARTNERS = {"VODAFONE_UK", "ORANGE_FR", "DT_DE"}

# Mock tariff table for validation only.
# DATA is charged per MB. VOICE is charged per started minute. SMS is charged per event.
TARIFFS = {
    "DATA_EU_001": {"service_type": "DATA", "unit": "MB", "rate": Decimal("0.05")},
    "VOICE_EU_001": {"service_type": "VOICE", "unit": "MINUTE", "rate": Decimal("0.20")},
    "SMS_EU_001": {"service_type": "SMS", "unit": "EVENT", "rate": Decimal("0.10")},
}


@dataclass(frozen=True)
class ValidationIssue:
    record_id: str
    severity: str
    rule_id: str
    field: str
    message: str


def parse_utc_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def ceil_minutes(seconds: int) -> int:
    if seconds <= 0:
        return 0
    return (seconds + 59) // 60


def expected_charge(row: dict[str, str]) -> Decimal | None:
    tariff = TARIFFS.get(row.get("tariff_id", ""))
    if tariff is None:
        return None

    service_type = row.get("service_type")
    if service_type != tariff["service_type"]:
        return None

    if tariff["unit"] == "MB":
        volume = parse_decimal(row.get("data_volume_mb", ""))
        if volume is None:
            return None
        return (volume * tariff["rate"]).quantize(Decimal("0.01"))

    if tariff["unit"] == "MINUTE":
        try:
            seconds = int(row.get("duration_sec", "0"))
        except ValueError:
            return None
        return (Decimal(ceil_minutes(seconds)) * tariff["rate"]).quantize(Decimal("0.01"))

    if tariff["unit"] == "EVENT":
        return tariff["rate"].quantize(Decimal("0.01"))

    return None


def validate_rows(rows: Iterable[dict[str, str]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_record_ids: set[str] = set()
    previous_sequence: int | None = None

    for row in rows:
        record_id = row.get("record_id") or "<missing>"

        for field in MANDATORY_FIELDS:
            if not row.get(field):
                issues.append(
                    ValidationIssue(record_id, "ERROR", "MANDATORY_FIELD_MISSING", field, f"Mandatory field '{field}' is missing.")
                )

        if record_id in seen_record_ids:
            issues.append(
                ValidationIssue(record_id, "ERROR", "DUPLICATE_RECORD_ID", "record_id", "Duplicate CDR record_id found.")
            )
        seen_record_ids.add(record_id)

        imsi = row.get("imsi", "")
        if imsi and not (imsi.isdigit() and 14 <= len(imsi) <= 15):
            issues.append(
                ValidationIssue(record_id, "ERROR", "INVALID_IMSI", "imsi", "IMSI must be numeric and 14-15 digits long.")
            )

        service_type = row.get("service_type", "")
        if service_type and service_type not in VALID_SERVICE_TYPES:
            issues.append(
                ValidationIssue(record_id, "ERROR", "INVALID_SERVICE_TYPE", "service_type", "Service type must be VOICE, SMS, or DATA.")
            )

        vpmn = row.get("vpmn", "")
        if vpmn and vpmn not in VALID_ROAMING_PARTNERS:
            issues.append(
                ValidationIssue(record_id, "ERROR", "UNKNOWN_ROAMING_PARTNER", "vpmn", f"Unknown VPMN partner '{vpmn}'.")
            )

        currency = row.get("currency", "")
        if currency and currency not in VALID_CURRENCIES:
            issues.append(
                ValidationIssue(record_id, "ERROR", "INVALID_CURRENCY", "currency", "Only EUR is allowed in this mock roaming agreement.")
            )

        start = parse_utc_timestamp(row.get("event_start_utc", ""))
        end = parse_utc_timestamp(row.get("event_end_utc", ""))
        if row.get("event_start_utc") and start is None:
            issues.append(ValidationIssue(record_id, "ERROR", "INVALID_START_TIME", "event_start_utc", "Invalid UTC timestamp."))
        if row.get("event_end_utc") and end is None:
            issues.append(ValidationIssue(record_id, "ERROR", "INVALID_END_TIME", "event_end_utc", "Invalid UTC timestamp."))
        if start and end and end < start:
            issues.append(ValidationIssue(record_id, "ERROR", "END_BEFORE_START", "event_end_utc", "Event end time is before start time."))

        try:
            duration_sec = int(row.get("duration_sec", "0"))
            if duration_sec < 0:
                raise ValueError
        except ValueError:
            issues.append(ValidationIssue(record_id, "ERROR", "INVALID_DURATION", "duration_sec", "Duration must be a non-negative integer."))
            duration_sec = 0

        data_volume = parse_decimal(row.get("data_volume_mb", "0"))
        if data_volume is None or data_volume < 0:
            issues.append(ValidationIssue(record_id, "ERROR", "INVALID_DATA_VOLUME", "data_volume_mb", "Data volume must be non-negative."))
            data_volume = Decimal("0")

        charge = parse_decimal(row.get("charge_amount", ""))
        if charge is None or charge < 0:
            issues.append(ValidationIssue(record_id, "ERROR", "INVALID_CHARGE", "charge_amount", "Charge amount must be non-negative."))

        tariff_id = row.get("tariff_id", "")
        tariff = TARIFFS.get(tariff_id)
        if tariff_id and tariff is None:
            issues.append(ValidationIssue(record_id, "ERROR", "UNKNOWN_TARIFF", "tariff_id", f"Unknown tariff_id '{tariff_id}'."))
        elif tariff and service_type and tariff["service_type"] != service_type:
            issues.append(ValidationIssue(record_id, "ERROR", "TARIFF_SERVICE_MISMATCH", "tariff_id", "Tariff does not match service type."))

        if service_type == "DATA" and data_volume <= 0:
            issues.append(ValidationIssue(record_id, "WARNING", "ZERO_DATA_VOLUME", "data_volume_mb", "DATA record has zero data usage."))
        if service_type in {"VOICE", "SMS"} and data_volume > 0:
            issues.append(ValidationIssue(record_id, "WARNING", "NON_DATA_VOLUME_PRESENT", "data_volume_mb", "VOICE/SMS record should not contain data volume."))

        exp_charge = expected_charge(row)
        if exp_charge is not None and charge is not None:
            variance = abs(charge - exp_charge)
            if variance > Decimal("0.01"):
                issues.append(
                    ValidationIssue(
                        record_id,
                        "ERROR",
                        "RATING_MISMATCH",
                        "charge_amount",
                        f"Expected charge {exp_charge} but found {charge}.",
                    )
                )

        try:
            seq = int(row.get("sequence_number", ""))
            if previous_sequence is not None and seq <= previous_sequence:
                issues.append(
                    ValidationIssue(record_id, "WARNING", "SEQUENCE_NOT_INCREASING", "sequence_number", "Sequence number is not strictly increasing.")
                )
            previous_sequence = seq
        except ValueError:
            issues.append(ValidationIssue(record_id, "ERROR", "INVALID_SEQUENCE", "sequence_number", "Sequence number must be an integer."))

    return issues


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_issues_csv(issues: list[ValidationIssue], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "severity", "rule_id", "field", "message"])
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue.__dict__)


if __name__ == "__main__":
    input_path = Path("data/mock_roaming_cdrs.csv")
    output_path = Path("reports/validation_issues.csv")
    rows = read_csv(input_path)
    issues = validate_rows(rows)
    write_issues_csv(issues, output_path)
    print(f"Validated {len(rows)} records.")
    print(f"Found {len(issues)} issues.")
    print(f"Issue report written to {output_path}")
