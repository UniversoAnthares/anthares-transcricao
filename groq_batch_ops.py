"""Prepare Groq Batch JSONL without network or automatic spending.

Submission intentionally requires a separate authenticated, budget-approved
executor and a persisted canonical receipt. This utility cannot charge users.
"""
import argparse
import hashlib
import json
from pathlib import Path

CHAT_MODELS = {"llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-20b", "openai/gpt-oss-120b"}
AUDIO_MODELS = {"whisper-large-v3", "whisper-large-v3-turbo"}
MAX_ITEMS = 50000
MAX_BYTES = 200 * 1024 * 1024

def prepare(items):
    rows = []
    seen = set()
    for item in items:
        cid, endpoint, body = item["custom_id"], item["url"], item["body"]
        if not isinstance(cid, str) or not cid or len(cid) > 100 or cid in seen:
            raise ValueError("invalid/duplicate custom_id")
        if endpoint == "/v1/chat/completions":
            if body.get("model") not in CHAT_MODELS:
                raise ValueError("unapproved chat model")
        elif endpoint in ("/v1/audio/transcriptions", "/v1/audio/translations"):
            if body.get("model") not in AUDIO_MODELS:
                raise ValueError("unapproved audio model")
        else:
            raise ValueError("unapproved endpoint")
        if not isinstance(body, dict):
            raise ValueError("invalid body")
        seen.add(cid)
        rows.append({"custom_id": cid, "method": "POST", "url": endpoint, "body": body})
        if len(rows) > MAX_ITEMS:
            raise ValueError("batch size exceeded")
    if not rows:
        raise ValueError("empty batch")
    data = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("batch bytes exceeded")
    return data, hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("output_jsonl")
    args = parser.parse_args()
    data, sha = prepare(json.loads(Path(args.input_json).read_text(encoding="utf-8")))
    out = Path(args.output_jsonl)
    if out.exists():
        raise FileExistsError("refusing to overwrite output")
    out.write_bytes(data)
    print(json.dumps({"lines": len(data.splitlines()), "sha256": sha,
      "status": "PREPARED_NOT_SUBMITTED", "paid_calls": 0}))
if __name__ == "__main__":
    main()
