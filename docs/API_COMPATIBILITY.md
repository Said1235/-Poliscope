# POLISCOPE — API Compatibility Report

Baseline: runner `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng`
(std lib `kzr02ndm…`, GenVM manager bundle `v0.6.0-rc3`), `genvm-linter 0.11.1-rc.2`,
`genlayer-test 0.30.0rc2`. Verified 2026-11-17.

Status legend: **OK** = signature read in installed SDK source and exercised by a probe;
**SRC** = signature read in source, not yet exercised; **N/A** = does not exist in this
generation; **UNV** = unverified.

## Symbols named in the Directive (§4.5)

| Symbol | Status | Verified signature / behavior |
|---|---|---|
| `gl.vm.run_nondet` | **OK** | `(leader_fn, validator_fn, /, *, custom_runners=None, catch_vm_error=False) -> T`. Generic; validator un-sandboxed; validator exception ⇒ Disagree. Probe passes. |
| `gl.vm.run_nondet_default` | SRC | Sandboxed validator (`allow_write_storage=True`); error comparators. **Not used** (see RESEARCH D-04). |
| `gl.vm.run_nondet_unsafe` | **N/A** | Does not exist. Still shown on the live Equivalence Principle page (stale). |
| `gl.vm.Return` | **OK** | dataclass, field `.calldata`. Used with `isinstance` in validator. |
| `gl.vm.UserError` | SRC | `Exception`; `__init__(data: Decoded)`; attribute **`.data`** (not `.message`); equality by `.data`; docstring warns messages are strictly compared by default. |
| `gl.vm.VMError` | SRC | dataclass with `.message` (plus `.detail`, `.public_code` in reference). |
| `gl.vm.Result` | SRC | `Return[T] \| VMError \| UserError`. |
| `gl.vm.unpack_result` | SRC | raises `UserError` for `UserError`/`VMError`; `TypeError` if not a `Result`. |
| `gl.nondet.exec_prompt` | **OK** | `(prompt: str, *, response_format='text'\|'json', images=None)`; `'json'` ⇒ parsed `JSONValue`; empty prompt ⇒ `ValueError`; **no temperature/seed arg**. |
| `gl.storage.copy_to_memory` | **OK** | `(val: T) -> T`; deep copy of a storage-enabled instance; `TypeError` otherwise. Not in `__all__` but accessible. |
| `gl.storage.TreeMap` | **OK** | `TreeMap[K, V]`, `K` needs `<`; `get`, `get_or_insert_default`, `items`, `keys`, `values`, `__contains__`, `__len__`, … |
| `gl.storage.DynArray` | **OK** | `append`, `append_new_get`, `__len__`, `__iter__`, `__getitem__`, … |
| `gl.storage.allow` | **OK** | Sets allow flag. **Linter quirk E014** → use alias `allow_storage = gl.storage.allow` (RESEARCH D-03a). |
| `gl.Keccak256` | **OK** | `Keccak256(initial_input: Buffer \| None = None)`; `.update`, `.digest()`, `.hexdigest()`; EVM Keccak-256 (vector matched). Pure Python. |
| `gl.public.view` / `gl.public.write` | **OK** | Decorators; undecorated ⇒ private; `write` has `.payable`/`.min_gas(...)` (unused). |
| `gl.message.sender_address` | SRC | `Address`. (`sender_account` is legacy.) |
| `gl.calldata` | SRC | `encode`, `decode`, `to_str`; `Decoded = None\|int\|Address\|bool\|str\|bytes\|list\|dict[str,…]` — **no float/tuple**. |
| Constructor behavior | **OK** | `def __init__(self): pass` ⇒ `ctor_params: 0` in schema. |
| Persistent dataclass requirements | **OK** | `@allow_storage` + `@dataclass`; fields typed with storage types; `dict`/`list` rejected by builder. |
| `gl.contract.Contract` | **OK** | Exactly one subclass per module. |

