import json

def test_storage_to_memory_nondet(direct_vm, direct_deploy):
    c = direct_deploy("contracts/probe2.py")
    c.add("p", "POL-001", "must state budget")
    c.add("p", "POL-002", "must name recipient")
    direct_vm.check_pickling = True
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"POL-001": "SATISFIED", "POL-002": "VIOLATED"}))
    c.run("p")
    assert json.loads(c.get_out("p")) == {"POL-001": "SATISFIED", "POL-002": "VIOLATED"}
    assert direct_vm.run_validator() is True

def test_validator_rejects_different(direct_vm, direct_deploy):
    c = direct_deploy("contracts/probe2.py")
    c.add("p", "POL-001", "x")
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"POL-001": "SATISFIED"}))
    c.run("p")
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"evaluate.*", json.dumps({"POL-001": "VIOLATED"}))
    assert direct_vm.run_validator() is False
