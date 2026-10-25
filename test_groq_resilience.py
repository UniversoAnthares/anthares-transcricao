import tempfile
import unittest
from pathlib import Path
from groq_resilience import Circuit, CircuitOpen, normalize_transcription, parse_retry_after

class CircuitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = [1000.]
        self.dbpath = str(Path(self.tmp.name) / "circuit.db")
        self.a = Circuit(self.dbpath, clock=lambda: self.now[0])
        self.b = Circuit(self.dbpath, clock=lambda: self.now[0])

    def tearDown(self):
        self.tmp.cleanup()

    def test_429_rate_limit_shared_and_expiry(self):
        self.a.trip("groq-stt", "RATE_LIMIT", "90")
        with self.assertRaises(CircuitOpen):
            self.b.check("groq-stt")
        self.now[0] += 91
        self.b.check("groq-stt")
        self.b.success("groq-stt")

    def test_402_fails_closed_until_approval(self):
        self.a.trip("groq-stt", "PAYMENT_REQUIRED")
        self.now[0] += 500000
        with self.assertRaises(CircuitOpen):
            self.b.check("groq-stt")
        with self.assertRaises(PermissionError):
            self.a.reconcile("groq-stt", "OPERATOR_APPROVED", "")
        self.a.reconcile("groq-stt", "OPERATOR_APPROVED", "provider-invoice-reviewed")
        self.b.check("groq-stt")

    def test_uncertain_not_retried_or_cleared_by_success(self):
        self.a.trip("groq-stt", "UNCERTAIN")
        self.b.success("groq-stt")
        with self.assertRaises(CircuitOpen):
            self.b.check("groq-stt")

    def test_5xx_opens_for_one_minute(self):
        self.a.trip("groq-stt", "UPSTREAM_ERROR")
        with self.assertRaises(CircuitOpen):
            self.b.check("groq-stt")
        self.now[0] += 61
        self.b.check("groq-stt")

    def test_transcript_segments(self):
        r = normalize_transcription({"text":"Olá","segments":[{"start":0.1,"end":0.9,"text":"Olá"},{"start":-1,"end":2,"text":"bad"}]})
        self.assertEqual(r["segmentos"], [{"inicio":0.1,"fim":0.9,"texto":"Olá"}])
        with self.assertRaises(ValueError):
            normalize_transcription({"text":""})

    def test_retry_after(self):
        self.assertEqual(parse_retry_after("12"), 12)
        self.assertEqual(parse_retry_after("invalid"), 60)

if __name__ == "__main__":
    unittest.main()
