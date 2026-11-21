# POLISCOPE — Research and Compatibility (Phase 2)

Date of verification: 2026-11-17.
Rule applied: where documentation and SDK disagree, the **installed SDK source and
tooling output decide** (Directive §5). Every claim below is tagged:

- **[SRC]** read directly in the installed SDK source (std lib `py-lib-genlayer-std:kzr02ndm…`)
- **[RUN]** reproduced by running a command; output quoted
- **[DOC]** stated by an official page (URL given)
- **[UNVERIFIED]** could not be confirmed in this environment

---

## 0. Executive summary of the compatibility situation

Three SDK generations are visible at once. Their runner hashes are **not interchangeable**.

| Runner hash (`py-genlayer:`) | Std lib | Layout / syntax | Where it appears | Verified here |
|---|---|---|---|---|
| `1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` | `11rhn…` | **Legacy** (`genlayer.gl.*`, `genlayer.py.*`) | Boilerplate, official `write-contract` skill, stable SDK "Using Runners" page | [RUN] rejects new syntax: `No module named 'genlayer.types'` |
| `1zr6nqk597d97kg0dyxg0shhrykx5v02zjgnyrajapy4wlqvfvwh` | `10pqy…` | New layout (v0.3.0-rc7) | GenVM `v0.3.0-rc7` bundle | [RUN] cannot be linted with any available linter (loader/bundle mismatch) |
| `5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` | `kzr02ndm…` | **New layout** (`import genlayer as gl`) | GenVM manager `v0.6.0-rc3` bundle | **[RUN] lint + validate OK; direct tests OK** |
| `kzybg95x1gn21dw72m7hyg0maaap04n4nx55j9yt6fkdqxtz6bz0` | `0v3kzt…` | New layout, SDK `v0.4.0-rc1` | `sdk.genlayer.com/main` API reference; GenVM manager `v0.6.0-rc15` bundle | **[RUN] lint + validate OK; 6/6 direct probe tests OK** (see §0a; originally recorded UNVERIFIED because only rc3 was cached) |


## 0b. Update 2026-11-19 — D-12 RESOLVED by owner evidence; baseline is the LEGACY runner

**Evidence (from the owner, not from this sandbox):** the first deliverable (new-generation syntax, runner `kzybg95x…`) failed in the owner's
Studio with *"Could not load contract schema"*; the owner's reference example for that Studio is the legacy form
(`# v0.2.16`, `py-genlayer:1jb45aa8…`, `from genlayer import *`, `class X(gl.Contract)`). This is exactly the failure mode described by
the project playbook §3 (runner/generation mismatch; local `genvm-lint` passed because it validated against the runner declared in the file).
**Root cause: my choice of generation, not the contract design.** I had flagged the Studio's runner as UNVERIFIED (D-12) and then applied
DEC-01a (switch to `kzybg95x…`) provisionally without confirmation; that was the wrong call for this Studio.

