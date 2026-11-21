import copy
import json

import pytest

import ref
from helpers import (ALL_SAT, F, RULES, TEXT_EN, TEXT_ES, indet, llm, miss, na, prohib, sat, viol)


def audit_and_fetch(env, pid, text=TEXT_ES, who=None):
    env.audit(pid, text, who)
    prop = env.c.get_proposal(pid)
    return prop, env.c.get_audit(prop["audit_id"])


# ----------------------------------------------------------------------------------------------- happy path
def test_audit_happy_path_every_derived_field_matches_independent_oracle(env, prompts):
    wid, pid = env.setup()
    env.mock(ALL_SAT)
    prop, a = audit_and_fetch(env, pid)

    source = ref.source_commitment(TEXT_ES)
    polc = ref.policy_commitment(wid, 1, RULES)
    aid = ref.audit_id(wid, pid, source, 1, polc)
    assert prop["state"] == "AUDITED" and prop["audit_id"] == aid
    assert a["audit_id"] == aid and a["global_verdict"] == "COMPLIANT" == ref.verdict([f["status"] for f in ALL_SAT])
    assert (a["workspace_id"], a["proposal_id"], a["policy_version"]) == (wid, pid, 1)
    assert (a["source_commitment"], a["policy_set_commitment"]) == (source, polc)
    assert (a["schema_version"], a["prompt_version"], a["segmentation_version"]) == (
        ref.SCHEMA_VERSION, ref.PROMPT_VERSION, ref.SEGMENTATION_VERSION)
    assert a["finding_count"] == 3
    spans = ref.ref_segment(TEXT_ES)
    for stored, given in zip(a["findings"], ALL_SAT):
        assert stored["rule_id"] == given["rule_id"] and stored["status"] == given["status"]
        for e in stored["evidence"]:                      # quotes are exact substrings derived by the contract
            s, t = spans[e["segment_id"]]
            assert (e["start"], e["end"], e["quote"]) == (s, t, TEXT_ES[s:t])
    assert a["findings"][0]["evidence"][0]["quote"] == "Solicitamos 50.000 USDC para el proveedor Acme."
    assert a["findings"][2]["evidence"][0]["quote"].endswith("liquidez del protocolo.")
    assert a["report_commitment"] == ref.report_commitment(aid, wid, pid, 1, source, polc, "COMPLIANT", ALL_SAT, TEXT_ES)
    assert len(prompts) == 1                              # exactly ONE LLM call for the leader


def test_audit_english_proposal_and_missing_and_prohibited_fields_roundtrip(env):
    wid, pid = env.setup(text=TEXT_EN)
    findings = [miss("POL-001", ["CURRENCY"]), sat("POL-002", [1]), prohib("POL-003", [3], ["UNRESTRICTED"])]
    env.mock(findings)
    _, a = audit_and_fetch(env, pid, TEXT_EN)
    assert a["global_verdict"] == "NON_COMPLIANT"
    assert a["findings"][0]["missing_elements"] == ["CURRENCY"] and a["findings"][0]["evidence"] == []
    assert a["findings"][2]["prohibited_hits"] == ["UNRESTRICTED"]
    assert a["findings"][2]["evidence"][0]["quote"] == "Access to the treasury is restricted until milestone 1."
    source = ref.source_commitment(TEXT_EN); polc = ref.policy_commitment(wid, 1, RULES)
    aid = ref.audit_id(wid, pid, source, 1, polc)
    assert a["report_commitment"] == ref.report_commitment(aid, wid, pid, 1, source, polc, "NON_COMPLIANT", findings, TEXT_EN)


def test_canonical_ordering_is_applied_to_llm_output(env):
    wid, pid = env.setup()
    scrambled = [sat("POL-003", [2, 0]), sat("POL-001", [3, 1]), sat("POL-002", [1])]
    scrambled[2]["evidence_segments"] = [1]
    env.mock(scrambled)
    _, a = audit_and_fetch(env, pid)
    assert [f["rule_id"] for f in a["findings"]] == ["POL-001", "POL-002", "POL-003"]    # policy order
    assert [e["segment_id"] for e in a["findings"][0]["evidence"]] == [1, 3]               # ascending
    assert [e["segment_id"] for e in a["findings"][2]["evidence"]] == [0, 2]


