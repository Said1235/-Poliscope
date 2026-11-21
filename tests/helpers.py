"""Shared builders for POLISCOPE direct tests."""
import copy
import json

import ref

CONTRACT = "contracts/poliscope.py"

RULES = [
    {
        "rule_id": "POL-001", "title": "Budget identified",
        "requirement_text": "The proposal must explicitly identify the requested treasury budget.",
        "scope": "Applies to treasury spending proposals.", "evaluation_guidance": "",
        "required_elements": [{"id": "AMOUNT", "description": "Requested amount"},
                              {"id": "CURRENCY", "description": "Currency or token"}],
        "prohibited_conditions": [],
    },
    {
        "rule_id": "POL-002", "title": "Recipient identified",
        "requirement_text": "The proposal must identify the intended recipient of the expenditure.",
        "scope": "Applies to treasury spending proposals.", "evaluation_guidance": "",
        "required_elements": [{"id": "RECIPIENT", "description": "Named recipient"}],
        "prohibited_conditions": [],
    },
    {
        "rule_id": "POL-003", "title": "Restricted access",
        "requirement_text": "The proposal must not request unrestricted treasury access.",
        "scope": "Applies to treasury spending proposals.", "evaluation_guidance": "",
        "required_elements": [],
        "prohibited_conditions": [{"id": "UNRESTRICTED", "description": "Unrestricted treasury access"}],
    },
]

# Segments: 0..3 citable, 4 ("Sí.") NOT citable.
TEXT_ES = (
    "Solicitamos 50.000 USDC para el proveedor Acme.\n"
    "El proveedor es Acme Servicios Limitados.\n"
    "El gasto apoya el objetivo de aumentar la liquidez del protocolo.\n"
    "Se solicita acceso restringido al tesoro hasta el hito 1.\n"
    "Sí."
)
TEXT_EN = (
    "We request 50,000 USDC for the vendor Acme.\n"
    "The vendor is Acme Services Limited.\n"
    "The spend supports the goal of increasing protocol liquidity.\n"
    "Access to the treasury is restricted until milestone 1."
)


def F(rule_id, status, reason, ev=(), ms=(), ph=()):
    return {"rule_id": rule_id, "status": status, "reason_code": reason,
            "evidence_segments": list(ev), "missing_elements": list(ms), "prohibited_hits": list(ph)}


def sat(rid, ev):
    return F(rid, "SATISFIED", "REQUIREMENT_SATISFIED", ev)


def viol(rid, ev):
    return F(rid, "VIOLATED", "REQUIREMENT_CONTRADICTED", ev)


def miss(rid, ms):
    return F(rid, "VIOLATED", "MANDATORY_ELEMENT_MISSING", (), ms)


def prohib(rid, ev, ph):
    return F(rid, "VIOLATED", "PROHIBITED_CONDITION_PRESENT", ev, (), ph)


def indet(rid):
    return F(rid, "INDETERMINATE", "INSUFFICIENT_EVIDENCE")


def na(rid):
    return F(rid, "NOT_APPLICABLE", "OUT_OF_SCOPE")


def rules_with_empty_scope():
    """RULES where POL-001 declares NO applicability scope (so it always applies)."""
    import copy as _c
    r = _c.deepcopy(RULES)
    r[0]["scope"] = ""
    return r


ALL_SAT = [sat("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])]


def llm(findings):
    return json.dumps({"findings": findings})


class Env:
    def __init__(self, vm, c, alice, bob, carol):
        self.vm, self.c, self.alice, self.bob, self.carol = vm, c, alice, bob, carol
        self.vm.sender = alice

    def as_(self, who):
        self.vm.sender = who

    def workspace(self, who=None, nonce="ws1", name="Test DAO"):
        who = who or self.alice
        self.as_(who)
        self.c.create_workspace(name, nonce)
        return ref.workspace_id(who, nonce)

    def publish(self, wid, version, rules=None, who=None):
        self.as_(who or self.alice)
        self.c.publish_policy(wid, version, copy.deepcopy(rules or RULES))

    def register(self, wid, version, text=TEXT_ES, nonce="p1", who=None, title="Proposal"):
        who = who or self.alice
        self.as_(who)
        self.c.register_proposal(wid, version, title, nonce, text)
        return ref.proposal_id(wid, version, who, ref.source_commitment(text), nonce)

    def warm(self, wid=None, pid=None):
        """Perform every read the audit performs, once, so lazy slot allocation has already happened.

        The runtime allocates storage slots for EMPTY containers (maps/arrays) on their first read. This grows the
        raw storage image but changes no logical data (proved by test_storage.py::test_first_read_*), so byte-identity
        assertions around failing calls are made on a warmed state.
        """
        calls = [lambda: self.c.get_audit("0" * 64)]
        if wid is not None:
            calls += [lambda: self.c.get_workspace(wid), lambda: self.c.get_policy_version(wid, 1)]
            calls += [(lambda i=i: self.c.get_policy_rule(wid, 1, i)) for i in range(3)]
        if pid is not None:
            calls += [lambda: self.c.get_proposal(pid)]
        for call in calls:
            try:
                call()
            except Exception:
                pass

    def logical_state(self, wid, pid, rules=3):
        """Decoded, semantic view of everything a failure must not touch."""
        out = {"ws": self.c.get_workspace(wid), "prop": self.c.get_proposal(pid)}
        out["pv"] = self.c.get_policy_version(wid, 1)
        out["rules"] = [self.c.get_policy_rule(wid, 1, i) for i in range(rules)]
        return out

    def setup(self, text=TEXT_ES, rules=None, nonce="p1"):
        wid = self.workspace()
        self.publish(wid, 1, rules)
        pid = self.register(wid, 1, text, nonce)
        self.warm(wid, pid)
        return wid, pid

    def mock(self, findings):
        self.vm.clear_mocks()
        self.vm.mock_llm("DATA DOCUMENT", llm(findings))

    def mock_raw(self, raw):
        self.vm.clear_mocks()
        self.vm.mock_llm("DATA DOCUMENT", raw)

    def audit(self, pid, text=TEXT_ES, who=None):
        self.as_(who or self.alice)
        self.c.audit_proposal(pid, text)

    def leader_report(self):
        return copy.deepcopy(self.vm._captured_validators[-1][0])

    def storage(self):
        return self.vm._storage.snapshot()