Consequences (all executed 2026-11-19):
1. **DEC-01a is REVERSED.** The deployed baseline is `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (legacy generation, std lib `11rhn…`, CPython 3.13 runner).
2. The contract was **ported** (not redesigned): dialect only. The new-generation build is archived at `variants/new_generation_UNSUPPORTED/poliscope_v04.py`
   (307 tests passed on it with `genlayer-test 0.30.0rc2`) and is **not maintained**; there is exactly one supported contract.
3. Local verification on the legacy runner: `genvm-lint check` → `ok:true`; `genvm-lint schema` → all 9 methods, constructor with 0 params, parameter types
   `string`, `int`, `[{"$rep":{"$dict":"any"}}]`; 314 direct tests passed with `genlayer-test==0.29.2` and 24/26 mutants were killed **at port time** (final audit numbers: 328 tests, 28/30 — see TEST_MATRIX).
4. This is **still local evidence**: a successful load/deploy in the owner's Studio has not been observed by me (StudioNet unreachable from the sandbox).

### Dialect differences actually applied (legacy SDK source read: std `11rhn002…`, `genlayer/__init__.py`, `gl/vm.py`, `gl/nondet`, `py/keccak.py`, `py/calldata.py`)

| Concept | New generation (archived) | **Legacy (deployed)** |
|---|---|---|
| Header | `# { "Depends": "py-genlayer:kzybg95x…" }` | `# v0.2.16` then `# { "Depends": "py-genlayer:1jb45aa8…" }` |
| Imports | `import genlayer as gl` + `from genlayer.types import *` + `allow_storage = gl.storage.allow` alias | `from genlayer import *` (provides `gl`, `allow_storage`, `TreeMap`, `DynArray`, `Keccak256`, `u32`, `Address`) — **no alias needed**, so the linter E014 false positive does not occur |
| Contract base | `gl.contract.Contract` | `gl.Contract` |
| Storage types | `gl.storage.TreeMap` / `gl.storage.DynArray` | `TreeMap` / `DynArray` |
| Keccak | `gl.Keccak256(data)` | `Keccak256(data)` (`KeccakHash.preset(1088,512,256)`); vector `Keccak256(b"abc")` = `4e03657a…` ✔ |
| Generic consensus API | `gl.vm.run_nondet(leader, validator)` | **`gl.vm.run_nondet_unsafe(leader, validator)`** (validator un-sandboxed; validator error ⇒ Disagree) |
| Sandboxed API (NOT used) | `run_nondet_default` | `gl.vm.run_nondet` — **same name, opposite meaning**; forbidden by a static test |
| `UserError` payload | `.data` | `.message` |
| `calldata.Decoded` | `None\|int\|Address\|bool\|str\|bytes\|list\|dict` | `None\|int\|str\|bytes\|list\|dict` — **no `bool`, no `Address`** (leader report and views contain none) |
| `exec_prompt(…, response_format="json")` | returns parsed value from raw text | returns `dict` |
| `genlayer-test` | 0.30.0rc2 (+ conftest mock workaround) | **0.29.2**, no workaround (its mock layer auto-parses str→dict, which this SDK expects) |
| Test bundle | GenVM manager `v0.6.0-rc15` | `v0.3.0-rc7` bundle (legacy runner `1jb45…` inside) |
| Unchanged | `gl.storage.copy_to_memory`, `gl.message.sender_address`, `gl.nondet.exec_prompt`, `gl.nondet.NondetException`, `gl.vm.Return`, `gl.public.view/write`, `Address.as_bytes/as_hex`, `get_or_insert_default`, `append_new_get`, `in` on `TreeMap` | same |

### Legacy-toolchain facts found
- `genlayer-test 0.29.2` downloads `genvm-universal.tar.xz` from GitHub; in this sandbox that returned 404. Workaround: link the bundle the linter already cached: `ln -s ~/.cache/genvm-linter/genvm-universal-v0.3.0-rc7.tar.xz ~/.cache/gltest-direct/` (KL-T8). Not needed on a normal network.
- The legacy mock layer returns a **non-JSON** mock as the raw `str`; the contract rejects it as `BAD_SHAPE` (a real host raises `NondetException`, which the contract maps to `[TRANSIENT] LLM_UNAVAILABLE`). Both fail closed.
- `genlayer-test 0.30.0rc2` has a regression loading legacy contracts (playbook §5.3); do not use it for this build.

---

## 0a. Update 2026-11-18 — runner baseline evidence changed (supersedes the premise of DEC-01)

While preparing Phase 4 the linter auto-downloaded GenVM manager bundle **`v0.6.0-rc15`** (newer than `v0.6.0-rc3`).
Findings **[RUN]**:

| Runner | Bundle(s) | Lint+validate (default tooling, 0.11.1-rc.2) | Direct tests (`genlayer-test 0.30.0rc2`) |
|---|---|---|---|
| `kzybg95x…` | rc15 (newest) | ✔ `ok:true`, `ctor_params:0` | ✔ 6/6 with `GENVM_VERSION=v0.6.0-rc15` |
| `babwp9t3…` | rc15 | ✔ but warning `I200: a newer runner is available (kzybg95x…)` | not run |
| `5jycge4q…` | rc3 only | ✘ `E101 runner … not found` with the default (newest) bundle | ✔ 3/3 (rc3 cache) |

