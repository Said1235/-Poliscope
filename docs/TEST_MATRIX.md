# POLISCOPE — Test Matrix and Execution Results

Executed 2026-11-20 (final audit pass). Everything below was actually run; nothing is extrapolated.

## 1. Environment (exact) — LEGACY generation (deployed)

| Item | Value |
|---|---|
| Contract | `contracts/poliscope.py`, 1143 lines, **sha256 `28bf8e7eb0412fe2e3724d0f043d0a4e242a5e2d2b6c376420970fcd8811f31a`** |
| Header | `# v0.2.16` / `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }` |
| Linter | `genvm-linter 0.11.1-rc.2` (GitHub `main`) |
| Test framework | `genlayer-test==0.29.2` (own venv), `pytest 9.2.0`, `cloudpickle 3.1.3`, Python 3.12.3; GenVM bundle `v0.3.0-rc7` |
| Flags | `direct_vm.check_pickling = True`, `direct_vm.strict_mocks = True` (autouse fixture) |
| Same-file chain (playbook §5.4) | the SAME file (`sha256` above) was linted, schema-extracted, tested (328) and mutation-tested, and is the file delivered |

## 2. Lint and schema (what the Studio needs to load)

```text
$ genvm-lint check contracts/poliscope.py --json
{"ok":true,"lint":{"ok":true,"passed":3},"validate":{"ok":true,"contract":"Poliscope","methods":9,"view_methods":5,"write_methods":4,"ctor_params":0,
  "warnings":[{"code":"I200","msg":"py-genlayer: a newer runner is available (kzybg95x…)"}]}}      # informational only; we intentionally stay on 1jb45

$ genvm-lint schema contracts/poliscope.py --json      # the reflection the node performs
ctor: params [] ; methods: audit_proposal(string,string) create_workspace(string,string) publish_policy(string,int,[dict]) register_proposal(string,int,string,string,string)
      get_audit(string) get_policy_rule(string,int,int) get_policy_version(string,int) get_proposal(string) get_workspace(string)   # views return dict
```

## 3. Direct-mode suite

```text
$ python -m pytest tests/direct -q          # in the legacy venv (genlayer-test==0.29.2)
328 passed, 0 failed, 0 skipped, 54 warnings
```

The warnings are `RuntimeWarning: LLM mock never matched` from `strict_mocks`. They are **expected**: in consensus tests the validator
rejects a fabricated leader report *before* spending its LLM call (fail-fast), so the prepared mock is never needed.

| File | Tests | Covers |
|---|---:|---|
| `test_workspace_policy.py` | 52 | workspace creation/IDs, administrator, duplicates, policy publication, compare-and-set versions, immutability, 24 invalid-policy cases, cross-workspace isolation, float rejection at calldata boundary |
| `test_proposals_commitments.py` | 59 | EVM Keccak vector, **golden vectors from DATA_MODEL**, encoding ambiguity, registration, duplicates, 21 hostile code points, empty/whitespace, size/segment limits, NFC vs NFD, segmenter parity vs independent oracle, **lossless reconstruction from segments + whitespace gaps (3,000 fuzz cases)** |
| `test_audit.py` | 71 | happy path with **every derived field recomputed by the independent oracle**, 10 verdict combinations, 38 invalid-LLM-output cases (fail closed + byte-identical state), retry, source mismatch, bound policy version, authorization matrix, duplicate audit, hard-cut regression, storage-tamper detection, **audit-time byte length (A-1)**, **returned IDs (A-2)**, **oversized output guards (A-3)**, **NOT_APPLICABLE without scope (A-4)** |
| `test_consensus.py` | 68 | **C01–C20** through the real `validator_fn` via `run_validator()`; 10 binding fields; 12 malformed leader results; smuggled derived fields; documented residual risk R-01; **unclassified validator exception never `True`**; **1,000,000-element leader list rejected in < 1 s**; **leader claiming NOT_APPLICABLE for an unscoped rule disagrees** |
| `test_security.py` | 25 | 11 injections (EN/ES, fake roles, delimiter forgery, JSON/markdown breakout) with pinned trusted-prompt fingerprints; obedient-model rejection; policy-text injection; title never sent; bilingual/mixed/Greek/CJK; max-size audit |
| `test_identity_storage.py` | 13 | many proposals per wallet, concurrent audit **race simulated inside the LLM call**, old audit unchanged, cross-workspace isolation, client-computable IDs, lazy-allocation proof, commitment sensitivity to every field |
| `test_api_compat.py` | 40 | pinned two-line header, **no names from the other SDK generation** (`import genlayer as gl`, `gl.contract.Contract`, `gl.storage.*`, `run_nondet(` …), no nondeterminism sources, one LLM call site, **AST proof closures never touch `self`/storage**, ctor, 4 maps, exact public surface, no swallowed exceptions |
| **Total** | **328** | |

## 3a. Mandatory consensus matrix status (Directive §41)

