"""
Provenance chain: every delegation (allowed or quarantined) is written here
as a cryptographically signed record. This is the audit trail the dashboard
reads from, and the source of truth for security verification.

Two backends:
  - LocalChainStore: append-only JSONL file, used for local dev/testing.
  - FirestoreChainStore: real backend for the deployed system
    (collection: "provenance_records"). Swap by setting CHAIN_BACKEND=firestore.

Records are HMAC-signed with a secret key so an adversary or compromised
agent cannot forge a fake "allowed" entry after the fact -- the auditor can
independently verify sign(record) == stored signature.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


SIGNING_SECRET = os.environ.get("PROVENANCE_SIGNING_SECRET", "dev-only-secret-change-me")


@dataclass
class ProvenanceRecord:
    record_id: str
    task_id: str
    parent_agent: str
    child_agent: str
    requested_scope: str
    granted_scope: str
    allowed: bool
    reason: str
    blast_radius_score: int
    timestamp: float
    risk_level: str = "LOW"
    signature: str = ""

    def signed_payload(self) -> str:
        payload = {k: v for k, v in asdict(self).items() if k != "signature"}
        return json.dumps(payload, sort_keys=True)

    def sign(self) -> "ProvenanceRecord":
        sig = hmac.new(
            SIGNING_SECRET.encode(), self.signed_payload().encode(), hashlib.sha256
        ).hexdigest()
        self.signature = sig
        return self

    def verify(self) -> bool:
        if not self.signature:
            return False
        expected = hmac.new(
            SIGNING_SECRET.encode(), self.signed_payload().encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, self.signature)


def new_record(
    task_id: str,
    parent_agent: str,
    child_agent: str,
    requested_scope: str,
    granted_scope: str,
    allowed: bool,
    reason: str,
    blast_radius_score: int,
    risk_level: str = "LOW",
) -> ProvenanceRecord:
    rec = ProvenanceRecord(
        record_id=str(uuid.uuid4()),
        task_id=task_id,
        parent_agent=parent_agent,
        child_agent=child_agent,
        requested_scope=requested_scope,
        granted_scope=granted_scope,
        allowed=allowed,
        reason=reason,
        blast_radius_score=blast_radius_score,
        risk_level=risk_level,
        timestamp=time.time(),
    )
    return rec.sign()


class BaseChainStore:
    def write(self, record: ProvenanceRecord) -> None:
        raise NotImplementedError

    def read_all(self) -> list[dict]:
        raise NotImplementedError

    def read_task(self, task_id: str) -> list[dict]:
        raise NotImplementedError

    def verify_all(self) -> dict:
        records = self.read_all()
        valid = 0
        tampered = []
        for r in records:
            # Reconstruct ProvenanceRecord
            rec = ProvenanceRecord(
                record_id=r.get("record_id", ""),
                task_id=r.get("task_id", ""),
                parent_agent=r.get("parent_agent", ""),
                child_agent=r.get("child_agent", ""),
                requested_scope=r.get("requested_scope", ""),
                granted_scope=r.get("granted_scope", ""),
                allowed=r.get("allowed", False),
                reason=r.get("reason", ""),
                blast_radius_score=r.get("blast_radius_score", 0),
                timestamp=r.get("timestamp", 0.0),
                risk_level=r.get("risk_level", "LOW"),
                signature=r.get("signature", ""),
            )
            if rec.verify():
                valid += 1
            else:
                tampered.append(r.get("record_id"))

        return {
            "total": len(records),
            "valid": valid,
            "tampered_count": len(tampered),
            "tampered_records": tampered,
            "is_integral": len(tampered) == 0,
        }

    def stats(self) -> dict:
        records = self.read_all()
        allowed_count = sum(1 for r in records if r.get("allowed"))
        quarantined_count = len(records) - allowed_count
        avg_score = (
            sum(r.get("blast_radius_score", 0) for r in records) / len(records)
            if records
            else 0.0
        )
        return {
            "total_records": len(records),
            "allowed_count": allowed_count,
            "quarantined_count": quarantined_count,
            "average_blast_radius": round(avg_score, 2),
        }


class LocalChainStore(BaseChainStore):
    """Append-only JSON-lines file. Good enough for local dev and CI tests."""

    def __init__(self, path: str = "provenance_log.jsonl"):
        self.path = path

    def write(self, record: ProvenanceRecord) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        records = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records

    def read_task(self, task_id: str) -> list[dict]:
        return [r for r in self.read_all() if r.get("task_id") == task_id]

    def simulate_tamper(self, record_id: str) -> bool:
        """Helper for demoing cryptographic tamper detection."""
        records = self.read_all()
        found = False
        with open(self.path, "w", encoding="utf-8") as f:
            for r in records:
                if r.get("record_id") == record_id:
                    # Tamper with the reason or allowed field without resigning
                    r["allowed"] = not r.get("allowed")
                    r["reason"] = "[TAMPERED VIA ADVERSARY] Unauthorized modification."
                    found = True
                f.write(json.dumps(r) + "\n")
        return found

    def clear(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)


class FirestoreChainStore(BaseChainStore):
    """
    Real backend for deployment. Requires google-cloud-firestore and
    GOOGLE_CLOUD_PROJECT to be set. Collection: provenance_records.
    """

    def __init__(self, collection: str = "provenance_records"):
        from google.cloud import firestore
        self._db = firestore.Client()
        self._collection = collection

    def write(self, record: ProvenanceRecord) -> None:
        self._db.collection(self._collection).document(record.record_id).set(asdict(record))

    def read_all(self) -> list[dict]:
        docs = self._db.collection(self._collection).order_by("timestamp").stream()
        return [d.to_dict() for d in docs]

    def read_task(self, task_id: str) -> list[dict]:
        docs = (
            self._db.collection(self._collection)
            .where("task_id", "==", task_id)
            .order_by("timestamp")
            .stream()
        )
        return [d.to_dict() for d in docs]


def get_chain_store() -> BaseChainStore:
    backend = os.environ.get("CHAIN_BACKEND", "local")
    if backend == "firestore":
        return FirestoreChainStore()
    return LocalChainStore()