Consequences:
1. The hash printed by the SDK reference `main` (`kzybg95x…`) **is real and verifiable** — D-12's earlier "no published bundle" was true only of the rc3 cache I had.
2. `5jycge4q…` is **superseded**; keeping it as baseline would require pinning the older bundle in every tool.
3. **Proposal DEC-01a** (owner approval pending): develop on `kzybg95x…`. This still does not assume StudioNet serves it (D-12).
4. Tool reproducibility is time-dependent (D-18).

**Working baseline chosen for development (per DEC-01; see §0a for the pending proposal DEC-01a):** `py-genlayer:5jycge4q…` (the only
current-generation runner that passes lint, schema validation and direct tests here).

**Open decision (blocking for deployment, not for development):** which runner the
target StudioNet actually serves. It could not be determined from this sandbox (see §3, D-12).

---

## 1. Decisions

### D-01 — Import structure and contract declaration
- **Requirement:** use the current SDK import pattern (Directive §15).
- **Source:** `https://sdk.genlayer.com/main/_static/ai/api.txt` → "Migration Guide / Import Pattern".
- **API:** `import genlayer as gl`; `from genlayer.types import *`; `class X(gl.contract.Contract)`.
- **Verified:** [SRC] `genlayer/__init__.py` docstring states this pattern. [RUN] probe contract with this syntax: `{"ok":true,… "ctor_params":0,"view_methods":1,"write_methods":1}`.
- **Runtime compat:** runner `5jycge4q…`. Legacy `from genlayer import *` / `gl.Contract` is **not** valid there.
- **Design consequence:** no star-import of `genlayer`; the contract uses `gl.*` namespaces only.
- **Test:** `docs/evidence/probes/probe_minimal.py` + lint gate.

### D-02 — Runner pinning
- **Requirement:** pinned `Depends` header, no `test`/`latest` aliases (official `write-contract` skill; Directive §7).
- **Source:** `…/api.txt` → "Available Runners"; skill file in `genlayerlabs/skills`.
- **Verified:** [RUN] table in §0. The official skill text itself still hard-codes the legacy hash `1jb45…`, i.e. **the skill is stale relative to the SDK reference**.
- **Design consequence:** header is `# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }` until D-12 is resolved. Single-file runner (`py-genlayer`), no multi-file, no embeddings runner.
- **Test:** lint gate; `grep` assertion that the header never contains `:test`, `:latest` or an unversioned name.

### D-03 — Linter and test-tool versions (tooling is generation-sensitive)
- **Verified [RUN]:**
  - `genvm-linter 0.11.0` (PyPI) hard-codes `from genlayer.py.get_schema import get_schema` → `E101 Failed to load SDK: No module named 'genlayer.py'`. Cannot validate this generation.
  - `genvm-linter 0.11.1-rc.2` (GitHub `main`) falls back correctly: `_import_get_schema()` tries `genlayer._internal.get_schema` first.
  - `genlayer-test 0.29.2` (PyPI stable, what the boilerplate pins as `@v0.29`) targets the legacy generation. `genlayer-test 0.30.0rc2` loads the current one.
- **Design consequence:** `requirements.txt` pins `genlayer-test==0.30.0rc2` and linter from `main`.
- **Test:** `pytest tests/direct` and `genvm-lint check` on the final file.

### D-03a — Linter false positive `E014` (documented, not hidden)
- **Verified [RUN]:** `@gl.storage.allow` (correct) on a dataclass used as a `TreeMap` value → `lint.ok:false`, `E014 "Class 'Policy' used in storage needs @allow_storage decorator"`, while `validate.ok:true`. The rule matches the literal text `allow_storage`.
- **Mitigation [RUN]:** `allow_storage = gl.storage.allow` (same object) then `@allow_storage` → `{"ok":true,…}`.
- **Design consequence:** the contract uses the alias, with a comment explaining why. No rule is suppressed.