def test_missing_elements_are_canonicalized_to_published_order(env):
    wid, pid = env.setup()
    env.mock([miss("POL-001", ["CURRENCY", "AMOUNT"]), sat("POL-002", [1]), sat("POL-003", [2])])
    _, a = audit_and_fetch(env, pid)
    assert a["findings"][0]["missing_elements"] == ["AMOUNT", "CURRENCY"]


# ----------------------------------------------------------------------------------------------- global verdict (all combinations)
S, V, I, N = "S", "V", "I", "N"


def build(code, rid, ev):
    return {S: sat, V: viol}[code](rid, ev) if code in (S, V) else (indet(rid) if code == I else na(rid))


@pytest.mark.parametrize("combo,expected", [
    ((S, S, S), "COMPLIANT"), ((S, V, S), "NON_COMPLIANT"), ((V, V, V), "NON_COMPLIANT"),
    ((S, I, S), "INDETERMINATE"), ((V, I, N), "NON_COMPLIANT"), ((N, N, N), "NOT_APPLICABLE"),
    ((S, N, N), "COMPLIANT"), ((I, N, N), "INDETERMINATE"), ((N, I, V), "NON_COMPLIANT"), ((S, S, N), "COMPLIANT"),
])
def test_global_verdict_is_derived_by_code(env, combo, expected):
    wid, pid = env.setup()
    findings = [build(c, r["rule_id"], [i]) for i, (c, r) in enumerate(zip(combo, RULES))]
    env.mock(findings)
    _, a = audit_and_fetch(env, pid)
    assert a["global_verdict"] == expected == ref.verdict([f["status"] for f in findings])


