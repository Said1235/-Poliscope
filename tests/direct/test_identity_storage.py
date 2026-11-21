"""Identity, concurrency-shaped sequences and storage integrity (THREAT_MODEL sections F and H)."""
import copy

import pytest

import ref
from helpers import ALL_SAT, RULES, TEXT_EN, TEXT_ES, na, sat, viol


# ----------------------------------------------------------------------------- identity (Pattern D)
def test_many_proposals_same_wallet_each_audit_returns_its_own_record(env):
    wid = env.workspace(); env.publish(wid, 1)
    texts = [TEXT_ES, TEXT_EN, TEXT_ES.replace("50.000", "70.000")]
    pids = [env.register(wid, 1, t, f"n{i}") for i, t in enumerate(texts)]
    assert len(set(pids)) == 3
    env.warm(wid, pids[0])
    verdict_plan = [ALL_SAT, [viol("POL-001", [0]), sat("POL-002", [1]), sat("POL-003", [2])], [na("POL-001"), na("POL-002"), na("POL-003")]]
    for pid, t, plan in reversed(list(zip(pids, texts, verdict_plan))):          # audit out of registration order
        env.mock(plan); env.audit(pid, t)
    got = [env.c.get_audit(env.c.get_proposal(p)["audit_id"]) for p in pids]
    assert [g["global_verdict"] for g in got] == ["COMPLIANT", "NON_COMPLIANT", "NOT_APPLICABLE"]
    for g, p in zip(got, pids):
        assert g["proposal_id"] == p
        assert env.c.get_proposal(p)["audit_id"] == g["audit_id"]


def test_overlapping_submitters_do_not_cross_records(env):
    wid = env.workspace(who=env.alice); env.publish(wid, 1)
    a = env.register(wid, 1, TEXT_ES, "x", who=env.alice)
    b = env.register(wid, 1, TEXT_ES, "x", who=env.bob)
    c = env.register(wid, 1, TEXT_ES, "y", who=env.alice)
    env.warm(wid, a)
    env.mock(ALL_SAT)
    env.audit(b, who=env.bob); env.audit(a, who=env.alice)
    pa, pb, pc = (env.c.get_proposal(x) for x in (a, b, c))
    assert (pa["state"], pb["state"], pc["state"]) == ("AUDITED", "AUDITED", "REGISTERED")
    assert pa["audit_id"] != pb["audit_id"] and pc["audit_id"] == ""
    assert env.c.get_audit(pa["audit_id"])["proposal_id"] == a and env.c.get_audit(pb["audit_id"])["proposal_id"] == b


def test_two_audits_of_the_same_proposal_second_is_rejected(env):
    wid = env.workspace(who=env.alice); env.publish(wid, 1)
    pid = env.register(wid, 1, TEXT_ES, "p", who=env.bob)
    env.warm(wid, pid)
    env.mock(ALL_SAT)
    env.audit(pid, who=env.bob)
    first = env.c.get_audit(env.c.get_proposal(pid)["audit_id"])
    before = env.storage()
    with env.vm.expect_revert("AUDIT_EXISTS"):
        env.audit(pid, who=env.alice)                                              # administrator races the submitter
    assert env.storage() == before and env.c.get_audit(first["audit_id"]) == first


