"""Consensus matrix C01-C20 (docs/CONSENSUS_DESIGN.md section 11).

These tests drive the REAL validator_fn captured from gl.vm.run_nondet through direct_vm.run_validator(), with
fabricated leader results. They are DIRECT-MODE evidence of the vote logic only; they are NOT network consensus.
"""
import copy

import pytest

from helpers import ALL_SAT, F, TEXT_ES, indet, llm, miss, na, prohib, sat, viol


@pytest.fixture
def led(env):
    """A proposal audited by an honest leader; returns env with the captured validator ready."""
    wid, pid = env.setup()
    env.mock(ALL_SAT)
    env.audit(pid)
    env.report = env.leader_report()
    return env


def vote(env, own_findings=None, **kw):
    """Run the validator with `own_findings` as ITS independent LLM answer (default: same as leader)."""
    env.mock(ALL_SAT if own_findings is None else own_findings)
    return env.vm.run_validator(**kw)


def mutated(env, fn):
    r = copy.deepcopy(env.report)
    fn(r)
    return r


# ---------------------------------------------------------------------------- C01-C04, C08, C09, C17: agreement / material differences
def test_C01_identical_reports_agree(led, prompts):
    prompts.clear()
    assert vote(led) is True
    assert len(prompts) == 1                                   # validator makes exactly ONE LLM call