### D-04 — Custom consensus API and its semantics
- **Requirement:** custom leader/validator with the actual leader result (Directive §18–19).
- **Sources:** SDK reference ("Non-deterministic Execution", "Migration Guide v0.2.x→v0.3.0"); `https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle`.
- **Signatures [SRC `vm/__init__.py`]:**
  - `run_nondet(leader_fn: () -> T, validator_fn: (Result) -> bool, /, *, custom_runners=None, catch_vm_error=False) -> T`
  - `run_nondet_default(leader_fn, validator_fn, /, *, compare_user_errors, compare_vm_errors, custom_runners, catch_vm_error) -> T`
  - `type Result[T] = Return[T] | VMError | UserError`; `Return.calldata`.
- **Verified behavior [SRC]:**
  - `run_nondet`: validator runs un-sandboxed; per the reference, an unhandled validator exception → **Disagree**. Returns the leader's value; leader `UserError` is re-raised.
  - `run_nondet_default`: validator runs in `spawn_sandbox(..., allow_write_storage=True, allow_send_messages=True)`. If leader and validator **both** end in `UserError`, agreement is decided by `compare_user_errors` (default lambda). If their result *kinds* differ → `TypeError`.
- **⚠ Documentation discrepancy [DOC vs SRC]:** the live equivalence-principle page still uses the **old names** (`run_nondet_unsafe` = generic, `run_nondet` = sandboxed, `e.message`, `genlayer.gl._internal.gl_call`). The SDK reference and installed source use the **new** names. `run_nondet_unsafe` does not exist in the current SDK.
- **Design consequence:** use `gl.vm.run_nondet` (generic). Rationale: (a) the validator must never run with `allow_write_storage=True`; (b) an agreed-upon *error* from `run_nondet_default` is an acceptance path that must be reasoned about separately; (c) fail-closed is simplest when any validator exception means Disagree. Leader `UserError`/`VMError` are handled explicitly inside `validator_fn` (see CONSENSUS_DESIGN.md, Phase 4).
- **Test:** direct-mode `run_validator()` matrix C01–C20.

### D-05 — Leader result shape and `calldata` limits
- **Verified [SRC `calldata/__init__.py`]:** `Decoded = None | int | Address | bool | str | bytes | list[Decoded] | dict[str, Decoded]`. **No `float`, no tuple, no set.**
- **Design consequence:** the leader returns only `dict[str, …]` / `list` / `str` / `int` / `bool`. No float anywhere (also required by Directive §21). Tuples become lists.
- **Test:** pickling/serialization assertions with `check_pickling = True`.

### D-06 — Structured LLM output
- **Signature [SRC `nondet/__init__.py`]:** `exec_prompt(prompt: str, *, response_format: 'text'|'json', images=None) -> str | JSONValue`. Empty prompt → `ValueError`. With `'json'`, the SDK runs `json.loads` on the text itself (`_decode_nondet_json`) and raises `NondetException('invalid JSON: …')` on failure.
- **Design consequence:** use `response_format="json"`; **no** regex extraction and **no** repair (Directive §30). Any `NondetException` propagates → leader failure → no persistence. There is **no temperature/seed parameter** in this signature, so exact-match consensus cannot rely on sampling determinism.
- **Test:** malformed-JSON, non-dict, extra/missing-key leader outputs.

### D-07 — Storage types and the dataclass requirement
- **Sources:** `…/api.txt` (storage section; Migration Guide "Storage"); docs `…/features/storage`, `…/types/dataclasses`.
- **Verified [SRC `storage/_internal/generate.py`]:**
  - `allow` just sets an `ALLOW_STORAGE_ATTR` flag. Without it the builder raises.
  - `dict` → error `use TreeMap instead of a dict`; `list` → `use DynArray instead of a list`.
  - Supported scalars: `bool`, sized ints (`u8…u256`), `bigint`, `str`, `bytes`, `Address`; (`float` has a descriptor, but is **excluded by policy** here).
  - `TreeMap[K, V]`: `K` must support `<` and be storage-allowed.
- **[RUN]:** `@allow_storage @dataclass class Policy: version: u32; rules: DynArray[Rule]` inside `TreeMap[str, Policy]` → validates and runs.
- **Design consequence:** all records are `@allow_storage @dataclass`; collections are `TreeMap`/`DynArray`; counts are `u32`; new fields are only ever **appended** to a dataclass.