def test_audit_that_completes_while_another_is_in_consensus_wins_and_the_loser_is_rejected(env, llm_hooks):
    """Race: tx B finishes its whole audit while tx A is inside its leader LLM call. A must NOT overwrite B."""
    wid = env.workspace(who=env.alice); env.publish(wid, 1)
    pid = env.register(wid, 1, TEXT_ES, "race", who=env.alice)
    env.warm(wid, pid)
    env.mock(ALL_SAT)
    winner_plan = [na("POL-001"), na("POL-002"), na("POL-003")]
    state = {}

    def interleaved_tx():                       # runs inside A's leader_fn, i.e. after A's pre-phase checks
        env.mock(winner_plan)
        env.audit(pid, who=env.alice)           # B: complete audit of the same proposal
        state["winner"] = env.c.get_audit(env.c.get_proposal(pid)["audit_id"])
        env.mock(ALL_SAT)                       # A's own LLM answer (COMPLIANT) is returned next

    llm_hooks.append(interleaved_tx)
    with env.vm.expect_revert("AUDIT_EXISTS"):
        env.audit(pid, who=env.alice)           # A
    assert state["winner"]["global_verdict"] == "NOT_APPLICABLE"
    assert env.c.get_audit(state["winner"]["audit_id"]) == state["winner"]          # B's record intact, never overwritten
    assert env.c.get_proposal(pid)["audit_id"] == state["winner"]["audit_id"]


def test_old_audit_is_unchanged_after_new_audits_and_new_policy_versions(env):
    wid = env.workspace(); env.publish(wid, 1)
    p1 = env.register(wid, 1, TEXT_ES, "a"); env.warm(wid, p1)
    env.mock(ALL_SAT); env.audit(p1)
    old = env.c.get_audit(env.c.get_proposal(p1)["audit_id"])
    env.publish(wid, 2, [copy.deepcopy(RULES[0])])
    p2 = env.register(wid, 2, TEXT_EN, "b")
    env.mock([sat("POL-001", [0])]); env.audit(p2, TEXT_EN)
    assert env.c.get_audit(old["audit_id"]) == old


def test_same_text_and_nonce_in_two_workspaces_are_isolated(env):
    w1 = env.workspace(who=env.alice, nonce="a"); env.publish(w1, 1, who=env.alice)
    w2 = env.workspace(who=env.bob, nonce="b"); env.publish(w2, 1, who=env.bob)
    p1 = env.register(w1, 1, TEXT_ES, "same", who=env.carol)
    p2 = env.register(w2, 1, TEXT_ES, "same", who=env.carol)
    assert p1 != p2 and env.c.get_proposal(p1)["workspace_id"] == w1 and env.c.get_proposal(p2)["workspace_id"] == w2
    assert env.c.get_workspace(w1)["proposal_counter"] == 1 and env.c.get_workspace(w2)["proposal_counter"] == 1


def test_ids_are_computable_before_submission_and_independent_of_counters(env):
    wid = env.workspace(); env.publish(wid, 1)
    expected = ref.proposal_id(wid, 1, env.alice, ref.source_commitment(TEXT_ES), "predicted")
    for i in range(3):                                                              # advance the informational counter
        env.register(wid, 1, TEXT_EN, f"other{i}")
    env.register(wid, 1, TEXT_ES, "predicted")
    assert env.c.get_proposal(expected)["proposal_id"] == expected


def test_publish_mid_flight_does_not_disturb_registered_proposal(env):
    wid = env.workspace(); env.publish(wid, 1)
    pid = env.register(wid, 1, TEXT_ES, "p")
    before = env.c.get_proposal(pid)
    env.publish(wid, 2, [copy.deepcopy(RULES[1])])
    assert env.c.get_proposal(pid) == before


# ----------------------------------------------------------------------------- storage
def test_initial_state_is_empty_and_deploys_without_arguments(env):
    for call in (lambda: env.c.get_workspace("0" * 64), lambda: env.c.get_proposal("0" * 64),
                 lambda: env.c.get_audit("0" * 64), lambda: env.c.get_policy_version("0" * 64, 1)):
        with env.vm.expect_revert("NOT_FOUND"):
            call()