## Legacy names that must NOT appear in the contract

`from genlayer import *`, `gl.Contract`, `@allow_storage` imported from `genlayer`,
`gl.message_raw`, `gl.message.sender_account`, `gl.UserError` (top level),
`gl.vm.run_nondet_unsafe`, `UserError.message`, `genlayer.gl.*`, `genlayer.py.*`.

A static test (`tests/direct/test_api_compat.py`, Phase 8) will grep the final contract for each.

## Tool compatibility matrix

| Tool | Version | Loads `5jycge4q…` | Notes |
|---|---|---|---|
| `genvm-linter` (PyPI) | 0.11.0 | ✗ | `E101 No module named 'genlayer.py'` |
| `genvm-linter` (GitHub main) | 0.11.1-rc.2 | ✓ | `E014` false positive (alias workaround) |
| `genlayer-test` (PyPI stable) | 0.29.2 | not tested | targets legacy generation |
| `genlayer-test` | 0.30.0rc2 | ✓ | `mock_llm` JSON bug (conftest workaround); needs `cloudpickle` |
| `gltest` integration / StudioNet | — | **UNV** | network unreachable from sandbox |

## Update 2026-11-18 — second runner verified

`py-genlayer:kzybg95x1gn21dw72m7hyg0maaap04n4nx55j9yt6fkdqxtz6bz0` (bundle `v0.6.0-rc15`, SDK reference `main`) passes lint, validate and 6/6
direct probe tests (`GENVM_VERSION=v0.6.0-rc15`). The public symbols in the table above are unchanged between it and `5jycge4q…`
(RESEARCH D-19). The baseline decision (DEC-01 vs DEC-01a) is pending owner approval; the matrix above applies to both.
Signatures must be re-read against the approved runner's std lib immediately before Phase 7.

## Update 2026-11-19 — the deployed generation is LEGACY (`1jb45…`)

The tables above document the **new** generation (archived variant). The deployed contract uses the legacy names below, each read in the legacy SDK
source (std `11rhn002…`) and exercised in a probe or in the direct-test suite (314 tests at port time; 328 in the final audit):

| Symbol (legacy) | Status | Verified behavior |
|---|---|---|
| `from genlayer import *` | **OK** | exports `gl, Address, allow_storage, DynArray, Keccak256, TreeMap, u8…u256, i8…i256, bigint` |
| `gl.Contract` | **OK** | exactly one subclass per module |
| `gl.vm.run_nondet_unsafe(leader, validator)` | **OK** | generic; validator un-sandboxed; validator error ⇒ Disagree; returns the value (eager via `@_lazy_api`) |
| `gl.vm.run_nondet` | **NOT USED** | **sandboxed** in this generation (opposite of the new one); forbidden by a static test |
| `gl.vm.Return` (`.calldata`), `gl.vm.UserError` (`.message`), `gl.vm.VMError` (`.message`) | **OK** | `UserError.message` is compared strictly by default |
| `gl.nondet.exec_prompt(prompt, response_format="json")` | **OK** | returns `dict`; `gl.nondet.NondetException` exists |
| `Keccak256(data).hexdigest()` | **OK** | `Keccak256(b"abc")` = `4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45` |
| `gl.storage.copy_to_memory` | **OK** | works on dataclass records with `Address`, nested `DynArray` |
| `gl.message.sender_address` | **OK** | `Address`; `.as_bytes`, `.as_hex` available |
| `@allow_storage @dataclass`, `TreeMap`, `DynArray` | **OK** | no E014 false positive (name is literally `allow_storage`) |
| `list[dict[str, typing.Any]]` parameter, `dict[str, typing.Any]` return | **OK** | schema: `[{"$rep":{"$dict":"any"}}]` / `{"$dict":"any"}` |
| `calldata.Decoded` | **OK** | `None\|int\|str\|bytes\|list\|dict[str,…]` — no `bool`, no `Address` |
