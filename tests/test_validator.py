from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from validator import validate_rows


class TestValidator(unittest.TestCase):

    def test_duplicate_record_is_detected(self):
        rows = [
            {
                "record_id": "CDR1",
                "imsi": "214010123456789",
                "hpmn": "SATELIOT_ES",
                "vpmn": "VODAFONE_UK",
                "service_type": "DATA",
                "event_start_utc": "2026-05-30T10:00:00Z",
                "event_end_utc": "2026-05-30T10:01:00Z",
                "duration_sec": "60",
                "data_volume_mb": "1",
                "charge_amount": "0.05",
                "currency": "EUR",
                "tariff_id": "DATA_EU_001",
                "sequence_number": "1",
            },
            {
                "record_id": "CDR1",
                "imsi": "214010123456789",
                "hpmn": "SATELIOT_ES",
                "vpmn": "VODAFONE_UK",
                "service_type": "DATA",
                "event_start_utc": "2026-05-30T10:01:00Z",
                "event_end_utc": "2026-05-30T10:02:00Z",
                "duration_sec": "60",
                "data_volume_mb": "1",
                "charge_amount": "0.05",
                "currency": "EUR",
                "tariff_id": "DATA_EU_001",
                "sequence_number": "2",
            },
        ]

        issues = validate_rows(rows)
        rule_ids = [issue.rule_id for issue in issues]

        self.assertIn("DUPLICATE_RECORD_ID", rule_ids)

    def test_rating_mismatch_is_detected(self):
        rows = [
            {
                "record_id": "CDR2",
                "imsi": "214010123456789",
                "hpmn": "SATELIOT_ES",
                "vpmn": "VODAFONE_UK",
                "service_type": "DATA",
                "event_start_utc": "2026-05-30T10:00:00Z",
                "event_end_utc": "2026-05-30T10:01:00Z",
                "duration_sec": "60",
                "data_volume_mb": "10",
                "charge_amount": "9.99",
                "currency": "EUR",
                "tariff_id": "DATA_EU_001",
                "sequence_number": "1",
            }
        ]

        issues = validate_rows(rows)
        rule_ids = [issue.rule_id for issue in issues]

        self.assertIn("RATING_MISMATCH", rule_ids)


if __name__ == "__main__":
    unittest.main()
