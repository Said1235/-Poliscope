# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import json
import genlayer as gl
from genlayer.types import *

STATUS_ENUM = frozenset(["SATISFIED", "VIOLATED"])
PROMPT_VERSION = "P-1"


class EvaluationError(Exception):
    pass


def canonicalize(resp, snapshot):
    """Module-level helper used from inside leader_fn / validator_fn."""
    if type(resp) is not dict or set(resp.keys()) != {"findings"}:
        raise EvaluationError("[LLM_ERROR] BAD_SHAPE")
    out = []
    for f in resp["findings"]:
        if f not in STATUS_ENUM:
            raise EvaluationError("[LLM_ERROR] BAD_STATUS")
        out.append(f)
    return sorted(out)


class Probe5(gl.contract.Contract):
    out: gl.storage.TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def run(self, key: str) -> None:
        snapshot = ("ws", ("r1", "r2"))                       # plain data only

        def leader_fn():
            resp = gl.nondet.exec_prompt("evaluate " + json.dumps(snapshot), response_format="json")
            return {"v": PROMPT_VERSION, "findings": canonicalize(resp, snapshot)}

        def validator_fn(res) -> bool:
            if not isinstance(res, gl.vm.Return):
                return False
            try:
                own = {"v": PROMPT_VERSION, "findings": canonicalize(
                    gl.nondet.exec_prompt("evaluate " + json.dumps(snapshot), response_format="json"), snapshot)}
            except EvaluationError:
                return False
            return own == res.calldata

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        self.out[key] = json.dumps(result, sort_keys=True)

    @gl.public.view
    def get_out(self, key: str) -> str:
        return self.out[key]
