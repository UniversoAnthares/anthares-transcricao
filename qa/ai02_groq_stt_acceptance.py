"""AI-02: bounded single-request Groq STT acceptance check. No publishing."""
import argparse
import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
import wave
from pathlib import Path

MAX_BYTES = 24 * 1024 * 1024
MODEL = "whisper-large-v3-turbo"
ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
HEADERS = ("x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
           "x-ratelimit-reset-requests", "x-ratelimit-limit-audio-seconds",
           "x-ratelimit-remaining-audio-seconds", "retry-after")

def words(s):
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)

def wer(reference, actual):
    a, b = words(reference), words(actual)
    if not a:
        raise ValueError("Empty reference is not evidence")
    dp = list(range(len(b)+1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(dp[j]+1, nxt[-1]+1, dp[j-1]+(x!=y)))
        dp = nxt
    return round(dp[-1]/len(a), 5)

def segments_ok(items, duration):
    if not isinstance(items, list) or not items:
        return False
    prev = 0.
    for s in items:
        if not isinstance(s, dict) or not isinstance(s.get("text"), str):
            return False
        try:
            start, end = float(s["start"]), float(s["end"])
        except (TypeError, ValueError, KeyError):
            return False
        if not (0 <= start < end <= duration + 2) or start < prev - .5:
            return False
        prev = max(prev, end)
    return float(items[0]["start"]) <= 2 and prev >= duration-2

def wav_info(filename):
    p = Path(filename)
    if p.suffix.lower() != ".wav" or not p.is_file() or p.stat().st_size > MAX_BYTES:
        raise ValueError("Use an authorized local WAV no larger than 24MiB")
    with wave.open(str(p), "rb") as f:
        if f.getnchannels()!=1 or f.getsampwidth()!=2:
            raise ValueError("Expected mono 16-bit PCM")
        duration = f.getnframes()/f.getframerate()
    if duration < 3 or duration > 60:
        raise ValueError("Audio must last 3..60 seconds")
    return p.read_bytes(), duration

def inspect(data, duration, reference, payload, headers=None, live=False, latency=None):
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        raise ValueError("Missing Groq transcript")
    error = wer(reference, payload["text"])
    stamps = segments_ok(payload.get("segments"), duration)
    quotas = {k:str(headers[k])[:80] for k in HEADERS if headers and k in headers}
    passed = error <= .20 and stamps
    return {"result":"PASS_LIVE_REQUIRES_ACCOUNT_ZDR_CHECK" if passed and live else
                    ("PASS_FIXTURE_ONLY" if passed else "FAIL_QUALITY"),
            "live":live, "model":MODEL, "sha256":hashlib.sha256(data).hexdigest(),
            "duration_s":round(duration,3), "wer":error,
            "timestamps_in_audio_and_monotonic":stamps,
            "segments":len(payload.get("segments",[])),
            "latency_s":round(latency,3) if latency is not None else None,
            "estimated_usd_at_published_rate":round(max(10,duration)*.04/3600,7),
            "rate_limit_headers":quotas,
            "retention_reference":"https://console.groq.com/docs/your-data",
            "potential_retention_days":30, "account_zdr_status":"UNVERIFIED"}

def request_once(data, key):
    boundary="anthares-ai02-"+hashlib.sha256(data).hexdigest()[:16]
    def field(k,v):
        return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    body=(field("model",MODEL)+field("language","pt")+
          field("response_format","verbose_json")+
          (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"probe.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode()+
          data+b"\r\n"+(f"--{boundary}--\r\n").encode())
    req=urllib.request.Request(ENDPOINT, data=body,
          headers={"Authorization":"Bearer "+key,
                   "Content-Type":"multipart/form-data; boundary="+boundary},method="POST")
    begin=time.monotonic()
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw=resp.read(1024*1024+1)
        if len(raw)>1024*1024:
            raise ValueError("Groq response exceeded 1MiB")
        return json.loads(raw),{k.lower():v for k,v in resp.headers.items()},time.monotonic()-begin

def run(filename, reference, live=False, fixture=None):
    data, duration=wav_info(filename)
    if fixture:
        return inspect(data,duration,reference,json.loads(Path(fixture).read_text("utf-8")))
    if not live:
        return {"result":"NO_LIVE_CALL", "sha256":hashlib.sha256(data).hexdigest()}
    key=os.environ.get("GROQ_API_KEY","").strip()
    if not key:
        return {"result":"BLOCKED_NO_AUTHORIZED_KEY","live":False}
    try:
        payload,h,elapsed=request_once(data,key)
    except urllib.error.HTTPError as ex:
        return {"result":"UPSTREAM_REJECTED_NO_RETRY","http_status":ex.code,"live":True}
    except (urllib.error.URLError, TimeoutError):
        return {"result":"UNCERTAIN_NO_RETRY","live":True}
    return inspect(data,duration,reference,payload,h,True,elapsed)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--audio",required=True)
    p.add_argument("--reference",required=True)
    p.add_argument("--live",action="store_true")
    p.add_argument("--fixture")
    args=p.parse_args()
    if args.live and args.fixture:
        p.error("Choose live OR fixture")
    print(json.dumps(run(args.audio,args.reference,args.live,args.fixture),sort_keys=True))
