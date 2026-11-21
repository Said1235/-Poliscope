"""Independent reference oracle for the contract (TST-03).

Nothing here imports the contract. Encoding and segmentation come from docs/evidence/*.py; Keccak-256 is the
SDK's pure-Python source (keccak_ref.py), validated against the EVM vector in test_commitments.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "docs", "evidence"))
from reference_encoding import enc, H as _H  # noqa: E402
from reference_segmenter import segment as ref_segment, citable as ref_citable  # noqa: E402
from keccak_ref import Keccak256  # noqa: E402

SCHEMA_VERSION = "POLISCOPE-REPORT-1"
PROMPT_VERSION = "POLISCOPE-PROMPT-1"
SEGMENTATION_VERSION = "POLISCOPE-SEG-1"


def H(domain, *fields):
    return _H(Keccak256, domain, *fields)


def workspace_id(creator_bytes, nonce):
    return H("POLISCOPE:WORKSPACE:V1", creator_bytes, nonce)


def source_commitment(text):
    return H("POLISCOPE:SOURCE:V1", text)


def proposal_id(ws, version, submitter_bytes, source, nonce):
    return H("POLISCOPE:PROPOSAL:V1", ws, version, submitter_bytes, source, nonce)


def policy_commitment(ws, version, rules):
    rl = [
        [
            r["rule_id"], r["title"], r["requirement_text"], r["scope"], r["evaluation_guidance"],
            [[e["id"], e["description"]] for e in r["required_elements"]],
            [[e["id"], e["description"]] for e in r["prohibited_conditions"]],
        ]
        for r in rules
    ]
    return H("POLISCOPE:POLICY:V1", ws, version, len(rules), rl)


def audit_id(ws, pid, source, version, polc):
    return H("POLISCOPE:AUDIT:V1", ws, pid, source, version, polc,
             SCHEMA_VERSION, PROMPT_VERSION, SEGMENTATION_VERSION)


def verdict(statuses):
    if "VIOLATED" in statuses:
        return "NON_COMPLIANT"
    if "INDETERMINATE" in statuses:
        return "INDETERMINATE"
    if all(s == "NOT_APPLICABLE" for s in statuses):
        return "NOT_APPLICABLE"
    return "COMPLIANT"


def evidence_refs(finding, text):
    spans = ref_segment(text)
    return [[sid, spans[sid][0], spans[sid][1], text[spans[sid][0]:spans[sid][1]]]
            for sid in finding["evidence_segments"]]


def report_commitment(aid, ws, pid, version, source, polc, verd, findings, text):
    fl = [[f["rule_id"], f["status"], f["reason_code"], evidence_refs(f, text),
           list(f["missing_elements"]), list(f["prohibited_hits"])] for f in findings]
    return H("POLISCOPE:REPORT:V1", aid, ws, pid, version, source, polc,
             SCHEMA_VERSION, PROMPT_VERSION, SEGMENTATION_VERSION, verd, fl)
