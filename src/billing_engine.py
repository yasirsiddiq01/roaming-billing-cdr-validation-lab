from pathlib import Path
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CDR_FILE = PROJECT_ROOT / "data" / "mock_roaming_cdrs.csv"
TARIFF_FILE = PROJECT_ROOT / "data" / "tariffs.csv"

REPORTS_DIR = PROJECT_ROOT / "reports"
BILLING_RESULTS_FILE = REPORTS_DIR / "billing_results.csv"
BILLING_SUMMARY_FILE = REPORTS_DIR / "billing_summary.csv"

MONEY = Decimal("0.01")
TOLERANCE = Decimal("0.01")


def to_decimal(value: str, default: Decimal = Decimal("0")) -> Decimal:
    try:
        if value is None or str(value).strip() == "":
            return default
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return default


def money_round(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def load_tariffs(tariff_path: Path) -> dict:
    tariffs = {}

    with tariff_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            tariff_id = row["tariff_id"].strip()

            tariffs[tariff_id] = {
                "service_type": row["service_type"].strip().upper(),
                "unit": row["unit"].strip().upper(),
                "rate": to_decimal(row["rate"]),
                "currency": row["currency"].strip().upper(),
            }

    return tariffs


def load_cdrs(cdr_path: Path) -> list[dict]:
    with cdr_path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def calculate_quantity(row: dict, tariff: dict) -> Decimal:
    service_type = tariff["service_type"]
    unit = tariff["unit"]

    if service_type == "DATA" and unit == "MB":
        return to_decimal(row.get("data_volume_mb", "0"))

    if service_type == "VOICE" and unit == "SEC":
        return to_decimal(row.get("duration_sec", "0"))

    if service_type == "SMS" and unit == "EVENT":
        return Decimal("1")

    return Decimal("0")


def calculate_expected_charge(row: dict, tariff: dict) -> Decimal:
    quantity = calculate_quantity(row, tariff)
    rate = tariff["rate"]
    return money_round(quantity * rate)


def evaluate_billing(row: dict, tariffs: dict) -> dict:
    record_id = row.get("record_id", "").strip()
    tariff_id = row.get("tariff_id", "").strip()
    actual_charge = money_round(to_decimal(row.get("charge_amount", "0")))
    actual_currency = row.get("currency", "").strip().upper()

    base_result = {
        "record_id": record_id,
        "imsi": row.get("imsi", ""),
        "hpmn": row.get("hpmn", ""),
        "vpmn": row.get("vpmn", ""),
        "service_type": row.get("service_type", ""),
        "tariff_id": tariff_id,
        "quantity": "",
        "unit": "",
        "rate": "",
        "currency": actual_currency,
        "actual_charge": str(actual_charge),
        "expected_charge": "",
        "difference": "",
        "billing_status": "",
        "notes": "",
    }

    if tariff_id not in tariffs:
        base_result["billing_status"] = "TARIFF_NOT_FOUND"
        base_result["notes"] = "No tariff rule found for this tariff_id."
        return base_result

    tariff = tariffs[tariff_id]

    quantity = calculate_quantity(row, tariff)
    expected_charge = calculate_expected_charge(row, tariff)
    difference = money_round(actual_charge - expected_charge)

    base_result.update(
        {
            "quantity": str(quantity),
            "unit": tariff["unit"],
            "rate": str(tariff["rate"]),
            "expected_charge": str(expected_charge),
            "difference": str(difference),
        }
    )

    if actual_currency != tariff["currency"]:
        base_result["billing_status"] = "CURRENCY_MISMATCH"
        base_result["notes"] = (
            f"CDR currency {actual_currency} does not match tariff currency "
            f"{tariff['currency']}."
        )
        return base_result

    if abs(difference) > TOLERANCE:
        base_result["billing_status"] = "RATING_MISMATCH"
        base_result["notes"] = (
            f"Actual charge {actual_charge} differs from expected charge "
            f"{expected_charge}."
        )
        return base_result

    base_result["billing_status"] = "OK"
    base_result["notes"] = "Actual charge matches expected tariff calculation."
    return base_result


def write_billing_results(results: list[dict]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    fieldnames = [
        "record_id",
        "imsi",
        "hpmn",
        "vpmn",
        "service_type",
        "tariff_id",
        "quantity",
        "unit",
        "rate",
        "currency",
        "actual_charge",
        "expected_charge",
        "difference",
        "billing_status",
        "notes",
    ]

    with BILLING_RESULTS_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def write_billing_summary(results: list[dict]) -> None:
    summary = defaultdict(
        lambda: {
            "record_count": 0,
            "total_actual_charge": Decimal("0"),
            "total_expected_charge": Decimal("0"),
            "total_difference": Decimal("0"),
        }
    )

    for row in results:
        key = (
            row["vpmn"],
            row["service_type"],
            row["billing_status"],
        )

        summary[key]["record_count"] += 1
        summary[key]["total_actual_charge"] += to_decimal(row["actual_charge"])
        summary[key]["total_expected_charge"] += to_decimal(row["expected_charge"])
        summary[key]["total_difference"] += to_decimal(row["difference"])

    fieldnames = [
        "vpmn",
        "service_type",
        "billing_status",
        "record_count",
        "total_actual_charge",
        "total_expected_charge",
        "total_difference",
    ]

    with BILLING_SUMMARY_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for (vpmn, service_type, billing_status), values in summary.items():
            writer.writerow(
                {
                    "vpmn": vpmn,
                    "service_type": service_type,
                    "billing_status": billing_status,
                    "record_count": values["record_count"],
                    "total_actual_charge": str(
                        money_round(values["total_actual_charge"])
                    ),
                    "total_expected_charge": str(
                        money_round(values["total_expected_charge"])
                    ),
                    "total_difference": str(
                        money_round(values["total_difference"])
                    ),
                }
            )


def main() -> None:
    if not INPUT_CDR_FILE.exists():
        raise SystemExit(f"Input CDR file not found: {INPUT_CDR_FILE}")

    if not TARIFF_FILE.exists():
        raise SystemExit(f"Tariff file not found: {TARIFF_FILE}")

    tariffs = load_tariffs(TARIFF_FILE)
    cdrs = load_cdrs(INPUT_CDR_FILE)

    results = [evaluate_billing(row, tariffs) for row in cdrs]

    write_billing_results(results)
    write_billing_summary(results)

    mismatch_count = sum(
        1 for row in results if row["billing_status"] != "OK"
    )

    print(f"Processed {len(results)} CDR records for billing validation.")
    print(f"Found {mismatch_count} billing exceptions.")
    print(f"Billing results written to {BILLING_RESULTS_FILE.relative_to(PROJECT_ROOT)}")
    print(f"Billing summary written to {BILLING_SUMMARY_FILE.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()