def test_validator_prompt_never_contains_leader_findings(led, prompts):
    """Independence: the validator evaluates from the snapshot only; the leader's result is not fed to the LLM."""
    led.mock([viol("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])])
    prompts.clear()
    led.vm.run_validator()
    assert len(prompts) == 1 and "REQUIREMENT_CONTRADICTED\"," not in prompts[0].split("END OF DATA DOCUMENT")[0]


def test_C02_different_global_verdict_disagrees(led):
    assert vote(led, [viol("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])]) is False


def test_C17_same_verdict_but_contradictory_findings_disagree(led):
    """Both nodes end NON_COMPLIANT, but they blame DIFFERENT rules: a summary-only validator would accept this."""
    leader = mutated(led, lambda r: r["findings"].__setitem__(1, viol("POL-002", [1])))        # leader: POL-002 violated
    own = [viol("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])]                       # validator: POL-001 violated
    assert vote(led, own, leader_result=leader) is False
    assert vote(led, [sat("POL-001", [0]), viol("POL-002", [1]), sat("POL-003", [2])], leader_result=leader) is True  # sanity


@pytest.mark.parametrize("own", [
    [sat("POL-001", [0]), sat("POL-002", [1]), indet("POL-003")],                   # C03 status differs, verdict differs
    [sat("POL-001", [0]), sat("POL-002", [1]), na("POL-003")],                      # C03 same verdict (COMPLIANT), status differs
    [sat("POL-001", [1]), sat("POL-002", [1]), sat("POL-003", [2])],                # C04 same verdict, different evidence
    [sat("POL-001", [0, 1]), sat("POL-002", [1]), sat("POL-003", [2])],             # C04 evidence superset
    [sat("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [3])],                # C04 another segment
])
def test_C03_C04_same_or_different_verdict_but_different_finding_disagree(led, own):
    assert vote(led, own) is False


def test_C08_different_reason_code_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].__setitem__(0, viol("POL-001", [0])))
    assert vote(led, [viol("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])], leader_result=leader) is True  # sanity: identical
    leader2 = mutated(led, lambda r: r["findings"].__setitem__(2, prohib("POL-003", [2], ["UNRESTRICTED"])))
    assert vote(led, [sat("POL-001", [0]), sat("POL-002", [1]), viol("POL-003", [2])], leader_result=leader2) is False


def test_C09_different_missing_element_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].__setitem__(0, miss("POL-001", ["AMOUNT"])))
    assert vote(led, [miss("POL-001", ["CURRENCY"]), sat("POL-002", [1]), sat("POL-003", [2])], leader_result=leader) is False
    assert vote(led, [miss("POL-001", ["AMOUNT", "CURRENCY"]), sat("POL-002", [1]), sat("POL-003", [2])], leader_result=leader) is False
    assert vote(led, [miss("POL-001", ["AMOUNT"]), sat("POL-002", [1]), sat("POL-003", [2])], leader_result=leader) is True


def test_different_prohibited_hits_disagree(led):
    leader = mutated(led, lambda r: r["findings"].__setitem__(2, prohib("POL-003", [2], ["UNRESTRICTED"])))
    assert vote(led, ALL_SAT, leader_result=leader) is False


# ---------------------------------------------------------------------------- C05-C07, C20: coverage
def test_C05_C20_missing_finding_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].pop())
    assert vote(led, leader_result=leader) is False


def test_C06_extra_finding_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].append(sat("POL-001", [0])))
    assert vote(led, leader_result=leader) is False


def test_C07_duplicate_finding_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].__setitem__(1, copy.deepcopy(r["findings"][0])))
    assert vote(led, leader_result=leader) is False


def test_wrong_order_of_findings_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].reverse())
    assert vote(led, leader_result=leader) is False


def test_non_canonical_evidence_order_in_leader_report_disagrees(led):
    leader = mutated(led, lambda r: r["findings"].__setitem__(0, sat("POL-001", [1, 0])))
    assert vote(led, [sat("POL-001", [0, 1]), sat("POL-002", [1]), sat("POL-003", [2])], leader_result=leader) is False


# ---------------------------------------------------------------------------- C10, C11: bindings
@pytest.mark.parametrize("field,value", [
    ("policy_version", 2), ("policy_version", True), ("policy_version", "1"),
    ("source_commitment", "0" * 64), ("policy_set_commitment", "f" * 64),
    ("workspace_id", "1" * 64), ("proposal_id", "2" * 64),
    ("schema_version", "POLISCOPE-REPORT-2"), ("prompt_version", "POLISCOPE-PROMPT-2"),
    ("segmentation_version", "POLISCOPE-SEG-2"),
])
def test_C10_C11_binding_mismatch_disagrees(led, field, value):
    leader = mutated(led, lambda r: r.__setitem__(field, value))
    assert vote(led, leader_result=leader) is False


def test_missing_binding_or_extra_key_disagrees(led):
    assert vote(led, leader_result=mutated(led, lambda r: r.pop("source_commitment"))) is False
    assert vote(led, leader_result=mutated(led, lambda r: r.__setitem__("global_verdict", "COMPLIANT"))) is False
    assert vote(led, leader_result=mutated(led, lambda r: r.__setitem__("findings", None))) is False


# ---------------------------------------------------------------------------- C12: malformed leader result never agrees
@pytest.mark.parametrize("junk", [None, 5, 1.5, True, "COMPLIANT", b"bytes", [], [ALL_SAT], {}, {"findings": ALL_SAT},
                                  {"foo": "bar"}, {"findings": "x"}])
def test_C12_malformed_leader_result_is_never_accepted(led, junk):
    try:
        result = vote(led, leader_result=junk)
    except Exception:
        result = False                                          # an exception is Disagree, never agreement
    assert result is not True


# ---------------------------------------------------------------------------- C13, C15: validator-side failures
@pytest.mark.parametrize("raw", ["not json", "[]", "{}", '{"findings": []}', llm([sat("POL-001", [0])]),
                                 llm([sat("POL-001", [99]), sat("POL-002", [1]), sat("POL-003", [2])])])
def test_C13_C15_validator_llm_failure_or_invalid_output_is_disagreement(led, raw):
    led.mock_raw(raw)
    assert led.vm.run_validator() is False


# ---------------------------------------------------------------------------- C14, C16: leader failure
def test_C14_leader_failure_never_agrees_even_if_validator_succeeds(led):
    led.mock(ALL_SAT)
    assert led.vm.run_validator(leader_error=Exception("leader exploded")) is False


def test_C16_both_fail_is_not_agreement(led):
    led.mock_raw("garbage")
    assert led.vm.run_validator(leader_error=Exception("leader exploded")) is False


# ---------------------------------------------------------------------------- C18, C19: evidence
@pytest.mark.parametrize("bad_ev", [[99], [-1], [4], [0, 0], ["0"], [True], [0.0]])
def test_C18_fabricated_or_invalid_evidence_ids_in_leader_report_disagree(led, bad_ev):
    leader = mutated(led, lambda r: r["findings"][0].__setitem__("evidence_segments", bad_ev))
    assert vote(led, leader_result=leader) is False


def test_C19_irrelevant_but_valid_segment_disagrees_when_validators_cite_otherwise(led):
    leader = mutated(led, lambda r: r["findings"].__setitem__(0, sat("POL-001", [3])))    # "acceso restringido..." for the budget rule
    assert vote(led, ALL_SAT, leader_result=leader) is False


def test_residual_risk_R01_identical_irrelevant_evidence_is_agreed(led):
    """DOCUMENTED LIMIT (THREAT_MODEL TM-B03/C14): if every node cites the same irrelevant segment, consensus agrees.

    This test pins the known residual risk so nobody believes the contract detects semantic irrelevance by itself.
    """
    wrong = [sat("POL-001", [3]), sat("POL-002", [1]), sat("POL-003", [2])]
    leader = mutated(led, lambda r: r["findings"].__setitem__(0, wrong[0]))
    assert vote(led, wrong, leader_result=leader) is True


# ---------------------------------------------------------------------------- structure-only validation must not pass (Pattern A/E)
def test_structure_only_validation_would_not_pass(led):
    """Leader and validator agree on shape, verdict and count but disagree on one finding."""
    own = [sat("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [0])]
    assert vote(led, own) is False


# ---------------------------------------------------------------------------- derived fields are never taken from the leader
@pytest.mark.parametrize("key,value", [("quote", "FORGED"), ("start", 0), ("end", 9), ("evidence", []), ("verdict", "COMPLIANT")])
def test_leader_cannot_smuggle_derived_fields_into_findings(led, key, value):
    """Quotes, offsets and verdict are derived by contract code; any such key in a finding is rejected."""
    leader = mutated(led, lambda r: r["findings"][0].__setitem__(key, value))
    assert vote(led, leader_result=leader) is False


def test_smuggled_derived_fields_from_the_llm_are_rejected_before_any_write(env):
    wid, pid = env.setup()
    env.mock_raw(llm([dict(f, quote="FORGED") for f in ALL_SAT]))
    before = env.storage()
    with env.vm.expect_revert("BAD_SHAPE"):
        env.audit(pid)
    assert env.storage() == before


class _Hostile(dict):
    """A leader 'result' whose behavior raises an UNCLASSIFIED exception inside the validator (not an EvaluationError)."""
    def keys(self):
        raise RuntimeError("unclassified failure inside validator")


def test_unclassified_validator_exception_is_never_agreement(led):
    """Directive 6.1(6)/17: an exception the validator does not anticipate must not become `True`.

    In the legacy SDK an unhandled validator exception is a Disagree (read in gl/vm.py: 'same as if this function returned False').
    Direct mode surfaces the exception itself; either outcome is non-agreement, never True.
    """
    led.mock(ALL_SAT)
    try:
        outcome = led.vm.run_validator(leader_result=_Hostile())
    except RuntimeError:
        outcome = "raised"
    assert outcome is not True


def test_oversized_leader_report_is_rejected_before_any_scan(led):
    """Resource safety (audit finding A-3): a leader report with a million-element list must cost O(1) to reject."""
    import time
    big = mutated(led, lambda r: r["findings"][0].__setitem__("evidence_segments", list(range(1_000_000))))
    t = time.perf_counter()
    assert vote(led, leader_result=big) is False
    assert time.perf_counter() - t < 1.0
    huge_dict = mutated(led, lambda r: r.update({f"x{i}": i for i in range(100_000)}))
    assert vote(led, leader_result=huge_dict) is False


def test_leader_claiming_not_applicable_for_an_unscoped_rule_disagrees(env):
    """Validator-side enforcement of audit finding A-4 (V4 re-applies the deterministic rules to the leader report)."""
    from helpers import rules_with_empty_scope
    wid, pid = env.setup(rules=rules_with_empty_scope())
    env.mock(ALL_SAT); env.audit(pid)
    leader = copy.deepcopy(env.leader_report())
    leader["findings"][0] = na("POL-001")                                       # POL-001 has no scope
    env.mock([na("POL-001"), sat("POL-002", [1]), sat("POL-003", [2])])         # even if the validator's own LLM agrees
    assert env.vm.run_validator(leader_result=leader) is False


def test_oversized_leader_lists_never_reach_the_element_scans(led):
    """Deterministic proof of audit finding A-3 (no timing involved): the O(n) scans must not even be CALLED.

    A profile hook records every call to the scanning helpers while the real validator processes a leader report whose
    evidence list has 1,000,000 elements. With the size guard in place the report is rejected before any scan.
    """
    import sys
    calls = []

    def prof(frame, event, arg):
        if event == "call" and frame.f_code.co_name in ("_is_int_list", "_is_str_list"):
            calls.append(frame.f_code.co_name)

    big = mutated(led, lambda r: r["findings"][0].__setitem__("evidence_segments", list(range(1_000_000))))
    led.mock(ALL_SAT)
    sys.setprofile(prof)
    try:
        assert led.vm.run_validator(leader_result=big) is False
    finally:
        sys.setprofile(None)
    assert calls == []
