# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import json
from dataclasses import dataclass

import genlayer as gl
from genlayer.types import *

# Same object as gl.storage.allow; the alias only lets genvm-lint's textual E014 rule recognise it.
allow_storage = gl.storage.allow


@allow_storage
@dataclass
class Rule:
    rule_id: str
    text: str


@allow_storage
@dataclass
class Policy:
    version: u32
    rules: gl.storage.DynArray[Rule]


class Probe2(gl.contract.Contract):
    policies: gl.storage.TreeMap[str, Policy]
    out: gl.storage.TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def add(self, key: str, rid: str, text: str) -> None:
        if key not in self.policies:
            p = self.policies.get_or_insert_default(key)
            p.version = 1
        p = self.policies[key]
        r = p.rules.append_new_get()
        r.rule_id = rid
        r.text = text

    @gl.public.write
    def run(self, key: str) -> None:
        pol = gl.storage.copy_to_memory(self.policies[key])   # storage -> memory
        snapshot = [(r.rule_id, r.text) for r in pol.rules]   # plain python data

        def leader_fn():
            res = gl.nondet.exec_prompt("evaluate " + json.dumps(snapshot), response_format="json")
            return res

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            mine = leader_fn()
            return mine == leader_result.calldata

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        self.out[key] = json.dumps(result, sort_keys=True)

    @gl.public.view
    def get_out(self, key: str) -> str:
        return self.out[key]
