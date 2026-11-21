"""Static compatibility/safety checks on the contract source (THREAT_MODEL TM-H*, Pattern J)."""
import ast
import hashlib
import os
import re

import pytest

SRC = open(os.path.join(os.path.dirname(__file__), "..", "..", "contracts", "poliscope.py"), encoding="utf-8").read()
TREE = ast.parse(SRC)
RUNNER = "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"


def code_only():
    """Source without comments/docstrings so words in prose do not trigger the checks."""
    out = []
    for node in ast.walk(TREE):
        if isinstance(node, (ast.Name, ast.Attribute)):
            out.append(ast.unparse(node))
    return " ".join(out)


def test_runner_header_is_first_line_and_pinned():
    lines = SRC.splitlines()
    assert lines[0] == "# v0.2.16"                                      # genvm ABI version line, exactly as the official example
    assert lines[1] == '# { "Depends": "%s" }' % RUNNER
    assert ":test" not in lines[1] and ":latest" not in lines[1] and re.search(r"py-genlayer:[0-9a-z]{52}", lines[1])


@pytest.mark.parametrize("other_generation", [
    # NEW-generation names: valid only for runner kzybg95x/5jycge4q, they make the schema fail to load on the 1jb45 runner
    "import genlayer as gl", "from genlayer.types import *", "gl.contract.Contract", "gl.storage.TreeMap", "gl.storage.DynArray",
    "gl.storage.allow", "gl.Keccak256", "gl.message.raw", "run_nondet_default", ".data",
    # names that exist in neither SDK or whose semantics differ between generations
    "sender_account", "gl.UserError", "run_nondet(", "message_raw", "genlayer.gl.", "genlayer.py.", "gl.eq_principle",
])
def test_no_names_from_the_other_sdk_generation(other_generation):
    assert other_generation not in code_only() and other_generation not in "\n".join(
        l for l in SRC.splitlines() if not l.lstrip().startswith(("#", '"')))


def test_uses_the_generic_unsafe_consensus_api_and_star_import():
    assert "from genlayer import *" in SRC
    assert SRC.count("gl.vm.run_nondet_unsafe(") == 1 and "class Poliscope(gl.Contract):" in SRC
    assert "allow_storage = " not in SRC                      # provided by the star import in this generation


@pytest.mark.parametrize("banned", ["hashlib", "hash(", "import random", "import time", "datetime", "import re\n", "unicodedata",
                                    "float(", ": float", "gl.nondet.web", "gl.evm", "gl.get_contract_at", "payable"])
def test_no_nondeterministic_or_unverified_dependencies(banned):
    assert banned not in code_only() and banned not in "\n".join(l for l in SRC.splitlines() if not l.lstrip().startswith(("#", '"')))


def test_exactly_one_llm_call_site_json_format_and_one_consensus_call():
    assert SRC.count("gl.nondet.exec_prompt(") == 1 and 'response_format="json"' in SRC
    

def test_nondeterministic_closures_never_reference_self_or_storage():
    audit = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "audit_proposal")
    closures = {n.name: n for n in ast.walk(audit) if isinstance(n, ast.FunctionDef) and n.name in ("leader_fn", "validator_fn")}
    assert set(closures) == {"leader_fn", "validator_fn"}
    for name, fn in closures.items():
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        assert "self" not in names, f"{name} references self"
        attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        assert not attrs & {"workspaces", "policy_versions", "proposals", "audits"}, f"{name} touches storage"
        free = names - {"gl", "snap", "leader_result", "report", "own", "findings", "e", "EvaluationError",
                        "_evaluate", "_make_report", "_check_report", "isinstance", "Return", "bool"}
        assert not free, f"{name} references unexpected names: {free}"


def test_constructor_takes_no_arguments_and_does_nothing():
    cls = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == "Poliscope")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    assert [a.arg for a in init.args.args] == ["self"] and len(init.body) == 1 and isinstance(init.body[0], ast.Pass)


def test_only_four_keyed_maps_are_persisted_and_no_latest_pointers():
    cls = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == "Poliscope")
    fields = {n.target.id: ast.unparse(n.annotation) for n in cls.body if isinstance(n, ast.AnnAssign)}
    assert set(fields) == {"workspaces", "policy_versions", "proposals", "audits"}
    assert all(v.startswith("TreeMap[str, ") for v in fields.values())
    assert not re.search(r"\blatest_\w+", SRC)


def test_public_surface_is_exactly_the_specified_methods():
    cls = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == "Poliscope")
    kinds = {}
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                kinds[n.name] = ast.unparse(d)
    assert kinds == {
        "create_workspace": "gl.public.write", "publish_policy": "gl.public.write", "register_proposal": "gl.public.write",
        "audit_proposal": "gl.public.write", "get_workspace": "gl.public.view", "get_policy_version": "gl.public.view",
        "get_policy_rule": "gl.public.view", "get_proposal": "gl.public.view", "get_audit": "gl.public.view"}


def test_every_storage_dataclass_uses_the_allow_alias_and_no_python_collections():
    for n in TREE.body:
        if isinstance(n, ast.ClassDef) and n.name in {"RuleElement", "PolicyRule", "PolicyVersion", "Workspace", "Proposal",
                                                      "EvidenceRef", "Finding", "AuditRecord"}:
            assert [ast.unparse(d) for d in n.decorator_list] == ["allow_storage", "dataclass"], n.name
            for f in n.body:
                ann = ast.unparse(f.annotation)
                assert not re.match(r"(dict|list|set|tuple|float)\b", ann), (n.name, ann)


def test_versions_and_domains_are_the_specified_constants():
    for const in ('SCHEMA_VERSION = "POLISCOPE-REPORT-1"', 'PROMPT_VERSION = "POLISCOPE-PROMPT-1"',
                  'SEGMENTATION_VERSION = "POLISCOPE-SEG-1"'):
        assert const in SRC
    for d in ("WORKSPACE", "POLICY", "SOURCE", "PROPOSAL", "AUDIT", "REPORT"):
        assert f'"POLISCOPE:{d}:V1"' in SRC


def test_no_bare_except_or_swallowed_exceptions():
    for n in ast.walk(TREE):
        if isinstance(n, ast.ExceptHandler):
            assert n.type is not None, "bare except"
            assert not (len(n.body) == 1 and isinstance(n.body[0], ast.Pass)), "swallowed exception"
            assert ast.unparse(n.type) != "Exception", "catch-all"