### D-08 — Storage → memory boundary
- **Directive §16:** nondeterministic blocks must not touch storage.
- **Verified [SRC `storage/__init__.py`]:** `copy_to_memory[T](val: T) -> T` "deep-copies a storage-enabled class instance into a new in-memory instance"; raises `TypeError` if `val` has no `__type_desc__`. It is **not** in `storage.__all__` but is accessible as `gl.storage.copy_to_memory` ([RUN] works).
- **[SRC]** `run_nondet` serializes the leader with `cloudpickle.dumps`. A closure that captures `self` or a storage proxy would be serialized with it.
- **[RUN] probe:** `pol = gl.storage.copy_to_memory(self.policies[key])` → build plain `list[tuple]` → closure captures only that list. With `direct_vm.check_pickling = True`: **2 passed**. Validator accepted identical output and rejected a different one via `direct_vm.run_validator()`.
- **Design consequence:** build an immutable snapshot of plain Python data (`str`, `int`, `tuple`, `list`) before `run_nondet`; leader/validator close over the snapshot only, never `self`.
- **Test:** pickling checks on every audit path; static grep that `leader_fn`/`validator_fn` bodies contain no `self.`.

### D-09 — Keccak-256 commitments
- **Signature [SRC `types/keccak.py`]:** `Keccak256(initial_input: Buffer | None = None) -> KeccakHash`; `.update(Buffer)`, `.digest() -> bytes` (32), `.hexdigest() -> str`.
- **[RUN]:** `Keccak256(b"").hexdigest() == c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` (the EVM Keccak-256 of empty input, **not** NIST SHA3). Incremental `update` equals one-shot.
- **Cost [RUN, native CPython]:** 1 KB ≈ 5 ms, 10 KB ≈ 45 ms, 100 KB ≈ 0.32 s. It is **pure Python** (source from `ctz/keccak`); cost inside GenVM/WASM is **[UNVERIFIED]** and must be measured on a real runtime before the proposal-size limit is fixed (Directive §37 forbids unmeasured limits).
- **Design consequence:** domain-separated, length-prefixed encoding (Phase 4). `hashlib` is not used. Python's `hash()` is not used.

### D-10 — Identity and authorization primitives
- **[SRC `message.py`]:** `gl.message.sender_address: Address`, `origin_address`, `signer_address`. Directive's `sender_address` is correct; the official skill's `gl.message.sender_account` is the legacy name.
- **Design consequence:** administrator checks use `gl.message.sender_address`. Because a DAO contract may be the administrator, the sender (not the origin/signer) is the authority.

### D-11 — Public method model
- **[SRC `…/guides/method_dispatch.txt`]:** undecorated methods are private; `gl.public.view` cannot change state; `gl.public.write` can; neither accepts value unless `.payable`.
- **Design consequence:** no payable methods (V1 holds no funds). Helpers are private (leading underscore, undecorated). Constructor is `def __init__(self): pass` — **[RUN]** `ctor_params: 0`.

### D-12 — Target runner for StudioNet  **[RESOLVED 2026-11-19: legacy `1jb45…`, by owner evidence — see §0b]**
- **Attempted:** `curl https://studio.genlayer.com` and `/api`, `rpc-studio.genlayer.com`, `docs.genlayer.com` from the sandbox → no response (domains are outside the network allow-list).
- **Evidence for each candidate:** stable SDK page documents `1jb45…`; SDK `main` documents `kzybg…`; only `5jycge4q…` is verifiable locally. GenVM public release feed shows `v0.3.0-rc7` as newest GenVM tag; the manager bundle is `v0.6.0-rc3`.
- **Consequence:** per the playbook's rule, if the served runner cannot be confirmed, deliver **both** a current-generation variant and (only if needed) a legacy-generation variant, each linted and tested separately. This decision requires either network access to the target Studio or the user's report of the deploy error text.

