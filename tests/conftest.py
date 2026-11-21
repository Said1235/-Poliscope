"""Test fixtures for the LEGACY generation (runner 1jb45..., genlayer-test==0.29.2).

genlayer-test 0.29.2 auto-parses a str LLM mock into a dict, which is exactly what the legacy SDK's JSON decoder expects,
so NO mocking workaround is needed here (the workaround in the 0.30.x/new-generation variant must NOT be applied: it would
break this generation). This module only wraps the handler to (a) record every prompt the LLM would receive and
(b) run one-shot hooks, which let a test simulate an interleaved transaction inside the leader's LLM call.
"""
import pytest

from helpers import Env

_PROMPTS = []
_HOOKS = []   # one-shot callbacks run when the next LLM call happens (simulates an interleaved transaction)


@pytest.fixture(autouse=True, scope="session")
def _record_prompts_and_run_hooks():
    from gltest.direct import wasi_mock

    original = wasi_mock._handle_llm_request

    def wrapped(vm, data):
        _PROMPTS.append(data.get("prompt", ""))
        if _HOOKS:
            _HOOKS.pop(0)()
        return original(vm, data)

    wasi_mock._handle_llm_request = wrapped
    yield
    wasi_mock._handle_llm_request = original


@pytest.fixture
def llm_hooks():
    _HOOKS.clear()
    yield _HOOKS
    _HOOKS.clear()


@pytest.fixture
def prompts():
    _PROMPTS.clear()
    return _PROMPTS


@pytest.fixture
def env(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.check_pickling = True      # TST-01: closures must be serializable
    direct_vm.strict_mocks = True        # TST-01: a mock that is never matched is reported
    _PROMPTS.clear()
    c = direct_deploy("contracts/poliscope.py")
    return Env(direct_vm, c, direct_alice, direct_bob, direct_charlie)
