def test_nested(direct_vm, direct_deploy):
    c = direct_deploy("contracts/probe4.py")
    c.publish([{"rule_id": "POL-001", "title": "x"}, {"rule_id": "POL-002", "n": 3}])
    out = c.get("a1")
    assert out["findings"][1]["rule_id"] == "POL-002"
    assert out["findings"][0]["evidence"] == ["hola!"] and out["findings"][0]["missing"] == ["E1"]