C01 ✔ · C02 ✔ · C03 ✔ · C04 ✔ · C05 ✔ · C06 ✔ · C07 ✔ · C08 ✔ · C09 ✔ · C10 ✔ · C11 ✔ · C12 ✔ · C13 ✔ · C14 ✔ · C15 ✔ · C16 ✔ · C17 ✔ · C18 ✔ · C19 ✔ · C20 ✔
(**direct-mode vote logic only — not network consensus**).

## 4. Mutation testing (does the suite have teeth?)

`tools/mutation_test.py` injects one deliberate defect at a time into a copy of the repository (30 mutants) and runs the suite with `-x`.

| Result | Count | Mutants |
|---|---:|---|
| **Killed** | **28** | validator always `True` (M01) · no independent re-evaluation (M02) · bindings skipped (M03) · source commitment skipped (M04) · **latest** policy used (M05) · post-consensus duplicate re-check (M07) · bool accepted as evidence (M08) · citable check (M09) · publish auth (M10) · audit auth (M11) · evidence unsorted (M12) · VIOLATED not dominant (M13) · report commitment omits evidence (M14) · policy commitment re-check (M15) · leader error accepted (M16) · zero-width chars allowed (M17) · version CAS (M18) · status/reason table (M19) · cardinality (M20) · bool/int binding confusion (M22) · title leaked to LLM (M23) · wrong quote span (M24) · coverage check (M25) · hard-cut trim (M26) · **audit-time byte length (M27, finding A-1)** · **oversized-list guard, canonical validation (M28, A-3)** · **oversized-list guard, LLM normalization (M29, A-3)** · **NOT_APPLICABLE without scope (M30, A-4)** |
| Survived — **equivalent by design** | 2 | **M06** pre-phase `audit_id` duplicate check (redundant with the `AUDITED` state check; saves LLM cost only) · **M21** element-ID membership/order inside `_validate_canonical` (redundant with `_normalize_llm` and exact equality in V6) |

How the final numbers were obtained (honest log): the full run covered M01–M27 (25 killed, 2 survived); the process then died, so M28–M30 were run separately.
M28 first **survived** because its test measured time with a loose threshold; it was replaced by a deterministic test (a profile hook proves the O(n) scans are never called), after which M28 was killed.
The tool initially contained only 29 mutants because a silent string replacement failed; M30 was added with an assertion and executed (killed).
Earlier survivors that exposed real test gaps (M07, M15, M26, M28) were each closed with a new test and re-killed.

## 5. Findings made while testing (contract was **not** weakened to pass)

| # | Finding | Resolution |
|---|---|---|
| T-0 | **Wrong generation delivered first** (owner's Studio: "Could not load contract schema"). The new-generation build passed local lint/tests because they validated against the runner the file itself declared | Ported to the legacy runner; static test now forbids other-generation names; RESEARCH §0b |
| T-1 | `float` is rejected by calldata encoding in direct mode (`not calldata encodable`), not by contract code; `bool` **is** encodable and still needs the explicit `type() is int` check | Test split; docs corrected (RESEARCH D-16, REVIEW F-5) |
| T-2 | **Lazy slot allocation:** first read of an *empty* container (empty `DynArray`, empty `TreeMap`) allocates a slot, so the raw storage image grows even when a call fails and writes nothing | Proven layout-only in `test_first_read_of_empty_containers_changes_layout_not_logical_data` (all decoded records identical; second failure is byte-idempotent). Byte-identity assertions are made on a warmed state. KL-T7 |
| T-3 | Injection fixtures change segmentation, so fixed evidence IDs became invalid | Tests compute citable IDs from the oracle |
| T-4 | Two of my own tests initially contained no-op/dead code (`… or True`, unused line) | Rewritten to assert real behavior |

## 6. NOT executed — BLOCKED / UNMEASURED (reported as such, DEC-01/AC-07)

| Area | Status | Reason |
|---|---|---|
| Deployment to StudioNet | **BLOCKED** | network unreachable from sandbox. **Nothing was deployed by me.** The legacy runner is the owner's Studio's runner (their evidence), but a successful load there is not yet observed. |
| `gltest tests/integration/` | **BLOCKED / not written** | needs a reachable network; `tests/integration/` is empty by design |
| Real leader-validator consensus, validator-exception handling, tx ordering, rollback semantics | **BLOCKED** | same |
| Liveness (agreement rate of strict equality across real LLMs) | **UNMEASURED** | needs real network + LLM providers; protocol LIV-* in CONSENSUS_DESIGN §13 |
| In-GenVM cost of Keccak/segmentation/serialization; real limit values | **UNMEASURED** | direct mode runs native CPython, not WASM (KL-01) |
| Real LLM behavior vs the trusted prompt (does it follow the decision procedure?) | **UNMEASURED** | all LLM answers in tests are mocks |
| Pre-ticked Directive box "deployed in StudioNet" | treated as **unchecked** | no receipt exists |
