import copy

import pytest

import ref
from helpers import RULES


def bad(rules_mut):
    r = copy.deepcopy(RULES)
    rules_mut(r)
    return r


# ----------------------------------------------------------------------------------------------- workspace
def test_workspace_id_matches_reference_and_creator_is_admin(env):
    wid = env.workspace(nonce="ws-1", name="Mi DAO ñandú")
    assert wid == ref.workspace_id(env.alice, "ws-1")
    ws = env.c.get_workspace(wid)
    assert ws["administrator"].lower() == ("0x" + env.alice.hex())
    assert ws["name"] == "Mi DAO ñandú"
    assert ws["current_policy_version"] == 0 and ws["proposal_counter"] == 0


def test_duplicate_workspace_rejected_state_unchanged(env):
    env.workspace(nonce="dup")
    before = env.storage()
    with env.vm.expect_revert("WORKSPACE_EXISTS"):
        env.c.create_workspace("Other name", "dup")
    assert env.storage() == before


def test_same_nonce_different_creators_get_distinct_workspaces(env):
    a = env.workspace(who=env.alice, nonce="same")
    b = env.workspace(who=env.bob, nonce="same")
    assert a != b
    assert env.c.get_workspace(a)["administrator"].lower() == ("0x" + env.alice.hex())
    assert env.c.get_workspace(b)["administrator"].lower() == ("0x" + env.bob.hex())


@pytest.mark.parametrize("name,nonce,code", [
    ("", "n", "INVALID_INPUT"), ("   ", "n", "INVALID_INPUT"), ("a\nb", "n", "INVALID_INPUT"),
    ("x" * 81, "n", "LIMIT_EXCEEDED"), ("ok", "", "INVALID_INPUT"), ("ok", "bad nonce", "INVALID_INPUT"),
    ("ok", "n" * 65, "INVALID_INPUT"), ("ok", "ñ", "INVALID_INPUT"), ("\u202eevil", "n", "INVALID_INPUT"),
    (5, "n", "INVALID_INPUT"), ("ok", None, "INVALID_INPUT"),
])
def test_workspace_input_validation(env, name, nonce, code):
    before = env.storage()
    with env.vm.expect_revert(code):
        env.c.create_workspace(name, nonce)
    assert env.storage() == before


def test_get_workspace_unknown_and_malformed(env):
    with env.vm.expect_revert("NOT_FOUND"):
        env.c.get_workspace("0" * 64)
    with env.vm.expect_revert("INVALID_INPUT"):
        env.c.get_workspace("xyz")


# ----------------------------------------------------------------------------------------------- policy
def test_publish_policy_commitment_matches_reference_and_rules_retrievable(env):
    wid = env.workspace()
    env.publish(wid, 1)
    pv = env.c.get_policy_version(wid, 1)
    assert pv["rule_count"] == 3
    assert pv["policy_set_commitment"] == ref.policy_commitment(wid, 1, RULES)
    for i, r in enumerate(RULES):
        got = env.c.get_policy_rule(wid, 1, i)
        assert got["rule_id"] == r["rule_id"]
        assert got["required_elements"] == r["required_elements"]
        assert got["prohibited_conditions"] == r["prohibited_conditions"]
    assert env.c.get_workspace(wid)["current_policy_version"] == 1
    with env.vm.expect_revert("NOT_FOUND"):
        env.c.get_policy_rule(wid, 1, 3)


def test_publish_requires_administrator(env):
    wid = env.workspace()
    before = env.storage()
    with env.vm.expect_revert("UNAUTHORIZED"):
        env.publish(wid, 1, who=env.bob)
    assert env.storage() == before


def test_cross_workspace_admin_is_isolated(env):
    w1 = env.workspace(who=env.alice, nonce="a")
    w2 = env.workspace(who=env.bob, nonce="b")
    with env.vm.expect_revert("UNAUTHORIZED"):
        env.publish(w2, 1, who=env.alice)       # alice administers w1 only
    env.publish(w1, 1, who=env.alice)
    env.publish(w2, 1, who=env.bob)
    assert env.c.get_workspace(w1)["current_policy_version"] == 1


def test_version_conflict_cas(env):
    wid = env.workspace()
    for v in (2, 3):                              # cannot skip
        with env.vm.expect_revert("VERSION_CONFLICT"):
            env.publish(wid, v)
    env.publish(wid, 1)
    with env.vm.expect_revert("VERSION_CONFLICT"):
        env.publish(wid, 1)                       # cannot re-publish / overwrite
    env.publish(wid, 2)
    assert env.c.get_workspace(wid)["current_policy_version"] == 2


def test_published_versions_are_immutable(env):
    wid = env.workspace()
    env.publish(wid, 1)
    v1 = env.c.get_policy_version(wid, 1)
    v1_rules = [env.c.get_policy_rule(wid, 1, i) for i in range(3)]
    changed = copy.deepcopy(RULES)
    changed[0]["requirement_text"] = "Completely different requirement."
    env.publish(wid, 2, changed)
    assert env.c.get_policy_version(wid, 1) == v1
    assert [env.c.get_policy_rule(wid, 1, i) for i in range(3)] == v1_rules
    assert env.c.get_policy_version(wid, 2)["policy_set_commitment"] != v1["policy_set_commitment"]
    assert env.c.get_policy_version(wid, 2)["policy_set_commitment"] == ref.policy_commitment(wid, 2, changed)


