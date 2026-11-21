# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import genlayer as gl
from genlayer.types import *


class Probe(gl.contract.Contract):
    counter: u32
    names: gl.storage.TreeMap[str, u32]

    def __init__(self):
        pass

    @gl.public.view
    def get_counter(self) -> int:
        return self.counter

    @gl.public.write
    def bump(self) -> None:
        self.counter += 1