### D-13 — Test-tool bug: `mock_llm` with `response_format="json"` (genlayer-test 0.30.0rc2)
- **Symptom [RUN]:** `NondetException: invalid nondeterministic response: JSON result is not text`.
- **Root cause [SRC both sides]:** `gltest/direct/wasi_mock.py::_handle_llm_request` auto-converts a `str` mock into a `dict` (correct for the legacy decoder); the current `genlayer.nondet._decode_nondet_json` requires the raw text and calls `json.loads` itself.
- **Mitigation:** `tests/conftest.py` wraps `_handle_llm_request` to return the mock verbatim (test-only; contract and installed package untouched). **[RUN]** probe tests pass afterwards.
- **Design consequence:** this is a *third-party tooling defect*, documented in KNOWN_LIMITATIONS.md. It must not be mistaken for a contract bug.

### D-14 — Direct mode runs only the leader
- **[DOC]** (official skill text; genlayer-test README): direct mode executes the leader path; the validator is captured.
- **[RUN]:** `direct_vm.run_validator()` executes the captured `validator_fn` under the *current* mocks and returns a bool; `clear_mocks()` then re-registering simulates a disagreeing validator. Mock matching is regex, first match wins (playbook §5.2).
- **Design consequence:** consensus tests call `run_validator()` explicitly, including with fabricated leader results. Direct mode is **not** evidence of real consensus; only StudioNet is (Directive §39).

### D-15 — Consensus outcome on failure
- **[DOC]** (equivalence-principle page): if the majority rejects, leaders rotate; if consensus still fails the transaction becomes **undetermined and does not modify contract state**.
- **Design consequence:** non-persistence on failure is a protocol property, but POLISCOPE additionally guarantees it by performing every write *after* `run_nondet` returns (Directive §12, §38).
- **Limit:** the contract controls each validator's vote, not the protocol quorum (Directive §23). Validator intermediate outputs are not persisted [DOC].

### D-16 — Typed public-method parameters and return values
- **[RUN]** `publish(self, rules: list[dict[str, typing.Any]]) -> None` and `get(...) -> dict[str, typing.Any]` pass lint (`ok:true`) and direct tests. Nested dataclass → `DynArray` → dataclass → `DynArray[str]` persists and reads back.
- **Caveat (corrected 2026-11-18 after running tests):** direct mode DOES calldata-encode arguments, so a `float` is rejected by the framework (`not calldata encodable 1.5: float`) before contract code runs, exactly as on a real network. `bool` IS encodable (`True` arrives as `bool`), so the contract keeps explicit `type(x) is int` checks and validates exact key sets itself (NFR-INP-01). An earlier draft of this document wrongly said direct mode skips type enforcement.
- **Design consequence:** `publish_policy` takes typed `list[dict]` (no JSON-in-a-string, which would allow duplicate keys silently).

### D-17 — Closures calling module-level helpers/constants/exception classes
- **[RUN]** leader/validator closures that call a module-level function, read module-level constants and catch a module-level exception class pickle correctly with `direct_vm.check_pickling = True`; validator returns `True` for identical, `False` for a classified evaluation failure. Passes on both `5jycge4q…` and `kzybg95x…`.
- **Design consequence:** pure helpers live at module level and are shared by leader, validator and post-consensus phases (ARCHITECTURE §2).

### D-18 — Tool bundle auto-selection (reproducibility)
- **[RUN]** `genvm-lint` and `gltest` pick the newest reachable GenVM bundle; with GitHub API 403 they fall back to the newest *cached* one. `gltest` honours `GENVM_VERSION` (read in `gltest/direct/sdk_loader.py`); `genvm-lint check` has no version flag (`--json` only).
- **Design consequence:** record the resolved bundle version in every log; set `GENVM_VERSION` for tests; KL-T4.

### D-19 — SDK surface diff, `5jycge4q…` (std `kzr02ndm…`) vs `kzybg95x…` (std `0v3kzt…`)
- **[SRC]** `nondet/*` and `types/keccak.py` unchanged (so `exec_prompt` and `Keccak256` are identical). `vm`: docstring clarifications; `run_nondet` signature unchanged. `message`: additive. `calldata`: minor typing tweak. `storage`: internal changes, `copy_to_memory` present, `TreeMap` adds mutation guards, `DynArray` adds reordering.
- **Design consequence:** every symbol POLISCOPE uses is unchanged in surface; the design is valid on both. Re-verify signatures against the final runner before Phase 7.

