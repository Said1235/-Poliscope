# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import typing
from dataclasses import dataclass

import genlayer as gl
from genlayer.types import *

allow_storage = gl.storage.allow


@allow_storage
@dataclass
class EvidenceRef:
    segment_id: u32
    start: u32
    end: u32
    quote: str


@allow_storage
@dataclass
class Finding:
    rule_id: str
    status: str
    evidence: gl.storage.DynArray[EvidenceRef]
    missing: gl.storage.DynArray[str]


@allow_storage
@dataclass
class Audit:
    audit_id: str
    findings: gl.storage.DynArray[Finding]


class Probe4(gl.contract.Contract):
    audits: gl.storage.TreeMap[str, Audit]

    def __init__(self):
        pass

    @gl.public.write
    def publish(self, rules: list[dict[str, typing.Any]]) -> None:
        a = self.audits.get_or_insert_default("a1")
        a.audit_id = "a1"
        for r in rules:
            f = a.findings.append_new_get()
            f.rule_id = r["rule_id"]
            f.status = "SATISFIED"
            e = f.evidence.append_new_get()
            e.segment_id = 3
            e.start = 0
            e.end = 5
            e.quote = "hola!"
            f.missing.append("E1")

    @gl.public.view
    def get(self, audit_id: str) -> dict[str, typing.Any]:
        a = gl.storage.copy_to_memory(self.audits[audit_id])
        return {"audit_id": a.audit_id,
                "findings": [{"rule_id": f.rule_id, "evidence": [e.quote for e in f.evidence], "missing": list(f.missing)} for f in a.findings]}
