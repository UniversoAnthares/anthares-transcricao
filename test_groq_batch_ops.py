import unittest
from groq_batch_ops import prepare

class BatchTests(unittest.TestCase):
    def test_prepares_deterministic_line_without_spending(self):
        rows=[{"custom_id":"job-1","url":"/v1/chat/completions",
          "body":{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"test"}]}}]
        a,sha=prepare(rows)
        self.assertEqual(a,prepare(rows)[0])
        self.assertEqual(len(sha),64)
        self.assertEqual(a.count(b"\n"),1)
    def test_rejects_duplicate_id_and_unknown_model(self):
        a={"custom_id":"job-1","url":"/v1/chat/completions","body":{"model":"llama-3.1-8b-instant"}}
        with self.assertRaises(ValueError): prepare([a,a])
        with self.assertRaises(ValueError): prepare([dict(a,body={"model":"unpriced-new-model"})])
if __name__ == "__main__":
    unittest.main()
