from pathlib import Path
import sys
import unittest
from decimal import Decimal

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from billing_engine import evaluate_billing


class TestBillingEngine(unittest.TestCase):

    def setUp(self):
        self.tariffs = {
            "DATA_EU_001": {
                "service_type": "DATA",
                "unit": "MB",
                "rate": Decimal("0.05"),
                "currency": "EUR",
            },
            "VOICE_EU_001": {
                "service_type": "VOICE",
                "unit": "SEC",
                "rate": Decimal("0.01"),
                "currency": "EUR",
            },
            "SMS_EU_001": {
                "service_type": "SMS",
                "unit": "EVENT",
                "rate": Decimal("0.10"),
                "currency": "EUR",
            },
        }

    def test_data_charge_is_calculated_correctly(self):
        row = {
            "record_id": "CDR_DATA_001",
            "imsi": "214010123456789",
            "hpmn": "SATELIOT_ES",
            "vpmn": "VODAFONE_UK",
            "service_type": "DATA",
            "tariff_id": "DATA_EU_001",
            "data_volume_mb": "10",
            "duration_sec": "0",
            "charge_amount": "0.50",
            "currency": "EUR",
        }

        result = evaluate_billing(row, self.tariffs)

        self.assertEqual(result["expected_charge"], "0.50")
        self.assertEqual(result["billing_status"], "OK")

    def test_voice_charge_is_calculated_correctly(self):
        row = {
            "record_id": "CDR_VOICE_001",
            "imsi": "214010123456789",
            "hpmn": "SATELIOT_ES",
            "vpmn": "ORANGE_FR",
            "service_type": "VOICE",
            "tariff_id": "VOICE_EU_001",
            "data_volume_mb": "0",
            "duration_sec": "120",
            "charge_amount": "1.20",
            "currency": "EUR",
        }

        result = evaluate_billing(row, self.tariffs)

        self.assertEqual(result["expected_charge"], "1.20")
        self.assertEqual(result["billing_status"], "OK")

    def test_sms_charge_is_calculated_correctly(self):
        row = {
            "record_id": "CDR_SMS_001",
            "imsi": "214010123456789",
            "hpmn": "SATELIOT_ES",
            "vpmn": "TELEFONICA_ES",
            "service_type": "SMS",
            "tariff_id": "SMS_EU_001",
            "data_volume_mb": "0",
            "duration_sec": "0",
            "charge_amount": "0.10",
            "currency": "EUR",
        }

        result = evaluate_billing(row, self.tariffs)

        self.assertEqual(result["expected_charge"], "0.10")
        self.assertEqual(result["billing_status"], "OK")

    def test_rating_mismatch_is_detected(self):
        row = {
            "record_id": "CDR_BAD_RATE_001",
            "imsi": "214010123456789",
            "hpmn": "SATELIOT_ES",
            "vpmn": "VODAFONE_UK",
            "service_type": "DATA",
            "tariff_id": "DATA_EU_001",
            "data_volume_mb": "10",
            "duration_sec": "0",
            "charge_amount": "9.99",
            "currency": "EUR",
        }

        result = evaluate_billing(row, self.tariffs)

        self.assertEqual(result["expected_charge"], "0.50")
        self.assertEqual(result["billing_status"], "RATING_MISMATCH")

    def test_missing_tariff_is_detected(self):
        row = {
            "record_id": "CDR_UNKNOWN_TARIFF_001",
            "imsi": "214010123456789",
            "hpmn": "SATELIOT_ES",
            "vpmn": "UNKNOWN_PARTNER",
            "service_type": "DATA",
            "tariff_id": "UNKNOWN_TARIFF",
            "data_volume_mb": "10",
            "duration_sec": "0",
            "charge_amount": "0.50",
            "currency": "EUR",
        }

        result = evaluate_billing(row, self.tariffs)

        self.assertEqual(result["billing_status"], "TARIFF_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()