def test_first_read_of_empty_containers_changes_layout_not_logical_data(env):
    """Documents RESEARCH D-21: the runtime lazily allocates empty containers on first read (layout only)."""
    wid = env.workspace(); env.publish(wid, 1); pid = env.register(wid, 1, TEXT_ES, "p")   # NOT warmed
    logical_before = env.logical_state(wid, pid)
    env.mock_raw("garbage")
    with env.vm.expect_revert():
        env.audit(pid)                                    # first failing audit: allocates, never writes data
    assert env.logical_state(wid, pid) == logical_before  # every decoded record is identical
    with env.vm.expect_revert("NOT_FOUND"):
        env.c.get_audit("0" * 64)
    settled = env.storage()
    with env.vm.expect_revert():
        env.audit(pid)
    assert env.storage() == settled                       # and the layout change is idempotent


def test_policy_with_maximum_elements_roundtrips(env):
    wid = env.workspace()
    r = copy.deepcopy(RULES[0])
    r["required_elements"] = [{"id": f"E{i}", "description": f"descripción {i}"} for i in range(6)]
    r["prohibited_conditions"] = [{"id": f"P{i}", "description": f"prohibición {i}"} for i in range(6)]
    env.publish(wid, 1, [r])
    got = env.c.get_policy_rule(wid, 1, 0)
    assert got["required_elements"] == r["required_elements"] and got["prohibited_conditions"] == r["prohibited_conditions"]
    assert env.c.get_policy_version(wid, 1)["policy_set_commitment"] == ref.policy_commitment(wid, 1, [r])


def test_policy_commitment_changes_with_any_single_field_or_order(env):
    base = ref.policy_commitment("a" * 64, 1, RULES)
    for mut in (lambda r: r[0].update(title="x"), lambda r: r[0].update(requirement_text="x"), lambda r: r[0].update(scope="x"),
                lambda r: r[0].update(evaluation_guidance="x"), lambda r: r[0]["required_elements"].reverse(),
                lambda r: r[0]["required_elements"][0].update(description="x"), lambda r: r[2]["prohibited_conditions"][0].update(id="Z"),
                lambda r: r.reverse(), lambda r: r.pop()):
        rules = copy.deepcopy(RULES); mut(rules)
        assert ref.policy_commitment("a" * 64, 1, rules) != base
    assert ref.policy_commitment("a" * 64, 2, RULES) != base and ref.policy_commitment("b" * 64, 1, RULES) != base


def test_report_commitment_covers_every_material_field(env):
    wid, pid = env.setup()
    env.mock(ALL_SAT); env.audit(pid)
    a = env.c.get_audit(env.c.get_proposal(pid)["audit_id"])
    src, polc = a["source_commitment"], a["policy_set_commitment"]

    def rc(findings=ALL_SAT, verdict="COMPLIANT", text=TEXT_ES, **kw):
        args = dict(aid=a["audit_id"], ws=wid, pid=pid, version=1, source=src, polc=polc)
        args.update(kw)
        return ref.report_commitment(args["aid"], args["ws"], args["pid"], args["version"], args["source"], args["polc"], verdict, findings, text)

    assert rc() == a["report_commitment"]
    changed = [
        rc(verdict="INDETERMINATE"), rc(aid="0" * 64), rc(ws="1" * 64), rc(pid="2" * 64), rc(version=2), rc(source="3" * 64), rc(polc="4" * 64),
        rc(findings=[sat("POL-001", [1])] + ALL_SAT[1:]),                                  # different evidence segment
        rc(findings=[ALL_SAT[0] | {"reason_code": "REQUIREMENT_CONTRADICTED"}] + ALL_SAT[1:]),
        rc(findings=ALL_SAT[:2]), rc(findings=list(reversed(ALL_SAT))),
        rc(findings=[ALL_SAT[0] | {"missing_elements": ["AMOUNT"]}] + ALL_SAT[1:]),
        rc(findings=ALL_SAT[:2] + [ALL_SAT[2] | {"prohibited_hits": ["UNRESTRICTED"]}]),
        rc(text=TEXT_ES.replace("Solicitamos", "Pedimos")),                                # different quote text
    ]
    assert all(c != a["report_commitment"] for c in changed) and len(set(changed)) == len(changed)