def test_publish_unknown_workspace(env):
    with env.vm.expect_revert("NOT_FOUND"):
        env.c.publish_policy("0" * 64, 1, copy.deepcopy(RULES))


def _many(n):
    r = []
    for i in range(n):
        x = copy.deepcopy(RULES[0]); x["rule_id"] = f"R{i}"; r.append(x)
    return r


BAD_POLICIES = {
    "empty_list": ([], "INVALID_INPUT"),
    "not_a_list": ("nope", "INVALID_INPUT"),
    "too_many_rules": (_many(13), "LIMIT_EXCEEDED"),
    "duplicate_rule_id": (bad(lambda r: r[1].update(rule_id="POL-001")), "RULE_DUPLICATE"),
    "empty_requirement": (bad(lambda r: r[0].update(requirement_text="")), "INVALID_INPUT"),
    "whitespace_requirement": (bad(lambda r: r[0].update(requirement_text="   \n ")), "INVALID_INPUT"),
    "requirement_too_long": (bad(lambda r: r[0].update(requirement_text="x" * 801)), "LIMIT_EXCEEDED"),
    "title_with_newline": (bad(lambda r: r[0].update(title="a\nb")), "INVALID_INPUT"),
    "bad_rule_id_charset": (bad(lambda r: r[0].update(rule_id="POL 001")), "INVALID_INPUT"),
    "rule_id_too_long": (bad(lambda r: r[0].update(rule_id="A" * 25)), "INVALID_INPUT"),
    "unknown_key": (bad(lambda r: r[0].update(extra="x")), "INVALID_INPUT"),
    "missing_key": (bad(lambda r: r[0].pop("scope")), "INVALID_INPUT"),
    "title_is_int": (bad(lambda r: r[0].update(title=5)), "INVALID_INPUT"),
    "title_is_bool": (bad(lambda r: r[0].update(title=True)), "INVALID_INPUT"),
    "elements_not_list": (bad(lambda r: r[0].update(required_elements="x")), "INVALID_INPUT"),
    "too_many_elements": (bad(lambda r: r[0].update(required_elements=[{"id": f"E{i}", "description": "d"} for i in range(7)])), "INVALID_INPUT"),
    "duplicate_element_id": (bad(lambda r: r[0].update(required_elements=[{"id": "A", "description": "d"}, {"id": "A", "description": "e"}])), "INVALID_INPUT"),
    "element_unknown_key": (bad(lambda r: r[0].update(required_elements=[{"id": "A", "description": "d", "x": 1}])), "INVALID_INPUT"),
    "element_bad_id": (bad(lambda r: r[0].update(required_elements=[{"id": "A B", "description": "d"}])), "INVALID_INPUT"),
    "control_char_in_guidance": (bad(lambda r: r[0].update(evaluation_guidance="a\x00b")), "INVALID_INPUT"),
    "bidi_in_requirement": (bad(lambda r: r[0].update(requirement_text="ok \u202e evil")), "INVALID_INPUT"),
    "rule_not_dict": ([["x"]], "INVALID_INPUT"),
}


@pytest.mark.parametrize("name", sorted(BAD_POLICIES))
def test_bad_policies_rejected_without_state_change(env, name):
    rules, code = BAD_POLICIES[name]
    wid = env.workspace()
    before = env.storage()
    with env.vm.expect_revert(code):
        env.c.publish_policy(wid, 1, rules)
    assert env.storage() == before
    assert env.c.get_workspace(wid)["current_policy_version"] == 0


@pytest.mark.parametrize("version", [0, -1, 1001, True, "1", 1.0, None])
def test_publish_version_type_and_range(env, version):
    wid = env.workspace()
    before = env.storage()
    with env.vm.expect_revert():
        env.c.publish_policy(wid, version, copy.deepcopy(RULES))
    assert env.storage() == before


def test_policy_accepts_max_rules_and_spanish_text(env):
    wid = env.workspace()
    rules = _many(12)
    rules[0]["requirement_text"] = "La propuesta debe identificar el presupuesto solicitado (¿cuánto? ¡siempre!)."
    env.publish(wid, 1, rules)
    assert env.c.get_policy_version(wid, 1)["rule_count"] == 12
    assert env.c.get_policy_rule(wid, 1, 0)["requirement_text"].startswith("La propuesta")


def test_float_is_rejected_at_the_calldata_boundary(env):
    """Floats cannot even be encoded as calldata (framework error, same as on a real network)."""
    wid = env.workspace()
    r = copy.deepcopy(RULES)
    r[0]["scope"] = 1.5
    with env.vm.expect_revert("not calldata encodable"):
        env.c.publish_policy(wid, 1, r)
    assert env.c.get_workspace(wid)["current_policy_version"] == 0
