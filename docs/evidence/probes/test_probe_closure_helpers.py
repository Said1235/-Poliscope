import json, pytest

def test_module_helpers_in_closures(direct_vm, direct_deploy):
    direct_vm.check_pickling = True
    c = direct_deploy("contracts/probe5.py")
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"findings": ["VIOLATED", "SATISFIED"]}))
    c.run("k")
    assert json.loads(c.get_out("k")) == {"v": "P-1", "findings": ["SATISFIED", "VIOLATED"]}
    assert direct_vm.run_validator() is True

def test_validator_classified_failure_is_false(direct_vm, direct_deploy):
    c = direct_deploy("contracts/probe5.py")
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"findings": ["SATISFIED"]}))
    c.run("k")
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"findings": ["NOPE"]}))      # validator's own output invalid
    assert direct_vm.run_validator() is False

def test_validator_unclassified_exception_never_true(direct_vm, direct_deploy):
    c = direct_deploy("contracts/probe5.py")
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"findings": ["SATISFIED"]}))
    c.run("k")
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"evaluate.*", json.dumps(["not", "a", "dict"]))       # -> EvaluationError (classified)
    assert direct_vm.run_validator() is False