### D-20 — Reference implementations validated during design
- **[RUN]** `docs/evidence/reference_encoding.py` (canonical encoding, golden vectors, ambiguity checks) and `reference_segmenter.py` (20,000-case invariant fuzz; found and fixed a trailing-whitespace defect). They become the independent oracle for contract tests (TST-03).


### D-21 — Lazy slot allocation on first read of an empty container  **[RUN]**
- A failed audit left the raw storage image different (4 slots, root header +4 bytes) although no data was written.
- Root cause (isolated by experiment): the runtime allocates storage for **empty** containers (empty `DynArray` such as a rule with no prohibited conditions, empty `TreeMap`) the first time they are *read*. Pre-reading every container the audit reads ("warming") makes the failed audit byte-identical (60/60).
- Proof it is layout-only: `test_first_read_of_empty_containers_changes_layout_not_logical_data` — every decoded record is identical before/after and a second failure changes nothing.
- Consequence: invariant I-13 is verified as *logical* state preservation always, and byte-identity on a warmed state. Whether the real runtime behaves identically is UNVERIFIED (KL-T7).

### D-22 — Direct-mode facts needed by the test suite  **[SRC/RUN]**
- Fixture accounts (`direct_alice`, …) are raw 20-byte `bytes`; the contract sees them as `Address`. `direct_vm.sender = …` sets the caller.
- `direct_vm.run_validator(leader_result=…, leader_error=…)` runs the *captured* real `validator_fn` under the *current* mocks.
- `direct_vm._storage.snapshot()` returns the raw image used for byte-identity assertions. Contract storage attributes are reachable from the wrapper (`env.c.policy_versions[key]…`), which lets a test corrupt storage deliberately.
- A one-shot hook in the patched LLM handler can run another contract call *inside* the leader's LLM call, simulating an interleaved transaction (race test).

---

## 2. Documentation / reference discrepancies found

| # | Source A | Source B | Resolution |
|---|---|---|---|
| 1 | Equivalence page: `run_nondet_unsafe` generic, `run_nondet` sandboxed | SDK ref + installed source: `run_nondet` generic, `run_nondet_default` sandboxed, no `_unsafe` | Follow SDK source (D-04) |
| 2 | Equivalence page: `e.message`, `genlayer.gl._internal.gl_call` | SDK: `UserError.data`; layout `genlayer._internal` | Follow SDK |
| 3 | Official skill + boilerplate: `from genlayer import *`, `gl.Contract`, `sender_account`, `1jb45…` | SDK `main`: `import genlayer as gl`, `gl.contract.Contract`, `sender_address`, `kzybg…` | Both are real, different generations (§0) |
| 4 | Skill text: runner hash `1jb45…` is "the" hash | `api.txt` "Current hash" differs | Directive §7: refresh at dev time → D-02/D-12 |
| 5 | Boilerplate `requirements.txt`: `genlayer-test@v0.29`, `genvm-linter@main` | New generation needs `genlayer-test 0.30.0rc2` | D-03 |
| 7 | Runner `5jycge4q…` documented as 'only verified' | Later evidence: `kzybg95x…` (SDK ref `main`) verifiable in rc15; `5jycge4q…` superseded | §0a; DEC-01a pending |
| 6 | Directive Part XX checklist has `[x] Contract deployed in StudioNet test environment` pre-checked | Nothing has been deployed | Treated as **unchecked** until a receipt exists |

---

## 3. Items explicitly NOT yet verified

1. Which runner/SDK generation StudioNet serves (D-12).
2. Real GenVM resource cost of Keccak-256, JSON canonicalization and prompt size (D-09).
3. Behavior of two real LLM validators on identical input (liveness of exact matching).
4. `gltest` integration options (`gltest tests/integration -v -s`, network flags) — needs the CLI on a reachable network.
5. The remaining official pages in Directive §4.6–4.15 (non-determinism, calling-llms, crafting-prompts, prompt-injection, error-handling, testing, tooling-setup, typical use cases) were **not yet read in full**; the full-documentation bulk file will be consulted per-decision in Phase 4 rather than assumed.
