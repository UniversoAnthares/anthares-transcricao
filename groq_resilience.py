"""Idempotent, local-process-shared circuit for the existing Groq STT consumer.

This SQLite state is scoped to one host. A distributed deployment must replace
it with the existing canonical shared ledger before automatic failover.
"""
import email.utils
from contextlib import contextmanager
import os
import sqlite3
import time
from datetime import datetime, timezone

class CircuitOpen(RuntimeError):
    def __init__(self, reason, until):
        self.reason, self.until = reason, until
        super().__init__(reason)

class Circuit:
    def __init__(self, path=None, clock=None):
        self.path = path or os.environ.get("GROQ_BREAKER_DB", "/tmp/anthares-groq-breaker.sqlite3")
        self.clock = clock or time.time
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS circuits (
                scope TEXT PRIMARY KEY, reason TEXT NOT NULL, open_until REAL NOT NULL
            )""")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute("PRAGMA busy_timeout=15000")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def check(self, scope):
        with self._db() as db:
            row = db.execute("SELECT reason, open_until FROM circuits WHERE scope=?", (scope,)).fetchone()
        if row and (row[0] in ("PAYMENT_REQUIRED", "UNCERTAIN") or row[1] > self.clock()):
            raise CircuitOpen(*row)

    def trip(self, scope, reason, retry_after=None):
        reason = str(reason).upper()
        if reason in ("PAYMENT_REQUIRED", "UNCERTAIN"):
            until = 253402300799.0  # operator intervention required
        elif reason == "RATE_LIMIT":
            until = self.clock() + min(3600, max(60, parse_retry_after(retry_after, self.clock())))
        elif reason == "UPSTREAM_ERROR":
            until = self.clock() + 60
        else:
            until = self.clock() + 120
        with self._db() as db:
            db.execute("""INSERT INTO circuits(scope,reason,open_until) VALUES (?,?,?)
              ON CONFLICT(scope) DO UPDATE SET reason=excluded.reason,
              open_until=excluded.open_until""", (scope, reason, until))
        return until

    def success(self, scope):
        # Never clear an uncertain or payment block via another worker's success.
        with self._db() as db:
            db.execute("""DELETE FROM circuits WHERE scope=? AND
                reason NOT IN ('PAYMENT_REQUIRED','UNCERTAIN')""", (scope,))

    def reconcile(self, scope, authorization, receipt):
        if authorization != "OPERATOR_APPROVED" or not str(receipt).strip():
            raise PermissionError("Operator approval and external reconciliation receipt required")
        with self._db() as db:
            db.execute("DELETE FROM circuits WHERE scope=?", (scope,))

def parse_retry_after(value, now=None):
    if not value:
        return 60
    try:
        return max(0, int(float(value)))
    except (ValueError, TypeError):
        try:
            date = email.utils.parsedate_to_datetime(str(value))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return max(0, int(date.timestamp() - (now or time.time())))
        except (ValueError, TypeError, OverflowError):
            return 60

def normalize_transcription(payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid payload")
    texto = payload.get("text", "")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("empty transcription")
    segments = []
    for s in payload.get("segments", []):
        if not isinstance(s, dict):
            continue
        try:
            start, end = float(s["start"]), float(s["end"])
        except (ValueError, TypeError, KeyError):
            continue
        if 0 <= start <= end:
            segments.append({"inicio": start, "fim": end, "texto": str(s.get("text", ""))})
    return {"texto": texto, "segmentos": segments}