def test_llm_cannot_inject_its_own_verdict(env):
    wid, pid = env.setup()
    raw = {"findings": [viol("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])], "global_verdict": "COMPLIANT"}
    env.mock_raw(json.dumps(raw))
    before = env.storage()
    with env.vm.expect_revert("BAD_SHAPE"):
        env.audit(pid)
    assert env.storage() == before


# ----------------------------------------------------------------------------------------------- invalid LLM output fails closed
def with_(idx, **kw):
    fs = copy.deepcopy(ALL_SAT); fs[idx].update(kw); return fs


BAD_OUTPUTS = {
    "not_json": ("this is not json", "BAD_SHAPE"),      # legacy mock layer hands back the raw str (real host raises NondetException -> TRANSIENT; both fail closed)
    "json_list": (json.dumps([1, 2]), "BAD_SHAPE"),
    "json_string": (json.dumps("COMPLIANT"), "BAD_SHAPE"),
    "empty_object": (json.dumps({}), "BAD_SHAPE"),
    "extra_top_key": (json.dumps({"findings": ALL_SAT, "x": 1}), "BAD_SHAPE"),
    "alias_key": (json.dumps({"results": ALL_SAT}), "BAD_SHAPE"),
    "findings_not_list": (json.dumps({"findings": "x"}), "BAD_COVERAGE"),
    "missing_finding": (json.dumps({"findings": ALL_SAT[:2]}), "BAD_COVERAGE"),
    "extra_finding": (json.dumps({"findings": ALL_SAT + [sat("POL-001", [0])]}), "BAD_COVERAGE"),
    "duplicate_finding": (json.dumps({"findings": [ALL_SAT[0], ALL_SAT[0], ALL_SAT[2]]}), "DUPLICATE_FINDING"),
    "unknown_rule_id": (json.dumps({"findings": with_(0, rule_id="POL-999")}), "MISSING_FINDING"),
    "finding_extra_key": (json.dumps({"findings": with_(0, offsets=[1])}), "BAD_SHAPE"),
    "finding_missing_key": (json.dumps({"findings": [{k: v for k, v in ALL_SAT[0].items() if k != "status"}] + ALL_SAT[1:]}), "BAD_SHAPE"),
    "bad_status": (json.dumps({"findings": with_(0, status="COMPLIANT")}), "BAD_STATUS"),
    "lowercase_status": (json.dumps({"findings": with_(0, status="satisfied")}), "BAD_STATUS"),
    "bad_reason": (json.dumps({"findings": with_(0, reason_code="LOOKS_FINE")}), "BAD_REASON"),
    "satisfied_with_missing_reason": (json.dumps({"findings": with_(0, reason_code="MANDATORY_ELEMENT_MISSING")}), "BAD_COMBINATION"),
    "na_with_contradicted": (json.dumps({"findings": [na("POL-001") | {"reason_code": "REQUIREMENT_CONTRADICTED"}] + ALL_SAT[1:]}), "BAD_COMBINATION"),
    "satisfied_without_evidence": (json.dumps({"findings": with_(0, evidence_segments=[])}), "BAD_COMBINATION"),
    "indeterminate_with_evidence": (json.dumps({"findings": [indet("POL-001") | {"evidence_segments": [0]}] + ALL_SAT[1:]}), "BAD_COMBINATION"),
    "na_with_evidence": (json.dumps({"findings": [na("POL-001") | {"evidence_segments": [0]}] + ALL_SAT[1:]}), "BAD_COMBINATION"),
    # 5 > LIM_EVIDENCE: since audit finding A-3 the size guard rejects this BEFORE the combination check (still rejected, more specific code)
    "too_many_evidence": (json.dumps({"findings": with_(0, evidence_segments=[0, 1, 2, 3, 4])}), "BAD_OUTPUT_SIZE"),
    "evidence_out_of_range": (json.dumps({"findings": with_(0, evidence_segments=[99])}), "BAD_EVIDENCE"),
    "evidence_negative": (json.dumps({"findings": with_(0, evidence_segments=[-1])}), "BAD_EVIDENCE"),
    "evidence_bool": (json.dumps({"findings": with_(0, evidence_segments=[True])}), "BAD_SHAPE"),
    "evidence_string": (json.dumps({"findings": with_(0, evidence_segments=["0"])}), "BAD_SHAPE"),
    "evidence_float": (json.dumps({"findings": with_(0, evidence_segments=[0.0])}), "BAD_SHAPE"),
    "evidence_duplicate": (json.dumps({"findings": with_(0, evidence_segments=[0, 0])}), "BAD_EVIDENCE"),
    "evidence_non_citable": (json.dumps({"findings": with_(0, evidence_segments=[4])}), "BAD_EVIDENCE"),
    "missing_ids_on_satisfied": (json.dumps({"findings": with_(0, missing_elements=["AMOUNT"])}), "BAD_COMBINATION"),
    "mandatory_missing_without_ids": (json.dumps({"findings": [miss("POL-001", [])] + ALL_SAT[1:]}), "BAD_COMBINATION"),
    "unknown_element_id": (json.dumps({"findings": [miss("POL-001", ["NOPE"])] + ALL_SAT[1:]}), "BAD_ELEMENT_ID"),
    "element_of_other_rule": (json.dumps({"findings": [miss("POL-001", ["RECIPIENT"])] + ALL_SAT[1:]}), "BAD_ELEMENT_ID"),
    "duplicate_element_id": (json.dumps({"findings": [miss("POL-001", ["AMOUNT", "AMOUNT"])] + ALL_SAT[1:]}), "BAD_ELEMENT_ID"),
    "prohibited_without_ids": (json.dumps({"findings": ALL_SAT[:2] + [prohib("POL-003", [2], [])]}), "BAD_COMBINATION"),
    "prohibited_unknown_id": (json.dumps({"findings": ALL_SAT[:2] + [prohib("POL-003", [2], ["X"])]}), "BAD_ELEMENT_ID"),
    "oversized_evidence_list_10k": (json.dumps({"findings": with_(0, evidence_segments=list(range(10000)))}), "BAD_OUTPUT_SIZE"),
    "oversized_missing_list": (json.dumps({"findings": [miss("POL-001", ["AMOUNT"]) | {"missing_elements": ["AMOUNT"] * 7}] + ALL_SAT[1:]}), "BAD_OUTPUT_SIZE"),
    "oversized_prohibited_list": (json.dumps({"findings": ALL_SAT[:2] + [ALL_SAT[2] | {"prohibited_hits": ["X"] * 7}]}), "BAD_OUTPUT_SIZE"),
    "huge_top_level_object": (json.dumps({"findings": ALL_SAT, **{f"k{i}": i for i in range(5000)}}), "BAD_SHAPE"),
    "mandatory_missing_on_rule_without_elements": (json.dumps({"findings": ALL_SAT[:2] + [miss("POL-003", ["AMOUNT"])]}), "BAD_ELEMENT_ID"),
}


@pytest.mark.parametrize("name", sorted(BAD_OUTPUTS))
def test_invalid_llm_output_fails_closed_and_preserves_state(env, name):
    raw, code = BAD_OUTPUTS[name]
    wid, pid = env.setup()
    env.mock_raw(raw)
    before = env.storage()
    with env.vm.expect_revert(code):
        env.audit(pid)
    assert env.storage() == before                          # byte-identical state
    p = env.c.get_proposal(pid)
    assert p["state"] == "REGISTERED" and p["audit_id"] == ""


def test_retry_after_failed_audit_succeeds(env):
    wid, pid = env.setup()
    env.mock_raw("garbage")
    with env.vm.expect_revert():
        env.audit(pid)
    env.mock(ALL_SAT)                                       # same proposal, LLM now behaves
    prop, a = audit_and_fetch(env, pid)
    assert prop["state"] == "AUDITED" and a["global_verdict"] == "COMPLIANT"


# ----------------------------------------------------------------------------------------------- commitments are enforced at audit time
def test_source_commitment_mismatch_one_byte(env):
    wid, pid = env.setup()
    env.mock(ALL_SAT)
    before = env.storage()
    for altered in (TEXT_ES[:-1] + "!", TEXT_ES + " ", TEXT_ES.replace("50.000", "50.001"), TEXT_ES.replace("Sí", "Si"),
                    TEXT_ES.replace("\n", "\r\n", 1), "x" + TEXT_ES):
        with env.vm.expect_revert("SOURCE_COMMITMENT_MISMATCH"):
            env.audit(pid, altered)
    assert env.storage() == before


def test_audit_unknown_proposal_and_bad_ids(env):
    with env.vm.expect_revert("NOT_FOUND"):
        env.c.audit_proposal("0" * 64, TEXT_ES)
    with env.vm.expect_revert("INVALID_INPUT"):
        env.c.audit_proposal("nothex", TEXT_ES)
    with env.vm.expect_revert("INVALID_INPUT"):
        env.c.audit_proposal("0" * 64, "")


def test_audit_uses_the_bound_policy_version_not_latest(env, prompts):
    wid = env.workspace(); env.publish(wid, 1)
    pid = env.register(wid, 1, TEXT_ES, "p1")
    v2 = copy.deepcopy(RULES)
    v2[0]["title"] = "SECOND-VERSION-ONLY-TITLE"; v2.append({**copy.deepcopy(RULES[1]), "rule_id": "POL-004"})
    env.publish(wid, 2, v2)                                  # a newer version appears before the audit
    env.mock(ALL_SAT)
    prop, a = audit_and_fetch(env, pid)
    assert a["policy_version"] == 1 and a["finding_count"] == 3
    assert "SECOND-VERSION-ONLY-TITLE" not in prompts[0] and "Budget identified" in prompts[0]
    assert a["policy_set_commitment"] == ref.policy_commitment(wid, 1, RULES)


def test_same_text_under_different_versions_gets_different_audit_ids(env):
    wid = env.workspace(); env.publish(wid, 1); env.publish(wid, 2)
    p1 = env.register(wid, 1, TEXT_ES, "p"); p2 = env.register(wid, 2, TEXT_ES, "p")
    env.mock(ALL_SAT)
    _, a1 = audit_and_fetch(env, p1); _, a2 = audit_and_fetch(env, p2)
    assert a1["audit_id"] != a2["audit_id"] and a1["report_commitment"] != a2["report_commitment"]


# ----------------------------------------------------------------------------------------------- authorization
def test_audit_authorization_matrix(env):
    wid = env.workspace(who=env.alice); env.publish(wid, 1, who=env.alice)
    pid = env.register(wid, 1, TEXT_ES, "p", who=env.bob)       # submitter = bob, administrator = alice
    env.mock(ALL_SAT)
    before = env.storage()
    with env.vm.expect_revert("UNAUTHORIZED"):
        env.audit(pid, who=env.carol)                            # third party
    assert env.storage() == before
    prop, a = audit_and_fetch(env, pid, who=env.alice)           # administrator may audit
    assert prop["state"] == "AUDITED"
    pid2 = env.register(wid, 1, TEXT_ES, "p2", who=env.bob)
    prop2, _ = audit_and_fetch(env, pid2, who=env.bob)           # submitter may audit
    assert prop2["state"] == "AUDITED"


def test_admin_of_other_workspace_cannot_audit(env):
    w1 = env.workspace(who=env.alice, nonce="a"); env.publish(w1, 1, who=env.alice)
    w2 = env.workspace(who=env.bob, nonce="b"); env.publish(w2, 1, who=env.bob)
    pid = env.register(w2, 1, TEXT_ES, "p", who=env.carol)
    env.mock(ALL_SAT)
    with env.vm.expect_revert("UNAUTHORIZED"):
        env.audit(pid, who=env.alice)


# ----------------------------------------------------------------------------------------------- duplicates / immutability
def test_duplicate_audit_rejected_and_first_audit_never_overwritten(env):
    wid, pid = env.setup()
    env.mock(ALL_SAT)
    prop, first = audit_and_fetch(env, pid)
    before = env.storage()
    env.mock([viol("POL-001", [0]), viol("POL-002", [1]), viol("POL-003", [2])])     # a different, worse result
    with env.vm.expect_revert("AUDIT_EXISTS"):
        env.audit(pid)
    assert env.storage() == before
    assert env.c.get_audit(prop["audit_id"]) == first


def test_hard_cut_segments_are_trimmed_and_quotes_match_the_oracle(env):
    """Regression for design defect F-1: a hard cut that lands right after a space must not leave trailing whitespace."""
    text = "a" * 499 + " " + "b" * 100 + " fin del texto de prueba."          # cut at 500 falls just after the space
    spans = ref.ref_segment(text)
    assert spans[0] == (0, 499) and text[spans[0][0]:spans[0][1]] == "a" * 499
    wid, pid = env.setup(text=text)
    findings = [sat("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [1])]
    env.mock(findings)
    env.audit(pid, text)
    a = env.c.get_audit(env.c.get_proposal(pid)["audit_id"])
    assert a["findings"][0]["evidence"][0]["quote"] == "a" * 499
    assert not a["findings"][0]["evidence"][0]["quote"].endswith(" ")
    polc = ref.policy_commitment(wid, 1, RULES)
    aid = ref.audit_id(wid, pid, ref.source_commitment(text), 1, polc)
    assert a["report_commitment"] == ref.report_commitment(aid, wid, pid, 1, ref.source_commitment(text), polc, "COMPLIANT", findings, text)


def test_tampered_policy_in_storage_is_detected_before_any_llm_call(env, prompts):
    """Integrity check against storage corruption (unreachable via the public API, hence simulated directly)."""
    wid, pid = env.setup()
    env.mock(ALL_SAT)
    env.c.policy_versions[wid + ":1"].rules[0].requirement_text = "TAMPERED requirement text"
    before = env.storage()
    with env.vm.expect_revert("POLICY_COMMITMENT_MISMATCH"):
        env.audit(pid)
    assert env.storage() == before and prompts == []             # rejected deterministically, LLM never consulted


def test_audit_checks_exact_byte_length_before_hashing_directive_9_1(env, prompts):
    """Audit finding A-1: the stored byte length must be compared at audit time, not only the Keccak commitment.

    The commitment is left intact and ONLY the stored length is corrupted, so the length check is the sole defence exercised.
    """
    wid, pid = env.setup()
    env.mock(ALL_SAT)
    env.c.proposals[pid].text_length_bytes = len(TEXT_ES.encode("utf-8")) + 1
    before = env.storage()
    with env.vm.expect_revert("SOURCE_COMMITMENT_MISMATCH: length"):
        env.audit(pid)
    assert env.storage() == before and prompts == []             # rejected before any LLM call


def test_audit_length_check_uses_bytes_not_characters(env):
    text = "Propuesta con acentos: áéíóú ñ ¿ok? ¡sí! 日本語。"        # chars != bytes
    assert len(text) != len(text.encode("utf-8"))
    wid, pid = env.setup(text=text)
    spans = ref.ref_segment(text)
    ev = [i for i, (a, b) in enumerate(spans) if ref.ref_citable(text[a:b])][0]
    env.mock([sat("POL-001", [ev]), sat("POL-002", [ev]), sat("POL-003", [ev])])
    env.audit(pid, text)
    assert env.c.get_proposal(pid)["state"] == "AUDITED"
    assert env.c.get_proposal(pid)["text_length_bytes"] == len(text.encode("utf-8"))


def test_write_methods_return_their_exact_ids_directive_23_2_and_24(env):
    """Audit finding A-2: a caller must receive the exact record ID of its own transaction (no wallet-list diffing)."""
    wid = env.c.create_workspace("Mi DAO", "ret")
    assert wid == ref.workspace_id(env.alice, "ret")
    polc = env.c.publish_policy(wid, 1, copy.deepcopy(RULES))
    assert polc == ref.policy_commitment(wid, 1, RULES) == env.c.get_policy_version(wid, 1)["policy_set_commitment"]
    pid = env.c.register_proposal(wid, 1, "t", "n1", TEXT_ES)
    assert pid == ref.proposal_id(wid, 1, env.alice, ref.source_commitment(TEXT_ES), "n1")
    env.mock(ALL_SAT)
    aid = env.c.audit_proposal(pid, TEXT_ES)
    assert aid == env.c.get_proposal(pid)["audit_id"] == ref.audit_id(wid, pid, ref.source_commitment(TEXT_ES), 1, polc)
    assert env.c.get_audit(aid)["audit_id"] == aid


def test_not_applicable_is_forbidden_for_a_rule_without_scope_directive_12_1(env):
    """Audit finding A-4: a rule that declares no applicability scope always applies; the model cannot opt out of it."""
    from helpers import rules_with_empty_scope
    wid, pid = env.setup(rules=rules_with_empty_scope())
    env.mock([na("POL-001"), sat("POL-002", [1]), sat("POL-003", [2])])         # POL-001 has empty scope
    before = env.storage()
    with env.vm.expect_revert("BAD_APPLICABILITY"):
        env.audit(pid)
    assert env.storage() == before
    env.mock([sat("POL-001", [0]), na("POL-002"), na("POL-003")])                # scoped rules may be NOT_APPLICABLE
    env.audit(pid)
    assert env.c.get_audit(env.c.get_proposal(pid)["audit_id"])["global_verdict"] == "COMPLIANT"


def test_all_rules_not_applicable_requires_every_rule_to_declare_a_scope(env):
    """The vacuous verdict NOT_APPLICABLE can only arise when EVERY rule explicitly declares when it applies."""
    from helpers import rules_with_empty_scope
    wid, pid = env.setup(rules=rules_with_empty_scope())
    env.mock([na("POL-001"), na("POL-002"), na("POL-003")])
    with env.vm.expect_revert("BAD_APPLICABILITY"):
        env.audit(pid)
    assert env.c.get_proposal(pid)["state"] == "REGISTERED"
