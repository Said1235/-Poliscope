"""Independent reference implementation of the POLISCOPE canonical encoding (spec: DATA_MODEL §3).

Used to (a) publish golden vectors in the docs and (b) later cross-check the contract.
Keccak256 comes from the SDK source (genlayer/types/keccak.py), which was validated
against the EVM Keccak-256 vector keccak256("") = c5d246...a470.
"""
import struct

def enc(x):
    if isinstance(x, bool):
        raise TypeError("bool not encodable")
    if isinstance(x, str):
        b = x.encode("utf-8")
        return b"S" + struct.pack(">I", len(b)) + b
    if isinstance(x, int):
        if not (0 <= x < 2**64):
            raise ValueError("uint out of range")
        return b"U" + struct.pack(">I", 8) + struct.pack(">Q", x)
    if isinstance(x, (bytes, bytearray)):
        return b"B" + struct.pack(">I", len(x)) + bytes(x)
    if isinstance(x, (list, tuple)):
        return b"L" + struct.pack(">I", len(x)) + b"".join(enc(e) for e in x)
    raise TypeError(f"unsupported type {type(x)}")

def H(keccak256, domain, *fields):
    return keccak256(enc(domain) + b"".join(enc(f) for f in fields)).hexdigest()
